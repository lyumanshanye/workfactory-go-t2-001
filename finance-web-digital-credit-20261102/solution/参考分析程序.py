from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import csv,json,hashlib,statistics
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment
from openpyxl.utils import get_column_letter
from docx import Document
from docx.shared import Pt,Inches
from docx.oxml.ns import qn
I=Path('/input');O=Path('/work/output');O.mkdir(exist_ok=True)
data=next(I.glob('*banco*'));dictionary=next(I.glob('*dicionario*'));rows=list(csv.DictReader(data.open(encoding='utf-8-sig',newline='')));defs=list(csv.DictReader(dictionary.open(encoding='utf-8-sig',newline='')));assert len(rows)==1000 and len({r['id'] for r in rows})==1000
floatv=lambda x:float(x) if x else None
yes=lambda x:x in ['1','1.0']
keys=list(rows[0]);p21=[k for k in keys if k.startswith('P21_')];p39=[k for k in keys if k.startswith('P39_')];channels=['ligacoes','whatsapp','app','sms','agencia','email'];book=Workbook();book.remove(book.active)
def sheet(name,head,data):
 s=book.create_sheet(name);s.append(head)
 for row in data:s.append(row)
 s.freeze_panes='A2';s.auto_filter.ref=s.dimensions;s.sheet_view.zoomScale=85
 for row in s:
  for c in row:
   c.alignment=Alignment(vertical='top',wrap_text=True);c.font=Font(name='Calibri',size=10)
   if c.row==1:c.fill=PatternFill('solid',fgColor='1D443D');c.font=Font(name='Calibri',size=10,bold=True,color='FFFFFF')
  s.row_dimensions[row[0].row].height=32
 for j in range(1,s.max_column+1):s.column_dimensions[get_column_letter(j)].width=25
 s.page_setup.orientation='landscape';s.page_setup.fitToWidth=1;s.sheet_properties.pageSetUpPr.fitToPage=True
 return s
computed=[];audit=Counter();group=Counter();base70=Counter();base80=Counter();risk_rows=[]
for i,r in enumerate(rows,2):
 p=[float(r['prob_c'+str(j)]) for j in range(1,4)];order=sorted(range(3),key=lambda j:(-p[j],j));best='c'+str(order[0]+1);orig='c'+r['cluster'].split()[1];wide='mixed' if r['cluster_amplo']=='Misto' else r['cluster_amplo'].split()[0];c70=best if max(p)>=.7 else 'mixed';c80=best if max(p)>=.8 else 'mixed';raw21=sum(yes(r[k]) for k in p21);raw39=sum(yes(r[k]) for k in p39);nactive=float(r['n_dividas_ativas']);nlate=float(r['n_contas_atraso']);total=float(r['n_propostas_total']);channel_sum=sum(float(r['n_propostas_'+s]) for s in channels)
 audit['prob_sum_invalid']+=abs(sum(p)-1)>1e-10;audit['hard_mismatch']+=best!=orig;audit['wide70_mismatch']+=c70!=wide;audit['offer_sum_mismatch']+=channel_sum!=total;audit['debt_count_mismatch']+=raw21!=nactive;audit['debt_any_mismatch']+=(raw21>0)!=(nactive>0);audit['late_equals_all_options']+=raw39==nlate;audit['p39_any']+=raw39>0;audit['p39_blank']+=raw39==0;audit['published_active_positive']+=nactive>0;audit['raw_p21_positive']+=raw21>0;audit['small_margin']+=p[order[0]]-p[order[1]]<.1;group[orig]+=1;base70[c70]+=1;base80[c80]+=1
 computed.append(dict(id=int(r['id']),best=best,c70=c70,c80=c80,p39=raw39,published_active=nactive>0,raw_active=raw21>0))
 risk_rows.append([int(r['id']),i, *p,f'=SUM(C{i}:E{i})',f'=MAX(C{i}:E{i})',f'=MAX(C{i}:E{i})-MEDIAN(C{i}:E{i})',orig,f'=IF(C{i}>=MAX(D{i}:E{i}),"c1",IF(D{i}>=E{i},"c2","c3"))',f'=IF(I{i}=J{i},1,0)',wide,f'=IF(G{i}>=0.7,J{i},"mixed")',f'=IF(L{i}=M{i},1,0)',f'=IF(G{i}>=0.8,J{i},"mixed")',f'=IF(M{i}<>O{i},1,0)',raw21,nactive,f'=IF(Q{i}=R{i},1,0)',f'=IF((Q{i}>0)=(R{i}>0),1,0)',raw39,nlate,f'=IF(U{i}=V{i},1,0)',total,channel_sum,f'=IF(X{i}=Y{i},1,0)',r['cluster_amplo']])
N=len(rows)+1
panel=sheet('逐行复核',['匿名ID','源CSV行','prob_c1','prob_c2','prob_c3','概率和','最大概率','前两类概率差','发布最大类','复算最大类','最大类一致0/1','发布70%标签','复算70%标签','70%一致0/1','作者80%标签','70到80迁移0/1','P21代码1计数','发布活动债务数','计数一致0/1','有无二元一致0/1','P39全部选项计数','发布逾期账户数','二者相等0/1','发布总报价数','六渠道报价求和','报价求和一致0/1','发布原标签'],risk_rows)
sheet('使用与来源',['事项','说明'],[
 ['作者性质','AI候选参考；未独立盲解、未专家验收、未校准难度。'],['原件','1份匿名调查CSV（原扩展名.tab）、1份变量字典CSV（原扩展名.tab）、1份原始问卷PDF。'],['范围','2025年巴西互联网可达人群C/D/E阶层的公开调查样本；仅样本内未加权分析。'],['真实下载','官方原始格式PDF和字典已取得。主数据刷新出现IncompleteRead，复用未经改写的本地原件，并与当前官方目录MD5逐字节校验。没有冒称刷新下载完整成功。'],['阈值','70%来自发布字典；60%、80%、90%是作者敏感性，不是已审批业务标准。'],['概率含义','潜在类别归属概率，不是逾期概率、还款能力或授信分。'],['债务指标','保留发布值，并与原始题项作关系核验；不将派生逾期数直接当作真实逾期户数。'],['用途','条件化客户教育/债务支持研究方案，非个人授信、定价或催收指令。'],['缺失','P39全空331行表示未观察到该题块回答；不能默认无逾期。'],['问卷限制','PDF选项文字与字典的P39列名并非一一完整对应，需作者编码表才能确认全部选项到列的映射。']])
fields={x['Variável']:x for x in defs};wanted=['cluster','cluster_amplo','prob_c1','prob_c2','prob_c3','n_dividas_ativas','n_contas_atraso','n_propostas_total']+p21+p39
sheet('字段与证据',['字段','字典说明','字典有效N','字典缺失N','本次用途'],[[k,fields.get(k,{}).get('Pergunta / Descrição',''),fields.get(k,{}).get('N válido',''),fields.get(k,{}).get('N missing',''),'原始字段/计算核验；问卷题块对应另核'] for k in wanted])
thresholds={};tr=[]
for idx,t in enumerate([.6,.7,.8,.9],2):
 c=Counter(x['best'] if max(float(rows[j]['prob_c'+str(q)]) for q in range(1,4))>=t else 'mixed' for j,x in enumerate(computed));thresholds[str(t)]=dict(c)
 tr.append([t]+[f'=COUNTIFS(\'逐行复核\'!$J$2:$J${N},"{cl}",\'逐行复核\'!$G$2:$G${N},">="&A{idx})' for cl in ['c1','c2','c3']]+[f'=COUNTIF(\'逐行复核\'!$G$2:$G${N},"<"&A{idx})',f'=SUM(B{idx}:E{idx})','字典基线' if t==.7 else '作者敏感性'])
sheet('置信度敏感性',['阈值','c1人数','c2人数','c3人数','mixed人数','合计','来源属性'],tr)
groups=[];group_metrics={}
for cl in ['c1','c2','c3']:
 ids=[j for j,x in enumerate(computed) if x['best']==cl];act=sum(computed[j]['published_active'] for j in ids);rawact=sum(computed[j]['raw_active'] for j in ids);offers=sum(float(rows[j]['n_propostas_total'])>0 for j in ids);group_metrics[cl]=dict(n=len(ids),published_active_positive=act,raw_p21_positive=rawact,offer_positive=offers,pure70=base70[cl],pure80=base80[cl]);groups.append([cl,len(ids),base70[cl],base80[cl],act,rawact,offers,'活动债务两种口径并列，不以类标签推断真实逾期。'])
for ri,row in enumerate(groups,2):
 row[1:7]=[f'=COUNTIF(\'逐行复核\'!$I$2:$I${N},A{ri})',f'=COUNTIF(\'逐行复核\'!$M$2:$M${N},A{ri})',f'=COUNTIF(\'逐行复核\'!$O$2:$O${N},A{ri})',f'=COUNTIFS(\'逐行复核\'!$I$2:$I${N},A{ri},\'逐行复核\'!$R$2:$R${N},">0")',f'=COUNTIFS(\'逐行复核\'!$I$2:$I${N},A{ri},\'逐行复核\'!$Q$2:$Q${N},">0")',f'=COUNTIFS(\'逐行复核\'!$I$2:$I${N},A{ri},\'逐行复核\'!$X$2:$X${N},">0")']
sheet('分群画像',['类别','最大类N','70%纯类N','80%纯类N','发布活动数>0人数','P21存在代码1人数','报价数>0人数','解释限制'],groups)
migration=[];mc=Counter((x['c70'],x['c80']) for x in computed)
for a in ['c1','c2','c3','mixed']:
 for b in ['c1','c2','c3','mixed']:migration.append([a,b,mc[a,b]])
for ri,row in enumerate(migration,2):row[2]=f'=COUNTIFS(\'逐行复核\'!$M$2:$M${N},A{ri},\'逐行复核\'!$O$2:$O${N},B{ri})'
sheet('70到80迁移',['70%类别','80%类别','人数'],migration)
issues=[['表格格式','两份.tab原件实际为CSV，须按内容识别分隔符','不改原件，不按扩展名当TSV读取'],['权重','数据有163列，没有权重字段；元数据描述样本加权','不反推个人权重；仅报样本未加权比例，不套总体3个百分点误差'],['活动债务数量',f'发布数与已保留P21代码1总数有{audit["debt_count_mismatch"]}行不一致；有无二元比较有{audit["debt_any_mismatch"]}行不一致','保留两种口径并索取完整选项、衍生算法，不能擅自指定哪个才是真值'],['逾期派生数',f'全部1000行发布n_contas_atraso等于P39全部15个选项的勾选数；有回答{audit["p39_any"]}、全空{audit["p39_blank"]}','PDF列有不知道/没有等非逾期选择；P39字典列标签不完整，不直接把勾选总数当逾期数'],['问卷路由','P29/33及P39—42存在跳题与非回答；P39只展示前序部分选择','结构性空白与明确否定分开，不能全表空白填0后计算逾期率'],['编码字典','P39各列说明被截断、缺少逐列选项标签；问卷选项与导出列不完全可读对应','不凭列序猜测哪一列就是没有或不知道，先取得作者代码本'],['模型解释','只提供类别概率及标签，未给原拟合对象、参数和独立留出验证','只核验标签/概率关系，不宣称重估潜在类别或已验证预测表现']]
sheet('指标准入问题',['问题','实证证据','处置'],issues)
plan=[['A. 内部复核','可开展','用1000条样本复算最大类别、70%标签及60/80/90敏感性；群体匿名汇总，不把类别当信用等级。','全部数据与字典；无需新增事实'],['B. 研究候选分层','条件可开展','70%纯类及mixed并列，提供80%敏感性。mixed单设待进一步问卷澄清的研究层，不丢弃。','获得合法且实际的后续研究接触条件后另行安排；本题不假定已能联系匿名ID'],['C. 债务支持需求','需补证','先核实P21派生算法、P39列码及跳题，再制定债务负担/逾期类支持口径。','完整代码本、原问卷实施版本、数据清洗及派生脚本'],['D. 试点评估','方案待批准','预先定义理解度、对成本/还款信息的识别、求助渠道理解及退出/缺失记录；未采集前不填改善率或统计显著性。','实际样本框、同意流程、预算、分配方式和事前评价方案；不虚构已进行实验'],['E. 资源安排','待真实约束','给出分层人数和可能的阈值敏感性，预算与每层名额未提供时保持待定。','真实预算和执行容量，不补造固定资源总数']]
sheet('试点建议与依赖',['阶段','建议状态','具体安排','依赖及缺口'],plan)
assert audit['hard_mismatch']==0 and audit['wide70_mismatch']==0
book.save(O/'分群与债务指标复核.xlsx')
metrics=dict(n=len(rows),columns=len(keys),dict_rows=len(defs),audit=dict(audit),hard_groups=dict(group),thresholds=thresholds,groups=group_metrics,migration=[dict(old=a,new=b,n=n) for (a,b),n in mc.items()],migrated70to80=sum(x['c70']!=x['c80'] for x in computed),source_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in I.iterdir() if f.is_file()},formula_count=sum(c.data_type=='f' for s in book for row in s for c in row))
doc=Document();sec=doc.sections[0];sec.top_margin=sec.bottom_margin=Inches(.7);normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10);normal.element.rPr.rFonts.set(qn('w:eastAsia'),'等线');doc.add_heading('消费信贷分群复核与客户支持试点建议',0)
sections=[('1. 给研究负责人的结论',[
 '现有材料可支持样本内分群标签重算、置信度敏感性及群体研究方案；不足以直接按发布的逾期账户数投放债务支持，也不足以作个人信用或授信决策。建议先通过分群口径的技术复核，再补齐债务变量编码，后者为试点实施前置依赖。',
 '采用同一Harvard Dataverse资料页6RK7RD的原始调查、变量字典及三页问卷。主数据1000条、163列、匿名ID唯一。原扩展名.tab的两份文件实际是CSV；原件没有改名或改写。']),('2. 分群结果与阈值',[
 f'三列概率的和及取值已复核，最大概率类别与发布cluster逐条一致，字典所定义的70%纯类/mixed也逐条一致。最大类人数为c1=186、c2=396、c3=418。这是发布数据内部一致性，不是模型对外部真实行为的预测正确率。',
 '70%阈值下c1=171、c2=347、c3=337、mixed=145；80%下分别152、304、290、254。109条从原纯类转为mixed，其中c1为19、c2为43、c3为47。不能只看纯类内部的构成变化，忽略被移出的109条。',
 '60%下mixed为64，90%下mixed为388。最大两类概率差小于0.1的有32条，说明一部分标签归属较不稳定。60%、80%、90%及0.1间隔为作者敏感性，70%才是字典原定义；比较前不任意四舍五入概率。']),('3. 债务与营销指标为什么需要隔离',[
 f'发布活动债务数与保留的P21代码1数量有{audit["debt_count_mismatch"]}条不同，有无二元关系也有{audit["debt_any_mismatch"]}条不同。发布值大于0为{audit["published_active_positive"]}人，P21存在代码1为{audit["raw_p21_positive"]}人。缺少完整编码与派生脚本时，不能擅自把任一口径宣布为真实债务数。',
 '发布n_contas_atraso在全部1000行都等于P39全部15列勾选数。有P39回答为669人，全空为331人；发布的该数大于0也为669人。问卷明确包括不知道、没有等特殊选项，故勾选数不等于真实逾期账户数。当前字典对P39列的说明截断，没有逐项完整标签，不能根据列序猜测并删除最后两列后宣布完成修复。',
 'P29及P33等问题存在跳题；P39—42题块的非回答也需要区分条件资格与实际作答。问卷不能机械替代实际导出编码。P39空白不直接填为明确无逾期；特殊选项也不视作一项违约。',
 '六类渠道的发布报价数求和与n_propostas_total逐条一致，说明该指标能做内部算术描述。但收到报价既不是实际借款，也不是贷款转化率或逾期原因，不据此作因果推断。']),('4. 样本画像及其限度',[
 '按最大类统计，c1有186条，发布活动债务数大于0的170条，收到报价137条；c2分别396、300、320；c3分别418、199、272。债务数字带上述待核口径，仅作发布字段描述，不能推成经验证的债务压力排序。',
 '这批数据来自针对巴西中低社会经济阶层且可接入互联网人群的2025调查，元数据说明采用加权，但附件没有提供个人权重字段。本成果仅报样本未加权计数与比例，不假装再现加权总体估计，也不将元数据的总体误差说明移用于各小组。',
 '类别名称是研究者潜在类别标签，不是人格结论、偿还能力或逾期概率。置信度上升意味着归属判断更明确，不意味着信用更好；只比较高置信度样本也可能改变构成。']),('5. 建议的研究试点与决策依赖',[
 '第一阶段可在内部使用样本复核分群与信息呈现：保留70%原分层及mixed，另给80%敏感性。mixed作为研究中需进一步澄清信息的层保留，不为整齐而删除。此处不认定匿名ID就是本机构客户或可实际联系的人。',
 '债务支持试点应先取得完整P21/P39选项编码、实际实施版问卷、清洗/派生脚本和权重说明，再决定需求分层。禁止依现有派生逾期数宣称已识别所有逾期客户。',
 '在有真实样本框、同意、预算和执行能力后，事前确定试点评价：成本与还款信息理解度、求助路径识别、参与/退出及缺失记录。实验分配、样本量、每层名额和改善率没有给定，均不填造；不声称已经实施随机实验或取得效果。']),('6. 来源与当前验证状态',[
 '资料页doi:10.7910/DVN/6RK7RD由用户指定Harvard目录中的数据集发现。官方目录、PDF及原始字典取得成功；主数据网络刷新发生IncompleteRead，使用未经改写的用户目录原件，并与当前官方目录原始MD5核验一致。原始格式CSV与默认TSV转换是两种表示，未把它们的哈希差异当作造假，也未冒称刷新成功。',
 '本成果由AI直接构题和编写参考程序；来源回执、程序及实际执行时长另存。未运行独立解题rollout、专家验收或难度校准，不能把本程序的短运行时间视为题目解题耗时。'])]
for title,paras in sections:
 doc.add_heading(title,1)
 for s in paras:doc.add_paragraph(s)
doc.save(O/'试点决策备忘录.docx');(O/'核算结果.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2));print(json.dumps(metrics,ensure_ascii=False))
