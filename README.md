# Agentic DevOps Autonomy Selector (AZ-401 Companion)

An interactive **Plotly Dash** decision-support tool for classifying DevOps backlog items across **Blast Radius**, **Irreversibility**, and **Task Complexity** based on Microsoft's Exam AZ-401 (*Designing and Implementing Microsoft Agentic DevOps Solutions*) framework.

![Agentic DevOps Autonomy Selector Dash App](/images/imagesdash_autonomy_selector.png)

## Features
- **Composite Risk Scoring & Hard Veto Detection:** Automatically maps tasks to *Assistant Mode*, *Semi-Autonomous Mode*, or *Autonomous Mode*.
- **2D Autonomy Positioning Matrix:** Visualizes Blast Radius vs. Irreversibility with Complexity represented by marker size.
- **Concrete Azure & GitHub Guardrails:** Recommends specific RBAC, Azure Policy, Branch Protection, and HITL environment controls for each task.
- **Exportable Backlog Table:** Pre-loaded with sample Contoso DevOps tasks and exportable to CSV.
- **Theme Changer:** Use **Change theme** to select a light or dark Bootstrap theme with `dash-bootstrap-templates`. Page text, controls, the matrix, and the backlog table follow the selected theme; Cyborg is the default. Theme stylesheets require internet access.

## Quickstart (Local)

1. Clone the repository:
```bash
git clone [https://github.com/](https://github.com/)<your-username>/az401-autonomy-selector.git
cd az401-autonomy-selector
```
2. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the Dash application:
```bash

python3 app.py
```
5. Open http://127.0.0.1:8050 in your browser.


### Reference Architecture Included
infra/main.bicep: Sample Azure Log Analytics workspace Bicep template.

.github/workflows/semi-autonomous-bicep-pr-gate.yml: Reference GitHub Actions pipeline demonstrating how a deterministic what-if check and a Human-in-the-Loop (HITL) environment approval gate govern agent-authored infrastructure changes.

#### 4. `backlog_samples/contoso_devops_backlog.csv`
```csv
Task,Blast Radius,Irreversibility,Complexity,Score,Recommended Mode
Auto-tag and triage non-critical Azure Monitor alerts in Dev,Low,Low,Low,3,AUTONOMOUS MODE
Scale down non-production ephemeral PR environments at 20:00 UTC,Low,Low,Moderate,4,AUTONOMOUS MODE
Draft PR to remediate Dependabot CVE alert and run unit tests,Moderate,Low,Moderate,5,SEMI-AUTONOMOUS MODE
Update Bicep Log Analytics retention policy in Production,High,Low,Moderate,6,SEMI-AUTONOMOUS MODE
Production database schema migration & VNet peering reconfiguration,High,High,High,9,ASSISTANT MODE
```