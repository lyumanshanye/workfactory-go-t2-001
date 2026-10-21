"""Deliberately faulty fictional training helper; never use for real intake."""
import argparse,json
from pathlib import Path
def route(records):
 return {"cases":[{"id":r["id"],"route":"APPROVED","clinical_clearance":True,"appointment_confirmed":True} for r in records]}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--cases",required=True);p.add_argument("--out",required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(route(json.loads(Path(a.cases).read_text()))))
