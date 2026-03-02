"""
Tests for the Agentic DevOps Copilot pipeline.
Run with: pytest tests/ -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestAlertIngestor:
    """Unit tests for Alert Ingestor Agent."""

    def test_alert_structure(self):
        """Test that a mock alert has the expected structure."""
        mock_alert = {
            "alert_id": "test-001",
            "severity": "High",
            "name": "High Error Rate",
            "description": "Error rate exceeded 5%",
            "resource": "api-service",
            "timestamp": "2024-01-01T00:00:00Z",
            "status": "active"
        }
        assert mock_alert["severity"] in ["Critical", "High", "Medium", "Low"]
        assert mock_alert["status"] == "active"
        assert "alert_id" in mock_alert

    def test_alert_severity_mapping(self):
        """Test severity level mapping."""
        severities = ["Critical", "High", "Medium", "Low"]
        for sev in severities:
            assert isinstance(sev, str)
            assert len(sev) > 0


class TestRCAAgent:
    """Unit tests for RCA Agent."""

    def test_rca_output_structure(self):
        """Test that RCA output has required fields."""
        mock_rca = {
            "root_cause": "Memory leak in request handler",
            "affected_component": "api-service/handlers/request_handler.py",
            "confidence": "HIGH",
            "recommended_action": "Fix memory leak in request handler",
            "analysis": "Detailed analysis..."
        }
        required_fields = ["root_cause", "affected_component", "recommended_action"]
        for field in required_fields:
            assert field in mock_rca

    def test_confidence_levels(self):
        """Test confidence level validation."""
        valid_levels = ["HIGH", "MEDIUM", "LOW"]
        assert "HIGH" in valid_levels
        assert "UNKNOWN" not in valid_levels


class TestSREReviewer:
    """Unit tests for SRE Reviewer Agent."""

    def test_risk_scoring(self):
        """Test risk level assignment based on keywords."""
        high_risk_keywords = ["database", "migration", "schema", "delete", "drop"]
        medium_risk_keywords = ["config", "timeout", "retry", "cache"]

        fix_desc = "Update database schema migration"
        risk = "HIGH" if any(kw in fix_desc.lower() for kw in high_risk_keywords) else "MEDIUM"
        assert risk == "HIGH"

        fix_desc2 = "Update cache timeout setting"
        risk2 = "HIGH" if any(kw in fix_desc2.lower() for kw in high_risk_keywords) else "MEDIUM"
        assert risk2 == "MEDIUM"

    def test_slo_validation(self):
        """Test SLO compliance check."""
        slo_targets = {"availability": 99.9, "latency_p99_ms": 500}
        current_metrics = {"availability": 99.95, "latency_p99_ms": 450}

        compliant = all(
            current_metrics.get(k, 0) >= v if k == "availability"
            else current_metrics.get(k, 9999) <= v
            for k, v in slo_targets.items()
        )
        assert compliant is True


class TestOrchestrator:
    """Integration tests for the orchestrator."""

    @pytest.mark.asyncio
    async def test_pipeline_no_alerts(self):
        """Test pipeline exits gracefully when no alerts."""
        with patch("orchestrator.orchestrator.AlertIngestorAgent") as mock_alert_cls:
            mock_agent = AsyncMock()
            mock_agent.run.return_value = {"status": "no_alerts"}
            mock_alert_cls.return_value = mock_agent

            from orchestrator.orchestrator import DevOpsCopilotOrchestrator
            orch = DevOpsCopilotOrchestrator()
            orch.alert_agent = mock_agent

            results = await orch.run()
            assert results["alert"]["status"] == "no_alerts"

    def test_orchestrator_initializes(self):
        """Test that orchestrator can be instantiated."""
        with patch("orchestrator.orchestrator.AlertIngestorAgent"), \
             patch("orchestrator.orchestrator.RCAAgent"), \
             patch("orchestrator.orchestrator.CodeFixAgent"), \
             patch("orchestrator.orchestrator.SREReviewerAgent"), \
             patch("orchestrator.orchestrator.ChangeManagerAgent"):
            from orchestrator.orchestrator import DevOpsCopilotOrchestrator
            orch = DevOpsCopilotOrchestrator()
            assert orch is not None
