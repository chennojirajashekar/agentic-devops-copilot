"""
Orchestrator: Coordinates the multi-agent Agentic DevOps Copilot pipeline.
This async version wraps the sync agents using run_in_executor so it can be
used from FastAPI, Azure Functions, or any async context.
"""
import asyncio
import logging
import time
from typing import Optional

from agents.alert_ingestor.agent import AlertIngestorAgent
from agents.rca_agent.agent import RCAAgent
from agents.code_fix_agent.agent import CodeFixAgent
from agents.sre_reviewer.agent import SREReviewerAgent
from agents.change_manager.agent import ChangeManagerAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DevOpsCopilotOrchestrator:
    """Async orchestrator that wraps sync agents for use in async/API contexts."""

    def __init__(self):
        self.alert_agent = AlertIngestorAgent()
        self.rca_agent = RCAAgent()
        self.fix_agent = CodeFixAgent()
        self.reviewer_agent = SREReviewerAgent()
        self.change_agent = ChangeManagerAgent()
        logger.info("DevOpsCopilotOrchestrator: all 5 agents initialized.")

    async def run(self, raw_alert: Optional[dict] = None) -> dict:
        """
        Run the full 5-stage DevOps pipeline asynchronously.
        Each sync agent method is offloaded to a thread via run_in_executor
        so the event loop is never blocked.
        Returns a dict with keys: alert, rca, fix, review, rollout, success.
        """
        loop = asyncio.get_event_loop()
        start = time.time()
        results = {}

        logger.info("=== Agentic DevOps Copilot Pipeline Started ===")

        # Stage 1: Alert Ingestion
        logger.info("[1/5] Alert Ingestor...")
        incident = await loop.run_in_executor(
            None, self.alert_agent.ingest, raw_alert
        )
        if incident is None:
            results["alert"] = {"status": "no_alerts"}
            logger.info("No alerts found. Pipeline complete.")
            return results
        results["alert"] = incident.to_dict()
        logger.info("  -> %s [%s]", incident.title, incident.severity)

        # Stage 2: Root Cause Analysis
        logger.info("[2/5] Root Cause Analysis...")
        rca = await loop.run_in_executor(
            None, self.rca_agent.analyze, incident
        )
        results["rca"] = rca.to_dict()
        logger.info("  -> %s (%s)", rca.root_cause[:80], rca.confidence)

        # Stage 3: Code Fix Proposal
        logger.info("[3/5] Code Fix Agent...")
        fix = await loop.run_in_executor(
            None, self.fix_agent.propose_fix, incident, rca
        )
        results["fix"] = fix.to_dict()
        logger.info("  -> %s | PR: %s", fix.fix_type, fix.pr_url or "N/A")

        # Stage 4: SRE Review
        logger.info("[4/5] SRE Reviewer...")
        review = await loop.run_in_executor(
            None, self.reviewer_agent.review, incident, rca, fix
        )
        results["review"] = review.to_dict()
        logger.info("  -> %s (risk=%d)", review.recommendation, review.risk_score)

        # Stage 5: Change Management
        logger.info("[5/5] Change Manager...")
        rollout = await loop.run_in_executor(
            None, self.change_agent.orchestrate_rollout, incident, fix, review, start
        )
        results["rollout"] = rollout.to_dict()
        logger.info("  -> %s | MTTR=%.2fm", rollout.status, rollout.actual_mttr_minutes)

        results["success"] = rollout.status in ("deployed", "approved")
        results["total_duration_seconds"] = round(time.time() - start, 2)

        logger.info(
            "=== Pipeline Complete: %s (%.2fs) ===",
            rollout.status,
            results["total_duration_seconds"],
        )
        return results


if __name__ == "__main__":
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    result = asyncio.run(DevOpsCopilotOrchestrator().run())
    print(json.dumps(result, indent=2))
