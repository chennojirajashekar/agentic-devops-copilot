"""Alert Ingestor Agent - polls Azure Monitor and normalizes alerts."""
from .agent import AlertIngestorAgent, Incident

__all__ = ["AlertIngestorAgent", "Incident"]
