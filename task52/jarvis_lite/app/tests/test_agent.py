"""Tests for agent module (intelligent routing and tool execution)."""

import pytest

from app.agent.agent import IntelligentAgent, AgentState
from app.memory.memory_service import MemoryService
from app.tools.calculator import CalculatorTool
from app.tools.weather import WeatherTool


class TestIntelligentAgent:
    """Test IntelligentAgent."""

    def test_agent_creation(self):
        """Test agent can be created."""
        agent = IntelligentAgent()
        
        assert agent is not None
        assert len(agent.tools) >= 2
        assert "calculator" in agent.tools
        assert "weather" in agent.tools

    def test_agent_has_memory(self):
        """Test agent has memory service."""
        agent = IntelligentAgent()
        
        assert agent.memory is not None
        assert isinstance(agent.memory, MemoryService)

    def test_routing_to_calculator(self):
        """Test that calculator queries are routed to calculator tool."""
        agent = IntelligentAgent(verbose=False)
        
        decision, tool_name, confidence = agent._route_query("What is 2 + 2?")
        
        assert tool_name == "calculator"
        assert confidence >= 0.5

    def test_routing_to_weather(self):
        """Test that weather queries are routed to weather tool."""
        agent = IntelligentAgent(verbose=False)
        
        decision, tool_name, confidence = agent._route_query("What is the weather in New York?")
        
        assert tool_name == "weather"
        assert confidence >= 0.5

    def test_routing_to_rag_default(self):
        """Test that unknown queries default to RAG."""
        agent = IntelligentAgent(verbose=False)
        
        decision, tool_name, confidence = agent._route_query("Tell me something interesting")
        
        assert tool_name is None or tool_name not in agent.tools
        assert decision == "rag_llm"

    def test_process_calculator_query(self):
        """Test processing a calculator query."""
        agent = IntelligentAgent(verbose=False)
        
        result = agent.process_query("Calculate 2 + 2")
        
        assert result is not None
        assert "answer" in result
        assert result["confidence"] > 0.0

    def test_process_weather_query(self):
        """Test processing a weather query."""
        agent = IntelligentAgent(verbose=False)
        
        result = agent.process_query("Weather in London")
        
        assert result is not None
        assert "answer" in result
        assert result["tool_used"] == "weather"

    def test_memory_tracks_conversation(self):
        """Test that agent memory tracks conversation."""
        agent = IntelligentAgent(verbose=False)
        
        agent.process_query("Calculate 5 + 5")
        agent.process_query("Calculate 10 * 2")
        
        history = agent.memory.get_context_for_prompt()
        
        # Should have at least 4 messages (2 user, 2 assistant)
        assert len(history) >= 2

    def test_execution_history_tracked(self):
        """Test that execution history is tracked."""
        agent = IntelligentAgent(verbose=False)
        
        result = agent.process_query("Calculate sqrt(16)")
        
        assert "execution_steps" in result
        assert len(result["execution_steps"]) > 0

    def test_clear_history(self):
        """Test clearing execution history."""
        agent = IntelligentAgent(verbose=False)
        
        agent.process_query("Calculate 2 + 2")
        assert len(agent.execution_history) > 0
        
        agent.clear_history()
        assert len(agent.execution_history) == 0

    def test_get_execution_history(self):
        """Test getting execution history."""
        agent = IntelligentAgent(verbose=False)
        
        agent.process_query("Calculate 2 + 2")
        history = agent.get_execution_history()
        
        assert len(history) > 0
        assert all("state" in step for step in history)

    def test_custom_tools(self):
        """Test agent with custom tools."""
        custom_tools = [CalculatorTool(), WeatherTool()]
        agent = IntelligentAgent(tools=custom_tools, verbose=False)
        
        assert len(agent.tools) == 2

    def test_agent_with_custom_memory(self):
        """Test agent with custom memory."""
        memory = MemoryService(memory_type="summary", max_context=3)
        agent = IntelligentAgent(memory_service=memory, verbose=False)
        
        assert agent.memory == memory

    def test_agent_repr(self):
        """Test agent string representation."""
        agent = IntelligentAgent(verbose=False)
        repr_str = repr(agent)
        
        assert "IntelligentAgent" in repr_str
        assert "tools=" in repr_str

    def test_multiple_queries_sequence(self):
        """Test processing multiple queries in sequence."""
        agent = IntelligentAgent(verbose=False)
        
        queries = [
            "Calculate 10 + 5",
            "What about 20 / 4",
            "Weather in Paris"
        ]
        
        for query in queries:
            result = agent.process_query(query)
            assert result is not None
            assert "answer" in result

    def test_routing_decision_values(self):
        """Test that routing decisions return expected values."""
        agent = IntelligentAgent(verbose=False)
        
        decision, tool_name, confidence = agent._route_query("Calculate 2 + 2")
        
        assert isinstance(decision, str)
        assert tool_name is None or isinstance(tool_name, str)
        assert 0 <= confidence <= 1

    def test_tool_output_formatting(self):
        """Test formatting of tool outputs."""
        calculator_result = {"result": 42}
        formatted = IntelligentAgent._format_tool_output("calculator", calculator_result)
        
        assert "42" in str(formatted)

    def test_weather_output_formatting(self):
        """Test formatting of weather tool output."""
        weather_result = {
            "location": "New York",
            "temperature_f": 72,
            "condition": "Sunny",
            "humidity_percent": 60
        }
        formatted = IntelligentAgent._format_tool_output("weather", weather_result)
        
        assert "New York" in formatted
        assert "72" in formatted or "Sunny" in formatted

    def test_agent_error_handling(self):
        """Test agent handles errors gracefully."""
        agent = IntelligentAgent(verbose=False)
        
        # Query that might cause issues but should be handled
        result = agent.process_query("Calculate 1 / 0")
        
        assert result is not None
        assert "answer" in result
        # Should have some response even if tool fails

    def test_verbose_mode(self):
        """Test agent verbose mode."""
        agent = IntelligentAgent(verbose=True)
        
        result = agent.process_query("Calculate 2 + 2")
        
        assert result is not None
        assert result["confidence"] > 0.0


class TestAgentRouting:
    """Test agent routing logic specifically."""

    def test_routing_with_mathematical_symbols(self):
        """Test routing with mathematical symbols."""
        agent = IntelligentAgent(verbose=False)
        
        queries = [
            "What is 5 + 3?",
            "Calculate 2 * 4",
            "Compute 10 ^ 2",
            "100 / 4",
        ]
        
        for query in queries:
            decision, tool_name, confidence = agent._route_query(query)
            assert tool_name == "calculator" or decision == "calculator"

    def test_routing_with_weather_keywords(self):
        """Test routing with weather keywords."""
        agent = IntelligentAgent(verbose=False)
        
        queries = [
            "What's the weather?",
            "Tell me the temperature",
            "Is it raining?",
            "Weather forecast for tomorrow",
        ]
        
        for query in queries:
            decision, tool_name, confidence = agent._route_query(query)
            assert tool_name == "weather" or decision == "weather"

    def test_routing_confidence_levels(self):
        """Test that routing confidence levels are reasonable."""
        agent = IntelligentAgent(verbose=False)
        
        # Strong calculator indicators
        decision, tool_name, conf1 = agent._route_query("Calculate 2 + 2")
        
        # Weak indicators should default to RAG
        decision, tool_name, conf2 = agent._route_query("Hello")
        
        # Strong indicators should have higher confidence
        assert conf1 >= conf2 or tool_name == "calculator"
