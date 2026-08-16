from datetime import datetime,timedelta,timezone
from .database import init_db
from .audit import log_interaction,verify_chain
def main():
    init_db(); users=["user-1001","user-1002","user-1003","analyst-2001","customer-3001"]
    samples=[("Check card 4111 1111 1111 1111","Payment status is available to the authorized service."),("My email is sara@example.com. What is support process?","Support begins with identity verification."),("Review ID PK-12345678 against policy.","Authorized verification is required."),("Call me at 0300-1234567 about my loan.","A representative can contact you through the registered channel."),("What is the refund policy?","Refund eligibility depends on transaction status and policy."),("Summarize security requirements.","Use strong authentication, least privilege and monitoring.")]
    now=datetime.now(timezone.utc)
    for i in range(25):
        p,r=samples[i%6];log_interaction(users[i%5],p+f" Reference {i+1}.",r,[f"policy-{i%5+1}.pdf"],["document_search","risk_check"],20+i,30+i%15,(now-timedelta(days=i%20)).isoformat())
    print("Seeded 25 interactions.");print(verify_chain()[1])
if __name__=="__main__":main()
