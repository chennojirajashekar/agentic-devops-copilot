"""
SRE Reviewer Agent - Validates fixes for SLO, blast radius, risk, compliance.
"""
import os, json, logging
from dataclasses import dataclass, asdict
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    incident_id: str
    approved: bool
    risk_score: int
    risk_level: str
    slo_impact: str
    blast_radius: str
    security_concerns: list
    compliance_passed: bool
    reviewer_notes: str
    recommendation: str
    conditions: list

    def to_dict(self): return asdict(self)
    def to_json(self): return json.dumps(self.to_dict(), indent=2)


class SREReviewerAgent:
    """Agent 4: Safety gate - risk, SLO, blast radius, compliance."""

    SLO_POLICIES = {
        "payment-service": {"slo": 99.9, "budget": 0.3},
        "api-gateway":     {"slo": 99.99, "budget": 0.05},
        "default":         {"slo": 99.0, "budget": 2.0},
    }

    SYSTEM_PROMPT = (
        "You are a senior SRE doing a safety review of a proposed production change. "
        "Evaluate risk, SLO impact, blast radius, and security. Respond in JSON."
    )

    def __init__(self):
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        self.risk_threshold = os.environ.get("RISK_THRESHOLD", "medium")
        logger.info("SREReviewerAgent initialized.")

    def review(self, incident, rca, fix) -> ReviewResult:
        policy = self.SLO_POLICIES.get(incident.service_name, self.SLO_POLICIES["default"])
        result = self._call_openai(incident, rca, fix, policy)
        return self._apply_policies(result)

    def _call_openai(self, incident, rca, fix, policy) -> ReviewResult:
        prompt = (
            f"INCIDENT: {incident.title} | severity={incident.severity} | service={incident.service_name}\n"
            f"ROOT_CAUSE: {rca.root_cause}\nFIX_TYPE: {fix.fix_type}\nRISK: {fix.risk_level}\n"
            f"PATCH: {fix.patch_content[:300]}\n"
            f"SLO={policy['slo']}% | ERROR_BUDGET_LEFT={policy['budget']}%\n\n"
            'JSON: {"risk_score":25,"risk_level":"low","slo_impact":"minor",'
            '"blast_radius":"single-service","security_concerns":[],'
            '"compliance_passed":true,"reviewer_notes":"...",'
            '"recommendation":"approve","conditions":[]}'
        )
        try:
            resp = self.openai_client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "system", "content": self.SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                temperature=0.1, response_format={"type": "json_object"},
            )
            r = json.loads(resp.choices[0].message.content)
            approved = r.get("recommendation", "reject") in ("approve", "approve_with_conditions")
            return ReviewResult(
                incident_id=incident.incident_id, approved=approved,
                risk_score=r.get("risk_score", 50), risk_level=r.get("risk_level", "medium"),
                slo_impact=r.get("slo_impact", "minor"), blast_radius=r.get("blast_radius", "single-service"),
                security_concerns=r.get("security_concerns", []), compliance_passed=r.get("compliance_passed", True),
                reviewer_notes=r.get("reviewer_notes", ""), recommendation=r.get("recommendation", "approve_with_conditions"),
                conditions=r.get("conditions", []),
            )
        except Exception as exc:
            logger.error("SRE review failed: %s", exc)
            is_rollback = fix.fix_type == "rollback"
            return ReviewResult(
                incident_id=incident.incident_id, approved=is_rollback,
                risk_score=20 if is_rollback else 50, risk_level="low" if is_rollback else "medium",
                slo_impact="minor", blast_radius="single-service",
                security_concerns=[], compliance_passed=True,
                reviewer_notes="Fallback: rollback approved as low risk.",
                recommendation="approve" if is_rollback else "approve_with_conditions",
                conditions=[] if is_rollback else ["Verify in staging first"],
            )

    def _apply_policies(self, review: ReviewResult) -> ReviewResult:
        if self.risk_threshold == "low" and review.risk_score > 30:
            review.approved = False
            review.recommendation = "reject"
            review.reviewer_notes += " [Auto-rejected: risk threshold=low]"
        if not review.compliance_passed:
            review.approved = False
            review.recommendation = "reject"
        if review.blast_radius == "platform-wide" and review.risk_score > 40:
            review.approved = False
            review.conditions.append("Platform-wide change requires manual SRE sign-off.")
        return review


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys; sys.path.insert(0, "../..")
    from agents.alert_ingestor.agent import AlertIngestorAgent
    from agents.rca_agent.agent import RCAAgent
    from agents.code_fix_agent.agent import CodeFixAgent
    inc = AlertIngestorAgent().ingest()
    rca = RCAAgent().analyze(inc)
    fix = CodeFixAgent().propose_fix(inc, rca)
    result = SREReviewerAgent().review(inc, rca, fix)
    print(result.to_json())
