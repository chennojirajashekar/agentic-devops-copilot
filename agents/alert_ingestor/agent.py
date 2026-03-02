"""
Alert Ingestor Agent - Subscribes to Azure Monitor/App Insights alerts
and normalizes them into structured Incident objects.
"""
import os
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional
import requests
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class Incident:
    incident_id: str
    title: str
    severity: str
    status: str = "open"
    source: str = "azure-monitor"
    service_name: str = ""
    resource_id: str = ""
    alert_rule: str = ""
    description: str = ""
    raw_payload: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class AlertIngestorAgent:
    """Agent 1: Polls Azure Monitor, normalizes alerts to Incident objects."""

    SEVERITY_MAP = {0: "critical", 1: "critical", 2: "high", 3: "medium", 4: "low"}

    def __init__(self):
        self.subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
        self.workspace_id = os.environ.get("AZURE_MONITOR_WORKSPACE_ID", "")
        self.credential = DefaultAzureCredential()
        self.logs_client = LogsQueryClient(self.credential)
        logger.info("AlertIngestorAgent initialized.")

    def ingest(self, raw_alert: Optional[dict] = None) -> Incident:
        if raw_alert:
            return self._parse_monitor_alert(raw_alert)
        alerts = self._poll_monitor_alerts()
        if not alerts:
            logger.warning("No active alerts found - using synthetic demo incident.")
            return self._create_synthetic_incident()
        return self._parse_monitor_alert(alerts[0])

    def ingest_from_app_insights(self, query_hours: int = 1) -> list:
        kusto = (
            f"exceptions | where timestamp > ago({query_hours}h) "
            "| summarize count() by problemId, outerMessage, cloud_RoleName "
            "| order by count_ desc | take 10"
        )
        try:
            result = self.logs_client.query_workspace(
                workspace_id=self.workspace_id, query=kusto, timespan=None
            )
            incidents = []
            for row in (result.tables[0].rows if result.tables else []):
                incidents.append(Incident(
                    incident_id=f"appinsights-{row[0]}",
                    title=f"Exception: {str(row[1])[:80]}",
                    severity="high",
                    source="app-insights",
                    service_name=str(row[2]),
                    description=str(row[1]),
                ))
            return incidents
        except Exception as exc:
            logger.error("App Insights query failed: %s", exc)
            return []

    def _poll_monitor_alerts(self) -> list:
        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            "/providers/Microsoft.AlertsManagement/alerts"
            "?api-version=2023-07-12-preview&alertState=Fired"
        )
        token = self.credential.get_token("https://management.azure.com/.default").token
        try:
            resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
            resp.raise_for_status()
            return resp.json().get("value", [])
        except Exception as exc:
            logger.error("Failed to poll alerts: %s", exc)
            return []

    def _parse_monitor_alert(self, alert: dict) -> Incident:
        props = alert.get("properties", {})
        ess = props.get("essentials", {})
        sev_raw = ess.get("severity", "Sev3").replace("Sev", "")
        severity = self.SEVERITY_MAP.get(int(sev_raw) if sev_raw.isdigit() else 3, "medium")
        return Incident(
            incident_id=alert.get("id", f"alert-{datetime.now().timestamp()}"),
            title=ess.get("alertRule", "Unknown Alert"),
            severity=severity,
            source="azure-monitor",
            service_name=ess.get("targetResourceName", ""),
            resource_id=(ess.get("targetResourceIds") or [""])[0],
            alert_rule=ess.get("alertRule", ""),
            description=ess.get("description", ""),
            raw_payload=alert,
        )

    def _create_synthetic_incident(self) -> Incident:
        """Demo incident for local testing without live Azure alerts."""
        return Incident(
            incident_id="demo-incident-001",
            title="High Error Rate: Payment Service returning HTTP 500s",
            severity="critical",
            source="azure-monitor",
            service_name="payment-service",
            resource_id="/subscriptions/demo/resourceGroups/rg-prod/providers/Microsoft.Web/sites/payment-service",
            alert_rule="HighErrorRate-PaymentService",
            description=(
                "Error rate exceeded 5% threshold. Azure Monitor detected elevated "
                "HTTP 500 responses on payment-service over the last 5 minutes. "
                "Possible memory leak or database connection timeout."
            ),
            tags={"environment": "production", "team": "payments", "synthetic": "true"},
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = AlertIngestorAgent()
    incident = agent.ingest()
    print("\n=== Ingested Incident ===")
    print(incident.to_json())
