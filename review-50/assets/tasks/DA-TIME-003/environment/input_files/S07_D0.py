# Original flawed draft, not TLC code. Do not run as authoritative audit.
from pathlib import Path
import pyarrow.parquet as pq
def draft_summary(path):
    rows=pq.read_table(path).slice(0,1000).to_pylist() # incorrectly calls sample a full batch
    rows=[r for r in rows if (r.get('trip_distance') or 0)>0] # loses anomaly coverage
    return {'month':Path(path).stem[-7:],'claimed_full_count':len(rows),
            'cbd_zero_count':sum((r.get('cbd_congestion_fee') or 0)==0 for r in rows)}
