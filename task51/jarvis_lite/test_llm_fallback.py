#!/usr/bin/env python
"""Test LLM fallback functionality."""

import sys
from app.agent.agent import IntelligentAgent

def test_llm_fallback():
    print("Testing LLM fallback without documents...")
    print()
    
    agent = IntelligentAgent(verbose=True)
    
    # Test 1: General question (no documents, should use LLM fallback)
    print("Test 1: General knowledge question (no documents)")
    print("-" * 60)
    query1 = "What is machine learning?"
    result1 = agent.process_query(query1)
    print(f"Query: {query1}")
    print(f"Tool used: {result1.get('tool_used', 'N/A')}")
    print(f"Confidence: {result1.get('confidence', 0):.0%}")
    answer1 = result1.get("answer", "N/A")
    print(f"Answer: {answer1[:300] if len(answer1) > 300 else answer1}...")
    print()
    
    # Test 2: Weather query (should use weather tool)
    print("Test 2: Weather query")
    print("-" * 60)
    query2 = "weather in paris"
    result2 = agent.process_query(query2)
    print(f"Query: {query2}")
    print(f"Tool used: {result2.get('tool_used', 'N/A')}")
    print(f"Confidence: {result2.get('confidence', 0):.0%}")
    answer2 = result2.get("answer", "N/A")
    print(f"Answer: {answer2[:300] if len(answer2) > 300 else answer2}...")
    print()
    
    # Test 3: Calculator query (should use calculator tool)
    print("Test 3: Calculator query")
    print("-" * 60)
    query3 = "calculate 25 * 4"
    result3 = agent.process_query(query3)
    print(f"Query: {query3}")
    print(f"Tool used: {result3.get('tool_used', 'N/A')}")
    print(f"Confidence: {result3.get('confidence', 0):.0%}")
    answer3 = result3.get("answer", "N/A")
    print(f"Answer: {answer3}")
    print()
    
    # Verify results
    print("=" * 60)
    print("✅ Test Results:")
    print("=" * 60)
    
    # Check Test 1
    if "llm_fallback" in result1.get("tool_used", "").lower() or "rag" in result1.get("tool_used", "").lower():
        print("✅ Test 1 PASSED: Used LLM fallback for general question")
    else:
        print(f"❌ Test 1 FAILED: Expected LLM fallback, got {result1.get('tool_used')}")
    
    # Check Test 2
    if "weather" in result2.get("tool_used", "").lower():
        print("✅ Test 2 PASSED: Used Weather tool for weather query")
    else:
        print(f"❌ Test 2 FAILED: Expected Weather tool, got {result2.get('tool_used')}")
    
    # Check Test 3
    if "calculator" in result3.get("tool_used", "").lower():
        print("✅ Test 3 PASSED: Used Calculator tool for math query")
    else:
        print(f"❌ Test 3 FAILED: Expected Calculator tool, got {result3.get('tool_used')}")
    
    print()
    print("All tests completed!")

if __name__ == "__main__":
    test_llm_fallback()
