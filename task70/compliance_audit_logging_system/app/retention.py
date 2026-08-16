import argparse,json
from datetime import datetime,timedelta,timezone
from .config import ARCHIVE_DIR,RETENTION_DAYS
from .database import init_db,delete_before
p=argparse.ArgumentParser();p.add_argument("--days",type=int,default=RETENTION_DAYS);p.add_argument("--action",choices=["archive","delete"],default="archive");a=p.parse_args()
init_db();rows=delete_before((datetime.now(timezone.utc)-timedelta(days=a.days)).isoformat())
if a.action=="archive" and rows:
 out=ARCHIVE_DIR/f"archive_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl";out.write_text("".join(json.dumps(x)+"\n" for x in rows));print("Archived",len(rows),"entries")
else:print("Deleted",len(rows),"entries")
