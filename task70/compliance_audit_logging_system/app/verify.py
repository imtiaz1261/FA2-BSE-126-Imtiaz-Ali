from .database import init_db
from .audit import verify_chain
if __name__=="__main__":
    init_db();ok,msg=verify_chain();print(msg);raise SystemExit(0 if ok else 1)
