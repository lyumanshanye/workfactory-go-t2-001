from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json,unicodedata,hashlib,statistics
from openpyxl import Workbook,load_workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml.ns import qn
INPUT=Path('/input');OUT=Path('/work/output');OUT.mkdir(exist_ok=True)
norm=lambda x:unicodedata.normalize('NFC',str(x)).strip()
tables={};filenames={};sourcehash={}
for f in INPUT.glob('*.xlsx'):
 n=int(f.name.split('_Suplementares_')[1].split('_')[0]);filenames[n]=f.name;sourcehash[f.name]=hashlib.sha256(f.read_bytes()).hexdigest();s=load_workbook(f,read_only=True,data_only=True).active;start={1:4,2:4,4:5,5:4}[n];tables[n]=[(i,list(r)) for i,r in enumerate(s.iter_rows(values_only=True),1) if i>=start and any(v is not None for v in r)]
script=next(INPUT.glob('*.txt'));sourcehash[script.name]=hashlib.sha256(script.read_bytes()).hexdigest()
company={norm(r[0]):(i,r[1]) for i,r in tables[1]}
indices={n:{(norm(r[0]),r[1].year):(i,r) for i,r in tables[n]} for n in [2,4,5]}
assert all(len(indices[n])==len(tables[n]) for n in indices),'Do not silently deduplicate'
assert set(indices[2])==set(indices[4])==set(indices[5]),'Full outer join required if key coverage differs'
assert set(k[0] for k in indices[2])<=set(company)
c=indices[2];st=indices[4];ctrl=indices[5];valid={k for k,(i,r) in c.items() if r[2:5]==['Sim','Sim','Sim'] and r[5] in ['Sim','Não']}
stage_names=['Introdução','Crescimento','Maturidade','Turbulência','Declínio'];stage_cn=['导入','成长','成熟','震荡','衰退'];stage_by={}
for k,(i,r) in st.items():
 a=[j for j in range(5,10) if r[j]=='Sim'];assert len(a)==1;stage_by[k]=a[0]-5
book=Workbook();book.remove(book.active)
def sheet(name,headers,rows):
 s=book.create_sheet(name);s.append(headers)
 for row in rows:s.append(row)
 s.freeze_panes='A2';s.sheet_view.zoomScale=85;s.auto_filter.ref=s.dimensions
 for row in s:
  for cell in row:
   cell.alignment=Alignment(vertical='top',wrap_text=True);cell.font=Font(name='Calibri',size=10)
   if cell.row==1:cell.fill=PatternFill('solid',fgColor='173E37');cell.font=Font(name='Calibri',size=10,bold=True,color='FFFFFF')
  s.row_dimensions[row[0].row].height=30 if row[0].row>1 else 42
 for j in range(1,s.max_column+1):s.column_dimensions[get_column_letter(j)].width=24 if j!=1 else 36
 s.page_setup.orientation='landscape';s.page_setup.fitToWidth=1;s.sheet_properties.pageSetUpPr.fitToPage=True;s.print_title_rows='1:1'
 return s
sheet('使用说明',['事项','说明'],[
 ['性质','AI试作参考成果，未完成独立盲解、专家验收或难度校准。'],
 ['材料','同一Harvard Dataverse资料页BGFTYG的4份原始XLSX及1份研究脚本；原件未修改。'],
 ['时点','历史观察窗口2010—2018；2018名单不代表当前借款人或持仓。'],
 ['总体','研究筛选后的非平衡公司年度样本；不能当作全部上市公司或所有债务人总体。'],
 ['纳统口径','披露、一般covenant、金融covenant均为Sim且违反字段合法；2条矛盾保留在底稿但暂不纳统，不擅改。'],
 ['比例','公司年度报告违反率；不是违约概率、合同法律认定、债券损失率或加权敞口。'],
 ['年度比较','只与同公司上一日历年对比；跨年缺口不按上一次观测补齐。'],
 ['优先级','作者设计的资料核查队列；持续、首次可比报告违反等用于安排复核，不是信用评级。'],
 ['财务控制变量','保留原值与数量级证据，未自行修复小数点或解释Tamanho单位，不用于金额/杠杆排序。'],
 ['脚本','仅作方法和材料依赖核验；没有运行Stata回归，未声称复现论文或取得脚本引用的Base Geral。'],
 ['溯源','合并底稿保留原始工作表行号；Unicode NFC及首尾空格只用于匹配键，不修改原始文件。'],
 ['重算','派生统计和上一年逻辑保留Excel公式；核心结果另有JSON供比对。']])
source_rows=[]
for n in [1,2,4,5]:source_rows.append([filenames[n],len(tables[n]),len({norm(r[0]) if n==1 else (norm(r[0]),r[1].year) for _,r in tables[n]}),'公司' if n==1 else '公司+年度','Planilha1',sourcehash[filenames[n]]])
source_rows.append([script.name,None,None,'研究方法文本','缺Base Geral及部分原始变量',sourcehash[script.name]])
sheet('来源与核验',['原文件','数据行数','唯一键数','主键/用途','工作表/限制','SHA256'],source_rows)
sheet('公司名录',['公司','行业','原表行'],[[name,sec,row] for name,(row,sec) in company.items()])
rows=[];row_for={};transitions={};keys=sorted(c,key=lambda k:(k[0],k[1]));N=len(keys)+1
for idx,k in enumerate(keys,2):
 name,y=k;i,r=c[k];si,sr=st[k];fi,fr=ctrl[k];prev=(name,y-1)
 if k not in valid:transition='源数据矛盾待核'
 elif prev not in c:transition='无连续上年记录'
 elif prev not in valid:transition='上年记录待核'
 else:transition={('Sim','Sim'):'持续报告违约',('Não','Sim'):'新增报告违约',('Sim','Não'):'转为未报告违约',('Não','Não'):'连续未报告违约'}[(c[prev][1][5],r[5])]
 transitions[k]=transition;row_for[k]=idx
 rows.append([name,y,company[name][1],*r[2:6],stage_names[stage_by[k]],*sr[2:5],i,si,fi,
 f'=IF(AND(D{idx}="Sim",E{idx}="Sim",F{idx}="Sim",OR(G{idx}="Sim",G{idx}="Não")),"一致","待核")',
 f'=IF(O{idx}="一致",1,0)',f'=IF(P{idx}=1,IF(G{idx}="Sim",1,0),"")',name+'|'+str(y),f'=P{idx}',f'=IF(P{idx}=1,Q{idx},"")',name+'|'+str(y-1),
 f'=COUNTIF($R$2:$R${N},U{idx})',f'=IF(V{idx}=0,"",VLOOKUP(U{idx},$R$2:$T${N},2,FALSE))',f'=IF(V{idx}=0,"",VLOOKUP(U{idx},$R$2:$T${N},3,FALSE))',
 f'=IF(P{idx}=0,"源数据矛盾待核",IF(V{idx}=0,"无连续上年记录",IF(W{idx}<>1,"上年记录待核",IF(AND(Q{idx}=1,X{idx}=1),"持续报告违约",IF(AND(Q{idx}=1,X{idx}=0),"新增报告违约",IF(AND(Q{idx}=0,X{idx}=1),"转为未报告违约","连续未报告违约"))))))'])
panel=sheet('合并底稿',['公司','年度','行业','披露covenant','有一般covenant','有财务covenant','报告违反','生命周期原分类','经营现金流原值','投资现金流原值','融资现金流原值','契约表原行','阶段表原行','控制变量原行','标记一致性','可纳统0/1','报告违反0/1','本年匹配键','本年资格桥','本年违反桥','上一年匹配键','上一年记录数','上一年资格','上一年违反','连续年度状态'],rows)
controlrows=[]
for k in keys:
 i,r=ctrl[k];controlrows.append([k[0],k[1],*r[2:],i,'未修复、未用于财务排序'])
sheet('财务变量原值',['公司','年度','Tamanho原值','Alavancagem原值','Gerenciamento原值','收入变动原值','流动比率原值','原表行','口径状态'],controlrows)
issues=[]
for k in sorted(set(c)-valid):
 i,r=c[k];issues.append(['逻辑矛盾',k[0],k[1],filenames[2],i,'有一般covenant=Não，但有财务covenant=Sim；报告违反='+r[5],'保留原值；本次统计暂排除；不认定哪一列错误','需要发布者/原始公告或研究底稿核实'])
for label,j in [('Tamanho',2),('Alavancagem',3),('Liquiz Corrente',6)]:
 numeric=[float(str(r[j]).replace(',','.')) for _,r in tables[5]]
 issues.append(['数量级/口径未明','全样本',None,filenames[5],'列'+get_column_letter(j+1),f'{label}: min={min(numeric):.8g}; median={statistics.median(numeric):.8g}; max={max(numeric):.8g}','不自动补小数点、缩放或裁剪；不作为财务排序依据','需字段单位、导出规则及原始财务数据'])
gapkeys=[k for k in keys if (k[0],k[1]-1) not in c and any(n==k[0] and y<k[1]-1 for n,y in keys)]
issues.append(['观察缺口','全样本',None,'三张公司年度表','主键序列',f'{len(gapkeys)}条记录前方存在曾观察到的更早年份，但没有上一日历年','不把上次观察视为上一年；不把缺失当未违反','缺口原因与未收录年份材料'])
issues.extend([
 ['复现依赖','全样本',None,script.name,'import excel及缺失值筛选段','脚本引用Base de dados - Ciclo vs covenants.xlsx的Base Geral，附件中未提供','不能宣称已运行原始样本筛选及复现回归','需要原始Base Geral及原始会计字段/变量字典'],
 ['增长方向','全样本',None,script.name,'gen varAtivo及gen Cresc','varAtivo=Ativototal_t1-Ativototal，方向与常用本期减上期相反','保留原脚本定义，不静默替换；披露方向解释','需要原文变量定义确认'],
 ['样本外推','全样本',None,script.name,'drop if段及winsor段','脚本有披露、债务、现金流及财务covenant筛选，并有winsor操作','不将已发布面板当作原始总体，不重复宣称完成筛选','需要完整样本流水与已应用转换说明']])
sheet('异常与处置',['问题类型','公司/范围','年度','来源文件','来源定位','可核实证据','本次处置','进一步核实资料'],issues)
yearrows=[];metrics=dict(original_panel=len(c),eligible_panel=len(valid),excluded_panel=len(c)-len(valid),companies=len(company),reported_breaches=sum(c[k][1][5]=='Sim' for k in valid),original_reported_breaches=sum(r[5]=='Sim' for _,r in tables[2]),gap_records=len(gapkeys),year={},stages={},latest_transitions={})
for i,y in enumerate(range(2010,2019),2):
 eligible=[k for k in valid if k[1]==y];b=sum(c[k][1][5]=='Sim' for k in eligible);metrics['year'][str(y)]=dict(n=len(eligible),breach=b,rate=b/len(eligible))
 yearrows.append([y,f'=COUNTIF(\'合并底稿\'!$B$2:$B${N},A{i})',f'=SUMIF(\'合并底稿\'!$B$2:$B${N},A{i},\'合并底稿\'!$P$2:$P${N})',f'=SUMIF(\'合并底稿\'!$B$2:$B${N},A{i},\'合并底稿\'!$Q$2:$Q${N})',f'=IF(C{i}=0,"",D{i}/C{i})','公司年度计数；非平衡面板，不是相同公司群体的因果比较'])
y=sheet('年度趋势',['年度','原记录数','可纳统记录数','报告违反数','报告违反率','统计限制'],yearrows)
for row in range(2,11):y.cell(row,5).number_format='0.00%'
stagerows=[]
for i,name in enumerate(stage_names,2):
 j=stage_names.index(name);eligible=[k for k in valid if stage_by[k]==j];b=sum(c[k][1][5]=='Sim' for k in eligible);metrics['stages'][name]=dict(n=len(eligible),breach=b,rate=b/len(eligible));stagerows.append([name,stage_cn[j],f'=SUMIF(\'合并底稿\'!$H$2:$H${N},A{i},\'合并底稿\'!$P$2:$P${N})',f'=SUMIF(\'合并底稿\'!$H$2:$H${N},A{i},\'合并底稿\'!$Q$2:$Q${N})',f'=IF(C{i}=0,"",D{i}/C{i})','仅为已发布样本中的描述性关联；同公司重复观测；非因果或样本外概率'])
s=sheet('阶段分组',['原阶段','中文辅助标签','可纳统记录数','报告违反数','报告违反率','解释边界'],stagerows)
for row in range(2,7):s.cell(row,5).number_format='0.00%'
latest=[k for k in keys if k[1]==2018];metrics['latest_transitions']=dict(Counter(transitions[k] for k in latest));metrics['latest_count']=len(latest);late_rows=[];priority_for={};streak_for={}
for i,k in enumerate(latest,2):
 name,y=k;pr=row_for[k];tr=transitions[k];breach=c[k][1][5]=='Sim';prior=sum(c[kk][1][5]=='Sim' for kk in valid if kk[0]==name and kk[1]<2018)
 priority=0 if k not in valid else 1 if tr=='持续报告违约' else 2 if tr=='新增报告违约' else 3 if breach else 4 if tr=='转为未报告违约' else 5;priority_for[k]=priority
 streak=0;yr=2018
 while (name,yr) in valid and c[(name,yr)][1][5]=='Sim':streak+=1;yr-=1
 streak_for[k]=streak
 late_rows.append([name,company[name][1],pr,f"='合并底稿'!P{pr}",f"='合并底稿'!Q{pr}",f"='合并底稿'!Y{pr}",stage_names[stage_by[k]],prior,f'=IF(D{i}=0,0,IF(F{i}="持续报告违约",1,IF(F{i}="新增报告违约",2,IF(E{i}=1,3,IF(F{i}="转为未报告违约",4,5)))))','队列0待核隔离；1持续；2新增；3当年违反但可比性有限；4转未报告；5其他','需契约原文、测试日、阈值、豁免/补救、债务余额和最新财务材料',streak,1 if st[k][1][2]<0 else 0])
sheet('2018复核名单',['公司','行业','合并底稿行','可纳统0/1','当年报告违反0/1','连续年度状态','生命周期原分类','2018前有效历史违反年数','作者核查队列','队列含义','尚需取得资料','连续报告违反年数','当年经营现金流负值0/1'],late_rows)
late_counts=Counter(priority_for.values());metrics['latest_priority_counts']=dict(late_counts)
# Reproducible work ordering uses source-supported operating cash-flow signs and uninterrupted observed breach histories; no credit probability is invented.
short=sorted(latest,key=lambda k:(priority_for[k],-(st[k][1][2]<0),-streak_for[k],k[0]))[:10];metrics['first_review_ten']=[k[0] for k in short]
sheet('首批核查10家',['顺序','公司','行业','队列','状态','连续报告违反年数','经营现金流负值0/1','排序说明','关联证据'],[[i,k[0],company[k[0]][1],priority_for[k],transitions[k],streak_for[k],1 if st[k][1][2]<0 else 0,'队列升序；同级先经营现金流负值，再连续报告违反年数降序，最后公司名；是作者核查顺序，不是信用评级',f"合并底稿第{row_for[k]}行；契约原表第{c[k][0]}行"] for i,k in enumerate(short,1)])
book.save(OUT/'契约监测与数据核验.xlsx')
# Word reference memo reports the arithmetic and its professional limits.
doc=Document();sec=doc.sections[0];sec.top_margin=sec.bottom_margin=Inches(.7);sec.left_margin=sec.right_margin=Inches(.75);normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10);normal.element.rPr.rFonts.set(qn('w:eastAsia'),'等线')
doc.add_heading('企业财务契约监测：材料接收、2018复核名单与数据准入意见',0)
sections=[
 ('1. 交接结论',[
 '五份材料足以支持已发布样本中的公司年度关联、报告违反记录复核和历史资料核查队列；不足以支持当前信用评级、债务余额加权损失测算、契约法律违约认定或完整论文复现。建议先批准描述性监测底稿使用，将未解释财务控制变量和原始模型复现保持待核。',
 f'公司名录197家；三张年度表各1328条、覆盖2010—2018。按公司名与年度的键无重复、三表键集合一致，且全部能匹配行业。两条契约标记矛盾保留原值并暂不纳统，形成1326条一致性样本。它们并非经独立公司公告复核后的评级样本。',
 '本成果为AI试作参考，来源网站与原始文件已实际取得；尚无独立模型解题、专家验收或模型难度结果。']),
 ('2. 来源、关联与证据',[
 '来源是Harvard Dataverse同一资料页doi:10.7910/DVN/BGFTYG。2026-11-02实际获取官方元数据及全部5份文件，文件MD5及本地原件字节均一致。普通HTML页出现JavaScript验证，取证使用同站公开API，未声称已绕过或读取未取得网页内容。每份文件的稳定下载链接、哈希和取证时间见来源记录。',
 '公司名录从Planilha1第4行开始；契约和财务控制表从第4行开始；生命周期表为双层表头，从第5行开始。关联键仅做Unicode NFC和首尾空白规范化，没有模糊归并公司、改写原件或强制去重。合并底稿保存三张年度表各自原行号。公司名录的行号另列在公司名录表。',
 '3份年度表完整外键匹配，1328是公司年度记录数，197是公司名录数量；不同年份观测公司数不同。2018有170条记录，不能把197当作每年的统计分母。']),
 ('3. 质量闸门与控制变量限制',[
 '契约表第195行与197行均为Cia Hidro Eletrica Sao Francisco，年份分别2012及2014；有一般covenant为Não，却同时有财务covenant为Sim。前者报告违反为Não，后者为Sim。本次不猜测哪一格错误，两条保留且排除一致性口径；直接全量计数则为726条报告违反，暂排除后为725。',
 '财务控制表Tamanho混合14.89至1855299的量级，Alavancagem最大1451611，Liquiz Corrente最大6110017。原始文件可能涉及导出、缩放或字段定义问题，但没有足够资料确认原因。不能擅自把1470342写成14.70342，也不能把异常极值自动截尾后当作验证完毕。全部原值保留，不用于本次风险排序或金额比较。',
 '生命周期五个分类字段在各记录中恰有一个Sim。本成果沿用发布分类并展示现金流原值，未宣称以未提供的理论定义独立验证其全部分类。三类现金流的原始计量单位未在附件中得到充分说明，不作跨公司金额排名。']),
 ('4. 历史比例与其解释',[
 '一致性样本中的报告违反数为725，分母1326，报告违反率约54.68%。原始1328条含726条，比例约54.67%。两种口径必须同时交代，不能静默删除矛盾行。',
 '按一致性口径，2010为54/114，2011为59/120，2012为80/139，2013为83/147，2014为89/154，2015为77/156，2016为87/159，2017为99/167，2018为97/170。2018约57.06%，2017约59.28%，差约-2.22个百分点；这不是同一组公司的状态改善证明。',
 '阶段分组为导入60/136、成长224/403、成熟359/628、震荡59/112、衰退23/47。成熟组约57.17%，成长约55.58%；这里是已筛选样本的描述性关联，同公司跨年重复出现，不能转成生命周期造成违约或未来违约概率。不同阶段及行业构成也可能变化。']),
 ('5. 2018核查队列与连续年度',[
 '2018的170家公司年度中，持续报告违反87、在可比上年未违反后新增报告违反5、转为未报告违反9、连续未报告违反58、没有连续上年记录11。必须只比较同公司上一日历年；全样本有16条记录在更早年度出现过、但缺少紧邻上一年，这些不能用上一次观察填补。',
 '2018有97条报告违反，其中87持续、5新增，另5条缺少连续上年记录；其余6条无连续上年记录的当年未报告违反。没有上年记录不等于新增违反，也不等于过去从未违反。',
 '作者核查队列按持续报告违反、可比新增报告违反、当年违反但连续可比性不足、转未报告违反及其他安排。矛盾行单设隔离队列，不当作经济风险高低。同队列优先核查当年经营现金流为负的记录，再按连续报告违反年数降序，最后以公司名称打破同分；全部为作者明示的资料核查规则，现金流仅使用符号，不假定其货币单位或风险系数。首批10家不是已验证的最危险10家；完整170家名单与证据行全部交付，避免只交付不透明名单。',
 '核查需取得实际契约、触发阈值、测试日期、豁免或补救、未偿债务、交叉违约及当前财务数据。现有表中报告违反不能替代法律违约认定；也没有证据据此确认加速到期、损失或处置权限。']),
 ('6. 研究脚本可复现性',[
 'Stata脚本首先导入未随附的Base de dados - Ciclo vs covenants.xlsx的Base Geral，并引用Ativototal、CtaRec、Imobil、RsReav、LAIR等原始会计变量。当前发布的分类与控制变量表不足以重新执行所有筛选、Jones残差、滞后变量和回归。缺文件要具体列出，不能把发布的最终控制值等同于全部底层原始数据。',
 '脚本包含duplicates drop ID ANO, force、destring replace force和多轮缺失、披露、负债、现金流及财务covenant筛选，还实施winsor。它们是原作者程序中的操作，不代表我们已获得足够输入或已执行；强制去重也不是本次静默删行的依据。',
 '脚本用Ativototal_t1-Ativototal定义varAtivo，再除以上期资产构造Cresc，其方向与常见本期减上期增长率相反。应保留原定义并要求确认，不能为迎合直觉改符号。已发布样本存在选择限制，不能将描述关联解释为因果效应。']),
 ('7. 下一步交接与适用范围',[
 '先向数据发布者核实两条契约标记冲突，以及Tamanho、杠杆和流动比率的单位与导出规则。再取得完整Base Geral、变量字典和筛选流水，才能评估是否启动模型复现。财务字段未解释前，暂不批准用它们生成客户或发行人风险评分。',
 '可立即交接的是逐行可追溯面板、透明分母的历史统计、完整2018核查名单及待核问题。若取得新材料，应保存版本、哈希、变更理由和前后口径；不得以之后事件无提示重写2018时点结论。'])]
for heading,paragraphs in sections:
 doc.add_heading(heading,1)
 for para in paragraphs:doc.add_paragraph(para)
sec.footer.paragraphs[0].text='AI试作参考｜非专家验收｜历史研究用途'
doc.save(OUT/'研究准入与复核备忘录.docx')
metrics['source_hashes']=sourcehash;metrics['formula_count']=sum(cell.data_type=='f' for s in book for row in s for cell in row);(OUT/'核算结果.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2));(OUT/'source_audit.json').write_text(json.dumps(dict(key_counts={str(n):len(indices[n]) for n in indices},master_count=len(company),duplicate_keys=0,unmatched_keys=0,invalid_covenant_rows=[dict(company=k[0],year=k[1],source_row=c[k][0]) for k in sorted(set(c)-valid)],gaps=[dict(company=k[0],year=k[1]) for k in gapkeys]),ensure_ascii=False,indent=2));print(json.dumps(metrics,ensure_ascii=False))
