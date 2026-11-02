import pandas as pd, numpy as np, hashlib, pathlib, math
from openpyxl import Workbook,load_workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.utils import get_column_letter as L
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
base=pathlib.Path('/app/input_files'); out=pathlib.Path('/work/output')
x=pd.read_csv(base/'dataverse_banco_final_clusters14novCSV_v2.tab'); dic=pd.read_csv(base/'dataverse_dicionario_variaveis_v2.tab')
w=Workbook();w.remove(w.active)
def sheet(name,headers,rows):
 s=w.create_sheet(name);s.append(headers)
 for r in rows:s.append([None if pd.isna(v) else v.item() if isinstance(v,np.generic) else v for v in r])
 return s
readme=[
['范围','仅1000条历史匿名调查，163字段；非本机构客户，不作授信、定价、催收。全部统计未加权。'],
['文件读取','两份.tab实际为逗号分隔UTF-8 CSV，按CSV读取；不按扩展名强行用制表符。字典163行，与数据字段一一对应。'],
['导航','原始数据保留源顺序/字段/空白；Excel第2行=源第1条记录。id仅调查匿名ID。字典原文与问卷文本提供证据。'],
['重算','参数B2为原定义70%，B3为作者80%，B4为作者90%；逐条复核含Excel公式，规模、迁移、指标检查链接公式。描述80为此次固定80%快照。'],
['边界','>=包含等号；先检概率范围、和误差<=1e-9、并列；异常进未决而非删除。纯类仅稳定归属，不是质量或违约标签。'],
['原始字段','P21为12个1/2二元编码题，问卷为RM多选；1按选中、2按未选操作性解读，有路由证据但缺正式值标签。计数是类型，不是实际合同数。'],
['空白','原表空白保持空白；COUNTIF仅数明确1，不将空白写为零。P39全空331条单列为无可观察回答，不解释为无逾期。'],
['P39','15列仅1/空白；字典每列说明截断且无选项名；PDF只有14个选项，不能按列序猜映射。P39_14、_15为特设敏感性剔除情景，不认定为不知道/没有。'],
['状态','算术复现≠业务定义验证；详见证据与指标检查。不得把报价数作为贷款或转化。'],
['未稳定组','保留Misto全量和未决组；80%下254人，其中原Misto145人+109人降为混合。不可把分母改为只剩纯类。'],
['描述表','描述80是未加权快照；P40_3、P41_1的分母同时列全组人数及P42非空代理路由人数，后者不是已确认合格分母。'],
['重跑提示','公式适用于当前1000行；追加数据需扩展引用范围。来源哈希在来源表，可比对原件。']]
sheet('使用说明',['条目','说明'],readme)
sheet('来源',['文件','用途','SHA256','字节'],[[p.name,('问卷：题意、选项、路由；PDF共3页' if p.suffix=='.pdf' else '字典：派生定义、分群阈值、有效数' if 'dicionario' in p.name else '匿名记录：保留原值，复核计算'),hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_size] for p in base.iterdir()])
sheet('参数',['参数','数值','性质'],[['基线',.7,'字典cluster_amplo：每类概率>=70%；否则Misto'],['严格',.8,'作者敏感性假设，不是发布规则'],['更严格',.9,'作者敏感性假设'],['概率和容差',1e-9,'作者数值容差']])
sheet('原始数据',list(x.columns),x.itertuples(index=False,name=None));sheet('字典原文',list(dic.columns),dic.itertuples(index=False,name=None))
pages=pathlib.Path('/work/question.txt').read_text().split('\f')
sheet('问卷文本',['PDF页','页内文本行','原文（布局抽取）'],[[i+1,j+1,line.strip()] for i,p in enumerate(pages) for j,line in enumerate(p.splitlines()) if line.strip()])
cols={c:L(i+1) for i,c in enumerate(x.columns)}
def raw(c,r):return f"'原始数据'!{cols[c]}{r}"
heads=['id','源Excel行','概率和','最大概率','最大类序号','最大值并列数','概率检查','重建cluster','标签一致','重建70','发布70一致','重建80','重建90','70至80','P21明确1数','P21有效数','发布活动债务','活动差值','P39明确1数','P39有效数','发布逾期数','逾期差值','P39_1至13敏感数','P39全空','六渠道和','发布报价总数','报价差值','P40_3选中','P41_1选中','P41_3选中','P42非空','六sim不一致数']
s=w.create_sheet('逐条复核');s.append(heads)
for r in range(2,1002):
 ps=','.join(raw(c,r) for c in ['prob_c1','prob_c2','prob_c3']); pr=f"{raw('prob_c1',r)}:{raw('prob_c3',r)}";p21=f"{raw('P21_1',r)}:{raw('P21_13',r)}";p39=f"{raw('P39_1',r)}:{raw('P39_15',r)}"
 def group(th):return f'=IF(G{r}<>"通过","未决",IF(D{r}>=参数!B{th},"c"&E{r}&" puro","Misto"))'
 channels=['ligacoes','whatsapp','app','sms','agencia','email']
 vals=[f'={raw("id",r)}',r,f'=SUM({pr})',f'=MAX({pr})',f'=MATCH(D{r},{pr},0)',f'=COUNTIF({pr},D{r})',f'=IF(AND(COUNT({pr})=3,MIN({pr})>=0,MAX({pr})<=1,ABS(C{r}-1)<=参数!B5,F{r}=1),"通过","未决")',f'=CHOOSE(E{r},"cluster 1 desorganizado","cluster 2 organizado","cluster 3 conservador")',f'=IF(H{r}={raw("cluster",r)},1,0)',group(2),f'=IF(J{r}={raw("cluster_amplo",r)},1,0)',group(3),group(4),f'=IF(J{r}=L{r},"不变","降为混合/未决")',f'=COUNTIF({p21},1)',f'=COUNT({p21})',f'={raw("n_dividas_ativas",r)}',f'=Q{r}-O{r}',f'=COUNTIF({p39},1)',f'=COUNT({p39})',f'={raw("n_contas_atraso",r)}',f'=U{r}-S{r}',f'=COUNTIF({raw("P39_1",r)}:{raw("P39_13",r)},1)',f'=IF(T{r}=0,1,0)',f'=SUM('+','.join(raw('n_propostas_'+c,r) for c in channels)+')',f'={raw("n_propostas_total",r)}',f'=Z{r}-Y{r}']
 for c in ['P40_3','P41_1','P41_3']:vals.append(f'=IF({raw(c,r)}=1,1,0)')
 vals += [f'=IF(ISNUMBER({raw("P42",r)}),1,0)', '='+ '+'.join(f'IF(IF({raw("n_propostas_"+c,r)}>0,1,0)={raw("propostas_"+c+"_sim",r)},0,1)' for c in channels)]
 s.append(vals)
groups=['c1 puro','c2 puro','c3 puro','Misto','未决']
ss=sheet('分层规模',['分组','70%基线','80%作者','90%作者','80减70'],[])
for i,g in enumerate(groups,2):ss.append([g]+[f'=COUNTIF(逐条复核!{c}2:{c}1001,A{i})' for c in ['J','L','M']]+[f'=C{i}-B{i}'])
ss.append(['全样本','=SUM(B2:B6)','=SUM(C2:C6)','=SUM(D2:D6)','=C7-B7'])
ss=sheet('归属迁移',['70分组 / 80分组']+groups,[])
for r,g in enumerate(groups,2):ss.append([g]+[f'=COUNTIFS(逐条复核!J2:J1001,$A{r},逐条复核!L2:L1001,{L(c)}$1)' for c in range(2,7)])
checks=[['记录数','=COUNTA(原始数据!A2:A1001)','1000'],['最大类标签匹配','=SUM(逐条复核!I2:I1001)','1000/1000；未发现标签错配'],['70%发布匹配','=SUM(逐条复核!K2:K1001)','1000/1000；基线非作者自定'],['概率未决','=COUNTIF(逐条复核!G2:G1001,"未决")','0；无并列、范围异常或和异常'],['活动数与12项明确1不一致','=COUNTIF(逐条复核!R2:R1001,"<>0")','168；全部发布值比可观察计数多1；未知原因'],['逾期数与15项明确1不一致','=COUNTIF(逐条复核!V2:V1001,"<>0")','0；仅算术复现，选项含义未验证'],['P39全空','=SUM(逐条复核!X2:X1001)','331；恰与发布活动债务为0一致，不等于无逾期'],['报价总数与六渠道和不一致','=COUNTIF(逐条复核!AA2:AA1001,"<>0")','0；但渠道原题不在PDF，无法验证单位/特殊码'],['渠道sim不一致合计','=SUM(逐条复核!AF2:AF1001)','0；sim与渠道数>0一致'],['P40_3选中','=SUM(逐条复核!AB2:AB1001)','166；收入下降并优先基本支出；多选'],['P41_1选中','=SUM(逐条复核!AC2:AC1001)','144；减少食物购买；多选'],['P41_3选中','=SUM(逐条复核!AD2:AD1001)','122；另借贷款偿债；多选'],['P42有效','=SUM(逐条复核!AE2:AE1001)','402；仅作条件题作答覆盖代理，不解释状态']]
sheet('指标检查',['核验项','公式结果','判读'],checks)
evidence=[
['E1','分群','字典cluster / cluster_amplo','潜在类别最大后验概率；基线>=70%，混合否则','已验证标签算术；类别命名是发布者行为描述，不是风险等级。模型题项、拟合与样本外稳定性未提供。'],
['E2','活动债务','PDF p2 P21；字典P21_1…13；数据12列，缺_5','P21问卷列12种借款+不知道；字典P21_11称信用卡，PDF称信用卡分期购买','12项全有1/2，明确1合计1947；发布活动合计2115。832相等、168多1。最大12 vs13，不能假造缺项或把不知道算债务。需值标签、完整题项及派生代码。'],
['E3','逾期账户','PDF p3 P39；字典15列描述均截断','PDF14个选项（含不知道、没有）；CSV15列，无逐列标签','发布逾期数完全等于15列选中数；548人=1但可能含非债务选项。不能称669人逾期。需P39映射、特殊选项排除规则及计数代码。'],
['E4','P39敏感性','数据P39_14=29人、_15=278人','剔除最后两列仅为作者压力测试，不推定其题意','15列合计887次选择；1至13合计580次；发布数与敏感数在307条不同。不得覆盖原发布字段。'],
['E5','路由','PDF p2 P37写Todos；p3 P40/P41/P42至少一个P39选项','P37仅669人非空，与发布活动>0一致；P42有效402人','P42非空中40人P39全空、362人P39有选项；P39有选项的307人P42空。PDF路由与数据不能简单对齐，空白兼有未选/未展示/缺失。'],
['E6','报价','字典n_propostas_* / propostas_*_sim；PDF p1直接P8跳到P14','PDF不含P12/P13及六渠道计数题；P20是产品报价有无而非渠道次数','六渠道和与总数1000条一致；每渠道0至22、sim与>0一致。22可能是真实值或编码，未证实。无缩放、截尾或静默改码。收到报价非借款或转化。'],
['E7','困难需求','PDF p3 P40_3 / P41_1 / P41_3；字典明确选项','均仅1/空白；多选，不能把百分比相加或用空白判无困难','明确选中可支持“有此需求的调查信号”，不支持全群患率/因果；须先核路由与有效分母。'],
['E8','覆盖与权重','PDF p1年龄、P3终止与面板隐藏变量；数据','问卷排除<=17、>=70、不贡献收入者；gender/state/sel由面板提取','未提供概率样本框、招募率、权重或面板编码。样本日期为2025-07-09至24；PDF版本为6月6日，不能认定执行版本完全相同。']]
sheet('证据与未决',['证据号','对象','来源定位','证据','结论/待核实'],evidence)
p=x[['prob_c1','prob_c2','prob_c3']];arg=p.values.argmax(axis=1)+1;g=np.where(p.max(axis=1)>=.8,['c'+str(a)+' puro' for a in arg],'Misto');a=x.filter(regex='^P21_').eq(1).sum(axis=1); rows=[]
for grp in groups[:4]:
 mask=g==grp;z=x[mask];n=len(z);route=z.P42.notna().sum();rows.append([grp,n,int((a[mask]>0).sum()),float(a[mask].mean()),int(z.P40_3.eq(1).sum()),int(z.P41_1.eq(1).sum()),int(z.P41_3.eq(1).sum()),int(route),float(z.n_propostas_total.mean()),float(z.n_propostas_total.median()),int(z.filter(regex='^P39_').notna().sum(axis=1).eq(0).sum())])
sheet('描述80快照',['80%组','全组N','P21至少一项1人数','P21明确1类型均数','P40_3明确选中','P41_1明确选中','P41_3明确选中','P42非空(非已确认分母)','发布报价均数(未核口径)','发布报价中位数(未核口径)','P39全空人数'],rows)
cov=[]
for c in ['faixa','gender','state','sel','P3','P49','P50']:
 for v,n in x[c].value_counts(dropna=False).sort_index().items():cov.append([c,str(v),n,n/1000,'原始编码频数；不猜标签，未加权'])
sheet('覆盖编码',['字段','原始码','人数','样本占比','限制'],cov)
# styling
for s in w:
 s.freeze_panes='C2' if s.title in ['原始数据','逐条复核'] else 'A2';s.auto_filter.ref=s.dimensions
 s.row_dimensions[1].height=30
 for cell in s[1]:cell.font=Font(name='微软雅黑',bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='17365D');cell.alignment=Alignment(wrap_text=True,vertical='center')
 for row in s.iter_rows(min_row=2):
  for c in row:
   c.font=Font(name='微软雅黑',size=10,color='166534' if c.data_type=='f' else '202C3A');c.alignment=Alignment(vertical='top',wrap_text=s.title not in ['原始数据','逐条复核'])
  if row[0].row%2==0:
   for c in row:c.fill=PatternFill('solid',fgColor='F1F5F9')
 for c in s.columns:
  col=c[0].column_letter
  if s.title=='原始数据':width=23 if c[0].value in ['cluster','cluster_amplo','StartDate'] else 15
  elif s.title=='逐条复核':width=23
  else:width=min(85,max(18,max(len(str(k.value or '')) for k in list(c)[:30])*1.1))
  s.column_dimensions[col].width=width
 if s.title in ['使用说明','证据与未决']: 
  for r in range(2,s.max_row+1):s.row_dimensions[r].height=75
 s.sheet_properties.pageSetUpPr.fitToPage=True;s.page_setup.orientation='landscape';s.page_setup.paperSize=s.PAPERSIZE_A3;s.page_setup.fitToWidth=1;s.page_setup.fitToHeight=0;s.print_title_rows='1:1'
for r in [2,3,4]:w['参数'].cell(r,2).number_format='0%'
for r in range(2,w['覆盖编码'].max_row+1):w['覆盖编码'].cell(r,4).number_format='0.0%'
w.save(out/'分群与债务指标复核.xlsx')
# memo
doc=Document();sec=doc.sections[0];sec.header.paragraphs[0].text='研究审查  /  历史匿名调查  /  决策用途受限'
sec.top_margin=Inches(.7);sec.bottom_margin=Inches(.7)
normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10.5);normal._element.rPr.rFonts.set(qn('w:eastAsia'),'微软雅黑')
normal.paragraph_format.space_after=Pt(6)
for name in ['Title','Heading 1','Heading 2']:
 doc.styles[name]._element.rPr.rFonts.set(qn('w:eastAsia'),'微软雅黑')
def para(t):doc.add_paragraph(t)
def h(t):doc.add_heading(t,level=1)
def table(headers,rs):
 t=doc.add_table(rows=1, cols=len(headers));t.style='Light Shading Accent 1'
 for c,v in zip(t.rows[0].cells,headers):c.text=str(v)
 for r in rs:
  for c,v in zip(t.add_row().cells,r):c.text=str(v)
doc.add_heading('试点决策备忘录',0)
para('致：消费金融产品研究与客户支持负责人\n主题：有条件开展内部研究；暂不批准按匿名分群直接实施客户触达\n材料口径：仅本次三份公开附件，不含当前客户、征信或后续市场资料。')
h('一、需要负责人作出的决定')
para('建议“内部研究可用、业务执行暂缓”。允许把现有潜在类别用作描述性研究分层和访谈假设，不将其当成经验证的风险模型。保留发布70%基线；80%作为作者提出的严格归属敏感性方案，不能因纯类更少就声称更有效。债务数与逾期业务定义存在实质未决问题，报价仅验证加总关系。对外试点须先完成编码澄清、伦理/隐私与招募审批，并取得可行资源估算。')
para('本次不作个人授信、利率定价或催收决定；匿名调查ID既不可联系，也不是本机构客户号。类别归属概率不是违约概率，“desorganizado”等名称是发布者命名，不宜作为面向客户的标签。')
h('二、材料、样本及外推边界')
para('数据文件 dataverse_banco_final_clusters14novCSV_v2.tab 提供1000条匿名记录、163个原始及派生字段；dataverse_dicionario_variaveis_v2.tab 提供163条变量说明、有效数及70%分类定义；Cópia de 2024-089_Bacen_Questionario_Fletcher.pdf（3页）用于核对题意、选项和条件跳转。两份.tab实为逗号分隔CSV。工作簿保留原字段、原空白、源行、匿名id、字典全文、问卷抽取文本和文件SHA256。')
para('StartDate覆盖2025-07-09至2025-07-24；问卷标示6月6日版本，不等于已确认的实际执行版本。PDF年龄入口排除17岁及以下和70岁及以上，P3排除不贡献家庭收入者，性别、州与社会经济层变量取自面板。数据faixa码1/2/3/4人数为267/228/380/125；gender码1/2为436/564；sel码1/2/3为354/309/337，覆盖26个州编码。没有完整值标签，故不强配码名。样本框、抽样概率、招募率、权重均未提供；所有比例是未加权历史样本内描述，不能外推巴西总体、现在市场或本机构客户。')
h('三、分层可复核性及80%影响')
para('字典规定cluster为最大类别归属概率；cluster_amplo为任一类别概率≥70%时归纯类，否则Misto。1000条最大类标签、70%标签均完全复现；三概率均在[0,1]内，和的最大误差2.22×10⁻¹⁶，没有并列最大值。最大类人数c1/c2/c3分别为186/396/418。概率模型的训练题项、拟合质量及外部验证未提供，因此这不是模型效度审查。')
table(['门槛','c1纯类','c2纯类','c3纯类','Misto','未决'],[['70% 发布基线',171,347,337,145,0],['80% 作者假设',152,304,290,254,0],['90% 作者假设',141,249,222,388,0]])
para('70%升至80%：c1有19人、c2有43人、c3有47人转入Misto，共109人（全样本10.9%；原纯类12.7%）。原145名Misto均保留，没有纯类之间互换。80%稳定组共746人，不是746名可招募客户。90%进一步展示精细分层与覆盖损失的权衡。等号归入纯类；概率异常或最大值并列按作者规则归“未决”，不得任意破同分。未稳定记录维持独立描述和后续一般性支持候选，不予删除。')
h('四、债务与报价：算得对不等于含义对')
table(['指标','已查到的证据','研究可用性'],[
['活动债务 n_dividas_ativas','P21可见12个二元题，1计选中、2计未选的操作性解读下合计1947次；发布合计2115。832条一致，168条均多1；最大可见12 vs 发布13。','不作为实际合同数或负债程度。可暂用“可见P21明确选中类型数”，保留未决差额。'],
['逾期 n_contas_atraso','完全等于P39全部15列选中数；合计887。PDF只有14个选项且含“不知道/没有”，字典每列截断无选项映射。','停止作为已验证逾期账户指标。不能把669条正数称为669名逾期者。'],
['报价 n_propostas_total','全部1000条等于六渠道之和，六个sim均与渠道数>0一致。渠道值0至22；总均数6.884，中位2，最大132。','只作发布的报价暴露代理；原始渠道题未在PDF中，单位、22及零的含义须确认。不代表贷款或转化。']])
para('P21问卷是多选类型，不是合同逐笔清单，且字典P21_11写“信用卡”，PDF写“信用卡分期购买”；不能因为字段名称是活动债务就认定口径相同。数据没有P21_5，但不能猜其题意或补成差额。P39_14与_15分别29和278条明确选中；只计_1至_13的作者压力测试得到580次，307条与发布数不同，绝不把最后两列猜定为“不知道/没有”后静默修正。')
para('P39全空331条，恰与发布活动数=0一致；它们是无可观察P39回答，不是已证明无逾期。P37在PDF为所有人，实际仅669条非空。P42仅402条非空，其中40条P39全空；P39有选项者另有307条P42空。P40/P41/P42条件分母不能由简单P39>0确定。原始空白保留，不能全部填零来消除路由不一致。P40/P41为多选，明确1可计选择信号，空白可能是未选、未展示或缺失，不合并解释为否。')
h('五、值得先验证的支持需求')
para('优先验证两个内容方向：（A）收入冲击下的基本支出保护与自愿债务支持导航；（B）借新还旧、报价比较及总成本教育。理由是明确选中题意，而非类别名称：P40_3有166人选择“收入下降、优先基本开支”，P41_1有144人选择“减少食物购买”，P41_3有122人选择“另借贷款偿债”。这些可能重叠，不能相加成独立人数，也不是干预会改善的因果证据。')
table(['80%组（N）','P21至少1项1','收入冲击选中','减少食物选中','P42非空*'],[[f'{r[0]} ({r[1]})',r[2],r[4],r[5],r[7]] for r in rows])
para('*以上为明确选中人数；全组N始终展示。P42非空只是条件题作答覆盖代理，不是已确认的适格分母。c1的收入冲击72/152（47.4%）和减少食物47/152（30.9%）提示先验证需求，但不能叫作c1的困难发生率。c2也有56与48人；Misto有30与33人；c3有8与16人，不应因标签“保守”而剥夺支持。')
para('P21可见明确1类型均数c1/c2/c3/Misto为3.45/2.56/0.89/1.52，仅用于描述。发布报价均数相应6.33/11.92/3.56/4.98（中位3/6/1/2），c2报价暴露信号较高但原题和编码缺失，不据此定位易借款人或声称获客转化。首轮宜以自愿表达的困难和教育需求作为筛查，而不是未验证逾期数或类别名称。')
h('六、实施前的闸门与作者拟议方案')
para('闸门1｜向发布者索取：实际执行版本、完整题项和值标签（尤其P21、P39、六渠道报价及22/零/特殊值）、多选存储和缺失规则、跳题/展示日志、活动/逾期/报价派生代码、潜在类别模型设定与权重/招募说明。用这些信息逐条闭合168条活动差额及P39/P42路由差异，保留版本化前后对照。若无法取得，债务/逾期数保持未验证，只做一般教育探索。')
para('闸门2｜独立建立经批准的研究样本框和知情同意流程：必须另行取得合法联系渠道、自愿招募和本地语言适配；公开匿名ID不可反识别或匹配客户。确认隐私、伦理、脆弱群体保护和投诉/退出路径；债务支持应由适当资质团队承接，不交叉销售、不影响信贷待遇。预算、人员容量、招募条件和样本量均待审批，不在此假定。')
para('作者方案（非已批准计划）｜先用认知访谈核实题意与支持接受度，再做小规模可行性试点。若未来分群问卷和模型获授权且有可迁移性证据，可用70%基线分层、80%做稳健性分析；否则按自报需求分层。保留Misto和未决，不以“信心不足”为理由排除帮助。共同设计基础模块（账单梳理、应急支出、报价总成本和渠道安全）及按需支持导航；不得建议无条件再借款偿债。')
h('七、未来如何评价，而不是现在宣称有效')
para('建议先评估可行性：同意率、覆盖与退出、完成率、内容理解、困难转介接受度、投诉与潜在伤害。合规获批后，可在符合条件且同意者中按预设分层随机分配“支持模块”与常规公开教育，记录分配和不依从；紧急支持不因研究分配被扣留。比较应按意向治疗，不只保留完成者。')
para('作者拟议主要终点为干预后4–6周的报价总成本理解/情境题得分，先验证量表；次要终点为预算计划完成、自报应对能力、支持导航使用；更长期债务/逾期仅在口径验证、另取授权且有适当观察期后考虑。设置基线及随访，报告效应量、区间、失访与分层覆盖；分群异质性为探索性并控制多重比较。不把收到报价、参与或满意度当作真实债务改善。')
para('样本量应由预定最小有意义差异、方差、失访及可招募规模估算，成本需报价和资源测算。预先登记主要终点、停止规则及扩展门槛；若理解未提升、退出/伤害增加或覆盖严重偏斜，应修改或停止。当前没有实验、成效数据或已审批预算，不能报告改善率或ROI。')
h('附件使用及复算说明')
para('工作簿“逐条复核”以源行和id链接原始字段，含概率检查、三门槛归属、指标差额与路由覆盖公式；“分层规模”“归属迁移”“指标检查”可重算。“描述80快照”与“覆盖编码”为本次数据的静态描述；改变参数后需重建这些快照。“证据与未决”E1–E8列出定位及核实请求。原始文件未修改。复核仅限所给资料，未联网补足代码本，未验证任何现实客户或业务效果。')
footer=sec.footer.paragraphs[0];footer.alignment=2;footer.text='内部研究建议 · 非客户决策依据  |  '
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
doc.save(out/'试点决策备忘录.docx')
print('created',out)
