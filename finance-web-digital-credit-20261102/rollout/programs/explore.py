import pandas as pd,numpy as np
x=pd.read_csv('/app/input_files/dataverse_banco_final_clusters14novCSV_v2.tab');p=x[['prob_c1','prob_c2','prob_c3']];m=p.max(axis=1);arg=p.values.argmax(axis=1)+1
print('dates',x.StartDate.min(),x.StartDate.max());print('prob',p.min().min(),p.max().max(),abs(p.sum(axis=1)-1).max(),'ties',p.eq(m,axis=0).sum(axis=1).gt(1).sum());print('arg mismatch',(x.cluster.str.extract('(\\d)')[0].astype(int)!=arg).sum())
for t in [.7,.8,.9]:print(t,pd.Series(np.where(m>=t,['c'+str(a)+' puro' for a in arg],'Misto')).value_counts().to_dict())
a=x.filter(regex='^P21_').eq(1).sum(axis=1); b=x.filter(regex='^P39_').eq(1).sum(axis=1)
for name,v in [('P21=1',a),('P39=1',b),('P39_1to13',x[[f'P39_{i}' for i in range(1,14)]].eq(1).sum(axis=1))]:
 print(name,v.describe().to_dict());print('equal', {c:int(v.eq(x[c]).sum()) for c in ['n_dividas_ativas','n_contas_atraso']})
print('P21sum cross debt',pd.crosstab(a,x.n_dividas_ativas).to_string())
print('P39 nonempty',x.filter(regex='^P39_').notna().sum(axis=1).value_counts().to_dict())
cs=[c for c in x if c.startswith('n_propostas_') and c!='n_propostas_total'];print('offers eq',x[cs].sum(axis=1).eq(x.n_propostas_total).sum(),x.n_propostas_total.describe().to_dict())
for c in cs:print(c,x[c].min(),x[c].max(), 'sim mismatch', ((x[c]>0).astype(int)!=x[c.replace('n_propostas_','propostas_')+'_sim']).sum())
for c in ['faixa','gender','sel','P37','P42','P40_3','P41_1','P41_3']: print(c,x[c].value_counts(dropna=False).to_dict())
print('cluster descriptions');x['group80']=np.where(m>=.8,['c'+str(a)+' puro' for a in arg],'Misto');x['p21count']=a;x['p39marks']=b
print(x.groupby('group80').agg(n=('id','size'),active_mean=('p21count','mean'),any_active=('p21count',lambda y:(y>0).sum()),marks=('p39marks',lambda y:(y>0).sum()),p40_3=('P40_3','count'),p41_1=('P41_1','count'),offers=('n_propostas_total','mean'),offer_med=('n_propostas_total','median'),p42=('P42','count')).to_string())
