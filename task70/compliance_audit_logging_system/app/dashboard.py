import pandas as pd,streamlit as st
from datetime import date,timedelta
from app.database import init_db, all_logs, search_logs
from app.audit import verify_chain
st.set_page_config(page_title="LLM Compliance Audit",layout="wide");init_db()
st.title("🔐 LLM Compliance Audit Dashboard")
ok,msg=verify_chain();(st.success if ok else st.error)(msg)
logs=all_logs();a,b,c,d=st.columns(4);a.metric("Audit entries",len(logs));b.metric("Users",len(set(x["user_id"] for x in logs)));c.metric("Tokens",sum(x["total_tokens"] for x in logs));d.metric("PII masking","ON")
users=["All"]+sorted(set(x["user_id"] for x in logs));u=st.selectbox("User",users);s=st.date_input("Start",date.today()-timedelta(days=30));e=st.date_input("End",date.today())
rows=search_logs(None if u=="All" else u,s.isoformat(),e.isoformat()+"T23:59:59");st.write(f"Found {len(rows)} records.")
if rows:st.dataframe(pd.DataFrame(rows)[["id","timestamp","user_id","prompt","response","documents","tools","total_tokens","entry_hash"]],use_container_width=True,hide_index=True)
st.subheader("PII masking demonstration");st.code("Original: card 4111 1111 1111 1111 and email sara@example.com\nStored: card [REDACTED_CREDIT_CARD] and email [REDACTED_EMAIL]")
if st.button("Verify hash chain"):
 ok,msg=verify_chain();(st.success if ok else st.error)(msg)
