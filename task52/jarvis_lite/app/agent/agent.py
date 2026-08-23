"""
Intelligent Agent with LangGraph-inspired routing.

Routes user queries to appropriate tools or RAG pipeline.
"""

import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from app.config.settings import settings
from app.core.exceptions import AgentError
from app.memory.memory_service import MemoryService
from app.tools.base import BaseTool, ToolOutput
from app.tools.calculator import CalculatorTool
from app.tools.weather import WeatherTool
from app.tools.document_search import DocumentSearchTool

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Possible agent states."""
    ROUTING = "routing"
    EXECUTING_TOOL = "executing_tool"
    GENERATING_RESPONSE = "generating_response"
    COMPLETE = "complete"


class ExecutionStep:
    """Records a single execution step for debugging."""

    def __init__(
        self,
        state: AgentState,
        query: str,
        decision: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_output: Optional[ToolOutput] = None,
        reasoning: Optional[str] = None,
    ) -> None:
        self.state = state
        self.query = query
        self.decision = decision
        self.tool_name = tool_name
        self.tool_output = tool_output
        self.reasoning = reasoning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "decision": self.decision,
            "tool_name": self.tool_name,
            "tool_success": self.tool_output.success if self.tool_output else None,
            "reasoning": self.reasoning,
        }


class IntelligentAgent:
    """
    Intelligent agent that routes queries to tools or RAG.
    
    Decision logic:
    - Calculator: mathematical expressions/questions
    - Weather: weather-related queries
    - Document Search: document/knowledge base queries
    - RAG/LLM: general conversation
    """

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        memory_service: Optional[MemoryService] = None,
        rag_service: Optional[Any] = None,
        verbose: bool = True,
    ) -> None:
        """
        Initialize agent.
        
        Args:
            tools: List of tools available to agent
            memory_service: Memory service for conversation context
            rag_service: RAG service for document queries
            verbose: Enable detailed logging
        """
        self.verbose = verbose
        self.memory = memory_service or MemoryService(memory_type="buffer", max_context=5)
        self.rag_service = rag_service
        self.execution_history: List[ExecutionStep] = []
        
        # Initialize tools
        self.tools: Dict[str, BaseTool] = {}
        
        if tools:
            for tool in tools:
                self.tools[tool.name] = tool
        else:
            # Default tools
            self.tools["calculator"] = CalculatorTool()
            self.tools["weather"] = WeatherTool()
            
            if rag_service:
                doc_search = DocumentSearchTool(rag_service)
                self.tools["search_documents"] = doc_search
        
        logger.info(f"Initialized IntelligentAgent with {len(self.tools)} tools")

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process user query with intelligent routing.
        
        Returns:
            {
                "answer": str,
                "reasoning": str,
                "tool_used": Optional[str],
                "execution_steps": List[ExecutionStep],
                "confidence": float
            }
        """
        self.execution_history.clear()
        
        try:
            # Add to memory
            self.memory.add_user_message(query)
            
            # Route to appropriate handler
            routing_step = ExecutionStep(
                state=AgentState.ROUTING,
                query=query,
            )
            self.execution_history.append(routing_step)
            
            decision, tool_name, confidence = self._route_query(query)
            routing_step.decision = decision
            routing_step.tool_name = tool_name
            
            if self.verbose:
                logger.info(f"Agent routing: {decision} ({confidence:.2f}% confidence)")
            
            # Execute based on routing decision
            if tool_name and tool_name in self.tools:
                result = self._execute_tool(query, tool_name)
            else:
                result = self._generate_rag_response(query)
            
            # Add response to memory
            self.memory.add_assistant_message(result["answer"])
            
            return result
        
        except Exception as e:
            logger.exception(f"Agent error: {e}")
            raise AgentError(f"Agent processing failed: {e}") from e

    def _route_query(self, query: str) -> tuple[str, Optional[str], float]:
        """
        Route query to appropriate tool or service.
        
        Returns:
            (decision_name, tool_name, confidence)
        """
        query_lower = query.lower()
        
        # Check for calculator keywords
        calc_keywords = ["calculate", "compute", "what is", "math", "plus", "minus", "times", "divide", "^"]
        calc_indicators = sum(1 for kw in calc_keywords if kw in query_lower)
        
        if calc_indicators >= 1 and any(char in query for char in "+-*/%()^"):
            return ("calculator", "calculator", 0.85)
        
        # Check for weather keywords
        weather_keywords = ["weather", "temperature", "forecast", "rain", "snow", "cloudy", "sunny", "humid"]
        weather_indicators = sum(1 for kw in weather_keywords if kw in query_lower)
        
        if weather_indicators >= 1:
            return ("weather", "weather", 0.85)
        
        # Check for document search keywords
        doc_keywords = ["find", "search", "look for", "document", "handbook", "policy", "what is", "tell me about", "information about"]
        doc_indicators = sum(1 for kw in doc_keywords if kw in query_lower)
        
        if doc_indicators >= 2 or "search_documents" in self.tools:
            if "search_documents" in self.tools:
                return ("document_search", "search_documents", 0.75)
        
        # Default to RAG/LLM
        return ("rag_llm", None, 0.50)

    def _execute_tool(self, query: str, tool_name: str) -> Dict[str, Any]:
        """Execute a tool and return result."""
        tool_step = ExecutionStep(
            state=AgentState.EXECUTING_TOOL,
            query=query,
            tool_name=tool_name,
        )
        
        try:
            tool = self.tools[tool_name]
            
            # Extract parameters from query for specific tools
            if tool_name == "calculator":
                # Extract expression
                expression = query.replace("calculate", "").replace("compute", "").strip()
                expression = expression.lstrip(":").strip()
                output = tool.execute(expression=expression)
            
            elif tool_name == "weather":
                # Extract location
                location = query.replace("weather", "").replace("forecast", "").replace("temperature", "").strip()
                location = location.lstrip("for:").lstrip("in:").strip()
                output = tool.execute(location=location or "New York")
            
            elif tool_name == "search_documents":
                # Extract search query
                search_q = query.replace("search", "").replace("documents", "").replace("for", "").strip()
                search_q = search_q.lstrip(":").strip()
                output = tool.execute(query=search_q or query)
            
            else:
                output = tool.execute(query=query)
            
            tool_step.tool_output = output
            
            if output.success:
                answer = self._format_tool_output(tool_name, output.result)
            else:
                answer = f"Tool error: {output.error}"
            
            self.execution_history.append(tool_step)
            
            return {
                "answer": answer,
                "reasoning": f"Used {tool_name} to process query",
                "tool_used": tool_name,
                "execution_steps": [step.to_dict() for step in self.execution_history],
                "confidence": 0.85,
            }
        
        except Exception as e:
            logger.exception(f"Tool execution failed: {e}")
            tool_step.reasoning = f"Failed: {e}"
            self.execution_history.append(tool_step)
            
            return {
                "answer": f"Tool execution failed: {e}",
                "reasoning": f"Failed to execute {tool_name}",
                "tool_used": tool_name,
                "execution_steps": [step.to_dict() for step in self.execution_history],
                "confidence": 0.0,
            }

    def _generate_rag_response(self, query: str) -> Dict[str, Any]:
        """Generate response using RAG."""
        rag_step = ExecutionStep(
            state=AgentState.GENERATING_RESPONSE,
            query=query,
            reasoning="Using RAG pipeline for response"
        )
        self.execution_history.append(rag_step)
        
        if not self.rag_service:
            return {
                "answer": "I can't provide an answer without a document store configured.",
                "reasoning": "RAG service not available",
                "tool_used": None,
                "execution_steps": [step.to_dict() for step in self.execution_history],
                "confidence": 0.0,
            }
        
        try:
            result = self.rag_service.query(query)
            return {
                "answer": result.get("answer", "No answer generated"),
                "reasoning": "Generated using RAG pipeline",
                "tool_used": None,
                "sources": result.get("sources", []),
                "execution_steps": [step.to_dict() for step in self.execution_history],
                "confidence": 0.75,
            }
        except Exception as e:
            logger.exception(f"RAG generation failed: {e}")
            return {
                "answer": f"Generation failed: {e}",
                "reasoning": "RAG pipeline error",
                "tool_used": None,
                "execution_steps": [step.to_dict() for step in self.execution_history],
                "confidence": 0.0,
            }

    @staticmethod
    def _format_tool_output(tool_name: str, result: Any) -> str:
        """Format tool output as readable text."""
        if tool_name == "calculator":
            return f"The calculation result is: **{result}**"
        
        elif tool_name == "weather":
            if isinstance(result, dict):
                loc = result.get("location", "Unknown")
                temp = result.get("temperature_f", "N/A")
                condition = result.get("condition", "N/A")
                humidity = result.get("humidity_percent", "N/A")
                return (f"**Weather in {loc}:**\n"
                       f"• Temperature: {temp}°F\n"
                       f"• Condition: {condition}\n"
                       f"• Humidity: {humidity}%")
            return str(result)
        
        elif tool_name == "search_documents":
            if isinstance(result, dict) and result.get("found"):
                results = result.get("results", [])
                if not results:
                    return "No documents found matching your query."
                
                answer = f"**Found {len(results)} result(s):**\n\n"
                for r in results[:3]:  # Top 3 results
                    answer += f"• **{r['document']}** (Page {r['page']}, Score: {r['relevance_score']})\n"
                    answer += f"  {r['excerpt']}\n\n"
                return answer
            elif isinstance(result, dict):
                return result.get("message", "No results found")
            return str(result)
        
        else:
            return str(result)

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get execution history for debugging."""
        return [step.to_dict() for step in self.execution_history]

    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()

    def __repr__(self) -> str:
        return f"IntelligentAgent(tools={len(self.tools)}, memory={self.memory.memory_type})"
