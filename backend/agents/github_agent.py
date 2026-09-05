from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage
import structlog

from agents.base import BaseAgent
from rag.engine import RAGEngine

logger = structlog.get_logger("agents.github")


class GitHubAgent(BaseAgent):
    def __init__(self, rag_engine: RAGEngine = None):
        super().__init__(rag_engine)
        self.system_prompt = """You are a GitHub Operations Specialist.
Your task is to manage GitHub interactions for the security review platform:
1. Create pull requests with security fixes
2. Manage branches and commits
3. Handle webhook events
4. Sync PR status

Guidelines:
- Follow GitHub best practices
- Create descriptive PR titles and bodies
- Link PRs to security findings
- Use proper commit messages
- Handle merge conflicts gracefully"""

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        action = input_data.get("action", "create_pr")
        
        if action == "create_pr":
            return await self.create_pr(input_data)
        elif action == "update_pr":
            return await self.update_pr(input_data)
        elif action == "sync_pr":
            return await self.sync_pr(input_data)
        elif action == "create_branch":
            return await self.create_branch(input_data)
        else:
            return await self.create_pr(input_data)
    
    async def create_pr(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        repo = input_data.get("repository")
        patches = input_data.get("patches", [])
        title = input_data.get("title", "Security Fixes")
        body = input_data.get("body", "")
        head_branch = input_data.get("head_branch", "security/fixes")
        base_branch = input_data.get("base_branch", "main")
        access_token = input_data.get("access_token")
        
        if not access_token:
            return {"success": False, "error": "GitHub access token required"}
        
        from github import Github
        
        try:
            g = Github(access_token)
            github_repo = g.get_repo(repo["full_name"])
            
            try:
                github_repo.get_branch(head_branch)
            except:
                base_ref = github_repo.get_branch(base_branch)
                github_repo.create_git_ref(f"refs/heads/{head_branch}", base_ref.commit.sha)
            
            commit_message = f"Security fixes: {len(patches)} vulnerabilities patched\n\n"
            for patch in patches:
                finding = patch.get("finding")
                if finding:
                    commit_message += f"- Fix {finding.get('rule_id')}: {finding.get('rule_name')} in {finding.get('file_path')}\n"
            
            for patch in patches:
                file_path = patch.get("file_path")
                if file_path:
                    local_file = input_data.get("local_path", "") + "/" + file_path
                    import os
                    if os.path.exists(local_file):
                        with open(local_file, 'r') as f:
                            content = f.read()
                        
                        github_repo.update_file(
                            path=file_path,
                            message=commit_message,
                            content=content,
                            branch=head_branch,
                        )
            
            github_pr = github_repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch,
            )
            
            return {
                "success": True,
                "pr_number": github_pr.number,
                "pr_url": github_pr.html_url,
                "pr_id": github_pr.id,
                "head_branch": head_branch,
                "base_branch": base_branch,
            }
            
        except Exception as e:
            logger.error("PR creation failed", repo=repo.get("full_name"), error=str(e))
            return {"success": False, "error": str(e)}
    
    async def update_pr(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        repo = input_data.get("repository")
        pr_number = input_data.get("pr_number")
        title = input_data.get("title")
        body = input_data.get("body")
        state = input_data.get("state")
        access_token = input_data.get("access_token")
        
        if not access_token:
            return {"success": False, "error": "GitHub access token required"}
        
        from github import Github
        
        try:
            g = Github(access_token)
            github_repo = g.get_repo(repo["full_name"])
            pr = github_repo.get_pull(pr_number)
            
            if title:
                pr.edit(title=title)
            if body:
                pr.edit(body=body)
            if state == "closed":
                pr.edit(state="closed")
            
            return {
                "success": True,
                "pr_number": pr.number,
                "title": pr.title,
                "state": pr.state,
            }
            
        except Exception as e:
            logger.error("PR update failed", repo=repo.get("full_name"), pr=pr_number, error=str(e))
            return {"success": False, "error": str(e)}
    
    async def sync_pr(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        repo = input_data.get("repository")
        pr_number = input_data.get("pr_number")
        access_token = input_data.get("access_token")
        
        if not access_token:
            return {"success": False, "error": "GitHub access token required"}
        
        from github import Github
        
        try:
            g = Github(access_token)
            github_repo = g.get_repo(repo["full_name"])
            pr = github_repo.get_pull(pr_number)
            
            return {
                "success": True,
                "merged": pr.merged,
                "state": pr.state,
                "merge_commit_sha": pr.merge_commit_sha,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
            }
            
        except Exception as e:
            logger.error("PR sync failed", repo=repo.get("full_name"), pr=pr_number, error=str(e))
            return {"success": False, "error": str(e)}
    
    async def create_branch(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        repo = input_data.get("repository")
        branch_name = input_data.get("branch_name")
        from_branch = input_data.get("from_branch", "main")
        access_token = input_data.get("access_token")
        
        if not access_token:
            return {"success": False, "error": "GitHub access token required"}
        
        from github import Github
        
        try:
            g = Github(access_token)
            github_repo = g.get_repo(repo["full_name"])
            
            source_branch = github_repo.get_branch(from_branch)
            github_repo.create_git_ref(f"refs/heads/{branch_name}", source_branch.commit.sha)
            
            return {
                "success": True,
                "branch": branch_name,
                "from_branch": from_branch,
            }
            
        except Exception as e:
            logger.error("Branch creation failed", repo=repo.get("full_name"), branch=branch_name, error=str(e))
            return {"success": False, "error": str(e)}
    
    async def generate_pr_description(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        patches = input_data.get("patches", [])
        scan = input_data.get("scan")
        repository = input_data.get("repository")
        
        rag_results = await self.rag_engine.query(
            "pull request description security fixes best practices",
            top_k=3
        )
        
        context = f"""
Repository: {repository.get('full_name') if repository else 'Unknown'}
Scan ID: {scan.get('id') if scan else 'Unknown'}
Patches: {len(patches)}

Patch Details:
{chr(10).join([f"- {p.get('finding', {}).get('rule_name')}: {p.get('file_path')} ({p.get('finding', {}).get('severity')})" for p in patches])}

Guidelines:
{chr(10).join([r['content'][:300] for r in rag_results])}
"""
        
        messages = [
            SystemMessage(content="""You are a Security Engineer writing a PR description.
Create a professional PR description that includes:
1. Summary of security fixes
2. List of vulnerabilities addressed
3. Testing instructions
4. Security impact assessment
5. References to findings"""),
            SystemMessage(content=context),
            HumanMessage(content="Generate a professional PR description for these security fixes.")
        ]
        
        response = await self._call_llm(messages)
        
        return {"description": response}