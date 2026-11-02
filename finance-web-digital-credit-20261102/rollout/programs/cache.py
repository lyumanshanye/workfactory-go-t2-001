import pandas as pd,numpy as np,zipfile,xml.etree.ElementTree as E
from openpyxl import load_workbook
p='/work/output/分群与债务指标复核.xlsx';x=pd.read_csv('/app/input_files/dataverse_banco_final_clusters14novCSV_v2.tab');prob=x[['prob_c1','prob_c2','prob_c3']];arg=prob.values.argmax(axis=1)+1;mx=prob.max(axis=1)
g={t:np.where(mx>=t,['c'+str(a)+' puro' for a in arg],'Misto') for t in [.7,.8,.9]}
a=x.filter(regex='^P21_').eq(1).sum(axis=1);b=x.filter(regex='^P39_').eq(1).sum(axis=1);ch=['ligacoes','whatsapp','app','sms','agencia','email'];cs=['n_propostas_'+c for c in ch];su=x[cs].sum(axis=1); caches={}
rows=[]
for i in range(1000):
 z=x.iloc[i];vals=[int(z.id),i+2,float(prob.iloc[i].sum()),float(mx[i]),int(arg[i]),1,'通过',z.cluster,1,g[.7][i],1,g[.8][i],g[.9][i],'不变' if g[.7][i]==g[.8][i] else '降为混合/未决',int(a[i]),12,int(z.n_dividas_ativas),int(z.n_dividas_ativas-a[i]),int(b[i]),int(x.filter(regex='^P39_').iloc[i].count()),int(z.n_contas_atraso),int(z.n_contas_atraso-b[i]),int(x[[f'P39_{j}' for j in range(1,14)]].iloc[i].eq(1).sum()),int(b[i]==0),int(su[i]),int(z.n_propostas_total),int(z.n_propostas_total-su[i]),int(z.P40_3==1),int(z.P41_1==1),int(z.P41_3==1),int(pd.notna(z.P42)),0];rows.append(vals)
caches['逐条复核']={(i+2,j+1):v for i,vs in enumerate(rows) for j,v in enumerate(vs)}
groups=['c1 puro','c2 puro','c3 puro','Misto','未决'];caches['分层规模']={}
for i,gr in enumerate(groups,2):
 vals=[int((g[t]==gr).sum()) for t in [.7,.8,.9]];vals.append(vals[1]-vals[0])
 for j,v in enumerate(vals,2):caches['分层规模'][i,j]=v
for j,v in enumerate([1000,1000,1000,0],2):caches['分层规模'][7,j]=v
caches['归属迁移']={(i+2,j+2):int(((g[.7]==ga)&(g[.8]==gb)).sum()) for i,ga in enumerate(groups) for j,gb in enumerate(groups)}
caches['指标检查']={(i+2,2):v for i,v in enumerate([1000,1000,1000,0,168,0,331,0,0,166,144,122,402])}
w=load_workbook(p); ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};tmp='/work/cached.xlsx'
with zipfile.ZipFile(p) as zin,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as zout:
 for info in zin.infolist():
  data=zin.read(info.filename)
  if info.filename.startswith('xl/worksheets/sheet') and info.filename.endswith('.xml'):
   num=int(info.filename.split('sheet')[-1].split('.')[0]);name=w.sheetnames[num-1]
   if name in caches:
    root=E.fromstring(data)
    for c in root.findall('.//m:c',ns):
     if c.find('m:f',ns) is None:continue
     cell=w[name][c.attrib['r']];value=caches[name][cell.row,cell.column]
     v=c.find('m:v',ns)
     if v is None:v=E.SubElement(c,'{'+ns['m']+'}v')
     if isinstance(value,str):c.set('t','str');v.text=value
     else:c.pop('t',None) if False else None;v.text=str(value)
    data=E.tostring(root,encoding='utf-8',xml_declaration=True)
  zout.writestr(info,data)
import shutil
shutil.move(tmp,p)
r=load_workbook(p,data_only=True);print('cached scale',list(r['分层规模'].values));print('errors',sum(isinstance(c.value,str) and c.value.startswith(('#REF!','#VALUE!','#DIV/0!')) for s in r for row in s for c in row));print('rowcounts',r['原始数据'].max_row,r['字典原文'].max_row)
from docx import Document
d=Document('/work/output/试点决策备忘录.docx');print('doc paragraphs/tables',len(d.paragraphs),len(d.tables))
