"""
Orchestrator: Coordinates the multi-agent Agentic DevOps Copilot pipeline.
"""
import asyncio
import logging
from typing import Optional

from agents.alert_ingestor.agent import AlertIngestorAgent
from agents.rca_agent.agent import RCAAgent
from agents.code_fix_agent.agent import CodeFixAgent
from agents.sre_reviewer.agent import SREReviewerAgent
from agents.change_manager.agent import ChangeManagerAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DevOpsCopilotOrchestrator:

    def __init__(self):
        self.alert_agent = AlertIngestorAgent()
        self.rca_agent = RCAAgent()
        self.fix_agent = CodeFixAgent()
        self.reviewer_agent = SREReviewerAgent()
        self.change_agent = ChangeManagerAgent()

    async def run(self, alert_id: Optional[str] = None) -> dict:
        logger.info("=== Agentic DevOps Copilot Pipeline Started ===")
        results = {}

        # Stage 1: Ingest alert
        alert = await self.alert_agent.run(alert_id=alert_id)
        results["alert"] = alert
        if not alert or alert.get("status") == "no_alerts":
            logger.info("No active alerts. Pipeline complete.")
            return results

        # Stage 2: Root Cause Analysis
        rca = await self.rca_agent.run(alert=alert)
        results["rca"] = rca

        # Stage 3: Code Fix Proposal
        fix = await self.fix_agent.run(rca=rca, alert=alert)
        results["fix"] = fix

        # Stage 4: SRE Review
        review = await self.reviewer_agent.run(fix=fix, rca=rca)
        results["review"] = review

        # Stage 5: Change Management
        change = await self.change_agent.run(fix=fix, review=review, alert=alert)
        results["change"] = change

        logger.info("=== Pipeline Complete ===")
        return results


if __name__ == "__main__":
    asyncio.run(DevOpsCopilotOrchestrator().run())
