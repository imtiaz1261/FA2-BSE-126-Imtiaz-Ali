from github import Github
class GH:
    def __init__(self,token): self.client=Github(token)
    def pr(self,name,number):
        repo=self.client.get_repo(name); return repo,repo.get_pull(number)
    def files(self,pr): return list(pr.get_files())
    def diff(self,pr):
        out=[]
        for f in self.files(pr):
            out.append(f"FILE: {f.filename}\nSTATUS: {f.status}\nADDITIONS: {f.additions}\nDELETIONS: {f.deletions}\nPATCH:\n{getattr(f,'patch',None) or '(patch unavailable)'}")
        return "\n\n".join(out)
    def review(self,pr,body,comments):
        return pr.create_review(body=body,event="COMMENT",comments=comments)
