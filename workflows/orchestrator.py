"""
Multi-Agent Orchestrator - chains all 5 agents in sequence.
"""
import time, logging, json
from dataclasses import dataclass, asdict

from agents.alert_ingestor.agent import AlertIngestorAgent
from agents.rca_agent.agent import RCAAgent
from agents.code_fix_agent.agent import CodeFixAgent
from agents.sre_reviewer.agent import SREReviewerAgent
from agents.change_manager.agent import ChangeManagerAgent

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    incident: dict
    rca: dict
    fix: dict
    review: dict
    rollout: dict
    total_duration_seconds: float
    success: bool
    summary: str

    def to_json(self):
        return json.dumps(asdict(self), indent=2)


class AgenticDevOpsOrchestrator:
    """Chains all 5 DevOps agents for incident-to-fix automation."""

    def __init__(self):
        self.alert_agent  = AlertIngestorAgent()
        self.rca_agent    = RCAAgent()
        self.fix_agent    = CodeFixAgent()
        self.review_agent = SREReviewerAgent()
        self.change_agent = ChangeManagerAgent()
        logger.info("All 5 agents initialized.")

    def run(self, raw_alert: dict = None) -> WorkflowResult:
        start = time.time()
        sep = "=" * 50
        logger.info("%s", sep)
        logger.info("  AGENTIC DEVOPS WORKFLOW STARTED")
        logger.info("%s", sep)

        logger.info("[1/5] Alert Ingestor...")
        incident = self.alert_agent.ingest(raw_alert)
        logger.info("  -> %s [%s]", incident.title, incident.severity)

        logger.info("[2/5] Root Cause Analysis...")
        rca = self.rca_agent.analyze(incident)
        logger.info("  -> %s (%s)", rca.root_cause, rca.confidence)

        logger.info("[3/5] Code Fix Agent...")
        fix = self.fix_agent.propose_fix(incident, rca)
        logger.info("  -> %s | PR: %s", fix.fix_type, fix.pr_url or "N/A")

        logger.info("[4/5] SRE Reviewer...")
        review = self.review_agent.review(incident, rca, fix)
        logger.info("  -> %s (risk=%d)", review.recommendation, review.risk_score)

        logger.info("[5/5] Change Manager...")
        rollout = self.change_agent.orchestrate_rollout(incident, fix, review, start)
        logger.info("  -> %s | MTTR=%.2fm", rollout.status, rollout.actual_mttr_minutes)

        duration = time.time() - start
        success = rollout.status in ("deployed", "approved")
        summary = (
            f"Incident : {incident.title} ({incident.severity})\n"
            f"Root Cause: {rca.root_cause}\n"
            f"Fix       : [{fix.fix_type}] {fix.title}\n"
            f"PR        : {fix.pr_url or 'N/A'}\n"
            f"Review    : {review.recommendation} (risk={review.risk_score}/100)\n"
            f"Rollout   : {rollout.status}\n"
            f"MTTR      : {rollout.actual_mttr_minutes:.2f} min\n"
            f"Result    : {'SUCCESS' if success else 'REJECTED/FAILED'}"
        )
        logger.info("%s", sep)
        logger.info("  WORKFLOW %s (%.2fs)", "SUCCEEDED" if success else "FAILED", duration)
        logger.info("%s", sep)

        return WorkflowResult(
            incident=incident.to_dict(), rca=rca.to_dict(),
            fix=fix.to_dict(), review=review.to_dict(), rollout=rollout.to_dict(),
            total_duration_seconds=round(duration, 2),
            success=success, summary=summary,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    result = AgenticDevOpsOrchestrator().run()
    print("\n" + "=" * 50)
    print(result.summary)
    with open("workflow_result.json", "w") as f:
        f.write(result.to_json())
    print("\nSaved to workflow_result.json")
