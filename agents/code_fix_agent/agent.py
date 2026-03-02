"""
Code Fix Agent - Proposes patches/rollbacks and creates GitHub PRs.
"""
import os
import json
import logging
from dataclasses import dataclass, asdict
from openai import AzureOpenAI
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class FixProposal:
    incident_id: str
    fix_type: str
    title: str
    description: str
    patch_content: str
    target_file: str
    pr_url: str = ""
    pr_number: int = 0
    risk_level: str = "medium"
    estimated_mttr_minutes: int = 10

    def to_dict(self): return asdict(self)
    def to_json(self): return json.dumps(self.to_dict(), indent=2)


class CodeFixAgent:
    """Agent 3: Generates fix proposals and creates GitHub PRs."""

    SYSTEM_PROMPT = (
        "You are an expert DevOps engineer. Given an incident and root cause, "
        "propose the best fix. Prefer rollback for critical issues. Respond in JSON."
    )

    def __init__(self):
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        self.gh = Github(os.environ.get("GITHUB_TOKEN", ""))
        self.repo_owner = os.environ.get("GITHUB_REPO_OWNER", "")
        self.repo_name = os.environ.get("GITHUB_REPO_NAME", "")
        self.default_branch = os.environ.get("GITHUB_DEFAULT_BRANCH", "main")
        logger.info("CodeFixAgent initialized.")

    def propose_fix(self, incident, rca) -> FixProposal:
        proposal = self._call_openai(incident, rca)
        if self.repo_owner and self.repo_name and os.environ.get("GITHUB_TOKEN"):
            proposal = self._create_github_pr(proposal, incident, rca)
        return proposal

    def _call_openai(self, incident, rca) -> FixProposal:
        prompt = (
            f"INCIDENT: {incident.title} (severity={incident.severity})\n"
            f"ROOT_CAUSE: {rca.root_cause}\nAFFECTED: {rca.affected_component}\n"
            f"ACTION: {rca.recommended_action}\n\n"
            'JSON schema: {"fix_type":"rollback|code_patch|config_change","title":"...",'
            '"description":"...","patch_content":"...","target_file":"...",'
            '"risk_level":"low|medium|high","estimated_mttr_minutes":8}'
        )
        try:
            resp = self.openai_client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "system", "content": self.SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                temperature=0.1, response_format={"type": "json_object"},
            )
            raw = json.loads(resp.choices[0].message.content)
            return FixProposal(
                incident_id=incident.incident_id,
                fix_type=raw.get("fix_type", "rollback"),
                title=raw.get("title", f"fix: remediate {incident.title[:60]}"),
                description=raw.get("description", ""),
                patch_content=raw.get("patch_content", ""),
                target_file=raw.get("target_file", "N/A"),
                risk_level=raw.get("risk_level", "medium"),
                estimated_mttr_minutes=raw.get("estimated_mttr_minutes", 10),
            )
        except Exception as exc:
            logger.error("OpenAI fix failed: %s", exc)
            return FixProposal(
                incident_id=incident.incident_id, fix_type="rollback",
                title="fix: rollback payment-service to last stable version",
                description=f"Rollback for: {incident.title}\nRoot cause: {rca.root_cause}",
                patch_content="kubectl rollout undo deployment/payment-service",
                target_file="k8s/payment-service.yaml",
                risk_level="low", estimated_mttr_minutes=8,
            )

    def _create_github_pr(self, proposal: FixProposal, incident, rca) -> FixProposal:
        try:
            repo = self.gh.get_repo(f"{self.repo_owner}/{self.repo_name}")
            branch = f"fix/incident-{incident.incident_id[:20].replace('/', '-')}"
            sha = repo.get_branch(self.default_branch).commit.sha
            try:
                repo.create_git_ref(ref=f"refs/heads/{branch}", sha=sha)
            except GithubException as e:
                if e.status != 422: raise
            fix_md = (
                f"# {proposal.title}\n\n**Incident:** {incident.title}\n"
                f"**Root Cause:** {rca.root_cause}\n**Type:** {proposal.fix_type}\n"
                f"**Risk:** {proposal.risk_level}\n\n## Patch\n```\n{proposal.patch_content}\n```"
            )
            try:
                repo.create_file(
                    f"fixes/{branch.replace('/', '-')}.md",
                    f"fix: remediation for {incident.incident_id[:30]}",
                    fix_md, branch=branch
                )
            except GithubException: pass
            pr = repo.create_pull(
                title=proposal.title,
                body=f"{proposal.description}\n\n---\nAuto-generated by **Agentic DevOps Copilot**\nIncident: `{incident.incident_id}` | Severity: `{incident.severity}`",
                head=branch, base=self.default_branch
            )
            proposal.pr_url = pr.html_url
            proposal.pr_number = pr.number
            logger.info("Created PR #%d: %s", pr.number, pr.html_url)
        except Exception as exc:
            logger.error("PR creation failed: %s", exc)
        return proposal


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys; sys.path.insert(0, "../..")
    from agents.alert_ingestor.agent import AlertIngestorAgent
    from agents.rca_agent.agent import RCAAgent
    inc = AlertIngestorAgent().ingest()
    rca = RCAAgent().analyze(inc)
    fix = CodeFixAgent().propose_fix(inc, rca)
    print(fix.to_json())
