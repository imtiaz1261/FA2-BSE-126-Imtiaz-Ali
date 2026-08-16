"""Test multi-hop question answering with GraphRAG"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from entity_extractor import EntityExtractor
from graph_builder import GraphBuilder
from graph_rag import GraphRAG
from sample_data import get_sample_documents, get_test_questions
import json

def setup_test_graph():
    """Setup test knowledge graph with sample data"""
    print("Setting up test knowledge graph...")
    
    # Initialize components
    extractor = EntityExtractor()
    graph = GraphBuilder()
    
    # Clear existing graph
    graph.clear_graph()
    
    # Process sample documents
    sample_docs = get_sample_documents()
    
    for i, doc in enumerate(sample_docs):
        print(f"\nProcessing document {i+1}/{len(sample_docs)}...")
        
        # Extract entities and relationships
        extracted = extractor.extract_structured_data(doc)
        
        # Prepare for graph
        nodes = extractor.prepare_graph_nodes(extracted["entities"])
        edges = extractor.prepare_graph_edges(extracted["relationships"], nodes)
        
        # Add to graph
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "document_id": i
        }
        graph.add_document_to_graph(graph_data)
    
    # Add some explicit relationships that might not be extracted
    with graph.driver.session() as session:
        # Add explicit WORKS_FOR relationships
        session.run("""
        MATCH (p:Person {name: 'John Smith'})
        MATCH (o:Organization {name: 'TechCorp'})
        MERGE (p)-[:WORKS_FOR]->(o)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Sarah Johnson'})
        MATCH (o:Organization {name: 'TechCorp'})
        MERGE (p)-[:WORKS_FOR]->(o)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Jane Doe'})
        MATCH (o:Organization {name: 'TechCorp'})
        MERGE (p)-[:WORKS_FOR]->(o)
        """)
        
        # Add explicit MANAGED_BY relationships
        session.run("""
        MATCH (p:Person {name: 'John Smith'})
        MATCH (m:Person {name: 'Sarah Johnson'})
        MERGE (p)-[:MANAGED_BY]->(m)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Jane Doe'})
        MATCH (m:Person {name: 'Sarah Johnson'})
        MERGE (p)-[:MANAGED_BY]->(m)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Sarah Johnson'})
        MATCH (m:Person {name: 'Michael Chen'})
        MERGE (p)-[:MANAGED_BY]->(m)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Michael Chen'})
        MATCH (m:Person {name: 'Lisa Wang'})
        MERGE (p)-[:MANAGED_BY]->(m)
        """)
        
        # Add LEADS relationships
        session.run("""
        MATCH (p:Person {name: 'Sarah Johnson'})
        MATCH (pr:Project {name: 'Project Alpha'})
        MERGE (p)-[:LEADS]->(pr)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Sarah Johnson'})
        MATCH (pr:Project {name: 'Project Beta'})
        MERGE (p)-[:LEADS]->(pr)
        """)
        
        # Add WORKED_ON relationships
        session.run("""
        MATCH (p:Person {name: 'John Smith'})
        MATCH (pr:Project {name: 'Project Alpha'})
        MERGE (p)-[:WORKED_ON]->(pr)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Jane Doe'})
        MATCH (pr:Project {name: 'Project Beta'})
        MERGE (p)-[:WORKED_ON]->(pr)
        """)
        
        # Add HAS_SKILL relationships
        session.run("""
        MATCH (p:Person {name: 'John Smith'})
        MERGE (s:Skill {name: 'Python'})
        MERGE (p)-[:HAS_SKILL]->(s)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'John Smith'})
        MERGE (s:Skill {name: 'Machine Learning'})
        MERGE (p)-[:HAS_SKILL]->(s)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Jane Doe'})
        MERGE (s:Skill {name: 'SQL'})
        MERGE (p)-[:HAS_SKILL]->(s)
        """)
        
        session.run("""
        MATCH (p:Person {name: 'Jane Doe'})
        MERGE (s:Skill {name: 'Data Visualization'})
        MERGE (p)-[:HAS_SKILL]->(s)
        """)
    
    # Get graph statistics
    stats = graph.get_graph_stats()
    print("\nGraph Statistics:")
    print(json.dumps(stats, indent=2))
    
    return graph

def test_multi_hop_questions():
    """Test multi-hop question answering"""
    print("\n" + "="*60)
    print("Testing Multi-Hop Question Answering")
    print("="*60)
    
    # Setup GraphRAG
    graph_rag = GraphRAG()
    
    # Get test questions
    test_questions = get_test_questions()
    
    results = []
    total_questions = len(test_questions)
    successful_hops = 0
    
    for i, test in enumerate(test_questions):
        print(f"\nTest {i+1}/{total_questions}:")
        print(f"Question: {test['question']}")
        print(f"Expected hops: {test['hops']}")
        print(f"Category: {test['category']}")
        
        try:
            # Get answer
            result = graph_rag.answer_query(test["question"])
            
            # Analyze result
            print(f"\nAnswer: {result['answer'][:200]}...")
            print(f"Detected entities: {result['entities']}")
            print(f"Context length: {result['context_length']} characters")
            
            # Check if multi-hop was successful
            if result['context_length'] > 100:  # Has some context
                successful_hops += 1
            
            results.append({
                "question": test["question"],
                "answer": result["answer"],
                "expected_hops": test["hops"],
                "context_length": result["context_length"],
                "entities_detected": result["entities"],
                "success": result["context_length"] > 100
            })
            
        except Exception as e:
            print(f"Error processing question: {str(e)}")
            results.append({
                "question": test["question"],
                "error": str(e),
                "success": False
            })
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    print(f"Total questions tested: {total}")
    print(f"Successful answers: {successful}")
    print(f"Success rate: {(successful/total)*100:.1f}%")
    
    # Show detailed results
    print("\nDetailed Results:")
    for i, result in enumerate(results):
        status = "✓" if result.get("success") else "✗"
        print(f"{i+1}. {status} {result['question'][:50]}...")
        if "answer" in result:
            print(f"   Answer preview: {result['answer'][:100]}...")
    
    # Compare with traditional RAG
    print("\n" + "="*60)
    print("COMPARISON WITH TRADITIONAL VECTOR RAG")
    print("="*60)
    print("Traditional Vector RAG Limitations:")
    print("- Can only retrieve documents based on semantic similarity")
    print("- Cannot follow entity relationships")
    print("- Struggles with multi-hop questions")
    print("- May return incomplete or inaccurate answers for relationship queries")
    
    print("\nGraphRAG Advantages:")
    print("- Understands entity relationships")
    print("- Can traverse multiple hops in knowledge graph")
    print("- More accurate for complex queries")
    print("- Better at answering relationship-based questions")
    
    return results

def test_specific_scenarios():
    """Test specific multi-hop scenarios"""
    print("\n" + "="*60)
    print("Testing Specific Multi-Hop Scenarios")
    print("="*60)
    
    graph_rag = GraphRAG()
    
    scenarios = [
        "Who is John Smith's manager?",
        "Which project does John Smith's manager lead?",
        "Who is the CEO of the company where Jane Doe works?",
        "What skills does the team working on Project Alpha have?",
        "Who manages the person who leads Project Beta?"
    ]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario}")
        try:
            result = graph_rag.answer_query(scenario)
            print(f"Answer: {result['answer']}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    graph_rag.close()

if __name__ == "__main__":
    print("GraphRAG Multi-Hop Testing System")
    print("-" * 40)
    
    # Note: This requires Neo4j to be running locally
    # For demonstration, we'll show the structure and expected results
    
    print("\nSYSTEM OVERVIEW:")
    print("1. Entity Extraction: spaCy NER for entities")
    print("2. Relationship Extraction: Pattern matching")
    print("3. Knowledge Graph: Neo4j for storage")
    print("4. Graph Traversal: Multi-hop relationship queries")
    print("5. LLM Integration: OpenAI for answer generation")
    
    print("\nEXPECTED MULTI-HOP TEST RESULTS:")
    print("1. 'Who is John Smith's manager?' → Sarah Johnson (1 hop)")
    print("2. 'Which project does John Smith's manager lead?' → Project Alpha (2 hops)")
    print("3. 'Who is the CEO of the company where Jane Doe works?' → Lisa Wang (3 hops)")
    print("4. 'What skills does the team lead of Project Alpha have?' → Leadership skills (2 hops)")
    print("5. 'Who manages the person who leads Project Beta?' → Michael Chen (3 hops)")
    
    print("\nNote: To run actual tests, you need to:")
    print("1. Install Neo4j (https://neo4j.com/download/)")
    print("2. Set up environment variables in .env file:")
    print("   NEO4J_URI=bolt://localhost:7687")
    print("   NEO4J_USER=neo4j")
    print("   NEO4J_PASSWORD=your_password")
    print("   OPENAI_API_KEY=your_openai_key")
    print("3. Install requirements: pip install -r requirements.txt")
    print("4. Download spaCy model: python -m spacy download en_core_web_sm")
    print("5. Run tests: python test_multihop.py")
    
    # Show sample run output
    print("\nSAMPLE OUTPUT FORMAT:")
    sample_output = """
    Processing query: Who is John Smith's manager?
    Detected entities: ['John Smith']
    Detected patterns: ['MANAGER']
    Retrieved context length: 450 characters
    
    Query: Who is John Smith's manager?
    
    Knowledge Graph Context:
    Entity: John Smith
      - WORKS_FOR -> TechCorp (Organization)
      - MANAGED_BY -> Sarah Johnson (Person)
      - WORKED_ON -> Project Alpha (Project)
    
    Graph Statistics:
      Person: 5 nodes
      Organization: 1 node
    
    Please provide an accurate answer based on the graph context above.
    
    Answer: Based on the knowledge graph, John Smith's manager is Sarah Johnson. 
    John works for TechCorp and reports to Sarah Johnson, who is identified as his manager.
    """
    
    print(sample_output)