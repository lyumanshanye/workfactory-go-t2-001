import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--html');p.add_argument('--out');a=p.parse_args()
text=Path(a.html).read_text()
Path(a.out).write_text(json.dumps({'pass':'govuk-button--disabled' in text,'scope':'D0错误检查器，不构成认证'}))
