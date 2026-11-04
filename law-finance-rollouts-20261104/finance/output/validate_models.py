#!/usr/bin/env python3
"""Independent replication of the four supplied GAUSS moment systems; no GAUSS required.
Usage: python validate_models.py --input-dir /app/input_files --output-dir /work/output
"""
import argparse, hashlib, warnings
from pathlib import Path
import numpy as np
from scipy.optimize import minimize, least_squares
from scipy.stats import chi2
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Pt
warnings.filterwarnings('ignore', category=RuntimeWarning)
TOL=1e-7

def read_data(p):
    port=np.loadtxt(p/'LV_port.txt',comments='@'); fac=np.loadtxt(p/'LV_fac.txt',comments='@')
    ff=np.loadtxt(p/'FF3a.txt',comments='@'); raw=(p/'CPI.txt').read_text().splitlines()
    cpi={(int(a),int(b[1:])):float(c) for line in raw for a,b,c in [line.split()]}
    years=np.arange(1953,2003)
    assert len(port)==len(fac)==50 and np.array_equal(port[:,0],years) and np.array_equal(fac[:,0],years)
    assert len(cpi)==708 and len(ff)==59 and np.array_equal(ff[:,0],np.arange(1952,2011))
    assert np.isfinite(port).all() and np.isfinite(fac).all()
    infl=np.array([cpi[y,12]/cpi[y-1,12]-1 for y in years]); rf=ff[1:51,4]/100
    gross=(1+rf)/(1+infl)
    return years,port[:,1:]/100,fac[:,1:]/100,gross,rf,infl,cpi

def system(model,typ,r,fac,gr):
    n=8; f=fac[:,0 if model in ('CAPM','EZ') else 1]; other=fac[:,1]
    if model=='EZ': z=np.column_stack((f,other)); assets=np.column_stack((r,f)); q=2; names=['Rvwexc','consumption']; df=7
    elif model=='CAPM': z=f[:,None];assets=np.column_stack((r,f));q=1;names=['Rvwexc'];df=8
    elif model=='CCAPM':z=f[:,None];assets=r;q=1;names=['consumption'];df=7
    else:z=f[:,None];assets=r;q=1;names=['consumption'];df=7
    t=len(r); mu=z.mean(axis=0); a=assets.shape[1]
    if model=='EZ' and typ.startswith('sym'):
        def sdf(v,center):
            x=z-v[2:4] if center else z
            return np.sin(v[0])+np.cos(v[0])*(x[:,0]*np.sin(v[1])+x[:,1]*np.cos(v[1]))
        init=np.array([0.,0.]+(list(mu) if typ=='sym_c' else [])); pn=['angle_1','angle_2']+(['mu_'+s for s in names] if typ=='sym_c' else [])
    elif typ.startswith('sym'):
        def sdf(v,center):
            x=z-v[1:2] if center else z
            return np.sin(v[0])+x[:,0]*np.cos(v[0])
        init=np.array([-.785398]+(list(mu) if typ=='sym_c' else []));pn=['angle']+(['mu_'+names[0]] if typ=='sym_c' else [])
    elif model=='GROSS' and typ.startswith('asym'):
        init=np.array([1.,1.]+(list(mu) if typ=='asym_c' else []));pn=['a','b']+(['mu_'+names[0]] if typ=='asym_c' else [])
        def sdf(v,center):return v[0]+(z-v[2:3] if center else z)@v[1:2]
    else:
        init=np.r_[np.ones(q),mu] if typ=='asym_c' else np.ones(q)
        pn=['tau_'+s for s in names]+(['mu_'+s for s in names] if typ=='asym_c' else [])
        def sdf(v,center):return 1-(z-v[q:2*q] if center else z)@v[:q]
    if typ!='reg':
        def h(v):
            m=sdf(v,typ.endswith('_c')); chunks=[assets*m[:,None]]
            if typ.endswith('_c'):chunks.append(z-v[-q:])
            if model=='GROSS':
                # source order: eight excess returns, factor mean (centered only), gross pricing
                chunks.append((gr*m-1)[:,None])
            return np.column_stack(chunks)
    else:
        if model=='CAPM':
            init=np.r_[np.zeros(8),mu];pn=['beta_P'+str(i+1) for i in range(8)]+['mu_Rvwexc']
            def h(v):
                b=v[:8]; resid=r-f[:,None]*b
                return np.column_stack([np.column_stack([resid[:,j],f*resid[:,j]]) for j in range(8)]+[z-v[-1:]])
        elif model=='CCAPM':
            init=np.r_[0.,np.zeros(8),mu];pn=['lambda']+['beta_P'+str(i+1) for i in range(8)]+['mu_consumption']
            def h(v):
                lam=v[0];b=v[1:9];resid=r-(f-v[-1]+lam)[:,None]*b
                return np.column_stack([np.column_stack([resid[:,j],f*resid[:,j]]) for j in range(8)]+[z-v[-1:]])
        elif model=='EZ':
            init=np.r_[0.,np.zeros(16),mu];pn=['lambda_consumption']+[f'beta_P{i+1}_{s}' for i in range(8) for s in names]+['mu_'+s for s in names]
            def h(v):
                b=v[1:17].reshape(8,2);resid=r-f[:,None]*b[:,0]-(other-v[-1]+v[0])[:,None]*b[:,1]
                return np.column_stack([np.column_stack([resid[:,j],z*resid[:,j,None]]) for j in range(8)]+[z-v[-2:]])
        else:
            init=np.r_[0.,np.zeros(9),mu,1.];pn=['lambda']+['beta_'+s for s in [f'P{i+1}' for i in range(8)]+['gross']]+['mu_consumption','vark_gross']
            def h(v):
                b=v[1:10];target=np.column_stack((r,gr-v[-1]));resid=target-(f-v[-2]+v[0])[:,None]*b
                return np.column_stack([np.column_stack([resid[:,j],f*resid[:,j]]) for j in range(9)]+[z-v[-2:-1]])
    return h,init,pn,df

def cov(h):
    u=h-h.mean(axis=0);return u.T@u/len(h)

def objective(v,h,weight=None):
    x=h(v); g=x.mean(axis=0)
    if weight is None:
        s=cov(x)
        try: sol=np.linalg.solve(s,g)
        except np.linalg.LinAlgError: return 1e9
        return max(0.,float(g@sol)) if np.isfinite(sol).all() else 1e9
    return float(g@weight@g)

def diff(fun,v,step=1e-5):
    v=np.asarray(v);return np.column_stack([(fun(v+np.eye(len(v))[j]*step*max(1,abs(v[j])))-fun(v-np.eye(len(v))[j]*step*max(1,abs(v[j]))))/(2*step*max(1,abs(v[j]))) for j in range(len(v))])

def optimize(h,start,w=None,cu=False,multi=False):
    starts=[start]
    if multi:
        rng=np.random.default_rng(202503)
        starts += [start+rng.normal(size=len(start))*0.10 for _ in range(2)]
    choices=[]
    for x in starts:
        if cu:
            sol=minimize(lambda v:objective(v,h),x,method='BFGS',options={'maxiter':250,'gtol':2e-6})
        else:
            # equivalent minimization of mean moments' quadratic norm at fixed weighting matrix
            try: root=np.linalg.cholesky(w).T
            except np.linalg.LinAlgError: root=np.linalg.cholesky(w+np.eye(len(w))*1e-8).T
            sol=least_squares(lambda v:root@h(v).mean(axis=0),x,max_nfev=180,ftol=1e-10,xtol=1e-10,gtol=1e-10)
        choices.append((objective(sol.x,h,None if cu else w),sol))
    choices.sort(key=lambda pair:pair[0]);return choices[0][1], [v for v,_ in choices]

def assess(model,typ,method,h,x,names,df,trace,success,spread):
    H=h(x);S=cov(H);g=H.mean(axis=0);sv=np.linalg.svd(S,compute_uv=False);cond=float(sv[0]/sv[-1]) if sv[-1]>0 else float('inf')
    try: W=np.linalg.inv(S)
    except np.linalg.LinAlgError:W=np.linalg.pinv(S,rcond=1e-12)
    if method=='CU':
        val=objective(x,h); D=diff(lambda v:h(v).mean(axis=0),x)
        # source's CU correction: D*. = D - (1/2) dS(theta)/dtheta W g
        wg=W@g
        ds=np.column_stack([(cov(h(x+np.eye(len(x))[j]*1e-5))-cov(h(x-np.eye(len(x))[j]*1e-5)))@wg/(2e-5) for j in range(len(x))]); D=D-.5*ds
    else:
        val=trace[-1][1]/50;D=diff(lambda v:h(v).mean(axis=0),x)
        # fixed-weight covariance of estimation equations, consistent with GAUSS d' w d
        W=assess.fixed_w
    info=D.T@W@D;rank=np.linalg.matrix_rank(info,tol=np.linalg.svd(info,compute_uv=False)[0]*1e-10)
    try: V=np.linalg.inv(info)/50;se=np.sqrt(np.maximum(0,np.diag(V))) if rank==len(x) else np.full(len(x),np.nan)
    except np.linalg.LinAlgError:se=np.full(len(x),np.nan)
    j=50*val
    return dict(model=model,typ=typ,method=method,x=x,se=se,names=names,df=df,j=j,p=chi2.sf(j,df),cond=cond,rank=rank,m=len(g),success=bool(success),spread=spread,trace=trace,mean_norm=float(np.linalg.norm(g)),smin=float(sv[-1]))

def run_all(r,fac,gr):
    results=[]
    for model in ['CAPM','CCAPM','EZ','GROSS']:
        for typ in (['sym_u','sym_c','asym_u','asym_c','reg'] if model!='GROSS' else ['asym_u','asym_c','reg']):
            h,init,names,df=system(model,typ,r,fac,gr)
            eye=np.eye(h(init).shape[1]);sol,_=optimize(h,init,eye);x0=sol.x
            S=cov(h(x0)); w=np.linalg.pinv(S,rcond=1e-12)
            sol2,_=optimize(h,x0,w);x2=sol2.x
            assess.fixed_w=w
            results.append(assess(model,typ,'2S',h,x2,names,df,[(1,50*objective(x0,h,eye)),(2,50*objective(x2,h,w))],sol2.success,0.))
            # Iterated: re-estimate weight at each previous iterate; retain last actual iterate if no convergence
            x=x2;trace=[(2,50*objective(x2,h,w))];ok=False
            for i in range(3,31):
                w=np.linalg.pinv(cov(h(x)),rcond=1e-12)
                nxt,_=optimize(h,x,w)
                delta=np.linalg.norm(nxt.x-x)/(1+np.linalg.norm(x)); j=50*objective(nxt.x,h,w)
                trace.append((i,j));ok=delta<1e-7 and abs(j-trace[-2][1])<1e-7
                x=nxt.x
                if ok:break
            assess.fixed_w=w
            results.append(assess(model,typ,'ITER',h,x,names,df,trace,ok and nxt.success,delta))
            # CU: multistart near 2S and first-stage; keep minima and show dispersion
            sc,vals=optimize(h,x2,cu=True,multi=True)
            xc=sc.x;tracecu=[('start min',50*min(vals)),('start max',50*max(vals)),('selected',50*objective(xc,h))]
            results.append(assess(model,typ,'CU',h,xc,names,df,tracecu,sc.success,50*(max(vals)-min(vals))))
            print(model,typ,'2S/ITER/CU',*[round(z['j'],4) for z in results[-3:]],'iter',len(trace),'CU status',sc.success,flush=True)
    return results

def sheet(ws,heads,rows):
    ws.append(heads)
    for row in rows:ws.append([float(v) if isinstance(v,(np.floating,)) and np.isfinite(v) else (None if isinstance(v,(float,np.floating)) and not np.isfinite(v) else (v.item() if isinstance(v,np.integer) else v)) for v in row])
    ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
    for cell in ws[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='183759');cell.alignment=Alignment(wrap_text=True)
    for col in ws.columns:
        letter=get_column_letter(col[0].column);ws.column_dimensions[letter].width=min(65,max(14,max(len(str(c.value or '')) for c in list(col)[:200])+2))

def deliver(p,out,data,res):
    years,r,fac,gr,rf,infl,cpi=data
    wb=Workbook();wb.remove(wb.active)
    files=['README.txt','table1.prg','table2.prg','tableA1.prg','tableA2.prg','LV_port.txt','LV_fac.txt','FF3a.txt','CPI.txt']
    audit=[('范围','1953–2002; 50 annual observations; portfolios and factors joined by equal year; no missing'),('原始单位','LV_port and LV_fac percent /100; FF3a RF percent /100; CPI level unchanged'),('A2 gross','(1+ FF3a current-year RF/100)/(CPI Dec current year/CPI Dec prior year)'),('NW','lag 0, centered cross-product /T; W= inverse; singular uses pinv rcond 1e-12 flagged'),('J / p','J=T*mean(h) W mean(h); chi-square upper-tail using source-program df'),('CU','minimize concentrated continuously-updated centered covariance objective (algebraic equivalent to GAUSS ols_r2 at lag 0)'),('SE','fixed W: sqrt(diag(inv(DᵀWD)/T)); CU: D*=D−0.5*dS/dtheta W mean(h); inverse only if full rank'),('2S / ITER','identity stage then centered S inverse; iterated weight updated until relative parameter and J changes <1e-7; cap 30'),('对照限制','No GAUSS installed: not a bit-for-bit optmum result; CU local starts 3, record objective spread'),('df','CAPM 8; CCAPM 7; EZ 7; gross CCAPM 7; not comparable across differing asset/moment sets')]
    audit += [(f'SHA256 {f}',hashlib.sha256((p/f).read_bytes()).hexdigest()) for f in files]
    sheet(wb.create_sheet('口径与算法'),['项目','审计记录'],audit)
    sheet(wb.create_sheet('样本与转换'),['年','P1','P2','P3','P4','P5','P6','P7','P8','Rvwexc','Consumption','RF','CPI_Dec_prior','CPI_Dec_current','通胀','实际gross'],[(int(y),*r[i],*fac[i],rf[i],cpi[y-1,12],cpi[y,12],infl[i],gr[i]) for i,y in enumerate(years)])
    sheet(wb.create_sheet('检验总表'),['模型','表示','估计法','T','矩数','参数数','df','J','p(右尾)','中心S条件数','S最小奇异值','信息矩阵秩','均值矩范数','求解/迭代收敛','起点J跨度或末次参数变化'],[(a['model'],a['typ'],a['method'],50,a['m'],len(a['x']),a['df'],a['j'],a['p'],a['cond'],a['smin'],a['rank'],a['mean_norm'],str(a['success']),a['spread']) for a in res])
    sheet(wb.create_sheet('参数与标准误'),['模型','表示','估计法','参数','估计','标准误','备注'],[(a['model'],a['typ'],a['method'],name,float(v),float(se),('角度折叠 '+str(np.arctan(np.tan(v))) if 'angle' in name else '')) for a in res for name,v,se in zip(a['names'],a['x'],a['se'])])
    sheet(wb.create_sheet('迭代轨迹'),['模型','表示','估计法','轮次/起点','J（本轮权重）'],[(a['model'],a['typ'],a['method'],i,j) for a in res for i,j in a['trace']])
    out.mkdir(parents=True,exist_ok=True);wb.save(out/'外汇资产定价验证.xlsx')
    doc=Document();sec=doc.sections[0];sec.header.paragraphs[0].text='研究方法独立验证  |  1953—2002'
    doc.add_heading('模型验证与准入意见',0)
    doc.add_paragraph('致：外汇策略研究负责人  |  范围：附件历史样本内的四个 GAUSS 模型，不涉及当期或样本外交易。')
    doc.add_heading('判定',level=1)
    doc.add_paragraph('有条件准入：可作为历史模型比较的可复算研究组件；不得将样本内卡方不拒绝解读为模型成立，更不得用于当期盈利主张。须先审查下述迭代及识别诊断，比较时固定资产集合与相同权重/矩条件口径。')
    doc.add_heading('样本与复刻方法',level=1)
    doc.add_paragraph('直接读取九份原件。组合收益与因子均为百分数转小数；1953—2002 年 50 个共同年度。A2 将当年 FF3a 无风险收益与上年十二月至当年十二月的 CPI 涨幅合成实际总收益。全部采用 lag=0 的去均值样本矩协方差（除以 50）。两步从单位权重拟合后更新一次，迭代反复更新权重；CU 直接最小化随参数更新的协方差加权二次型，与原程序 lag=0 下的 OLSQR2/ols_r2 集中目标等价，非 GAUSS optmum 的逐位复现。')
    doc.add_heading('计算结果（取各模型非中心非对称 SDF）',level=1)
    table=doc.add_table(rows=1,cols=5);table.style='Light Shading Accent 1'
    for c,v in zip(table.rows[0].cells,['模型','2S J / p','迭代 J / p','CU J / p','诊断']):c.text=v
    for model in ['CAPM','CCAPM','EZ','GROSS']:
        a=[next(x for x in res if x['model']==model and x['typ']=='asym_u' and x['method']==m) for m in ['2S','ITER','CU']]
        row=table.add_row().cells
        for c,v in zip(row,[model]+[f"{x['j']:.3f} / {x['p']:.3g}" for x in a]+['迭代收敛' if a[1]['success'] else '迭代未收敛']):c.text=v
    flagged=[a for a in res if not a['success'] or a['rank']<len(a['x']) or a['cond']>1e10]
    doc.add_paragraph(f'共 {len(res)} 套模型×表示×估计法；{len(flagged)} 行触及未收敛、信息秩不足或协方差条件数>1e10。未删除任何结果；全套估计值、标准误、J、自由度、p、起点跨度、信息秩和逐轮轨迹见底稿。')
    doc.add_heading('解释与限制',level=1)
    doc.add_paragraph('CAPM 把市场超额收益既作为因子又作为被定价资产；EZ 使用市场加消费两因子、市场收益亦被定价；CCAPM 仅对八组超额收益定价；A2 增加一个实际总收益的单位定价方程。因而即使 df 相同也不能直接横向以 J 排名。对称归一化使用角度，角度可跨周期且存在正负尺度及近零截距的边界；非对称归一化固定截距 1，不一定覆盖同一全局解。中心形式同时估计因子均值，回归形式还估计暴露、风险价格或总收益常数，权重矩和参数维度不同。CU、两步与迭代在小样本下非同一最优化目标，J 差异不自动意味着代码错误。')
    worst=sorted(res,key=lambda a:a['cond'],reverse=True)[:3]
    doc.add_paragraph('协方差最差条件数：'+ '；'.join(f"{a['model']}/{a['typ']}/{a['method']} {a['cond']:.2g}" for a in worst)+'。近奇异矩、弱因子相关、局部解及数值差分会放大标准误不稳定性。空白标准误表示信息矩阵非满秩；伪逆仅用于继续显示估计路径，不能据此声称可靠推断。迭代停止在 30 轮的实际末值，不以两步或 CU 冒充收敛值。')
    gross_cu=next(a for a in res if a['model']=='GROSS' and a['typ']=='asym_u' and a['method']=='CU')
    gross_2s=next(a for a in res if a['model']=='GROSS' and a['typ']=='asym_u' and a['method']=='2S')
    doc.add_paragraph(f"重点否决边界：总收益模型的非中心 SDF 在 CU 下 a={gross_cu['x'][0]:.3g}、b={gross_cu['x'][1]:.3g}，均值矩范数 {gross_cu['mean_norm']:.3g}；其 CU J={gross_cu['j']:.3f} 与未加入总收益的 CCAPM CU 值近似相同，而同一总收益表示 2S J={gross_2s['j']:.3f}。这不是总收益方程无关紧要的证据：尺度逸出时随参数变化的协方差会掩盖大的原始定价误差。该 CU 解应列作数值/识别边界，不凭其 p 值批准含总收益模型。")
    doc.add_paragraph('进一步准入条件：对有标记的估计检查多起点/尺度与协方差特征谱；在统一资产和矩体系内重做敏感性分析；对比独立数值实现及原论文表格前不得承诺逐位复现。历史 p 值是所选渐近卡方参考下的样本内诊断，而非模型被证实的概率。')
    doc.styles['Normal'].font.size=Pt(9)
    doc.save(out/'模型验证与准入意见.docx')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',type=Path,default=Path('/app/input_files'));ap.add_argument('--output-dir',type=Path,default=Path('/work/output'));args=ap.parse_args()
    data=read_data(args.input_dir);res=run_all(data[1],data[2],data[3]);deliver(args.input_dir,args.output_dir,data,res)
if __name__=='__main__':main()
