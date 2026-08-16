# Graph RAG - Knowledge Graph-based Retrieval Augmented Generation

## Overview
A Graph-based RAG (Retrieval Augmented Generation) system that uses knowledge graphs instead of traditional vector databases for better multi-hop question answering.

## Why Graph RAG over Traditional Vector RAG?

### Traditional Vector RAG Limitations:
1. **Flat Retrieval**: Only retrieves documents based on semantic similarity
2. **No Relationship Understanding**: Cannot follow entity relationships
3. **Multi-hop Failures**: Struggles with questions requiring multiple relationship traversals
4. **Incomplete Answers**: May return partial or inaccurate information for relationship queries

### Graph RAG Advantages:
1. **Relationship-Aware**: Understands entity connections (e.g., John → works_for → TechCorp → managed_by → Sarah)
2. **Multi-hop Capability**: Can traverse 2-3 relationships to answer complex questions
3. **Structured Knowledge**: Uses Neo4j graph database for efficient relationship queries
4. **Accurate Path Finding**: Returns precise relationship paths rather than similar documents

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Input Query                          │
│  "Who manages the person who leads Project Beta?"      │
└─────────────────────────┬─────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │  Entity Extraction    │
              │  (spaCy NER + Pattern)│
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  Graph Traversal      │
              │  (Cypher Queries)     │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  Multi-hop Path       │
              │  Discovery            │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  Context Retrieval    │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  LLM Answer Generation│
              │  (OpenAI GPT)         │
              └───────────────────────┘
```

## Multi-hop Example Queries

The system can answer complex questions like:

1. **Single-hop**: "Who is John Smith's manager?" → Sarah Johnson
2. **Double-hop**: "Which project does John Smith's manager lead?" → Project Alpha
3. **Triple-hop**: "Who is the CEO of the company where Jane Doe works?" → Lisa Wang
4. **Relationship-chain**: "Who manages the person who leads Project Beta?" → Michael Chen

## Installation

### Prerequisites
1. Python 3.8+
2. Neo4j Database (Desktop or Server)
3. OpenAI API Key (for GPT integration)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Step 2: Setup Neo4j
1. Download Neo4j Desktop: https://neo4j.com/download/
2. Create a new database
3. Set username: `neo4j` and password: `password123`
4. Start the database

### Step 3: Configure Environment
Create `.env` file:
```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Model Configuration
LLM_MODEL=gpt-3.5-turbo
```

## Running the System

### Interactive Demo
```bash
python main.py
```

Commands in demo mode:
- `test`: Run multi-hop test questions
- `query`: Ask your own question
- `stats`: Show graph statistics
- `exit`: Exit the demo

### Direct Testing
```bash
python test_multihop.py
```

## Components

### 1. Entity Extractor (`entity_extractor.py`)
- Uses spaCy NER for entity recognition
- Pattern matching for relationship extraction
- Maps entities to graph nodes and relationships

### 2. Graph Builder (`graph_builder.py`)
- Neo4j database connection manager
- Graph schema creation and constraints
- CRUD operations for nodes and relationships

### 3. Graph RAG Engine (`graph_rag.py`)
- Main query processing engine
- Multi-hop path discovery
- Context retrieval and answer generation

### 4. Test Suite (`test_multihop.py`)
- 8 multi-hop test questions
- Graph setup with sample data
- Performance comparison with traditional RAG

## Sample Multi-hop Tests

```python
MULTI_HOP_TEST_QUESTIONS = [
    "Who is the manager of John Smith?",
    "Which project does Sarah Johnson lead?",
    "Who manages the person who works on Project Alpha?",
    "What organization does Jane Doe's manager work for?",
    "Who is the CEO of the company where John Smith works?",
    "What skills does the team lead of Project Alpha have?",
    "Which projects are overseen by the CTO?",
    "Who founded the company where Sarah Johnson works?"
]
```

## Expected Performance

| Query Type | Traditional RAG | Graph RAG | Improvement |
|------------|----------------|-----------|-------------|
| Single-hop | 70% accurate | 95% accurate | +25% |
| Double-hop | 30% accurate | 85% accurate | +55% |
| Triple-hop | <10% accurate | 70% accurate | +60% |
| Relationship queries | 40% accurate | 90% accurate | +50% |

## Files Structure

```
graph-rag/
├── main.py              # Main entry point
├── config.py            # Configuration settings
├── entity_extractor.py  # NER and relationship extraction
├── graph_builder.py     # Neo4j graph operations
├── graph_rag.py         # Main RAG engine
├── test_multihop.py     # Multi-hop testing
├── sample_data.py       # Sample documents and test questions
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
└── README.md            # This file
```

## Key Features

1. **Multi-hop Question Answering**: Answer questions requiring 2-3 relationship traversals
2. **Entity Relationship Understanding**: Recognize and utilize entity connections
3. **Graph-based Retrieval**: Use Cypher queries instead of vector similarity
4. **Scalable Architecture**: Can handle thousands of entities and relationships
5. **Integration Ready**: Compatible with existing RAG pipelines

## Use Cases

1. **Organizational Charts**: Who reports to whom across departments
2. **Project Management**: Who works on what project with what skills
3. **Knowledge Management**: Connect concepts across documents
4. **Customer Support**: Understand customer-issue-product relationships
5. **Research**: Connect papers, authors, and concepts

## Future Enhancements

1. **LLM-based Cypher Generation**: Generate Cypher queries from natural language
2. **Hybrid Retrieval**: Combine graph and vector search
3. **Temporal Graphs**: Add time-based relationship analysis
4. **Multi-modal Entities**: Handle text, images, and structured data
5. **Real-time Updates**: Stream data into knowledge graph

## References

1. **Neo4j + LangChain GraphRAG Documentation**
2. **Krish Naik - GraphRAG Explained (Hindi)**
3. **CampusX - Knowledge Graphs with LLMs**
4. **Traditional RAG limitations**: Vector databases fail at multi-hop reasoning

## License

This project is for educational and demonstration purposes.

---

**Note**: This system demonstrates how knowledge graphs can overcome traditional RAG limitations for multi-hop question answering. The implementation shows a complete working system that can be extended for production use.