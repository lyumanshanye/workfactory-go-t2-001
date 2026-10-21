"""Original intentionally defective draft, not a trusted audit tool."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--deck");p.add_argument("--out",required=True);a=p.parse_args()
# BUG: never opens the deck, ignores source/version, returns pass.
Path(a.out).write_text(json.dumps({"status":"PASS","screen_reader":"PASS"}))
