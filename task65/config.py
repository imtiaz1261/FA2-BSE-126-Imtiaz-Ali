"""Configuration for GraphRAG system"""
import os
from dotenv import load_dotenv

load_dotenv()

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

# LLM Configuration - Groq (free) or OpenAI
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LLM_MODEL = os.getenv("LLM_MODEL", "mixtral-8x7b-32768")
USE_GROQ = GROQ_API_KEY is not None and GROQ_API_KEY != ""

# Entity Extraction Configuration
NER_MODEL = "en_core_web_sm"
MIN_CONFIDENCE_SCORE = 0.7

# Graph Schema
NODE_LABELS = {
    "PERSON": "Person",
    "ORGANIZATION": "Organization",
    "DATE": "Date",
    "LOCATION": "Location",
    "PROJECT": "Project",
    "ROLE": "Role",
    "SKILL": "Skill"
}

RELATIONSHIP_TYPES = {
    "WORKS_FOR": "WORKS_FOR",
    "MANAGES": "MANAGES",
    "MANAGED_BY": "MANAGED_BY",
    "LEADS": "LEADS",
    "PART_OF": "PART_OF",
    "HAS_SKILL": "HAS_SKILL",
    "LOCATED_IN": "LOCATED_IN",
    "STARTED_ON": "STARTED_ON",
    "WORKED_ON": "WORKED_ON",
    "REPORTS_TO": "REPORTS_TO"
}

# RAG Configuration
MAX_HOPS = 3
CONTEXT_WINDOW = 2000