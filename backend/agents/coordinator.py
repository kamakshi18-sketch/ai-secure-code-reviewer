import structlog
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from agents.base import BaseAgent, AgentOrchestrator
from agents.security_analysis import SecurityAnalysisAgent
from agents.patch_generator import PatchGeneratorAgent
from agents.verification import VerificationAgent
from rag.engine import RAGEngine

logger = structlog.get_logger("agents.coordinator")


class CoordinatorAgent(BaseAgent):
    def __init__(self, rag_engine: RAGEngine = None):
        super().__init__(rag_engine)
        self.system_prompt = """You are the Coordinator Agent for an AI Secure Code Reviewer platform.
Your role is to orchestrate the security analysis workflow by coordinating with specialized agents.

You have access to:
1. Security Analysis Agent - analyzes vulnerabilities and provides explanations
2. RAG Agent - retrieves secure coding references and best practices
3. Patch Generation Agent - generates secure code patches
4. Verification Agent - verifies patches through testing and re-scanning
5. Documentation Agent - generates professional security reports
6. GitHub Agent - manages pull requests and repository operations

When users ask questions, determine which agent(s) to involve and provide comprehensive answers.
Always cite sources from the RAG system when providing security recommendations.
Never hallucinate security advice - always ground responses in retrieved knowledge."""

        self.orchestrator = AgentOrchestrator(rag_engine)
        self._register_agents()
    
    def _register_agents(self):
        self.orchestrator.register_agent("security_analysis", SecurityAnalysisAgent(self.rag_engine))
        self.orchestrator.register_agent("patch_generator", PatchGeneratorAgent(self.rag_engine))
        self.orchestrator.register_agent("verification", VerificationAgent(self.rag_engine))
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "chat")
        
        if action == "chat":
            return await self.process_chat(
                messages=input_data.get("messages", []),
                context=input_data.get("context", {}),
                user_id=input_data.get("user_id", ""),
            )
        elif action == "full_analysis":
            return await self.run_full_analysis(input_data)
        elif action == "explain_finding":
            return await self.explain_finding(input_data)
        elif action == "generate_patch":
            return await self.generate_patch(input_data)
        elif action == "verify_patch":
            return await self.verify_patch(input_data)
        else:
            return await self.process_chat(
                messages=input_data.get("messages", []),
                context=input_data.get("context", {}),
                user_id=input_data.get("user_id", ""),
            )
    
    async def process_chat(
        self,
        messages: List[Dict[str, str]],
        context: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        from agents.security_analysis import SecurityAnalysisAgent
        from agents.patch_generator import PatchGeneratorAgent
        
        security_agent = SecurityAnalysisAgent(self.rag_engine)
        patch_agent = PatchGeneratorAgent(self.rag_engine)
        
        last_message = messages[-1]["content"] if messages else ""
        
        sources = []
        answer_parts = []
        
        if any(keyword in last_message.lower() for keyword in ["why", "explain", "what is", "how does", "cwe", "owasp"]):
            if context.get("finding"):
                result = await security_agent.explain_finding(
                    finding=context["finding"],
                    question=last_message,
                    context=context
                )
                answer_parts.append(result["answer"])
                sources.extend(result.get("sources", []))
            else:
                result = await self._answer_general_question(last_message, context)
                answer_parts.append(result["answer"])
                sources.extend(result.get("sources", []))
        
        elif any(keyword in last_message.lower() for keyword in ["patch", "fix", "remediate", "resolve"]):
            if context.get("finding"):
                result = await patch_agent.generate_patch(
                    finding=context["finding"],
                    source_code=context.get("source_code", ""),
                    file_path=context["finding"].get("file_path", ""),
                    language=context.get("language", "python")
                )
                answer_parts.append(f"Generated patch:\n```diff\n{result['diff']}\n```")
                answer_parts.append(f"Provider: {result['provider']}, Model: {result['model']}")
            else:
                answer_parts.append("Please specify a finding to generate a patch for.")
        
        elif any(keyword in last_message.lower() for keyword in ["verify", "test", "validate"]):
            answer_parts.append("Verification requires running tests and re-scanning. Use the verification API endpoint.")
        
        else:
            result = await self._answer_general_question(last_message, context)
            answer_parts.append(result["answer"])
            sources.extend(result.get("sources", []))
        
        return {
            "answer": "\n\n".join(answer_parts),
            "sources": sources
        }
    
    async def run_full_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pipeline = [
            {"agent": "security_analysis", "output_key": "analysis"},
            {"agent": "patch_generator", "output_key": "patch"},
            {"agent": "verification", "output_key": "verification"},
        ]
        
        return await self.orchestrator.run_pipeline(pipeline, input_data)
    
    async def explain_finding(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        security_agent = SecurityAnalysisAgent(self.rag_engine)
        
        result = await security_agent.explain_finding(
            finding=input_data.get("finding"),
            question=input_data.get("question", "Explain this vulnerability"),
            context=input_data.get("context", {})
        )
        
        return result
    
    async def generate_patch(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        patch_agent = PatchGeneratorAgent(self.rag_engine)
        
        result = await patch_agent.generate_patch(
            finding=input_data.get("finding"),
            source_code=input_data.get("source_code", ""),
            file_path=input_data.get("file_path", ""),
            language=input_data.get("language", "python")
        )
        
        return result
    
    async def verify_patch(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        verification_agent = VerificationAgent(self.rag_engine)
        
        result = await verification_agent.analyze_failure(input_data)
        
        return result
    
    async def _answer_general_question(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.llm:
            return {"answer": "Mock response: I would answer your question using the RAG system.", "sources": []}
        
        rag_results = await self.rag_engine.query(question, top_k=5)
        
        context_str = "\n\n".join([f"Source: {r['metadata'].get('source', 'Unknown')}\n{r['content']}" for r in rag_results])
        
        messages = [
            SystemMessage(content=self.system_prompt),
            SystemMessage(content=f"Relevant security knowledge:\n{context_str}"),
            HumanMessage(content=question)
        ]
        
        answer = await self._call_llm(messages)
        
        return {
            "answer": answer,
            "sources": [{"source": r["metadata"].get("source"), "content": r["content"][:200]} for r in rag_results]
        }


class WorkflowOrchestrator:
    def __init__(self, rag_engine: RAGEngine = None):
        self.coordinator = CoordinatorAgent(rag_engine)
        self.rag_engine = rag_engine or RAGEngine()
    
    async def run_security_review_workflow(
        self,
        scan_id: str,
        findings: List[Dict[str, Any]],
        repository: Dict[str, Any]
    ) -> Dict[str, Any]:
        results = {
            "scan_id": scan_id,
            "findings_analyzed": 0,
            "patches_generated": 0,
            "patches_verified": 0,
            "patches_failed": 0,
            "errors": []
        }
        
        for finding in findings:
            try:
                if finding.get("status") != "open":
                    continue
                
                analysis_result = await self.coordinator.process({
                    "action": "explain_finding",
                    "finding": finding,
                    "context": {"repository": repository}
                })
                
                patch_result = await self.coordinator.process({
                    "action": "generate_patch",
                    "finding": finding,
                    "source_code": finding.get("source_code", ""),
                    "file_path": finding.get("file_path"),
                    "language": repository.get("language", "python")
                })
                
                results["findings_analyzed"] += 1
                results["patches_generated"] += 1
                
            except Exception as e:
                logger.error("Failed to process finding", finding_id=finding.get("id"), error=str(e))
                results["errors"].append({"finding_id": finding.get("id"), "error": str(e)})
        
        return results


# Global orchestrator instance
workflow_orchestrator = WorkflowOrchestrator()