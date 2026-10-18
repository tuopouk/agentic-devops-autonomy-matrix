from pathlib import Path
import math
import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeChangerAIO, template_from_url
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd

DBC_CSS = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.2/dbc.min.css"

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP, DBC_CSS],
    title="Agentic DevOps Autonomy Selector (AZ-401)"
)
server = app.server

LEVEL_MAP = {
    1: "Low",
    2: "Moderate",
    3: "High"
}

# Reverse map for table string -> int conversion
REVERSE_LEVEL_MAP = {
    "Low": 1,
    "Moderate": 2,
    "High": 3
}

SAMPLE_CSV_PATH = Path(__file__).parent / "backlog_samples" / "contoso_devops_backlog.csv"


def evaluate_autonomy(
    blast_radius: int,
    irreversibility: int,
    complexity: int,
    has_hard_control_point: bool = False
):
    """
    Evaluates the autonomy operating mode, Unit 4 autonomy ceiling, and required guardrails based on:
    - Blast Radius (1=Low, 2=Moderate, 3=High)
    - Irreversibility (1=Low, 2=Moderate, 3=High)
    - Complexity & Context Breadth (1=Low, 2=Moderate, 3=High)
    - Unit 4 Mandatory Production Control Point override
    """
    total_score = blast_radius + irreversibility + complexity

    # Rule 1: Hard Veto (Unit 4 Table)
    # Never grant autonomous/semi-autonomous execution when Low Reversibility (Irreversibility == 3)
    # combines with Medium or High Blast Radius (blast_radius >= 2), OR when a Unit 4 Hard Control Point is touched.
    if has_hard_control_point or (irreversibility == 3 and blast_radius >= 2):
        reason_prefix = (
            "Mandatory Production Control Point triggered. "
            if has_hard_control_point
            else "Unit 4 Veto Rule: High Irreversibility (low reversibility) combined with Moderate/High Blast Radius. "
        )
        return {
            "mode": "ASSISTANT MODE",
            "unit4_ceiling": "Inform / Suggest Only",
            "subtitle": "Unit 4 Ceiling: Inform / Suggest Only — Human Executes",
            "color": "#ef4444",
            "badge_color": "danger",
            "score": total_score,
            "rationale": (
                f"{reason_prefix}"
                "Never grant autonomous execution to actions that combine low reversibility with meaningful "
                "blast radius, or touch production security, credentials, or policy controls."
            ),
            "guardrails": [
                "Keep agent at Inform or Suggest ceiling (summarize logs or propose Bicep/YAML; human executes).",
                "Enforce Unit 4 Hard Control Points: Prod deployments, Key Vault secrets, Prod variable groups, RBAC/NSG, and Policy exemptions.",
                "Run interactive sessions under user access (IDE / Azure Portal) and require documented change authorization.",
                "Record audit trails across Azure Monitor activity logs, Azure DevOps audit logs, and GitHub audit logs."
            ]
        }

    # Rule 2: High total score (8-9) -> Assistant Mode (Suggest Only)
    if total_score >= 8:
        return {
            "mode": "ASSISTANT MODE",
            "unit4_ceiling": "Suggest Only",
            "subtitle": "Unit 4 Ceiling: Suggest Only — Human Executes",
            "color": "#ef4444",
            "badge_color": "danger",
            "score": total_score,
            "rationale": (
                "The combined complexity, context breadth, and risk profile are too high for unattended agent loops. "
                "Keep the AI at the 'Suggest' ceiling to accelerate human authoring and investigation."
            ),
            "guardrails": [
                "Interactive human-led prompting only (GitHub Copilot chat / Azure Copilot).",
                "Mandatory peer code review from Senior/Platform Engineers.",
                "Run 'az deployment group what-if' or 'terraform plan' drift synthesis prior to manual execution.",
                "Strict RBAC disallowing background agent managed identities from write actions in target scope."
            ]
        }

    # Rule 3: Low total score (3-4) with Low Blast Radius and Low Irreversibility -> Autonomous Mode
    if total_score <= 4 and blast_radius == 1 and irreversibility == 1:
        return {
            "mode": "AUTONOMOUS MODE",
            "unit4_ceiling": "Execute Autonomously",
            "subtitle": "Unit 4 Ceiling: Execute Autonomously (Closed-Loop)",
            "color": "#10b981",
            "badge_color": "success",
            "score": total_score,
            "rationale": (
                "High reversibility (Low Irreversibility) and Low Blast Radius make this an ideal candidate for "
                "closed-loop autonomy (e.g., bug triage in Azure Boards, read-only MCP queries, PR descriptions)."
            ),
            "guardrails": [
                "Scope Microsoft Entra Managed Identities & MCP server connections to least-privilege (read-only where possible).",
                "Enforce Azure Policy guardrails to block out-of-bounds SKU or network changes.",
                "Log all agent actions in Azure Monitor activity logs, Azure DevOps audit logs, and GitHub audit logs.",
                "Document the assigned autonomy level, rationale, and review cycle as your compliance baseline."
            ]
        }

    # Rule 4: The Governed Middle Ground -> Semi-Autonomous Mode (Execute on Approval)
    if blast_radius >= 2:
        subtitle = "Unit 4 Ceiling: Execute on Approval (HITL Approval Gates)"
        color = "#3b82f6"
        badge_color = "primary"
    else:
        subtitle = "Unit 4 Ceiling: Execute on Approval (Committer / Peer Supervision)"
        color = "#f59e0b"
        badge_color = "warning"

    return {
        "mode": "SEMI-AUTONOMOUS MODE",
        "unit4_ceiling": "Execute on Approval",
        "subtitle": subtitle,
        "color": color,
        "badge_color": badge_color,
        "score": total_score,
        "rationale": (
            "The agent can asynchronously gather multi-source context, write code in a sandbox, run tests, "
            "and stage a Pull Request or remediation plan, pausing for explicit human confirmation before apply."
        ),
        "guardrails": [
            "Isolate cloud coding agent runs in a GitHub Actions sandbox using a Managed Identity with federated credentials.",
            "Enforce GitHub Branch Protection / Azure DevOps branch policies requiring human CODEOWNERS approval.",
            "Require automated CI validation (unit tests, security scans, Bicep what-if drift synthesis) on agent PRs.",
            "Gate environment deployments with manual human approvals in GitHub Actions or Azure Pipelines."
        ]
    }


def load_initial_backlog():
    """
    Loads the default Unit 5 exercise backlog from CSV if present.
    Normalizes column names across different CSV versions so it never raises a KeyError.
    """
    default_rows = [
        {
            "Task": "1. Review incoming bug reports and assign to area path and team (Daily)",
            "Blast Radius": "Low",
            "Irreversibility": "Low",
            "Complexity": "Low",
            "Score": 3,
            "Unit 4 Ceiling": "Execute Autonomously",
            "Recommended Mode": "AUTONOMOUS MODE"
        },
        {
            "Task": "2. Generate Bicep templates for new storage accounts from naming docs (Weekly)",
            "Blast Radius": "Moderate",
            "Irreversibility": "Low",
            "Complexity": "Moderate",
            "Score": 5,
            "Unit 4 Ceiling": "Execute on Approval",
            "Recommended Mode": "SEMI-AUTONOMOUS MODE"
        },
        {
            "Task": "3. Create RBAC role assignments for new team members in prod subscriptions (Monthly)",
            "Blast Radius": "High",
            "Irreversibility": "High",
            "Complexity": "Low",
            "Score": 7,
            "Unit 4 Ceiling": "Suggest Only",
            "Recommended Mode": "ASSISTANT MODE"
        },
        {
            "Task": "4. Summarize last 7 days of pipeline failures and top 3 patterns (Weekly)",
            "Blast Radius": "Low",
            "Irreversibility": "Low",
            "Complexity": "Moderate",
            "Score": 4,
            "Unit 4 Ceiling": "Execute Autonomously",
            "Recommended Mode": "AUTONOMOUS MODE"
        },
        {
            "Task": "5. Update Azure Key Vault secrets when service credentials rotate (Quarterly)",
            "Blast Radius": "High",
            "Irreversibility": "High",
            "Complexity": "Low",
            "Score": 7,
            "Unit 4 Ceiling": "Inform / Suggest Only",
            "Recommended Mode": "ASSISTANT MODE"
        },
        {
            "Task": "6. Write pull request descriptions for infrastructure changes before review (Daily)",
            "Blast Radius": "Low",
            "Irreversibility": "Low",
            "Complexity": "Moderate",
            "Score": 4,
            "Unit 4 Ceiling": "Execute Autonomously",
            "Recommended Mode": "AUTONOMOUS MODE"
        },
        {
            "Task": "7. Apply Azure Policy exemptions for approved exception requests (As needed)",
            "Blast Radius": "High",
            "Irreversibility": "High",
            "Complexity": "Low",
            "Score": 7,
            "Unit 4 Ceiling": "Inform Only",
            "Recommended Mode": "ASSISTANT MODE"
        },
        {
            "Task": "8. Triage failing unit tests in CI builds and surface probable root cause (Daily)",
            "Blast Radius": "Low",
            "Irreversibility": "Moderate",
            "Complexity": "Moderate",
            "Score": 5,
            "Unit 4 Ceiling": "Execute on Approval",
            "Recommended Mode": "SEMI-AUTONOMOUS MODE"
        },
        {
            "Task": "9. Generate sprint summary report for weekly platform status meeting (Weekly)",
            "Blast Radius": "Low",
            "Irreversibility": "Low",
            "Complexity": "Moderate",
            "Score": 4,
            "Unit 4 Ceiling": "Execute Autonomously",
            "Recommended Mode": "AUTONOMOUS MODE"
        },
        {
            "Task": "10. Modify production pipeline variable groups for new deployment target (Monthly)",
            "Blast Radius": "High",
            "Irreversibility": "High",
            "Complexity": "Moderate",
            "Score": 8,
            "Unit 4 Ceiling": "Suggest Only",
            "Recommended Mode": "ASSISTANT MODE"
        }
    ]

    if not SAMPLE_CSV_PATH.exists():
        return default_rows

    try:
        df = pd.read_csv(SAMPLE_CSV_PATH)
        df.columns = [str(c).strip() for c in df.columns]

        # Normalize column aliases from earlier CSV schemas
        if "Complexity" not in df.columns and "Context Breadth" in df.columns:
            df["Complexity"] = df["Context Breadth"]
        if "Recommended Mode" not in df.columns and "Operating Mode" in df.columns:
            df["Recommended Mode"] = df["Operating Mode"]
        if "Unit 4 Ceiling" not in df.columns and "Unit 4 Autonomy Ceiling" in df.columns:
            df["Unit 4 Ceiling"] = df["Unit 4 Autonomy Ceiling"]

        # Ensure base risk columns exist
        for col in ["Blast Radius", "Irreversibility", "Complexity"]:
            if col not in df.columns:
                df[col] = "Low"

        # Dynamically populate Score, Recommended Mode, or Unit 4 Ceiling if missing
        records = df.to_dict("records")
        normalized_records = []
        for idx, row in enumerate(records):
            b_val = REVERSE_LEVEL_MAP.get(str(row.get("Blast Radius", "Low")).strip(), 1)
            i_val = REVERSE_LEVEL_MAP.get(str(row.get("Irreversibility", "Low")).strip(), 1)
            c_val = REVERSE_LEVEL_MAP.get(str(row.get("Complexity", "Low")).strip(), 1)
            eval_res = evaluate_autonomy(b_val, i_val, c_val)

            normalized_records.append({
                "Task": row.get("Task", f"DevOps Task #{idx + 1}"),
                "Blast Radius": LEVEL_MAP[b_val],
                "Irreversibility": LEVEL_MAP[i_val],
                "Complexity": LEVEL_MAP[c_val],
                "Score": row.get("Score", eval_res["score"]),
                "Unit 4 Ceiling": row.get("Unit 4 Ceiling", eval_res["unit4_ceiling"]),
                "Recommended Mode": row.get("Recommended Mode", eval_res["mode"]),
            })
        return normalized_records if normalized_records else default_rows
    except Exception:
        return default_rows


def build_matrix_figure(
    blast_radius: int,
    irreversibility: int,
    complexity: int,
    eval_result: dict,
    backlog_data: list,
    theme: str = dbc.themes.CYBORG,
    has_hard_control_point: bool = False
):
    """
    Builds a 3x3 discrete Blast Radius vs. Irreversibility matrix.
    Plots all backlog items as background context markers, highlighting the currently selected task.
    """
    fig = go.Figure()
    template = template_from_url(theme)
    foreground = pio.templates[template].layout.font.color

    color_fill_map = {
        "#10b981": ("rgba(16, 185, 129, 0.18)", "rgba(16, 185, 129, 0.45)"),  # Green: Execute Autonomously
        "#3b82f6": ("rgba(59, 130, 246, 0.18)", "rgba(59, 130, 246, 0.45)"),  # Blue: Execute on Approval (HITL)
        "#f59e0b": ("rgba(245, 158, 11, 0.18)", "rgba(245, 158, 11, 0.45)"),  # Amber: Execute on Approval (Supervised)
        "#ef4444": ("rgba(239, 68, 68, 0.18)", "rgba(239, 68, 68, 0.45)"),    # Red: Suggest / Inform Only
    }

    # Draw 3x3 discrete cells centered at 1, 2, 3
    for b_val in [1, 2, 3]:
        for i_val in [1, 2, 3]:
            cell_eval = evaluate_autonomy(b_val, i_val, complexity, has_hard_control_point)
            fill_rgba, line_rgba = color_fill_map[cell_eval["color"]]
            fig.add_shape(
                type="rect",
                x0=i_val - 0.5, x1=i_val + 0.5,
                y0=b_val - 0.5, y1=b_val + 0.5,
                fillcolor=fill_rgba,
                line=dict(color=line_rgba, width=1.5),
                layer="below"
            )

    annotations = [
        dict(x=1.0, y=0.67, text="<b>AUTONOMOUS</b><br><span style='font-size:10px'>Execute Autonomously</span>"),
        dict(x=1.0, y=2.67, text="<b>SEMI-AUTONOMOUS</b><br><span style='font-size:10px'>Execute on Approval (HITL)</span>"),
        dict(x=2.0, y=1.67, text="<b>SEMI-AUTONOMOUS</b><br><span style='font-size:10px'>Governed Middle Ground</span>"),
        dict(x=3.0, y=0.67, text="<b>SEMI-AUTONOMOUS</b><br><span style='font-size:10px'>Execute on Approval</span>"),
        dict(x=3.0, y=2.67, text="<b>ASSISTANT ONLY</b><br><span style='font-size:10px'>Suggest / Inform Only</span>"),
    ]

    for ann in annotations:
        fig.add_annotation(
            x=ann["x"], y=ann["y"],
            text=ann["text"],
            showarrow=False,
            font=dict(size=11, color=foreground),
            opacity=0.75
        )

    # 1. Plot background backlog items if available (with subtle circular offset for overlapping coordinates)
    if backlog_data:
        cell_counts = {}
        for item in backlog_data:
            i_val = REVERSE_LEVEL_MAP.get(item.get("Irreversibility"), 1)
            b_val = REVERSE_LEVEL_MAP.get(item.get("Blast Radius"), 1)
            cell_counts[(i_val, b_val)] = cell_counts.get((i_val, b_val), 0) + 1

        cell_seen = {}
        bg_x, bg_y, bg_text, bg_size = [], [], [], []
        for item in backlog_data:
            i_val = REVERSE_LEVEL_MAP.get(item.get("Irreversibility"), 1)
            b_val = REVERSE_LEVEL_MAP.get(item.get("Blast Radius"), 1)
            c_val = REVERSE_LEVEL_MAP.get(item.get("Complexity"), 1)

            total_in_cell = cell_counts[(i_val, b_val)]
            idx_in_cell = cell_seen.get((i_val, b_val), 0)
            cell_seen[(i_val, b_val)] = idx_in_cell + 1

            if total_in_cell > 1:
                angle = (2 * math.pi * idx_in_cell) / total_in_cell
                offset_x = 0.16 * math.cos(angle)
                offset_y = 0.16 * math.sin(angle)
            else:
                offset_x, offset_y = 0.0, 0.0

            bg_x.append(i_val + offset_x)
            bg_y.append(b_val + offset_y)
            ceiling_str = item.get("Unit 4 Ceiling", item.get("Recommended Mode", ""))
            bg_text.append(f"{item.get('Task', 'Backlog Task')} [{ceiling_str}]")
            bg_size.append(10 + (c_val * 5))

        fig.add_trace(go.Scatter(
            x=bg_x,
            y=bg_y,
            mode="markers",
            marker=dict(
                size=bg_size,
                color="rgba(255, 255, 255, 0.45)",
                line=dict(width=1, color=foreground)
            ),
            text=bg_text,
            hovertemplate="<b>Backlog Item:</b> %{text}<extra></extra>",
            name="Other Backlog Items"
        ))

    # 2. Plot the currently active/selected task with prominent highlight
    marker_size = 16 + (complexity * 12)
    fig.add_trace(go.Scatter(
        x=[irreversibility],
        y=[blast_radius],
        mode="markers+text",
        marker=dict(
            size=marker_size,
            color=eval_result["color"],
            line=dict(width=3, color=foreground),
            opacity=0.95
        ),
        text=[f"Active Task ({LEVEL_MAP[complexity]})"],
        textposition="top center",
        textfont=dict(color=foreground, size=12),
        hovertemplate=(
            "<b>Active Task Profile</b><br>"
            f"Blast Radius: {LEVEL_MAP[blast_radius]}<br>"
            f"Irreversibility: {LEVEL_MAP[irreversibility]}<br>"
            f"Complexity / Context: {LEVEL_MAP[complexity]}<br>"
            f"Unit 4 Ceiling: <b>{eval_result['unit4_ceiling']}</b><br>"
            f"Operating Mode: <b>{eval_result['mode']}</b><extra></extra>"
        ),
        name="Selected Task"
    ))

    fig.update_layout(
        template=template,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=30, b=40),
        height=400,
        xaxis=dict(
            title="<b>IRREVERSIBILITY</b> (Low = Easy Rollback -> High = Hard to Undo)",
            range=[0.5, 3.5],
            tickvals=[1, 2, 3],
            ticktext=["Low (1)", "Moderate (2)", "High (3)"],
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            title="<b>BLAST RADIUS</b> (Low = Scoped -> High = System/Prod)",
            range=[0.5, 3.5],
            tickvals=[1, 2, 3],
            ticktext=["Low (1)", "Moderate (2)", "High (3)"],
            showgrid=False,
            zeroline=False
        ),
        showlegend=False
    )

    return fig


INITIAL_BACKLOG = load_initial_backlog()

app.layout = dbc.Container(fluid=True, className="dbc py-4 px-4", children=[
    dbc.Row(className="mb-4 align-items-center", children=[
        dbc.Col(md=8, children=[
            html.H2("Agentic DevOps Autonomy Selector", className="fw-bold mb-1"),
            html.P(
                "Evaluate DevOps backlog items across Blast Radius, Irreversibility, and Context/Complexity to determine "
                "the right AI operating mode, Unit 4 Autonomy Ceiling, and Human-in-the-Loop (HITL) boundaries on Azure.",
                className="mb-0"
            )
        ]),
        dbc.Col(md=4, className="text-md-end mt-2 mt-md-0", children=[
            dbc.Badge("Exam AZ-401 Companion Tool", color="info", text_color="dark", className="p-2 fs-6 mb-2"),
            ThemeChangerAIO(
                aio_id="theme",
                radio_props={"value": dbc.themes.CYBORG},
                button_props={"children": "Change theme", "color": "secondary", "className": "ms-2 mb-2"}
            )
        ])
    ]),

    dbc.Row(className="g-4", children=[
        dbc.Col(lg=4, children=[
            dbc.Card(className="h-100 shadow-sm border-secondary", children=[
                dbc.CardHeader(html.H5("1. Score Your DevOps Task", className="mb-0")),
                dbc.CardBody([
                    dbc.Label("DevOps Task Name (Optional, for Backlog Table)", className="fw-bold"),
                    dbc.Input(
                        id="task-name-input",
                        type="text",
                        placeholder="e.g., Synthesize Bicep what-if drift results...",
                        className="mb-3"
                    ),

                    dbc.Label("Blast Radius & Potential Impact (Unit 4)", className="fw-bold"),
                    html.Small("Scope of impact if the agent makes an error (Single RG/Branch vs. Downstream Prod)", className="d-block mb-2"),
                    dbc.RadioItems(
                        id="blast-radius-input",
                        options=[
                            {"label": "Low (1)", "value": 1},
                            {"label": "Moderate (2)", "value": 2},
                            {"label": "High (3)", "value": 3},
                        ],
                        value=2,
                        inline=True,
                        className="mb-3 btn-group w-100",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-secondary w-100",
                        labelCheckedClassName="active fw-bold"
                    ),

                    dbc.Label("Irreversibility / Rollback Difficulty (Units 3 & 4)", className="fw-bold mt-1"),
                    html.Small("How hard is it to undo the action completely? (Git revert vs. Key Vault secret deletion)", className="d-block mb-2"),
                    dbc.RadioItems(
                        id="irreversibility-input",
                        options=[
                            {"label": "Low (1)", "value": 1},
                            {"label": "Moderate (2)", "value": 2},
                            {"label": "High (3)", "value": 3},
                        ],
                        value=1,
                        inline=True,
                        className="mb-3 btn-group w-100",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-secondary w-100",
                        labelCheckedClassName="active fw-bold"
                    ),

                    dbc.Label("Context Breadth & Task Complexity (Unit 3)", className="fw-bold mt-1"),
                    html.Small("Sources to synthesize & reasoning required (Single file vs. multi-log/policy correlation)", className="d-block mb-2"),
                    dbc.RadioItems(
                        id="complexity-input",
                        options=[
                            {"label": "Low (1)", "value": 1},
                            {"label": "Moderate (2)", "value": 2},
                            {"label": "High (3)", "value": 3},
                        ],
                        value=2,
                        inline=True,
                        className="mb-3 btn-group w-100",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-secondary w-100",
                        labelCheckedClassName="active fw-bold"
                    ),

                    dbc.Checklist(
                        id="hard-control-point-input",
                        options=[
                            {
                                "label": " Touches a Unit 4 Mandatory Prod Control Point (Prod Deploy, Key Vault Secrets, Prod Variable Groups, RBAC/NSG, or Policy Exemptions)",
                                "value": "hard_gate"
                            }
                        ],
                        value=[],
                        switch=True,
                        className="small mb-3"
                    ),

                    dbc.Button(
                        [html.I(className="bi bi-plus-circle me-2"), "Add Task to Backlog Table"],
                        id="add-task-btn",
                        color="secondary",
                        className="w-100 fw-bold"
                    )
                ])
            ])
        ]),

        dbc.Col(lg=4, children=[
            dbc.Card(className="h-100 shadow-sm border-secondary", children=[
                dbc.CardHeader(html.H5("2. Autonomy Positioning Matrix", className="mb-0")),
                dbc.CardBody(className="p-2 d-flex flex-column justify-content-center", children=[
                    dcc.Graph(id="autonomy-matrix-graph", config={"displayModeBar": False}),
                    html.Small(
                        "*Background dots show all Unit 5 backlog items; large highlighted marker is the active task.",
                        className="text-center d-block mt-1 text-muted"
                    )
                ])
            ])
        ]),

        dbc.Col(lg=4, children=[
            dbc.Card(className="h-100 shadow-sm border-secondary", children=[
                dbc.CardHeader(html.H5("3. Recommended Mode & Guardrails", className="mb-0")),
                dbc.CardBody(id="recommendation-panel")
            ])
        ])
    ]),

    dbc.Row(className="mt-4", children=[
        dbc.Col(width=12, children=[
            dbc.Card(className="shadow-sm border-secondary", children=[
                dbc.CardHeader(className="d-flex justify-content-between align-items-center", children=[
                    html.H5("Team Backlog Autonomy Classification (Preloaded with Unit 5 Exercise)", className="mb-0"),
                    dbc.Button(
                        [html.I(className="bi bi-download me-2"), "Export CSV"],
                        id="export-csv-btn",
                        color="secondary",
                        outline=True,
                        size="sm"
                    )
                ]),
                dbc.CardBody([
                    dcc.Store(id="backlog-store", data=INITIAL_BACKLOG),
                    dcc.Download(id="download-csv"),
                    dash_table.DataTable(
                        id="backlog-table",
                        columns=[
                            {"name": "DevOps Task", "id": "Task"},
                            {"name": "Blast Radius", "id": "Blast Radius"},
                            {"name": "Irreversibility", "id": "Irreversibility"},
                            {"name": "Complexity / Context", "id": "Complexity"},
                            {"name": "Risk Score (3-9)", "id": "Score"},
                            {"name": "Unit 4 Ceiling", "id": "Unit 4 Ceiling"},
                            {"name": "Recommended Mode", "id": "Recommended Mode"},
                        ],
                        data=INITIAL_BACKLOG,
                        row_deletable=True,
                        style_table={"overflowX": "auto"},
                        style_header={
                            "backgroundColor": "var(--bs-body-bg)",
                            "color": "var(--bs-body-color)",
                            "fontWeight": "bold",
                            "border": "1px solid var(--bs-border-color)"
                        },
                        style_cell={
                            "backgroundColor": "var(--bs-body-bg)",
                            "color": "var(--bs-body-color)",
                            "border": "1px solid var(--bs-border-color)",
                            "padding": "10px",
                            "textAlign": "left",
                            "fontFamily": "inherit",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_data_conditional=[
                            {
                                "if": {"filter_query": '{Recommended Mode} = "AUTONOMOUS MODE"', "column_id": "Recommended Mode"},
                                "borderLeft": "4px solid var(--bs-success)",
                                "fontWeight": "bold"
                            },
                            {
                                "if": {"filter_query": '{Recommended Mode} = "SEMI-AUTONOMOUS MODE"', "column_id": "Recommended Mode"},
                                "borderLeft": "4px solid var(--bs-primary)",
                                "fontWeight": "bold"
                            },
                            {
                                "if": {"filter_query": '{Recommended Mode} = "ASSISTANT MODE"', "column_id": "Recommended Mode"},
                                "borderLeft": "4px solid var(--bs-danger)",
                                "fontWeight": "bold"
                            }
                        ]
                    )
                ])
            ])
        ])
    ])
])


@app.callback(
    Output("autonomy-matrix-graph", "figure"),
    Output("recommendation-panel", "children"),
    Input("blast-radius-input", "value"),
    Input("irreversibility-input", "value"),
    Input("complexity-input", "value"),
    Input("hard-control-point-input", "value"),
    Input(ThemeChangerAIO.ids.radio("theme"), "value"),
    Input("backlog-store", "data")
)
def update_evaluation(
    blast_radius,
    irreversibility,
    complexity,
    hard_control_list=None,
    theme=dbc.themes.CYBORG,
    backlog_data=None
):
    has_hard_gate = "hard_gate" in (hard_control_list or [])
    res = evaluate_autonomy(blast_radius, irreversibility, complexity, has_hard_gate)
    fig = build_matrix_figure(
        blast_radius, irreversibility, complexity, res, backlog_data, theme, has_hard_gate
    )

    panel_content = html.Div([
        dbc.Badge(f"Composite Risk Score: {res['score']} / 9", color="secondary", className="mb-2 p-2"),
        html.H3(
            res["mode"],
            style={"borderLeft": f"4px solid {res['color']}", "paddingLeft": "0.5rem"},
            className="fw-bold mb-1"
        ),
        html.H6(res["subtitle"], className="mb-3"),
        html.P(res["rationale"], className="small border-bottom border-secondary pb-3"),
        html.H6("Required Identity, Control Points & Audit Trails (Unit 4):", className="fw-bold mt-3 mb-2"),
        html.Ul(
            [html.Li(g, className="small mb-2") for g in res["guardrails"]],
            className="ps-3"
        )
    ])

    return fig, panel_content


@app.callback(
    Output("backlog-store", "data"),
    Output("backlog-table", "data"),
    Output("task-name-input", "value"),
    Input("add-task-btn", "n_clicks"),
    Input("backlog-table", "data_timestamp"),
    State("task-name-input", "value"),
    State("blast-radius-input", "value"),
    State("irreversibility-input", "value"),
    State("complexity-input", "value"),
    State("hard-control-point-input", "value"),
    State("backlog-table", "data"),
    prevent_initial_call=True
)
def manage_backlog(n_clicks, timestamp, task_name, blast, irrev, comp, hard_control_list, current_table_data):
    triggered_id = ctx.triggered_id

    if triggered_id == "backlog-table":
        return current_table_data, current_table_data, dash.no_update

    has_hard_gate = "hard_gate" in (hard_control_list or [])
    res = evaluate_autonomy(blast, irrev, comp, has_hard_gate)
    clean_name = task_name.strip() if task_name and task_name.strip() else f"DevOps Task #{len(current_table_data) + 1}"

    new_row = {
        "Task": clean_name,
        "Blast Radius": LEVEL_MAP[blast],
        "Irreversibility": LEVEL_MAP[irrev],
        "Complexity": LEVEL_MAP[comp],
        "Score": res["score"],
        "Unit 4 Ceiling": res["unit4_ceiling"],
        "Recommended Mode": res["mode"]
    }

    updated_data = current_table_data + [new_row]
    return updated_data, updated_data, ""


@app.callback(
    Output("download-csv", "data"),
    Input("export-csv-btn", "n_clicks"),
    State("backlog-store", "data"),
    prevent_initial_call=True
)
def export_csv(n_clicks, backlog_data):
    df = pd.DataFrame(backlog_data)
    return dcc.send_data_frame(df.to_csv, "agentic_devops_autonomy_backlog.csv", index=False)


if __name__ == "__main__":
    app.run(debug=True)