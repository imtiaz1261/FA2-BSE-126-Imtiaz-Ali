import re

def check_password_strength(password: str) -> dict:
    if not isinstance(password, str): raise TypeError('Password must be a string.')
    checks={'length':len(password)>=8,'uppercase':bool(re.search(r'[A-Z]',password)),'number':bool(re.search(r'\d',password)),'symbol':bool(re.search(r'[^A-Za-z0-9]',password))}
    score=sum([25 if checks['length'] else 0,20 if checks['uppercase'] else 0,20 if checks['number'] else 0,20 if checks['symbol'] else 0,10 if len(password)>=12 else 0,5 if len(password)>=16 else 0])
    label='Strong' if score>=80 else 'Medium' if score>=50 else 'Weak'
    messages=[{'passed':checks['length'],'text':'Use at least 8 characters.'},{'passed':checks['uppercase'],'text':'Include at least one uppercase letter (A-Z).'},{'passed':checks['number'],'text':'Include at least one number (0-9).'},{'passed':checks['symbol'],'text':'Include at least one symbol, such as !, @, #, or $.'}]
    return {'score':min(score,100),'label':label,'checks':checks,'length':len(password),'messages':messages}
