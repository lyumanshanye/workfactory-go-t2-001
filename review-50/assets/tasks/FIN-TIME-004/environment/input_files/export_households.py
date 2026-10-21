"""Offline export only. Contains no investment decision or eligibility answer."""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
from openpyxl import load_workbook

def main():
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=root/'S05_households_latest.xlsx');parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if not args.source.is_file():
        print(json.dumps(dict(status='BLOCKED_SOURCE_MISSING',source=str(args.source),hint='No data exported. Check the approved recovery register; do not invent household records.'),ensure_ascii=False),file=sys.stderr);return 2
    register=json.loads((root/'S10_授权备份登记.json').read_text())
    digest=hashlib.sha256(args.source.read_bytes()).hexdigest()
    if digest!=register['approved_sha256']:
        print(json.dumps(dict(status='UNAPPROVED_SOURCE_BYTES',actual_sha256=digest),ensure_ascii=False),file=sys.stderr);return 3
    book=load_workbook(args.source,data_only=True,read_only=True);rows=list(book['家庭访谈'].values);head=rows[0]
    if list(head)!=register['columns'] or len(rows)-1!=register['case_count']:
        print('SOURCE_SCHEMA_OR_ROWCOUNT_MISMATCH',file=sys.stderr);book.close();return 4
    records=[dict(zip(head,r)) for r in rows[1:]];book.close()
    ids=[r['case_id'] for r in records]
    if len(ids)!=len(set(ids)):print('DUPLICATE_CASE_ID',file=sys.stderr);return 5
    payload=dict(status='EXPORTED_NOT_APPROVED',executed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_name=args.source.name,source_sha256=digest,case_count=len(records),records=records,scope='Frozen fictional interview facts only; not policy conclusions, verified entitlements or payment approval.')
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in payload.items() if k!='records'},ensure_ascii=False));return 0
if __name__=='__main__':sys.exit(main())
