#!/usr/bin/env python3
"""
Agentic DevOps Copilot - Main Entry Point
==========================================
Usage:
  python main.py                         # Run with demo incident
  python main.py --mode webhook          # Simulate webhook trigger
  python main.py --output result.json    # Save full output to file

Requirements:
  pip install -r requirements.txt
  cp .env.example .env && edit .env with your Azure credentials
"""
import sys
import json
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agentic_devops.log"),
    ]
)
logger = logging.getLogger("main")

# Demo webhook payload for testing
DEMO_WEBHOOK_ALERT = {
    "id": "/subscriptions/demo/providers/Microsoft.AlertsManagement/alerts/demo-001",
    "properties": {
        "essentials": {
            "alertRule": "HighErrorRate-PaymentService",
            "severity": "Sev1",
            "targetResourceName": "payment-service",
            "targetResourceIds": ["/subscriptions/demo/resourceGroups/rg-prod/providers/Microsoft.Web/sites/payment-service"],
            "description": "Error rate exceeded 5% threshold on payment-service",
            "monitorCondition": "Fired",
        }
    }
}


def parse_args():
    parser = argparse.ArgumentParser(description="Agentic DevOps Copilot")
    parser.add_argument(
        "--mode",
        choices=["auto", "webhook", "demo"],
        default="demo",
        help="Run mode: 'auto' polls Azure Monitor, 'webhook' uses demo payload, 'demo' uses synthetic incident"
    )
    parser.add_argument(
        "--output",
        default="workflow_result.json",
        help="Output file for workflow result JSON"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("   AGENTIC DEVOPS COPILOT")
    logger.info("   AI-Driven Incident-to-Fix on Azure")
    logger.info("=" * 60)
    logger.info("Mode: %s", args.mode)

    # Import orchestrator
    from workflows.orchestrator import AgenticDevOpsOrchestrator

    orchestrator = AgenticDevOpsOrchestrator()

    # Determine input
    raw_alert = None
    if args.mode == "webhook":
        logger.info("Using demo webhook payload.")
        raw_alert = DEMO_WEBHOOK_ALERT
    elif args.mode == "auto":
        logger.info("Polling Azure Monitor for real alerts...")
        raw_alert = None  # orchestrator will poll
    else:  # demo
        logger.info("Using synthetic demo incident (no Azure required).")
        raw_alert = None  # alert agent will create synthetic incident

    # Run the workflow
    result = orchestrator.run(raw_alert=raw_alert)

    # Print summary
    print("\n" + "=" * 60)
    print("WORKFLOW RESULT SUMMARY")
    print("=" * 60)
    print(result.summary)
    print(f"\nTotal duration: {result.total_duration_seconds:.2f}s")
    print(f"Status: {'SUCCESS' if result.success else 'FAILED/REJECTED'}")

    # Save to file
    output_path = Path(args.output)
    output_path.write_text(result.to_json())
    logger.info("Full result saved to %s", output_path)
    print(f"\nFull JSON result saved to: {output_path}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
