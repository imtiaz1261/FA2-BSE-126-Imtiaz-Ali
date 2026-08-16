"""Sample documents and test data for GraphRAG"""
SAMPLE_DOCUMENTS = [
    """John Smith is a senior software engineer at TechCorp. 
    He works on Project Alpha which is focused on AI development.
    John reports to his manager, Sarah Johnson.
    John has skills in Python, Machine Learning, and Cloud Computing.""",
    
    """Sarah Johnson is a project lead at TechCorp.
    She manages a team of 5 engineers including John Smith and Jane Doe.
    Sarah leads Project Alpha and also oversees Project Beta.
    She reports to the CTO, Michael Chen.""",
    
    """Jane Doe is a data scientist at TechCorp.
    She works on Project Beta which involves big data analytics.
    Jane reports to Sarah Johnson.
    Jane has skills in SQL, Data Visualization, and Statistical Analysis.""",
    
    """Michael Chen is the CTO of TechCorp.
    He manages all technical projects and reports to the CEO, Lisa Wang.
    Michael oversees Project Alpha, Project Beta, and Project Gamma.""",
    
    """Lisa Wang is the CEO of TechCorp.
    She founded the company in 2015 and is based in San Francisco.
    Lisa oversees all departments including engineering, sales, and marketing.""",
    
    """Project Alpha is an AI development project started in January 2023.
    It's led by Sarah Johnson and involves 10 team members.
    The project uses technologies like Python, TensorFlow, and AWS.""",
    
    """Project Beta is a big data analytics project started in March 2023.
    It's led by Sarah Johnson with Jane Doe as the lead data scientist.
    The project uses Apache Spark, Hadoop, and Tableau.""",
    
    """Project Gamma is a blockchain research project started in June 2023.
    It's overseen by Michael Chen and involves 3 research scientists.
    The project focuses on smart contracts and decentralized applications.""",
    
    """TechCorp is a technology company based in San Francisco.
    It was founded in 2015 by Lisa Wang.
    The company has 200 employees and focuses on AI, big data, and blockchain."""
]

MULTI_HOP_TEST_QUESTIONS = [
    {
        "question": "Who is the manager of John Smith?",
        "expected_answer": "Sarah Johnson",
        "hops": 1,
        "category": "Manager Relationship"
    },
    {
        "question": "Which project does Sarah Johnson lead?",
        "expected_answer": "Project Alpha and Project Beta",
        "hops": 1,
        "category": "Project Leadership"
    },
    {
        "question": "Who manages the person who works on Project Alpha?",
        "expected_answer": "Michael Chen",
        "hops": 2,
        "category": "Multi-hop Management"
    },
    {
        "question": "What organization does Jane Doe's manager work for?",
        "expected_answer": "TechCorp",
        "hops": 2,
        "category": "Organization Chain"
    },
    {
        "question": "Who is the CEO of the company where John Smith works?",
        "expected_answer": "Lisa Wang",
        "hops": 3,
        "category": "Leadership Chain"
    },
    {
        "question": "What skills does the team lead of Project Alpha have?",
        "expected_answer": "Expected to mention project management, leadership skills",
        "hops": 2,
        "category": "Skill Query"
    },
    {
        "question": "Which projects are overseen by the CTO?",
        "expected_answer": "Project Alpha, Project Beta, and Project Gamma",
        "hops": 1,
        "category": "Project Oversight"
    },
    {
        "question": "Who founded the company where Sarah Johnson works?",
        "expected_answer": "Lisa Wang",
        "hops": 2,
        "category": "Founder Chain"
    }
]

# Simplified sample data for quick testing
QUICK_TEST_DATA = [
    """John works at TechCorp as a developer. He reports to Sarah. Sarah is the manager.""",
    """Sarah leads Project X. She manages the development team.""",
    """TechCorp is located in Bangalore. It has 100 employees.""",
    """Project X is a web application started in 2024. It uses React and Node.js."""
]

def get_sample_documents():
    """Get sample documents for testing"""
    return SAMPLE_DOCUMENTS

def get_test_questions():
    """Get multi-hop test questions"""
    return MULTI_HOP_TEST_QUESTIONS

def get_quick_test_data():
    """Get quick test data"""
    return QUICK_TEST_DATA