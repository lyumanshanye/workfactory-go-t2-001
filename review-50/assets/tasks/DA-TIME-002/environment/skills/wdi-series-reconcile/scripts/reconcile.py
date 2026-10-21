"""Offline WDI packet audit; no live API, Office output, or release action."""
import argparse,datetime,hashlib,json,math
from decimal import Decimal
from pathlib import Path
from openpyxl import load_workbook

CD='NY.GDP.MKTP.CD';KD='NY.GDP.MKTP.KD';ZG='NY.GDP.MKTP.KD.ZG'
NAMES=['S01_WDI原始观测.json','S02_指标定义汇编.json','S03_口径与修订依据.docx','S04_待审旧稿D0.xlsx','S05_研究委托.docx','S06_版本与授权.json']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(),parse_float=Decimal)

def audit(inp):
    contract=load(inp/NAMES[5]);asof=datetime.datetime.fromisoformat(contract['as_of'])
    if asof.tzinfo is None:raise ValueError('Offset-aware as_of required')
    choices=[]
    for c in contract['versions']:
        effective=datetime.datetime.fromisoformat(c['effective_at'])
        if effective.tzinfo is None:raise ValueError('Offset-aware contract dates required')
        if c['approved'] is True and c['authority']=='chief_analyst' and effective<=asof:choices.append((effective,c))
    if not choices:raise ValueError('No approved effective contract')
    choices.sort(key=lambda p:p[0])
    if len(choices)>1 and choices[-1][0]==choices[-2][0]:raise ValueError('Ambiguous effective authority')
    chosen=choices[-1][1]
    if chosen['objective']!='real_gdp_review':raise ValueError('Selected scope not supported by this helper')
    countries=chosen['countries'];years=chosen['years'];baseline=chosen['baseline_year']
    if len(set(countries))!=len(countries) or years!=list(range(min(years),max(years)+1)) or baseline!=years[0]:raise ValueError('Invalid country/year/baseline contract')
    frozen=load(inp/NAMES[0]);meta,raw=frozen
    if meta['pages']!=1 or int(meta['total'])!=len(raw):raise ValueError('Incomplete API response')
    if datetime.date.fromisoformat(meta['lastupdated'])>asof.date():raise ValueError('Future snapshot update')
    definitions=load(inp/NAMES[1]);defs={}
    for item in definitions['records']:
        response=item['raw_api_response']
        if len(response[1])!=1:raise ValueError('Invalid indicator definition response')
        d=response[1][0]
        if d['id'] in defs:raise ValueError('Duplicate indicator definition')
        defs[d['id']]=d
    if set(defs)!={CD,KD,ZG} or '2015' not in defs[KD]['name'] or '2015' not in defs[KD]['sourceNote']:raise ValueError('Incompatible frozen indicator definitions')
    values={}
    for r in raw:
        key=(r['countryiso3code'],int(r['date']),r['indicator']['id'])
        if key in values:raise ValueError('Duplicate observation key')
        value=r['value']
        if value is None or isinstance(value,bool):raise ValueError('Missing or invalid numeric observation')
        value=Decimal(str(value))
        if not value.is_finite() or key[2] in [CD,KD] and value<=0:raise ValueError('Nonfinite or nonpositive level')
        values[key]=value
    expected={(c,y,i) for c in countries for y in years for i in [CD,KD,ZG]}
    if set(values)!=expected:raise ValueError('Country/year/indicator coverage mismatch')
    rows=[]
    for c in countries:
        for y in years:
            current=values[c,y,CD];constant=values[c,y,KD];official=values[c,y,ZG]
            real=nominal=delta=None
            if y>baseline:
                real=(constant/values[c,y-1,KD]-1)*100
                nominal=(current/values[c,y-1,CD]-1)*100
                delta=real-official
                if abs(delta)>Decimal(str(chosen['growth_tolerance_pp'])):raise ValueError('Official growth reconciliation outside contract tolerance')
            rows.append(dict(country=c,year=y,current_usd=current,constant_2015_usd=constant,official_growth_pct=official,derived_real_growth_pct=real,nominal_usd_growth_pct=nominal,nominal_minus_real_pp=None if real is None else nominal-real,real_index_2019=constant/values[c,baseline,KD]*100,reconcile_delta_pp=delta,derived_growth_status='NO_2018_LEVEL' if y==baseline else 'RECONCILED'))
    book=load_workbook(inp/NAMES[3],data_only=True);sheet=book['D0'];draft=[]
    for c,y,numerator_id,denominator_id,numerator,denominator,draft_rate,label in list(sheet.values)[1:]:
        if (c,y,numerator_id) not in values or (c,y-1,denominator_id) not in values:raise ValueError('Draft key outside frozen source')
        if abs(Decimal(str(numerator))-values[c,y,numerator_id])>Decimal('0.1') or abs(Decimal(str(denominator))-values[c,y-1,denominator_id])>Decimal('0.1'):raise ValueError('Draft value does not match stated source key')
        computed=(Decimal(str(numerator))/Decimal(str(denominator))-1)*100
        if abs(computed-Decimal(str(draft_rate)))>Decimal('0.00001'):raise ValueError('Draft cached ratio inconsistent')
        draft.append(dict(country=c,year=y,numerator_indicator=numerator_id,denominator_indicator=denominator_id,draft_rate_pct=computed,diagnosis='MIXED_PRICE_BASIS_INVALID' if numerator_id!=denominator_id else 'NOMINAL_USD_NOT_REAL' if numerator_id==CD else 'REAL_GROWTH',official_prior_vintage_available=False))
    book.close()
    if len(draft)!=len(countries) or {d['country'] for d in draft}!=set(countries):raise ValueError('Draft country coverage invalid')
    skill=Path(__file__).resolve().parents[1]
    return dict(executor='wdi-series-reconcile',selected_contract=chosen['id'],as_of=contract['as_of'],snapshot_lastupdated=meta['lastupdated'],snapshot_retrieved_at_utc=definitions['observations_retrieved_at_utc'],input_sha256={n:sha(inp/n) for n in NAMES},skill_sha256={str(p.relative_to(skill)):sha(p) for p in [skill/'SKILL.md',skill/'references/packet-rules.md',Path(__file__).resolve()]},rows=rows,draft_diagnosis=draft,external_release_authorized=False,official_prior_vintage_available=False,scope='Actual offline authored helper; hashes are provenance not a trusted signature, expert certification or solver trajectory.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=audit(a.input_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=lambda x:float(x) if isinstance(x,Decimal) else x)+'\n')
    print(json.dumps({'rows':len(result['rows']),'draft_cases':len(result['draft_diagnosis']),'selected_contract':result['selected_contract'],'external_release_authorized':False}))

if __name__=='__main__':main()
