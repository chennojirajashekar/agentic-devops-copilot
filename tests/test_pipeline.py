"""
Tests for the Agentic DevOps Copilot pipeline.
Run with: pytest tests/ -v
"""
import pytest
import os
from unittest.mock import MagicMock, patch


class TestAgentInstantiation:
    """Test that all agents can be instantiated with mocked Azure credentials."""

    def test_alert_ingestor_agent_init(self):
        """Test AlertIngestorAgent can be initialized."""
        with patch("azure.identity.DefaultAzureCredential"), \
             patch("azure.monitor.query.LogsQueryClient"):
            os.environ["AZURE_SUBSCRIPTION_ID"] = "test-sub-id"
            from agents.alert_ingestor.agent import AlertIngestorAgent
            agent = AlertIngestorAgent()
            assert agent is not None

    def test_rca_agent_init(self):
        """Test RCAAgent can be initialized."""
        with patch("azure.identity.DefaultAzureCredential"), \
             patch("azure.monitor.query.LogsQueryClient"), \
             patch("openai.AzureOpenAI"):
            os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
            os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
            from agents.rca_agent.agent import RCAAgent
            agent = RCAAgent()
            assert agent is not None

    def test_code_fix_agent_init(self):
        """Test CodeFixAgent can be initialized."""
        with patch("openai.AzureOpenAI"), \
             patch("github.Github"):
            os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
            os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
            from agents.code_fix_agent.agent import CodeFixAgent
            agent = CodeFixAgent()
            assert agent is not None

    def test_sre_reviewer_agent_init(self):
        """Test SREReviewerAgent can be initialized."""
        with patch("openai.AzureOpenAI"):
            os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"
            os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
            from agents.sre_reviewer.agent import SREReviewerAgent
            agent = SREReviewerAgent()
            assert agent is not None

    def test_change_manager_agent_init(self):
        """Test ChangeManagerAgent can be initialized."""
        with patch("github.Github"):
            from agents.change_manager.agent import ChangeManagerAgent
            agent = ChangeManagerAgent()
            assert agent is not None


class TestWorkflowOrchestrator:
    """Test the synchronous workflow orchestrator."""

    def test_orchestrator_imports(self):
        """Test that orchestrator can be imported."""
        from workflows.orchestrator import AgenticDevOpsOrchestrator, WorkflowResult
        assert AgenticDevOpsOrchestrator is not None
        assert WorkflowResult is not None
