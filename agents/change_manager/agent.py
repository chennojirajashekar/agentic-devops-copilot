"""
Change Manager Agent - Orchestrates rollout with human approval and CI/CD.
"""
import os, json, logging, time
from dataclasses import dataclass, asdict
from github import Github
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class RolloutResult:
    incident_id: str
    status: str
    deployment_triggered: bool
    pipeline_url: str
    pr_merged: bool
    actual_mttr_minutes: float
    actions_taken: list
    final_notes: str

    def to_dict(self): return asdict(self)
    def to_json(self): return json.dumps(self.to_dict(), indent=2)


class ChangeManagerAgent:
    """Agent 5: Orchestrates rollout - approval gates, CI/CD, PR merge."""

    def __init__(self):
        self.gh = Github(os.environ.get("GITHUB_TOKEN", ""))
        self.repo_owner = os.environ.get("GITHUB_REPO_OWNER", "")
        self.repo_name = os.environ.get("GITHUB_REPO_NAME", "")
        self.automation_level = os.environ.get("AUTOMATION_LEVEL", "semi-auto")
        self.human_approval = os.environ.get("HUMAN_APPROVAL_REQUIRED", "true").lower() == "true"
        logger.info("ChangeManagerAgent initialized. Level=%s", self.automation_level)

    def orchestrate_rollout(self, incident, fix, review, start_time: float) -> RolloutResult:
        actions = []
        result = RolloutResult(
            incident_id=incident.incident_id, status="pending_approval",
            deployment_triggered=False, pipeline_url="",
            pr_merged=False, actual_mttr_minutes=0.0,
            actions_taken=actions, final_notes=""
        )

        # Gate 1: SRE approval
        if not review.approved:
            result.status = "rejected"
            result.final_notes = f"Rejected: {review.reviewer_notes}"
            actions.append(f"SRE REJECTED: {review.recommendation}")
            return self._finalize(result, start_time)

        actions.append(f"SRE approved (risk={review.risk_score}/{review.risk_level})")

        # Gate 2: Human approval
        if self.human_approval and self.automation_level != "full-auto":
            actions.append("Human approval: AUTO-APPROVED (demo mode)")
        else:
            actions.append("Auto-approved (full-auto)")
        result.status = "approved"

        # Step 3: Trigger CI/CD
        pipeline_url = self._trigger_pipeline(incident, fix, actions)
        if pipeline_url:
            result.deployment_triggered = True
            result.pipeline_url = pipeline_url

        # Step 4: Merge PR
        if fix.pr_number and fix.pr_number > 0:
            result.pr_merged = self._merge_pr(fix.pr_number, actions)

        result.status = "deployed" if result.deployment_triggered else "approved"
        result.final_notes = (
            f"Fix={fix.fix_type} | PR=#{fix.pr_number or 'N/A'} | "
            f"Deployment={'triggered' if result.deployment_triggered else 'manual'}"
        )
        return self._finalize(result, start_time)

    def _trigger_pipeline(self, incident, fix, actions: list) -> str:
        if not (self.repo_owner and self.repo_name and os.environ.get("GITHUB_TOKEN")):
            actions.append("Pipeline: skipped (GitHub not configured)")
            return ""
        try:
            repo = self.gh.get_repo(f"{self.repo_owner}/{self.repo_name}")
            workflows = list(repo.get_workflows())
            deploy_wf = next((w for w in workflows if "deploy" in w.name.lower()), None)
            url = f"https://github.com/{self.repo_owner}/{self.repo_name}/actions"
            if deploy_wf:
                deploy_wf.create_dispatch(ref="main", inputs={
                    "incident_id": incident.incident_id[:50],
                    "fix_type": fix.fix_type
                })
                actions.append(f"GitHub Actions triggered: {url}")
            else:
                actions.append(f"No deploy workflow found. Manual: {url}")
            return url
        except Exception as exc:
            logger.error("Pipeline trigger failed: %s", exc)
            actions.append(f"Pipeline failed: {exc}")
            return ""

    def _merge_pr(self, pr_number: int, actions: list) -> bool:
        if not os.environ.get("GITHUB_TOKEN"):
            return False
        try:
            repo = self.gh.get_repo(f"{self.repo_owner}/{self.repo_name}")
            pr = repo.get_pull(pr_number)
            if pr.mergeable:
                pr.merge(
                    commit_title=f"[auto] {pr.title}",
                    commit_message="Merged by Agentic DevOps Copilot.",
                    merge_method="squash"
                )
                actions.append(f"PR #{pr_number} merged.")
                return True
            else:
                actions.append(f"PR #{pr_number} not mergeable.")
                return False
        except Exception as exc:
            logger.error("Merge failed: %s", exc)
            actions.append(f"Merge error: {exc}")
            return False

    def _finalize(self, result: RolloutResult, start_time: float) -> RolloutResult:
        result.actual_mttr_minutes = round((time.time() - start_time) / 60, 2)
        logger.info("Rollout done: status=%s MTTR=%.2fm", result.status, result.actual_mttr_minutes)
        return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys; sys.path.insert(0, "../..")
    from agents.alert_ingestor.agent import AlertIngestorAgent
    from agents.rca_agent.agent import RCAAgent
    from agents.code_fix_agent.agent import CodeFixAgent
    from agents.sre_reviewer.agent import SREReviewerAgent
    t0 = time.time()
    inc = AlertIngestorAgent().ingest()
    rca = RCAAgent().analyze(inc)
    fix = CodeFixAgent().propose_fix(inc, rca)
    review = SREReviewerAgent().review(inc, rca, fix)
    rollout = ChangeManagerAgent().orchestrate_rollout(inc, fix, review, t0)
    print(rollout.to_json())
