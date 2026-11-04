#!/usr/bin/env python3
"""闭卷复核；运行 python review.py --input /app/input_files --output /work/output"""
import argparse, json, re, math, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from docx import Document
from docx.shared import Pt, Inches

IDS=['81100_69','3612156_42','6931942_17','5655150_280','11341177_13','6139418_72','11644460_32','1313717_86','12122490_155','5861465_62','6215707_64','8210237_68']
LABELS=['FORMAL','GRAND','NONE']
def period(y):
 return '1870–1936' if y<=1936 else '1937–1980' if y<=1980 else '1981–2024'
def metrics(d):
 n=len(d); res={'n':n,'accuracy':round((d['class']==d.predicted_label).mean(),4) if n else None}
 f=[]
 for c in LABELS:
  tp=((d['class']==c)&(d.predicted_label==c)).sum();support=(d['class']==c).sum(); predicted=(d.predicted_label==c).sum()
  pr=tp/predicted if predicted else 0;rc=tp/support if support else 0;f1=2*pr*rc/(pr+rc) if pr+rc else 0
  res[c+'_support']=int(support);res[c+'_precision']=round(pr,4);res[c+'_recall']=round(rc,4);res[c+'_f1']=round(f1,4);f.append(f1)
 res['macro_f1']=round(sum(f)/3,4);return res
def wb_sheet(w,name,df,limit=None):
 ws=w.create_sheet(name); cols=list(df.columns);ws.append(cols)
 for row in df.head(limit).itertuples(index=False,name=None) if limit else df.itertuples(index=False,name=None):
  ws.append([None if pd.isna(v) else (str(v)[:1400] if isinstance(v,str) else (v.item() if isinstance(v,np.generic) else v)) for v in row])
 ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
 for c in ws[1]:c.font=Font(bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='153D57')
 for col in ws.columns:
  letter=col[0].column_letter;ws.column_dimensions[letter].width=min(62,max(13,max(len(str(c.value or '')) for c in list(col)[:75])+2))
 return ws
def clean(x):return re.sub(r'\s+',' ',str(x)).strip()
def make_doc(out,summary,records,performance,trend,join):
 doc=Document();sec=doc.sections[0];sec.top_margin=Inches(.7);sec.bottom_margin=Inches(.65)
 style=doc.styles['Normal'];style.font.name='宋体';style.font.size=Pt(10);style.paragraph_format.space_after=Pt(5)
 doc.add_heading('最高法院推理分析工具｜法律研究采纳审查',0)
 doc.add_paragraph('会议用独立意见 · 2026年材料闭卷复核 · 决定：附条件试用（历史研究辅助，不上线为律师独立精读筛选器）')
 doc.add_heading('一、决定及法律边界',1)
 doc.add_paragraph('允许：1870—2024年美国最高法院意见的探索性年代比较、已知判决集合的排序及人工复核候选线索。禁止：把形式／宏观（grand）／无（none）当作案件裁判结论、判决效力、法条解释正确性、判例拘束力、当前有效法律或律师检索的排他过滤标准。律师必须查完整多数意见、协同／异议意见、引文和后续权威资料；该指标不能替代对裁判理由与法律权威的判断。')
 doc.add_paragraph('分类单位是裁判意见中经筛选的段落；zformal是意见段落分数标准化后的一项测量，并非案件全部理由的裁判标签。论文附录将FORMAL定义为封闭规则推演，GRAND为开放考虑政策、社会、经济，NONE包含未呈现清晰推理等情形。注释者对低置信度文本协商标签，且被要求不凭整份意见补入上下文；律师精读反而须读上下文。')
 doc.add_heading('二、证据及口径',1)
 doc.add_paragraph(f"原件：paper.pdf（第9–15、18–19页）、supplement.pdf（codebook）；legal_reasoning_annotations.csv {summary['annotations']}条段落，annotation_predictions.csv {summary['pred_rows']}行、{summary['pred_ids']}个section_id、{summary['folds']}个test_num；reasoning.csv {summary['opinions']}行意见，{summary['cases']}个project_case_id，年度 {summary['minyear']}–{summary['maxyear']}；sc_data.csv意见连接结果见工作簿。missing_data.csv列{summary['missing']}条匹配缺项，不应当作全部缺失案件数。")
 doc.add_paragraph(f"预测文件为同一section_id跨折重复的测试输出，并非9070份独立专家标注；同test_num逐项评分，或先对每个section_id按多数票汇总（替代口径）；不能在9070行上做独立性检验。注释连接：{join['matched']}条预测均能以section_id连到标注；未出现于预测的标注{join['unpred']}条。logit列虽名为prob_，含负数且不和为1，熵计算必须先softmax。")
 doc.add_paragraph(f"逐折宏F1均值 {performance['fold_macro_mean']:.3f}（本地10折，按每折计算再平均）；去重多数票宏F1 {performance['vote_macro']:.3f}，准确率 {performance['vote_acc']:.3f}。重复折非十个独立外部样本；eval_crossfold_output.csv独立存的是三种模型随训练样本比例的既有指标，无法从仅有的本地预测重新验证其训练与测试切分。表内 LEGAL-BERT 全量macro_f1均值 {performance['eval_macro']:.3f}（含汇总行时不可误作独立分割），见工作簿对照。")
 doc.add_paragraph(f"本地逐折去重熵（自然对数）低置信度均值 {performance['lc_entropy']:.3f}、其余 {performance['nlc_entropy']:.3f}，差 {performance['entropy_diff']:.3f}；低置信度准确率 {performance['lc_acc']:.3f} vs 非低置信度 {performance['nlc_acc']:.3f}。论文p.19报告熵差0.250及置换p<0.0001；本地文件的跨折logits、测试子集与论文使用的全模型预测并不必一致；不得以这项比较声称已独立验证其置换实验或模型校准。")
 doc.add_heading('三、Figure 9 历史描述复核',1)
 doc.add_paragraph('按作者4_measure_formal.py，意见分数为段落[(pFORMAL−pGRAND)×(pFORMAL+pGRAND)]的均值后标准化；reasoning.csv仅含最终zformal，不含逐段推断所需完整logits。本审计可重算给定意见分数的年度统计，不能重新计算逐段评分或证明断点显著性。原论文Figure 9是年度意见等权均值；本审计另以同一project_case_id内意见均分后按案件等权，并以仅多数意见（含per_curiam另单列，不并入）比较。')
 for x in trend:doc.add_paragraph(x)
 doc.add_paragraph('关键限制：本地三口径后期(1981–2024)总体均值均低于0，不能支持论文所述“1980年代后始终形式主义占主导”的强表述；尽管相较1937–1980均值回升，这并不等于翻正，亦不能推断1937为唯一显著断点。各口径年度完整序列及三段时期均值在工作簿；以正负判断“主导”仅为此数据的标准化零点，且多数意见筛选会减少不同年代的意见，历史拐点和当前实务不应由图形外推成因果结论。')
 doc.add_heading('四、争议文本精读规则与核验',1)
 doc.add_paragraph('有目的选取：固定test_num=0、专家与模型不一致、含低置信度，覆盖1870—1936、1937—1980、1981—2014；优先兼顾FORMAL/GRAND/NONE与多数、协同、异议意见；用case_url数字定位sc_data与reasoning意见，以未遮蔽原文短语定位并抽取前后文。不能把此争议样本当作随机误差估计。遇文本不匹配或同案多意见一律明示；协议标签与上下文法律判断分栏。')
 for rec in records:
  doc.add_heading(f"{rec['year']} · {rec['name']} [{rec['section_id']}]",2)
  doc.add_paragraph(f"原件：reasoning.csv.opinion_text（sc_data.csv同意见键可交叉查验），{rec['project_opinion_id']}，{rec['opinion_type']}，字符位{rec['offset']}（0起，-1为未精确匹配），case_url {rec['url']}；折0 专家{rec['class']}、模型{rec['predicted_label']}、低置信{rec['low_confidence']}。")
  doc.add_paragraph('原文：“'+rec['quote']+'”')
  doc.add_paragraph('复核：'+rec['legal_reason']+' 协议层：'+rec['protocol_note']+'。影响：'+rec['impact'])
 doc.add_heading('五、上线闸门及证据空白',1)
 for x in ['研究管理员锁定版本、来源和连接键，保留所有原始标签及模型分数；按年代、意见类型及类别抽独立新案标注，至少双人盲评并裁决歧义，固定不可用于训练的测试集，记录召回率、误排率与置信区间。','律师筛选不得只显示模型判定：必须显示完整意见和原文位置、异议／协同身份、低置信及NONE；低置信、不一致、无法定位、影响争点的段落强制人工精读，负标签不得静默剔除。上线阈值须由业务方事前设定（例如关注GRAND的漏检上限），未达则停止用于排序。','跨法律领域：训练采样重点是法条解释段落，宪法、程序及其他领域须单列盲测；跨法域：没有本地独立标注，不能推定能迁移；当前实务：材料只覆盖至2024且没有后续先例追踪，不提供现行法判断。模型权重与逐段完整预测不在本地原件，不能独立重训、重跑或验证每条意见的推断；原代码与历史标签可审计的范围限于现有输出。']:
  doc.add_paragraph('• '+x)
 doc.add_paragraph('证据出处：输入原件名称和复核代码详见工作簿「来源」、「说明」；逐案文字与原件字段逐项保存在case_analysis.json。')
 doc.save(out/'法律研究工具审查意见.docx')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',default='/app/input_files');ap.add_argument('--output',default='/work/output');ar=ap.parse_args();p=Path(ar.input);out=Path(ar.output);out.mkdir(parents=True,exist_ok=True)
 a=pd.read_csv(p/'legal_reasoning_annotations.csv');pred=pd.read_csv(p/'annotation_predictions.csv');ev=pd.read_csv(p/'eval_crossfold_output.csv');miss=pd.read_csv(p/'missing_data.csv')
 # one label per section; duplicates across folds and their effect recorded
 d=pred.merge(a[['section_id','url','name','year','date','class','low_confidence']],on='section_id',suffixes=('_pred',''))
 d=d.rename(columns={'class_pred':'class_file','low_confidence_pred':'lc_file','class':'class_annotation','low_confidence':'lc_annotation'});d['class']=d['class_annotation'];d['low_confidence']=d['lc_annotation']
 d['period']=d.year.map(period);d['correct']=d['class']==d.predicted_label
 logits=d[['prob_GRAND','prob_NONE','prob_FORMAL']].to_numpy(dtype=float).copy();logits-=logits.max(axis=1,keepdims=True);pr=np.exp(logits);pr/=pr.sum(axis=1,keepdims=True);d['entropy']=-(pr*np.log(pr)).sum(axis=1)
 folds=pd.DataFrame([dict(test_num=k,**metrics(g)) for k,g in d.groupby('test_num')]);v=d.sort_values('test_num').drop_duplicates('section_id').copy(); vote=d.groupby('section_id').predicted_label.agg(lambda x:x.value_counts().index[0]);v['predicted_label']=v.section_id.map(vote);v['correct']=v['class']==v.predicted_label
 perf=[]
 for (key,val),g in [(('sample','all rows'),d),(('sample','one first fold'),v.sort_values('test_num').assign(predicted_label=v.sort_values('test_num').section_id.map(d[d.test_num==0].set_index('section_id').predicted_label)).dropna(subset=['predicted_label'])),(('sample','unique majority vote'),v)]:perf.append(dict(group=key,segment=val,**metrics(g)))
 for (k,seg),g in d.groupby(['period','low_confidence']):perf.append(dict(group='period × LC',segment=f'{k} / {seg}',**metrics(g)))
 for k,g in d.groupby('low_confidence'):perf.append(dict(group='LC',segment=str(k),**metrics(g)))
 for k,g in d.groupby('period'):perf.append(dict(group='period',segment=k,**metrics(g)))
 for k,g in d.groupby('test_num'):perf.append(dict(group='fold',segment=str(k),**metrics(g)))
 perf=pd.DataFrame(perf); entropy=d.groupby('low_confidence').agg(rows=('entropy','size'),mean_entropy=('entropy','mean'),accuracy=('correct','mean')).reset_index();entropy_unique=v.groupby('low_confidence').agg(ids=('entropy','size'),mean_entropy=('entropy','mean'),accuracy=('correct','mean')).reset_index()
 confusion=d.groupby(['class','predicted_label']).size().rename('n').reset_index();eval_summary=ev.groupby(['model','percentage','split'],dropna=False).agg({'macro_f1':'mean','grand_f1':'mean','formal_f1':'mean','none_f1':'mean'}).reset_index()
 # read source in chunks; capture opinion metadata only (avoid storing enormous text)
 meta=[];raw=[]; url_ids={int(s.split('_')[0]) for s in IDS}
 for ch in pd.read_csv(p/'reasoning.csv',chunksize=2500,usecols=['project_case_id','project_opinion_id','case_url','case_name','citations','year','opinion_type','opinion_text','zformal','source','scdbCaseId']):
  for t in ch.itertuples(index=False):
   meta.append((t.project_case_id,t.project_opinion_id,t.year,t.opinion_type,t.zformal,t.source,t.scdbCaseId,t.case_url))
   if re.search(r'/cases/(\d+)/',str(t.case_url)) and int(re.search(r'/cases/(\d+)/',str(t.case_url)).group(1)) in url_ids:
    raw.append(dict(zip(ch.columns,t)))
 r=pd.DataFrame(meta,columns=['project_case_id','project_opinion_id','year','opinion_type','zformal','source','scdbCaseId','case_url']);raw=pd.DataFrame(raw)
 annual=r.groupby('year').agg(opinion_mean=('zformal','mean'),opinions=('zformal','size'),cases=('project_case_id','nunique')).reset_index()
 ca=r.groupby(['year','project_case_id'],as_index=False).zformal.mean();annual=annual.merge(ca.groupby('year').zformal.mean().rename('case_mean'),on='year');maj=r[r.opinion_type=='majority'];annual=annual.merge(maj.groupby('year').zformal.agg(majority_mean='mean',majority_n='size'),on='year',how='left');annual['opinion_minus_case']=annual.opinion_mean-annual.case_mean;annual['period']=annual.year.map(period)
 period_means=pd.concat([r.assign(period=r.year.map(period)).groupby('period').zformal.agg(mean='mean',count='size').assign(denominator='all opinions'),ca.assign(period=ca.year.map(period)).groupby('period').zformal.agg(mean='mean',count='size').assign(denominator='cases after within-case mean'),maj.assign(period=maj.year.map(period)).groupby('period').zformal.agg(mean='mean',count='size').assign(denominator='majority opinions only')]).reset_index()
 # source comparison join by stable project opinion identifier, not case citation
 scmeta=[];scraw=[]
 for ch in pd.read_csv(p/'sc_data.csv',chunksize=2500,usecols=['project_case_id','project_opinion_id','case_url','opinion_type','year','opinion_text']):
  scmeta.extend(zip(ch.project_opinion_id,ch.project_case_id,ch.case_url,ch.opinion_type,ch.year))
  sub=ch[ch.case_url.str.extract(r'/cases/(\d+)/',expand=False).isin([str(i) for i in url_ids])]
  scraw.extend(sub.to_dict('records'))
 s=pd.DataFrame(scmeta,columns=['project_opinion_id','sc_project_case_id','sc_url','sc_opinion_type','sc_year']); link=r.merge(s,on='project_opinion_id',how='left',indicator=True);unmatched=s[~s.project_opinion_id.isin(set(r.project_opinion_id))]
 join={'matched':int(d.shape[0]),'unpred':int((~a.section_id.isin(pred.section_id)).sum()),'opinion_join':int((link._merge=='both').sum()),'sc_only':len(unmatched),'sc_duplicates':int(s.project_opinion_id.duplicated().sum()),'r_duplicates':int(r.project_opinion_id.duplicated().sum()),'case_id_mismatch':int(((link.sc_project_case_id!=link.project_case_id)&(link._merge=='both')).sum())}
 selected=a[a.section_id.isin(IDS)].copy();case_notes=json.loads((Path(__file__).parent/'case_analysis.json').read_text(encoding='utf-8'))['notes']; recs=[]; scraw=pd.DataFrame(scraw)
 for sid in IDS:
  row=selected[selected.section_id==sid].iloc[0];cid=sid.split('_')[0];matches=raw[raw.case_url.str.contains('/cases/'+cid+'/',regex=False)]; best=None
  for _,m in matches.iterrows():
   text=str(m.opinion_text); needle=str(row.paragraph)[:min(90,len(str(row.paragraph)))];pos=text.find(needle)
   if pos<0:pos=text.find(clean(needle)[:40])
   if pos>=0: best=(m,pos);break
  if best is None:
   m=matches.iloc[0];pos=-1
  else:m,pos=best
  gold=d[(d.section_id==sid)&(d.test_num==0)].iloc[0]; rawtext=str(m.opinion_text)
  # quote always from the full opinion, never invented from cleaned annotation
  quote=clean(rawtext[max(0,pos):pos+min(210,len(str(row.paragraph)))]) if pos>=0 else clean(rawtext[:210]);
  record=dict(section_id=sid,name=str(row['name']),year=int(row.year),url=str(row.url),project_opinion_id=str(m.project_opinion_id),opinion_type=str(m.opinion_type),offset=int(pos),quote=quote,class_label=str(row['class']),predicted_label=str(gold.predicted_label),low_confidence=bool(row.low_confidence),legal_reason=case_notes[sid]['legal_reason'],protocol_note=case_notes[sid]['protocol_note'],impact=case_notes[sid]['impact'],annotation_paragraph=str(row.paragraph)[:250],nearby_original=clean(rawtext[max(pos-240,0):pos+400]) if pos>=0 else clean(rawtext[:400]))
  record['class']=record.pop('class_label');recs.append(record)
 (out/'case_analysis.json').write_text(json.dumps({'selection':'指定折0、模型与专家冲突、含低置信，按年代与意见类型覆盖的目的样本；非随机估计','notes':case_notes,'cases':recs},ensure_ascii=False,indent=2),encoding='utf-8')
 counts={'annotations':len(a),'pred_rows':len(pred),'pred_ids':pred.section_id.nunique(),'folds':pred.test_num.nunique(),'opinions':len(r),'cases':r.project_case_id.nunique(),'minyear':int(r.year.min()),'maxyear':int(r.year.max()),'missing':len(miss)}
 perfdoc={'fold_macro_mean':folds.macro_f1.mean(),'vote_macro':metrics(v)['macro_f1'],'vote_acc':metrics(v)['accuracy'],'eval_macro':ev[(ev.model=='nlpaueb/legal-bert-base-uncased')&(ev.percentage==1)&(ev.split!='averages')].macro_f1.mean(),'lc_entropy':float(entropy.loc[entropy.low_confidence,'mean_entropy'].iloc[0]),'nlc_entropy':float(entropy.loc[~entropy.low_confidence,'mean_entropy'].iloc[0]),'lc_acc':float(entropy.loc[entropy.low_confidence,'accuracy'].iloc[0]),'nlc_acc':float(entropy.loc[~entropy.low_confidence,'accuracy'].iloc[0])};perfdoc['entropy_diff']=perfdoc['lc_entropy']-perfdoc['nlc_entropy']
 trend=[]
 for label,(l,u) in [('早期(1870–1936)',(1870,1936)),('中期(1937–1980)',(1937,1980)),('后期(1981–2024)',(1981,2024))]:
  z=period_means[period_means.period==period(l)];trend.append(label+'：'+ '；'.join(f"{t.denominator} n={int(t['count'])}、均值={t['mean']:.3f}" for _,t in z.iterrows()))
 def yr(y):
  z=annual[annual.year==y].iloc[0];return f"{y}: 意见{z.opinion_mean:.3f} / 案件{z.case_mean:.3f} / 多数意见{z.majority_mean:.3f} (各分母{int(z.opinions)}/{int(z.cases)}/{int(z.majority_n) if not pd.isna(z.majority_n) else 0})"
 trend.append('转折附近逐年：'+'；'.join(yr(y) for y in [1935,1936,1937,1938,1979,1980,1981,1982,2024]))
 make_doc(out,counts,recs,perfdoc,trend,join)
 w=Workbook();w.remove(w.active)
 sources=pd.DataFrame([{'文件':f.name,'字节':f.stat().st_size,'用途':{'paper.pdf':'定义、图9、验证论文报告','supplement.pdf':'编码手册','reasoning.csv':'意见zformal、年度比较和原判决','sc_data.csv':'原判决文本及意见连接','annotation_predictions.csv':'10折测试预测、logits','legal_reasoning_annotations.csv':'专家标注、年代','eval_crossfold_output.csv':'现成模型报告（不可复训）','missing_data.csv':'原作者的未匹配项目','legal-reasoning-main.zip':'预处理／模型代码','supreme-court-data-main.zip':'意见得分公式及replication notebook'}.get(f.name,'来源及取得信息')} for f in p.iterdir() if f.is_file()]);wb_sheet(w,'来源',sources)
 wb_sheet(w,'说明',pd.DataFrame([{'项目':'判定','内容':'附条件试用，仅限历史辅助，不可排他筛选或替代法律权威审查'},{'项目':'连接','内容':'section_id为段落标注键；case_url中案件数字≠project_case_id；project_opinion_id连原件意见；同一案件含多意见'},{'项目':'折数','内容':'同一section_id跨test_num重复；macro F1逐折均值，按人类标注做监督参照而非法律真值'},{'项目':'logit','内容':'prob_GRAND/NONE/FORMAL是logits，softmax后自然对数熵；逐折重复非独立样本'},{'项目':'趋势','内容':'zformal为现有标准化意见分数；案件等权先在project_case_id内平均；仅majority排除per_curiam'},{'项目':'排除','内容':'缺预测的注释不计评分；reasoning未覆盖的sc_data意见不计趋势；missing_data独立来源清单不可简单相加'},{'项目':'文本','内容':'精读原文匹配用case_url及原句短语，offset为reasoning.csv原意见0起字符位置；-1须人工查验'}]))
 wb_sheet(w,'数据核对',pd.DataFrame([{'指标':k,'值':v} for k,v in {**counts,**join,'prediction_id_duplicates':int(pred.duplicated('section_id').sum()),'annotation_id_duplicates':int(a.duplicated('section_id').sum()),'pred_vs_annotation_class_mismatch':int((d['class_file']!=d['class_annotation']).sum()),'pred_vs_annotation_LC_mismatch':int((d['lc_file']!=d['lc_annotation']).sum())}.items()]))
 wb_sheet(w,'分类评估',perf);wb_sheet(w,'混淆矩阵',confusion);wb_sheet(w,'折级结果',folds);wb_sheet(w,'熵和准确率',entropy);wb_sheet(w,'熵去重口径',entropy_unique);wb_sheet(w,'原评估报告',eval_summary);wb_sheet(w,'年度趋势',annual);wb_sheet(w,'分期口径',period_means)
 wb_sheet(w,'逐案精读',pd.DataFrame(recs).drop(columns=['nearby_original','annotation_paragraph']));wb_sheet(w,'争议段落记录',pd.DataFrame(recs)[['section_id','annotation_paragraph','nearby_original']]);wb_sheet(w,'异常排除',pd.DataFrame([{'类型':'专家标注未进预测','数量':join['unpred'],'定位':'legal_reasoning_annotations.section_id – annotation_predictions.section_id'},{'类型':'预测重复行','数量':int(pred.duplicated('section_id').sum()),'定位':'annotation_predictions.section_id/test_num；不视独立标注'},{'类型':'sc_data有而reasoning无的意见行','数量':join['sc_only'],'定位':'sc_data.project_opinion_id – reasoning.project_opinion_id'},{'类型':'reasoning意见连接到sc_data','数量':join['opinion_join'],'定位':'project_opinion_id'},{'类型':'sc_data重复意见键','数量':join['sc_duplicates'],'定位':'sc_data.project_opinion_id'},{'类型':'reasoning重复意见键','数量':join['r_duplicates'],'定位':'reasoning.project_opinion_id'},{'类型':'同意见键案件ID冲突','数量':join['case_id_mismatch'],'定位':'project_opinion_id与project_case_id'},{'类型':'作者missing_data原表','数量':len(miss),'定位':'missing_data.csv；不能等同sc_data→reasoning差集'}]))
 wb_sheet(w,'未入趋势意见',unmatched[['project_opinion_id','sc_project_case_id','sc_url','sc_opinion_type','sc_year']]);wb_sheet(w,'未进预测标注',a[~a.section_id.isin(pred.section_id)][['section_id','url','name','year','class','low_confidence']]);wb_sheet(w,'作者缺失记录',miss);wb_sheet(w,'意见类型统计',r.groupby(['opinion_type','source']).agg(opinions=('project_opinion_id','size'),cases=('project_case_id','nunique')).reset_index());wb_sheet(w,'折0逐段定位',d[d.test_num==0][['section_id','url','year','class','predicted_label','low_confidence','correct','entropy','prob_GRAND','prob_NONE','prob_FORMAL']]);wb_sheet(w,'专家类别时期',a.assign(period=a.year.map(period)).groupby(['period','class','low_confidence']).size().rename('paragraphs').reset_index())
 w.save(out/'证据与复核工作簿.xlsx');print(json.dumps({'counts':counts,'join':join,'performance':perfdoc,'period':period_means.to_dict('records'),'offset_unmatched':[x['section_id'] for x in recs if x['offset']<0]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
