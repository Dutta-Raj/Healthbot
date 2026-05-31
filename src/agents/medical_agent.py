# src/agents/medical_agent.py
"""
Agentic AI System for Medical Diagnosis using Multiple LLMs
Supports: Claude, OpenAI, Cohere, and Open Source Models
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import cohere
import openai
from anthropic import Anthropic
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain_cohere import ChatCohere
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

class ModelProvider(Enum):
    COHERE = "cohere"
    OPENAI = "openai"
    CLAUDE = "claude"
    LLAMA = "llama"

@dataclass
class AgentConfig:
    provider: ModelProvider
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 0.9

class MedicalAgent:
    """Multi-Model Medical Agent with RAG and Reasoning"""
    
    def __init__(self):
        self.configs = {
            ModelProvider.COHERE: AgentConfig(
                provider=ModelProvider.COHERE,
                model_name="command-r-plus",
                temperature=0.7
            ),
            ModelProvider.OPENAI: AgentConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-4-turbo-preview",
                temperature=0.6
            ),
            ModelProvider.CLAUDE: AgentConfig(
                provider=ModelProvider.CLAUDE,
                model_name="claude-3-opus-20240229",
                temperature=0.7
            )
        }
        
        # Initialize clients
        self.cohere_client = cohere.Client(os.getenv("COHERE_API_KEY"))
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.tools = self._create_tools()
        
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent"""
        return [
            Tool(
                name="Medical_Symptom_Checker",
                func=self.check_symptoms,
                description="Check symptoms and provide possible conditions"
            ),
            Tool(
                name="Drug_Interaction_Checker",
                func=self.check_drug_interactions,
                description="Check potential drug interactions"
            ),
            Tool(
                name="Emergency_Detector",
                func=self.detect_emergency,
                description="Detect emergency medical situations"
            ),
            Tool(
                name="Medical_Knowledge_Base",
                func=self.query_medical_kb,
                description="Query medical knowledge base for information"
            )
        ]
    
    async def process_with_fallback(self, query: str) -> Dict[str, Any]:
        """Process query with fallback between models"""
        results = {}
        
        for provider in [ModelProvider.CLAUDE, ModelProvider.OPENAI, ModelProvider.COHERE]:
            try:
                result = await self._query_model(provider, query)
                results[provider.value] = {
                    "success": True,
                    "response": result,
                    "provider": provider.value
                }
                
                # If high confidence, break early
                if self._calculate_confidence(result) > 0.8:
                    break
                    
            except Exception as e:
                results[provider.value] = {
                    "success": False,
                    "error": str(e),
                    "provider": provider.value
                }
                continue
        
        # Aggregate and vote on best response
        return self._aggregate_results(results)
    
    async def _query_model(self, provider: ModelProvider, query: str) -> str:
        """Query specific model"""
        config = self.configs[provider]
        
        if provider == ModelProvider.COHERE:
            response = self.cohere_client.chat(
                model=config.model_name,
                message=query,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
            return response.text
            
        elif provider == ModelProvider.OPENAI:
            response = self.openai_client.chat.completions.create(
                model=config.model_name,
                messages=[
                    {"role": "system", "content": "You are a medical AI assistant."},
                    {"role": "user", "content": query}
                ],
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
            return response.choices[0].message.content
            
        elif provider == ModelProvider.CLAUDE:
            response = self.anthropic_client.messages.create(
                model=config.model_name,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                messages=[
                    {"role": "user", "content": query}
                ]
            )
            return response.content[0].text
    
    def check_symptoms(self, symptoms: str) -> str:
        """Check symptoms using medical knowledge base"""
        prompt = f"""
        Analyze these symptoms: {symptoms}
        
        Provide:
        1. Possible conditions (ranked by likelihood)
        2. Recommended actions
        3. When to seek emergency care
        4. Self-care measures
        
        Use medical guidelines and evidence-based information.
        """
        # Implementation with RAG
        return self._query_medical_llm(prompt)
    
    def check_drug_interactions(self, drugs: str) -> str:
        """Check potential drug interactions"""
        prompt = f"""
        Check interactions for: {drugs}
        
        Provide:
        1. Known interactions (major, moderate, minor)
        2. Side effects to watch for
        3. Recommendations for safe use
        """
        return self._query_medical_llm(prompt)
    
    def detect_emergency(self, query: str) -> Dict[str, Any]:
        """Detect emergency situations"""
        emergency_keywords = [
            "heart attack", "stroke", "seizure", "unconscious",
            "bleeding severely", "difficulty breathing", "chest pain",
            "suicide", "overdose", "poisoning", "head injury"
        ]
        
        is_emergency = any(keyword in query.lower() for keyword in emergency_keywords)
        
        return {
            "is_emergency": is_emergency,
            "message": "Call emergency services immediately (911/112)" if is_emergency else None,
            "urgency_level": "critical" if is_emergency else "normal"
        }
    
    def query_medical_kb(self, query: str) -> str:
        """Query medical knowledge base"""
        # Integrate with RAG pipeline
        from rag.rag_pipeline import rag_pipeline
        enhanced_query = rag_pipeline.enhance_prompt_with_rag(query)
        return self._query_medical_llm(enhanced_query)
    
    def _query_medical_llm(self, prompt: str) -> str:
        """Internal method to query LLM with medical context"""
        response = self.cohere_client.chat(
            model="command-r-plus",
            message=prompt,
            temperature=0.3,
            max_tokens=800
        )
        return response.text
    
    def _calculate_confidence(self, response: str) -> float:
        """Calculate confidence score of response"""
        # implement confidence scoring logic
        return 0.8 if len(response) > 50 else 0.5
    
    def _aggregate_results(self, results: Dict) -> Dict[str, Any]:
        """Aggregate results from multiple models"""
        successful = [r for r in results.values() if r.get("success")]
        
        if not successful:
            return {"error": "All models failed", "results": results}
        
        # Voting mechanism for best response
        responses = [r["response"] for r in successful]
        best_response = max(responses, key=len)  # Simple heuristic
        
        return {
            "response": best_response,
            "model_votes": len(successful),
            "all_responses": responses,
            "confidence": self._calculate_confidence(best_response)
        }

# Global agent instance
medical_agent = MedicalAgent()
