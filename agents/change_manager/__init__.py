"""Change Manager Agent - orchestrates rollout with approval gates and CI/CD."""
from .agent import ChangeManagerAgent, RolloutResult

__all__ = ["ChangeManagerAgent", "RolloutResult"]
