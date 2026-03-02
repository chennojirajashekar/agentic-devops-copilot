# Agentic DevOps Copilot - Architecture

## Overview

The Agentic DevOps Copilot is a multi-agent AI system built on Azure that automates the full incident response lifecycle: from alert detection to root cause analysis, code fix, SRE review, and change management.

## Architecture Diagram

```
+------------------+     +------------+     +--------------+     +---------------+     +----------------+
|  Azure Monitor   | --> |    Alert   | --> |     RCA      | --> |   Code Fix    | --> |  SRE Reviewer  |
|  Application     |     |  Ingestor  |     |    Agent     |     |    Agent      |     |    Agent       |
|  Insights        |     |   Agent    |     | (Azure OAI)  |     | (OAI + GitHub)|     | (OAI + Rules)  |
+------------------+     +------------+     +--------------+     +---------------+     +----------------+
                                                                                                 |
                                                                                                 v
                                                                                      +-------------------+
                                                                                      |  Change Manager   |
                                                                                      |     Agent         |
                                                                                      | (Approval + Log)  |
                                                                                      +-------------------+
```

## Agent Descriptions

### 1. Alert Ingestor Agent
- **Purpose**: Fetches active alerts from Azure Monitor / Application Insights
- **Tools**: Azure Monitor REST API, Azure SDK for Python
- **Outputs**: Structured alert dict with severity, message, resource info

### 2. Root Cause Analysis (RCA) Agent
- **Purpose**: Analyzes alert context and determines probable root cause
- **Tools**: Azure OpenAI GPT-4o
- **Inputs**: Alert data from Alert Ingestor
- **Outputs**: Root cause summary, affected component, recommended action

### 3. Code Fix Agent
- **Purpose**: Proposes a code fix based on RCA and creates a GitHub Pull Request
- **Tools**: Azure OpenAI GPT-4o, PyGitHub
- **Inputs**: RCA output, alert data
- **Outputs**: Fix diff, PR URL, branch name

### 4. SRE Reviewer Agent
- **Purpose**: Reviews the proposed fix for safety, risk, and SLO compliance
- **Tools**: Azure OpenAI GPT-4o, custom risk scoring rules
- **Inputs**: Fix proposal, RCA output
- **Outputs**: Risk level (LOW/MEDIUM/HIGH), review comments, approval status

### 5. Change Manager Agent
- **Purpose**: Creates a change record and triggers deployment approval workflow
- **Tools**: Azure OpenAI GPT-4o, ServiceNow API (or mock)
- **Inputs**: Fix proposal, SRE review, alert data
- **Outputs**: Change ID, approval status, deployment trigger

## Technology Stack

| Layer | Technology |
|-------|------------|
| AI/LLM | Azure OpenAI Service (GPT-4o) |
| Agent Framework | Microsoft Agent Framework / Semantic Kernel |
| Alert Source | Azure Monitor + Application Insights |
| Code Repository | GitHub (via PyGitHub) |
| Infrastructure | Azure Bicep (IaC) |
| CI/CD | GitHub Actions |
| Runtime | Python 3.11 |
| Container | Docker |

## Data Flow

1. **Trigger**: A new alert fires in Azure Monitor (e.g., high error rate, latency spike)
2. **Ingest**: Alert Ingestor fetches alert details via Azure Monitor API
3. **Analyze**: RCA Agent sends alert context to Azure OpenAI for root cause determination
4. **Fix**: Code Fix Agent generates a patch and opens a GitHub PR
5. **Review**: SRE Reviewer Agent scores the change risk
6. **Approve**: Change Manager creates a change record; if risk is LOW, auto-approves
7. **Deploy**: High-risk changes require human approval before merge

## Infrastructure

All Azure resources are provisioned via `infra/main.bicep`:

- **Azure OpenAI Service**: GPT-4o deployment for all LLM calls
- **Log Analytics Workspace**: Centralized logging
- **Application Insights**: Alert source + telemetry
- **Key Vault**: Secrets management (API keys, tokens)
- **Container App** (optional): Hosted runtime

## Security

- All secrets stored in Azure Key Vault
- GitHub Actions uses OIDC federation (no long-lived secrets)
- Bicep validates before every main branch deployment
- SRE Reviewer blocks high-risk changes from auto-deploying

## Running Locally

```bash
# 1. Clone repo
git clone https://github.com/chennojirajashekar/agentic-devops-copilot
cd agentic-devops-copilot

# 2. Set up environment
cp .env.example .env
# Edit .env with your Azure credentials

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run pipeline
python main.py

# 5. Run with specific alert
python main.py --alert-id <ALERT_ID>

# 6. Output to file
python main.py --output results.json
```
