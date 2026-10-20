import json, sys
from collections import defaultdict
data=json.load(open(sys.argv[1]))
latest={}
for r in data:
    if r["version"] > latest.get(r["id"],{}).get("version",-1): latest[r["id"]]=r
totals=defaultdict(int)
for r in latest.values():
    if r["state"]=="accepted": totals[r["team"]]+=r["units"]*r["unit_cents"]
json.dump({"team_totals_cents":dict(sorted(totals.items())),"total_cents":sum(totals.values())},open(sys.argv[2],"w"),sort_keys=True)
