"""Historical packet controls only; calendar convention is explicitly local."""
import argparse,calendar,datetime as dt,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]

def date(value):
    if value is None:return None
    d=dt.date.fromisoformat(value)
    if d.isoformat()!=value:raise ValueError('date must be YYYY-MM-DD')
    return d

def add_months(d,n):
    y,m=divmod(d.year*12+d.month-1+n,12);m+=1
    return dt.date(y,m,min(d.day,calendar.monthrange(y,m)[1]))

def signature_status(check,signed):
    if signed is None:return 'MISSING_SIGNATURE',None
    if signed>check:return 'FUTURE_SIGNATURE',None
    limit=add_months(signed,6)
    return ('BOUNDARY_REVIEW' if check==limit else 'CURRENT_BY_PACKET' if check<limit else 'UPDATE_SIGNATURE'),limit

def evaluate(rows,contract):
    if not isinstance(rows,list) or not rows:raise ValueError('nonempty case list required')
    seen=set();out=[]
    for r in rows:
        if not {'id','as_of','financial_cutoff','report_issued','last_signature','extension'}<=r.keys():raise ValueError('missing field')
        if not isinstance(r['id'],str) or not r['id'] or r['id'] in seen:raise ValueError('invalid/duplicate ID')
        seen.add(r['id']);check=date(r['as_of'])
        if check is None:raise ValueError('as_of required')
        cut=date(r['financial_cutoff']);issued=date(r['report_issued']);signed=date(r['last_signature'])
        ext=r['extension']
        if not isinstance(ext,dict) or not {'verified','by','record_id','until'}<=ext.keys():raise ValueError('extension object required')
        if type(ext['verified']) is not bool:raise ValueError('verified must be Boolean')
        until=date(ext['until']);base=ceiling=used=None
        sign,signlimit=signature_status(check,signed)
        if check>date(contract['snapshot_date']) or check<date(contract['national_rule']['effective_date']):financial='POLICY_VERSION_REVIEW';sign='POLICY_VERSION_REVIEW';signlimit=None
        elif cut is None:financial='MISSING_CUTOFF'
        elif cut>check or (issued is not None and issued<cut):financial='DATE_ORDER_REVIEW'
        elif (cut.month,cut.day) not in [(3,31),(6,30),(9,30),(12,31)]:financial='INVALID_PERIOD_END'
        else:
            base=add_months(cut,6);ceiling=add_months(cut,9)
            if check==base:financial='BOUNDARY_REVIEW'
            elif check<base:financial='CURRENT_BY_PACKET';used=base
            elif until and until>ceiling:financial='EXTENSION_LIMIT_BREACH'
            elif ext['verified'] and ext['by']=='project_legal' and ext['record_id'] and until:
                used=until;financial='BOUNDARY_REVIEW' if check==until else 'EXTENDED_BY_GIVEN_EVIDENCE' if check<until else 'UPDATE_FINANCIALS'
            else:financial='EXTENSION_UNCONFIRMED' if check<=ceiling else 'UPDATE_FINANCIALS'
        out.append(dict(id=r['id'],financial_review_date=str(base) if base else None,theoretical_ceiling=str(ceiling) if ceiling else None,evidence_until=str(used) if used else None,financial_status=financial,signature_review_date=str(signlimit) if signlimit else None,signature_status=sign,release_authorized=False,source_refs=['S01第46条','S03日历/边界约定','S05延期核验登记']))
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--cases',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.cases.resolve()==a.out.resolve():p.error('output must differ from input')
    policy=BASE/'references/packet-contract.json';contract=json.loads(policy.read_text())
    cases=evaluate(json.loads(a.cases.read_text()),contract)
    files=['SKILL.md','references/packet-contract.json','scripts/check_windows.py']
    result=dict(schema='ipo-document-control-evidence/1',skill='ipo-document-control',source_sha256=hashlib.sha256(a.cases.read_bytes()).hexdigest(),contract_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),skill_file_hashes={r:hashlib.sha256((BASE/r).read_bytes()).hexdigest() for r in files},cases=cases,release_authorized=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'cases':len(cases),'release_authorized':False}))

if __name__=='__main__':main()
