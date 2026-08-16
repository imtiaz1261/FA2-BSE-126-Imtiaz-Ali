import argparse
from .researcher import ResearchAgent

def main():
    p=argparse.ArgumentParser()
    p.add_argument("topic",nargs="+")
    args=p.parse_args()
    topic=" ".join(args.topic)
    print("Starting autonomous research:",topic)
    report=ResearchAgent().research(topic)
    print("Research complete. Report:",report)

if __name__=="__main__":
    main()
