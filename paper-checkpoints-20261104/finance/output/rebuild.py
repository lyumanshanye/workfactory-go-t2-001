#!/usr/bin/env python3
"""Independent annual-path audit; no author-derived columns used as inputs."""
import argparse, os, json, hashlib
import numpy as np, pandas as pd
from scipy.special import expit
from scipy.optimize import minimize
from scipy.stats import rankdata
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Pt, Inches
P=argparse.ArgumentParser();P.add_argument('--input',default='/input');P.add_argument('--output',required=True);a=P.parse_args();os.makedirs(a.output,exist_ok=True)
rng=np.random.default_rng(20250308)
raw=['Year','crisis','credit_spread','bank_credit_GDP','bank_credit','GDP','p','xK','w','K','underlying_lambda','capital_excess_return','bank_equity']
def ols(y,x):
 m=np.isfinite(y)&np.isfinite(x);return float(np.cov(x[m],y[m],bias=True)[0,1]/np.var(x[m])),int(m.sum())
def label(c,h,include=False):
 # annual observation at t; future t+1..t+h; no fabricated right-edge zeros
 z=np.full(len(c),np.nan)
 for k in range(len(c)-h):z[k]=int(np.any(c[k if include else k+1:k+h if include else k+h+1]))
 return z
def auc(y,p):
 pos=y==1;n=pos.sum();return float((rankdata(p)[pos].sum()-n*(n+1)/2)/(n*(len(y)-n))) if n and n<len(y) else np.nan
def fit(x,y):
 m=np.isfinite(x)&np.isfinite(y);x=x[m];y=y[m]
 def f(b):
  q=expit(b[0]+b[1]*x);return np.logaddexp(0,b[0]+b[1]*x).sum()-np.dot(y,b[0]+b[1]*x)
 o=minimize(f,[np.log((y.mean()+1e-5)/(1-y.mean()+1e-5)),0.],method='BFGS',options={'gtol':1e-5});return o.x
def evaltest(y,p):
 return {'n':len(y),'events':int(y.sum()),'rate':float(y.mean()),'auc':auc(y,p),'brier':float(np.mean((y-p)**2)),'pred_mean':float(p.mean())}
book=Workbook();book.remove(book.active)
def sheet(name,head,rows):
 ws=book.create_sheet(name);ws.append(head)
 for r in rows:ws.append([v.item() if isinstance(v,np.generic) else v for v in r])
 ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
 for c in ws[1]:c.font=Font(bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='17365D')
 for col in ws.columns:
  letter=get_column_letter(col[0].column);ws.column_dimensions[letter].width=min(75,max(14,max(len(str(c.value or '')) for c in list(col)[:300])+2))
 return ws
manifest=json.load(open(os.path.join(a.input,'source_manifest.json')))
provenance=[]
for model in ['bayesian','diagnostic']:
 path=os.path.join(a.input,'Model/simulated data',model+'_full_yearly.dta');sha=hashlib.sha256(open(path,'rb').read()).hexdigest();d=pd.read_stata(path,columns=raw);assert len(d)==100000 and np.array_equal(d.Year.to_numpy(),np.arange(1,100001))
 provenance.append([model,os.path.relpath(path,a.input),len(d),int(d.Year.iloc[0]),int(d.Year.iloc[-1]),sha, int(d.crisis.sum()),'预处理后年度路径，非月度原始路径'])
 globals()[model]=d
sheet('来源与边界',['模型','相对输入路径','行数','首年','末年','SHA256','登记危机数(核对用)','等级'],provenance)
metrics=[];checks=[];pred=[];events=[];policy=[];confidence=[]
for name,d in [('Bayesian',bayesian),('Diagnostic',diagnostic)]:
 c=d.crisis.to_numpy().astype(int);s=d.credit_spread.to_numpy();b=d.bank_credit_GDP.to_numpy();g=d.GDP.to_numpy();n=len(c);idx=np.flatnonzero(c)
 # explicit separate reconstructions; derivatives are comparison only
 credit=d.bank_credit.to_numpy()/g; debt=d.p.to_numpy()*(d.xK.to_numpy()-1)*d.w.to_numpy()*d.K.to_numpy()/g
 for field,calc,original,tol in [('bank_credit/GDP vs debt',credit,debt,1e-4),('bank_credit/GDP normalized: level',credit/np.nanstd(credit,ddof=1),b,0.05)]:
  delta=np.abs(calc-original);checks.append([name,field,float(np.nanmedian(delta)),float(np.nanquantile(delta,.99)),int(np.sum(~np.isfinite(delta))),tol,'不同计量：原比率/模型恒等式；标准化基于月度路径，年度重估不要求严格相等'])
 # sampled source records
 for i in [0,1,49999,99999]:events.append([name,int(i+1),float(d.Year.iloc[i]),int(c[i]),float(s[i]),float(b[i]),float(g[i]),float(debt[i]),'dta行=Year（不计表头）；字段见变量表'])
 for h in [1,3,5]:
  y=label(c,h);valid=np.isfinite(y);froth=s<=np.median(s[:n-h]);t=valid
  rd=float(y[t&froth].mean()-y[t&~froth].mean())*100
  # 200-year moving blocks, uncertainty about dependence within a fixed simulated run, not parametric/real-world uncertainty
  N=n-h;block=200;bs=[]
  for _ in range(160):
   starts=rng.integers(0,N-block+1,size=int(np.ceil(N/block)));take=np.concatenate([np.arange(k,k+block) for k in starts])[:N];v=froth[take];yy=y[take];bs.append((yy[v].mean()-yy[~v].mean())*100)
  lo,hi=np.percentile(bs,[2.5,97.5]);overlap=float(np.mean(np.diff(idx)<=h))
  metrics.append([name,h,'严格未来 t+1..t+h',N,int(y[valid].sum()),float(y[valid].mean()*100),int(froth[:N].sum()),rd,float(lo),float(hi),overlap,'200年移动块重抽160次; seed=20250308'])
 # year before crisis vs post-crisis inclusive t..t+4, independent from derived indicators
 pre=np.zeros(n);pre[idx[idx>0]-1]=1
 post=np.zeros(n);post[np.minimum(idx[:,None]+np.arange(5),n-1)]=1
 X=np.column_stack([np.ones(n),pre,post]);beta=np.linalg.lstsq(X,s,rcond=None)[0]
 # paper table Panel C
 checks.append([name,'表3C 前一年spread回归系数（本算 / 表）',float(beta[1]),-.25 if name=='Bayesian' else -.30,float(beta[1]-(-.25 if name=='Bayesian' else -.30)),.015,'允许预处理事件细节差异；代码 before_crises 仅前一年，表注称五年'])
 # Panel A GDP 3 years; author uses forward spread (at t+1 minus t), observed only ex post
 yy=100*(g[3:]/g[:-3]-1);xx=np.zeros(n-3);xx[:]=c[:-3]*(s[1:n-2]-s[:-3]);v,k=ols(yy,xx)
 checks.append([name,'表3A GDP三年增长~危机×未来一年利差变动',v,-2.87 if name=='Bayesian' else -3.44,v-(-2.87 if name=='Bayesian' else -3.44),.10,'拟合/严重度描述，未来利差绝不可作为t时预警输入'])
 # credit x crisis
 v,k=ols(yy,b[:-3]*c[:-3]);checks.append([name,'表3A GDP三年增长~危机×标准化信贷',v,-2.18 if name=='Bayesian' else -3.49,v-(-2.18 if name=='Bayesian' else -3.49),.10,'回归量含当期危机，不是预警'])
 # author panel D model rolling 3 incl current, vs table caption 5 future
 yy=label(c,3,True);froth=s<=np.median(s);rd=(yy[:n-3][froth[:n-3]].mean()-yy[:n-3][~froth[:n-3]].mean())*100
 checks.append([name,'表3D froth边际效应；代码3年含当期（概率差）',rd,5.67 if name=='Bayesian' else 7.40,rd-(5.67 if name=='Bayesian' else 7.40),1.,'R glm crisis_next_3_year=rollsum(crisis,3)含t；表头/注释称未来5年；端点补零差异'])
 # credit logit AME approximation
 yy=np.r_[c[1:],np.nan];coef=fit(b[:-1],yy[:-1]);ame=float(np.mean(expit(coef[0]+coef[1]*b[:-1])*(1-expit(coef[0]+coef[1]*b[:-1]))*coef[1])*100)
 checks.append([name,'表3D 标准化信贷t预测t+1 logit AME 百分点/单位',ame,4.05 if name=='Bayesian' else 3.85,ame-(4.05 if name=='Bayesian' else 3.85),.2,'独立MLE与平均边际效应；数值差异可因优化/窗口'])
 # temporal split 70/30; past-observable raw standardized levels. train threshold only, no leakage
 cut=70000;h=3;Y=label(c,h);train=np.arange(5,cut-h);test=np.arange(cut,n-h)
 for feature in ['spread','credit','debt','spread_5y']:
  if feature=='spread':x=s
  elif feature=='credit':x=b
  elif feature=='debt':x=debt
  else:x=pd.Series(s).rolling(5,min_periods=5).mean().to_numpy()
  mu=np.nanmean(x[train]);sd=np.nanstd(x[train]);z=(x-mu)/sd; coef=fit(z[train],Y[train]);prob=expit(coef[0]+coef[1]*z[test]);e=evaltest(Y[test],prob)
  pred.append([name,feature,'70000年以前训练；70000-3空档；70001..99997测试',len(train),e['n'],e['events'],e['rate']*100,float(coef[1]),e['auc'],e['brier'],e['pred_mean']*100,float(np.mean((Y[test]-Y[train].mean())**2)),'仅模拟时间留出；训练均值/方差；未来3年不含当期'])
 # observational state matching: both models standardized spread/credit matched bins separately later
 globals()[name+'_pre']=(s,b,c,g)
# state matching raw paths: common support using within-model quantile high leverage + low spread, stratify decile ranks of each
D=bayesian;E=diagnostic
for name,d in [('Bayesian',D),('Diagnostic',E)]:
 s=d.credit_spread.to_numpy();b=d.bank_credit_GDP.to_numpy();c=d.crisis.to_numpy();g=d.GDP.to_numpy();debt=d.p.to_numpy()*(d.xK.to_numpy()-1)*d.w.to_numpy()*d.K.to_numpy()/g
 # absolute economic units: spread and unnormalized debt; fixed common bins selected from joint empirical overlap
 globals()[name+'_state']=(s,debt,c,g)
s1,x1,c1,g1=Bayesian_state;s2,x2,c2,g2=Diagnostic_state
for q in [(2,4),(3,5),(4,6)]:
 # fixed common percentile bins of pooled distributions, condition on simultaneous bins; reporting noncausal comparison
 allS=np.r_[s1,s2];allX=np.r_[x1,x2];sl,sh=np.quantile(allS,[q[0]/10,(q[0]+1)/10]);xl,xh=np.quantile(allX,[q[1]/10,(q[1]+1)/10]);row=[f'pooled spread P{q[0]*10}-{(q[0]+1)*10}; debt P{q[1]*10}-{(q[1]+1)*10}',sl,sh,xl,xh]
 for ss,xx,cc,gg in [Bayesian_state,Diagnostic_state]:
  ix=np.where((ss>=sl)&(ss<sh)&(xx>=xl)&(xx<xh)&(np.arange(len(cc))<len(cc)-3))[0];row.extend([len(ix),int(cc[ix].sum()),float(label(cc,3)[ix].mean()*100) if len(ix) else None,float(np.median(gg[ix+3]/gg[ix]-1)*100) if len(ix) else None])
 policy.append(row)
# alternative annual event definition: lower 4% realized one-year bank-equity return; not the paper's monthly threshold
alts=[]
for name,d in [('Bayesian',bayesian),('Diagnostic',diagnostic)]:
 eq=d.bank_equity.to_numpy();growth=eq[1:]/eq[:-1]-1;threshold=float(np.quantile(growth,.04));candidate=np.zeros(len(eq),dtype=int);candidate[1:]=(growth<=threshold).astype(int)
 spaced=candidate.copy();last=-100
 for i in np.flatnonzero(candidate):
  if i-last<=3:spaced[i]=0
  else:last=i
 ss=d.credit_spread.to_numpy()
 for tag,cc in [('原作者年度标签',d.crisis.to_numpy()),('权益年收益尾部4%原事件',candidate),('权益年收益尾部4%且事件间隔>3年',spaced)]:
  y=label(cc,3);valid=np.isfinite(y);f=ss<=np.median(ss[:-3]);diff=100*(y[valid&f].mean()-y[valid&~f].mean())
  alts.append([name,tag,threshold if tag!='原作者年度标签' else None,int(cc.sum()),int(y[valid].sum()),float(diff),'仅年度权益指标替代定义；原文另有月度权益事件定义，不可混同'])
sheet('事件定义敏感性',['模型','事件口径','权益年收益下4%阈值','事件总数','未来3年阳性窗','低利差风险差pp','边界'],alts)
sheet('变量与定义',['字段','输入/独立计算','单位','定义及信息时点','代码来源'],[
 ['Year','dta Year','模型年','1..100000连续','preprocessing_simulation_data.R gen_yearly_data'],['crisis','dta crisis','0/1','年度事件从月度信用收缩阈值转化；无法从年度值独立重判月度危机','preprocessing_simulation_data.R gen_crisis / gen_yearly_data'],['credit_spread','dta credit_spread','月度全路径标准差单位','年度首个观察值；不是基点，时点t可见性需数据治理','gen_basic_definitions / gen_yearly_data'],['bank_credit_GDP','dta bank_credit_GDP','月度全路径标准差单位','年度首个观察值；全年样本标准差构造，实盘不能照搬','gen_basic_definitions / gen_yearly_data'],['debt','p*(xK-1)*w*K/GDP','原比率','年度当期状态；与bank_credit/GDP独立交叉校核','Main_Step3.do bank_debt'],['GDP_3Y','100*(GDP[t+3]/GDP[t]-1)','百分比','末三年剔除；非预警特征','本代码'],['froth','credit_spread[t]<=训练样本中位数','0/1','即时模型利差；R作者代码用全路径中位数（泄漏阈值）','Analyze_simulations.R reg_crises_predictability'],['future event','any(crisis[t+1:t+h+1])','0/1','未来h年不包括t；末h行丢弃','本代码 label'],['event overlap','连续事件距离<=h','比例','窗口可重叠，不是独立事件数','本代码']])
sheet('核对与差异',['模型','对账项目','本算/中位绝差','作者表或p99绝差','差','容差/缺失','归因与说明'],checks)
sheet('危机与敏感性',['模型','未来窗年','定义','有效年份','阳性窗口','发生率%','低利差年','风险差pp','块自助下界pp','上界pp','事件间距<=h占比','不确定性方法'],metrics)
sheet('时序留出预警',['模型','特征','切分','训练行','测试行','测试阳性','测试率%','logit系数/训练SD','AUC','Brier','平均预测%','基线Brier','限制'],pred)
sheet('状态匹配非政策',['匹配格','利差下界','利差上界','原比率下界','原比率上界','B行数','B当期事件','B未来3年%','B GDP3年中位增幅%','D行数','D当期事件','D未来3年%','D GDP3年中位增幅%'],policy)
sheet('原始记录定位',['模型','dta数据行(1起)','Year','crisis','credit_spread','bank_credit_GDP','GDP','debt重算','定位说明'],events)
sheet('结论索引',['报告位置','结论','证据页/代码','等级'],[
 ['§1','仅研究试用；不准实盘预警或资本决策','时序留出预警；状态匹配非政策','验证判断'],['§2','两个100000年模拟路径；不含静态信念年度路径','来源与边界；/input/source_manifest.json','输入记录'],['§3','作者表注与代码危机窗口口径不一致','核对与差异；Analyze_simulations.R reg_crises_predictability','代码/表对账'],['§4','滚动窗口重叠导致朴素标准误失真','危机与敏感性；事件定义敏感性；rebuild.py label','重算模拟'],['§5','匹配状态的自然路径不能识别注资处理效应','状态匹配非政策；paper.pdf §6','非因果描述']])
book.save(os.path.join(a.output,'模型验证证据.xlsx'))
# report
r=Document();sec=r.sections[0];sec.header.paragraphs[0].text='模型风险管理  |  独立验证  |  决策稿';r.styles['Normal'].font.name='宋体';r.styles['Normal'].font.size=Pt(10)
def title(t):r.add_heading(t,level=1)
def para(t):r.add_paragraph(t)
def tab(headers,rows):
 t=r.add_table(rows=1,cols=len(headers));t.style='Light Shading Accent 1'
 for cell,h in zip(t.rows[0].cells,headers):cell.text=h
 for row in rows:
  for cell,v in zip(t.add_row().cells,row):cell.text=str(v)
r.add_heading('危机模型独立验证报告',0)
para('对象：Krishnamurthy 与 Li《Dissecting Mechanisms of Financial Crises: Intermediation and Sentiment》；审查范围：提供的2023年10月工作稿、2024年Dataverse复制包及两份作者年度模拟路径。独立验证日期：未指定（代码随机种子20250308仅用于重抽）。')
title('1  决议建议与使用边界')
para('决定：有条件准入研究沙箱，且仅限研究试用；不准生产部署。可用于机制教学、对贝叶斯与诊断预期路径作情景敏感性分析、提出待实证检验的预警指标与资本政策假说。禁止将模拟概率解释为真实市场校准违约/危机概率、用于自动预警/限额/资本缓冲设定、监管报送、政策净收益或因果效果宣传；禁止把当前危机、未来利差、模型不可观测信念作为实时输入。')
para('准入条件（逐项签收）：①数据治理登记每个可观测指标的发布时间、修订史和信贷/GDP口径，建立仅截至t可得的面板；②用预先锁定的未来1/3/5年危机定义和国家/事件隔离，执行滚动起点真实样本外测试，报告AUC、Brier、校准、召回及误报成本和块/国家聚类置信区间；③纠正表注与代码窗口差异，保存版本、单元测试边界年份及月度原始路径复算危机事件；④政策使用须取得状态匹配下有/无注资的同随机冲击成对模拟、跨校准/成本/福利敏感性与可识别的外部政策数据；⑤二线签字、研究沙箱无交易接口、每季度漂移复核及12个月到期复审。任一条件未达成不得升级用途。')
title('2  资料链、校准和外部检验')
para('paper.pdf封面明确October 2023（工作稿），Dataverse元数据 doi:10.7910/DVN/TIL7KK 的发布日期为2024-07-12；2025期刊发表作为另一个版本，不将2023工作稿或2024表格误标为期刊正文。需取得2025正文和逐表差异清单方能确认发表版一致；本次未取得发表版独立全文。来源清单source_manifest.json记录校验和，证据“来源与边界”给出本次路径SHA256。两份dta各100000年、无静态信念年度路径；ReadMe宣称原始月度Excel可由MATLAB生成，但此次提供材料未含这些路径；不能从年度文件独立复原月度阈值、最初1000点烧入或静态信念机制。')
para('校准：论文§4使用约4%危机发生率作为目标、参数（如折旧10%、贴现4%、诊断权重0.90）部分来自文献与目标矩；这不是独立外部检验。作者R代码将信用/GDP及利差按全月度样本标准差标准化，年度取首个价格，危机按月度信用/GDP增长阈值选择并转年；论文§4文字称三年不连续事件，所交R代码gen_non_clustered_crisis中条件 index-crisis_last<0*12，不能据此宣称实现了三年间隔：属待查实现/材料版本差异，而不是认定论文有误。两条年度路径已含目标危机标签，独立复算的是年度条件统计而不是重新识别月度事件。经验系数-7.46、-0.34、18.0、2.8等在Analyze_simulations.R中以系数覆盖方式手动登记；对应原始实证面板不在输入，证据等级仅为作者引用/登记，不作实证复现。')
title('3  年度路径独立重算与作者表对账')
para('rebuild.py仅读取dta原始年度字段（Year、crisis、credit_spread、bank_credit_GDP、GDP、p、xK、w、K等），从数组切片构造未来事件、GDP增长、危机前一年及危机后五年指示；不用dta预计算的before_crises、crises_next_5Y、GDP_3Y_change、froth。工作簿“原始记录定位”给示例行、核对页给代码与作者表差异；作者表来源Tables/…tex。')
tab(['模型','事件年/总年','未来3年风险差(低利差-高利差) pp [块区间]','未来3年窗口率%'],[[m, f"{next(x[6] for x in provenance if x[0]==m.lower())}/100000",f'{z[7]:.2f} [{z[8]:.2f},{z[9]:.2f}]',f'{z[5]:.2f}'] for m in ['Bayesian','Diagnostic'] for z in metrics if z[0]==m and z[1]==3])
para('风险差使用未来t+1至t+3且剔除右端三年；区间为200年移动块、160次重抽，不等于模型参数误差或跨市场置信区间。工作簿另列1/5年敏感性、危机重叠比例，且以年度银行权益收益最差4%重定事件（以及间隔>3年的去簇事件）；此替代定义不等同论文的月度危机定义。表3C列名为“pre-crisis”但R回归变量before_crises仅前一年，而表下注称五年；表3D中R使用rollsum(crisis,3)含当期，而表标题和注称未来5年；表3A用t+1利差变动解释t到t+3 GDP，是严重度事后关系，不是t时预警证据。对账数值偏差先分为窗口/端点/边际效应统计定义、输入版本或预处理差异和可能实现问题；不直接推断论文错误。')
title('4  预警证据、样本与不确定性')
para('仅以当期利差、标准化信用/GDP、原比率debt或过去五年利差均值预测严格未来3年事件，训练前70000年、隔离3年、测试70001至99997年；训练集拟合logit、训练集标准化，无未来GDP或未来危机标签进入特征；模型利差/信贷含全路径标准化，仍非真实市场可直接观测尺度。表中模拟测试AUC/Brier/基线Brier为样本内机制产物的时序留出，并非真实市场样本外。')
tab(['模型','信号','测试阳性/样本','AUC','Brier / 基线'],[[x[0],x[1],f'{x[5]}/{x[4]}',f'{x[8]:.3f}',f'{x[9]:.4f} / {x[11]:.4f}'] for x in pred if x[1] in ['spread','debt']])
para('有效样本末端h年剔除；同一危机使相邻多个未来窗为阳性，且100000年为同一次/少数路径实现，常规独立年标准误不可信。块区间只量化时间序列重抽波动，尚缺随机种子/参数/机制/真实历史不确定性；同源模拟测试表现不能证明机构可用的前瞻预警增量。')
title('5  资本政策与经济状态可比性')
para('论文§6的干预是在繁荣状态从家庭向银行转移财富、初始银行财富份额w0提高10%，固定可观察信用利差与银行杠杆的初态，经solve_for_states_from_cs_and_lvg.m跨模型映射到不同潜在状态；诊断模型还设历史参考信念λT0=λ0，并比较有/无注资、共同冲击下脉冲响应。它不是现实的逆周期资本规则、净福利/财政成本估计或自然样本因果识别。当前提供年度dta只有未干预自然路径，无法独立重算有/无政策的配对处理效果。')
para('可复算的弱证据：工作簿“状态匹配非政策”以跨模型共同利差（已标准化）与原比率银行债务p(xK−1)wK/GDP的合并分布十分位矩形格，列示两模型匹配覆盖、事件和自然路径未来GDP；不同状态格不等于论文固定利差与杠杆的注资起点，债务/GDP亦不等于杠杆。空格/低覆盖禁止外推。这只能检验共同支持与描述差异，不能验证注资收益相似或宣称政策因果。升格授权需取得可执行IRF求解与成对反事实、初态匹配误差/参考信念敏感性、资本筹资与福利代价、跨参数稳健性，以及真实制度变动的准实验或可信结构识别。')
title('6  剩余限制与复核指引')
para('未安装或执行MATLAB/Stata；未重新求解均衡、重新校准、取得月度原始Excel或实证面板；静态信念只有作者表可供参考。输入的dta是作者发布的预处理年度模拟产物而非真实市场记录；模型状态与市场变量口径不等价。工作簿结论索引把报告位置、证据页及代码串联；复算命令、依赖、种子和容差详见运行说明。')
r.save(os.path.join(a.output,'危机模型独立验证报告.docx'))
print('written',a.output,'metrics',metrics,'checks',checks[-6:])
