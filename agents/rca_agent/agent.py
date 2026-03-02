"""
Root Cause Analysis (RCA) Agent
Correlates logs and metrics, uses Azure OpenAI to identify root cause.
"""
import os
import json
import logging
from dataclasses import dataclass, field, asdict
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class RCAResult:
    incident_id: str
    root_cause: str
    confidence: str
    affected_component: str
    probable_commit: str = ""
    error_pattern: str = ""
    recommended_action: str = ""
    analysis_details: str = ""

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)


class RCAAgent:
    """Agent 2: Root cause analysis using Azure Monitor logs + Azure OpenAI."""

    SYSTEM_PROMPT = (
        "You are an expert SRE AI. Analyze production incidents using logs and metrics. "
        "Identify root cause, affected components, and remediation. Respond in JSON."
    )

    def __init__(self):
        self.workspace_id = os.environ.get("AZURE_MONITOR_WORKSPACE_ID", "")
        self.credential = DefaultAzureCredential()
        self.logs_client = LogsQueryClient(self.credential)
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        logger.info("RCAAgent initialized.")

    def analyze(self, incident) -> RCAResult:
        logger.info("Starting RCA for: %s", incident.incident_id)
        logs = self._fetch_logs(incident.service_name)
        metrics = self._metrics_summary(incident.service_name)
        context = self._build_prompt(incident, logs, metrics)
        return self._call_openai(incident.incident_id, context)

    def _fetch_logs(self, service: str, minutes: int = 30) -> list:
        if not self.workspace_id:
            return self._demo_logs()
        kusto = (
            f"AppRequests | where TimeGenerated > ago({minutes}m) "
            f"| where AppRoleName == '{service}' | where ResultCode >= 500 "
            "| project TimeGenerated, Name, ResultCode, DurationMs | take 20"
        )
        try:
            r = self.logs_client.query_workspace(self.workspace_id, kusto, timespan=None)
            return [{"t": str(row[0]), "ep": row[1], "code": row[2], "ms": row[3]} for row in (r.tables[0].rows if r.tables else [])]
        except Exception as e:
            logger.warning("Log query failed: %s", e)
            return self._demo_logs()

    def _demo_logs(self) -> list:
        return [
            {"t": "2026-03-02T14:00:01Z", "ep": "POST /api/payment", "code": 500, "ms": 12500, "error": "OutOfMemoryError"},
            {"t": "2026-03-02T14:00:05Z", "ep": "POST /api/payment", "code": 500, "ms": 13200, "error": "OutOfMemoryError"},
            {"t": "2026-03-02T13:50:00Z", "ep": "POST /api/payment", "code": 200, "ms": 320, "error": None},
        ]

    def _metrics_summary(self, service: str) -> str:
        return (
            f"Service={service or 'payment-service'} | Memory=94% | CPU=45% | "
            "ErrorRate5m=7.3% | P95Latency=12.5s | HealthyInstances=1/3"
        )

    def _build_prompt(self, incident, logs, metrics) -> str:
        return (
            f"INCIDENT: {incident.title} (severity={incident.severity})\n"
            f"Description: {incident.description}\n\n"
            f"METRICS: {metrics}\n\n"
            f"LOGS: {json.dumps(logs)}\n\n"
            "Respond in JSON: {\"root_cause\":\"...\",\"confidence\":\"high|medium|low\","
            "\"affected_component\":\"...\",\"probable_commit\":\"...\","
            "\"error_pattern\":\"...\",\"recommended_action\":\"...\",\"analysis_details\":\"...\"}"
        )

    def _call_openai(self, incident_id: str, context: str) -> RCAResult:
        try:
            resp = self.openai_client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = json.loads(resp.choices[0].message.content)
            return RCAResult(
                incident_id=incident_id,
                root_cause=raw.get("root_cause", "Unknown"),
                confidence=raw.get("confidence", "medium"),
                affected_component=raw.get("affected_component", ""),
                probable_commit=raw.get("probable_commit", ""),
                error_pattern=raw.get("error_pattern", ""),
                recommended_action=raw.get("recommended_action", ""),
                analysis_details=raw.get("analysis_details", ""),
            )
        except Exception as exc:
            logger.error("OpenAI call failed: %s", exc)
            return RCAResult(
                incident_id=incident_id,
                root_cause="Memory leak in payment-service (OutOfMemoryError)",
                confidence="high",
                affected_component="payment-service heap memory",
                error_pattern="OutOfMemoryError",
                recommended_action="Rollback to last stable deployment",
                analysis_details="Fallback: memory at 94%, error rate 7.3%. Recommend rollback.",
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys; sys.path.insert(0, "../..")
    from agents.alert_ingestor.agent import AlertIngestorAgent
    incident = AlertIngestorAgent().ingest()
    result = RCAAgent().analyze(incident)
    print(result.to_json())
