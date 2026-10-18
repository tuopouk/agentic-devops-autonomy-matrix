from pathlib import Path
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


def load_initial_backlog():
    """Loads the default Contoso sample backlog from CSV if present."""
    if SAMPLE_CSV_PATH.exists():
        return pd.read_csv(SAMPLE_CSV_PATH).to_dict("records")
    return [
        {
            "Task": "Auto-tag and triage non-critical Azure Monitor alerts in Dev",
            "Blast Radius": "Low",
            "Irreversibility": "Low",
            "Complexity": "Low",
            "Score": 3,
            "Recommended Mode": "AUTONOMOUS MODE"
        },
        {
            "Task": "Draft PR to remediate Dependabot CVE alert and run unit tests",
            "Blast Radius": "Moderate",
            "Irreversibility": "Low",
            "Complexity": "Moderate",
            "Score": 5,
            "Recommended Mode": "SEMI-AUTONOMOUS MODE"
        },
        {
            "Task": "Production database schema migration & VNet peering reconfiguration",
            "Blast Radius": "High",
            "Irreversibility": "High",
            "Complexity": "High",
            "Score": 9,
            "Recommended Mode": "ASSISTANT MODE"
        }
    ]


def evaluate_autonomy(blast_radius: int, irreversibility: int, complexity: int):
    """
    Evaluates the autonomy operating mode and required guardrails based on:
    - Blast Radius (1=Low, 2=Moderate, 3=High)
    - Irreversibility (1=Low, 2=Moderate, 3=High)
    - Complexity (1=Low, 2=Moderate, 3=High)
    """
    total_score = blast_radius + irreversibility + complexity

    # Rule 1: Hard Veto - High Blast Radius + High Irreversibility always requires Assistant Mode
    if blast_radius == 3 and irreversibility == 3:
        return {
            "mode": "ASSISTANT MODE",
            "subtitle": "Synchronous / Direct Human Control (Veto Rule Triggered)",
            "color": "#ef4444",
            "badge_color": "danger",
            "score": total_score,
            "rationale": (
                "High Blast Radius combined with High Irreversibility poses an unacceptable risk "
                "for autonomous or semi-autonomous execution. The human must remain in direct command."
            ),
            "guardrails": [
                "Use GitHub Copilot in VS Code or Azure Portal Copilot strictly for drafting Bicep, YAML, or KQL.",
                "Human manually reviews, tests, and executes every state-changing command.",
                "No unattended agent execution or automated PR merging permitted.",
                "Enforce Privileged Identity Management (PIM) and multi-party approval for production access."
            ]
        }

    # Rule 2: High total score (8-9) -> Assistant Mode
    if total_score >= 8:
        return {
            "mode": "ASSISTANT MODE",
            "subtitle": "Synchronous / Direct Human Control",
            "color": "#ef4444",
            "badge_color": "danger",
            "score": total_score,
            "rationale": (
                "The combined complexity and risk profile are too high for unattended agent loops. "
                "Keep the AI in an interactive assistant role to accelerate human authoring and investigation."
            ),
            "guardrails": [
                "Interactive human-led prompting only (IDE / CLI / Azure Copilot).",
                "Mandatory peer code review from Senior/Platform Engineers.",
                "Manual dry-run validation (e.g., 'az deployment group what-if') prior to execution.",
                "Strict RBAC disallowing agent service principals from write actions in target scope."
            ]
        }

    # Rule 3: Low total score (3-4) and neither Blast Radius nor Irreversibility is High -> Autonomous Mode
    if total_score <= 4 and blast_radius < 3 and irreversibility < 3:
        return {
            "mode": "AUTONOMOUS MODE",
            "subtitle": "Closed-Loop / Policy-Enforced Execution",
            "color": "#10b981",
            "badge_color": "success",
            "score": total_score,
            "rationale": (
                "Low blast radius and easy rollback make this an ideal candidate for event-driven, "
                "closed-loop autonomy within pre-approved policy boundaries."
            ),
            "guardrails": [
                "Scope Microsoft Entra Agent Identity to least-privilege RBAC on non-prod/targeted resources.",
                "Enforce Azure Policy guardrails to block out-of-bounds SKU or network changes.",
                "Enable immutable audit logging in Azure Monitor / Log Analytics for every agent action.",
                "Configure automated circuit-breakers and budget/token rate limits."
            ]
        }

    # Rule 4: The Governed Middle Ground -> Semi-Autonomous Mode
    if blast_radius == 3:
        subtitle = "Human-in-the-Loop (HITL) Approval Gates Required"
        color = "#3b82f6"
        badge_color = "primary"
    else:
        subtitle = "Asynchronous Execution with Human Supervision"
        color = "#f59e0b"
        badge_color = "warning"

    return {
        "mode": "SEMI-AUTONOMOUS MODE",
        "subtitle": subtitle,
        "color": color,
        "badge_color": badge_color,
        "score": total_score,
        "rationale": (
            "The agent can asynchronously investigate, write code, run tests, and stage a remediation "
            "or Pull Request, but a mandatory human control point must verify the output before apply."
        ),
        "guardrails": [
            "Allow agent (e.g., Copilot Coding Agent / SRE Agent) to work on isolated branches or staging slots.",
            "Enforce GitHub Branch Protection / Azure DevOps Policies requiring human CODEOWNERS approval.",
            "Require automated CI validation (unit tests, security scans, Bicep what-if) on agent PRs.",
            "Gate production deployment stages with manual environment approvals in GitHub Actions / Azure Pipelines."
        ]
    }


def build_matrix_figure(
    blast_radius: int, irreversibility: int, complexity: int,
    eval_result: dict, backlog_data: list, theme: str = dbc.themes.CYBORG
):
    """
    Builds a 3x3 discrete Blast Radius vs. Irreversibility matrix.
    Plots all backlog items as background context markers, highlighting the currently selected task.
    """
    fig = go.Figure()
    template = template_from_url(theme)
    foreground = pio.templates[template].layout.font.color

    color_fill_map = {
        "#10b981": ("rgba(16, 185, 129, 0.18)", "rgba(16, 185, 129, 0.45)"),  # Green: Autonomous
        "#3b82f6": ("rgba(59, 130, 246, 0.18)", "rgba(59, 130, 246, 0.45)"),  # Blue: Semi-Auto (HITL Gates)
        "#f59e0b": ("rgba(245, 158, 11, 0.18)", "rgba(245, 158, 11, 0.45)"),  # Amber: Semi-Auto (Supervision)
        "#ef4444": ("rgba(239, 68, 68, 0.18)", "rgba(239, 68, 68, 0.45)"),    # Red: Assistant Mode
    }

    # Draw 3x3 discrete cells centered at 1, 2, 3
    for b_val in [1, 2, 3]:
        for i_val in [1, 2, 3]:
            cell_eval = evaluate_autonomy(b_val, i_val, complexity)
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
        dict(x=1.0, y=0.67, text="<b>AUTONOMOUS</b><br><span style='font-size:10px'>Closed-Loop / Policy</span>"),
        dict(x=1.0, y=2.67, text="<b>SEMI-AUTONOMOUS</b><br><span style='font-size:10px'>HITL Approval Gates</span>"),
        dict(x=2.0, y=1.67, text="<b>SEMI-AUTONOMOUS</b><br><span style='font-size:10px'>Governed Middle Ground</span>"),
        dict(x=3.0, y=0.67, text="<b>SEMI-AUTONOMOUS</b><br><span style='font-size:10px'>Human Supervision</span>"),
        dict(x=3.0, y=2.67, text="<b>ASSISTANT ONLY</b><br><span style='font-size:10px'>Strict Human Control</span>"),
    ]

    for ann in annotations:
        fig.add_annotation(
            x=ann["x"], y=ann["y"],
            text=ann["text"],
            showarrow=False,
            font=dict(size=11, color=foreground),
            opacity=0.75
        )

    # 1. Plot background backlog items if available
    if backlog_data:
        bg_x, bg_y, bg_text, bg_size = [], [], [], []
        for item in backlog_data:
            # Avoid duplicating the currently selected active point if it's already in the table
            i_val = REVERSE_LEVEL_MAP.get(item.get("Irreversibility"), 1)
            b_val = REVERSE_LEVEL_MAP.get(item.get("Blast Radius"), 1)
            c_val = REVERSE_LEVEL_MAP.get(item.get("Complexity"), 1)
            
            bg_x.append(i_val)
            bg_y.append(b_val)
            bg_text.append(item.get("Task", "Backlog Task"))
            bg_size.append(10 + (c_val * 6))

        fig.add_trace(go.Scatter(
            x=bg_x,
            y=bg_y,
            mode="markers",
            marker=dict(
                size=bg_size,
                color="rgba(255, 255, 255, 0.4)",
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
            f"Complexity: {LEVEL_MAP[complexity]}<br>"
            f"Recommended: <b>{eval_result['mode']}</b><extra></extra>"
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
                "Evaluate DevOps backlog items across Blast Radius, Irreversibility, and Complexity to determine "
                "the right AI operating mode and Human-in-the-Loop (HITL) boundaries on Azure.",
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
                        placeholder="e.g., Generate Bicep module for AKS cluster...",
                        className="mb-3"
                    ),

                    dbc.Label("Blast Radius & Potential Impact", className="fw-bold"),
                    html.Small("Scope of impact if the agent makes an error (Dev/Scoped vs. Prod/System-wide)", className="d-block mb-2"),
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

                    dbc.Label("Irreversibility (Rollback Difficulty)", className="fw-bold mt-2"),
                    html.Small("How hard is it to undo the action? (Git revert vs. stateful data deletion)", className="d-block mb-2"),
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

                    dbc.Label("Task Complexity & Ambiguity", className="fw-bold mt-2"),
                    html.Small("Level of reasoning required (Routine pattern vs. multi-system architecture)", className="d-block mb-2"),
                    dbc.RadioItems(
                        id="complexity-input",
                        options=[
                            {"label": "Low (1)", "value": 1},
                            {"label": "Moderate (2)", "value": 2},
                            {"label": "High (3)", "value": 3},
                        ],
                        value=2,
                        inline=True,
                        className="mb-4 btn-group w-100",
                        inputClassName="btn-check",
                        labelClassName="btn btn-outline-secondary w-100",
                        labelCheckedClassName="active fw-bold"
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
                        "*Background dots show all backlog items; large highlighted marker is the active task.",
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
                    html.H5("Team Backlog Autonomy Classification (Exportable to Excel/CSV)", className="mb-0"),
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
                            {"name": "Complexity", "id": "Complexity"},
                            {"name": "Risk Score (3-9)", "id": "Score"},
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
                            "fontFamily": "inherit"
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
    Input(ThemeChangerAIO.ids.radio("theme"), "value"),
    Input("backlog-store", "data")
)
def update_evaluation(blast_radius, irreversibility, complexity, theme=dbc.themes.CYBORG, backlog_data=None):
    res = evaluate_autonomy(blast_radius, irreversibility, complexity)
    fig = build_matrix_figure(blast_radius, irreversibility, complexity, res, backlog_data, theme)

    panel_content = html.Div([
        dbc.Badge(f"Composite Risk Score: {res['score']} / 9", color="secondary", className="mb-2 p-2"),
        html.H3(
            res["mode"],
            style={"borderLeft": f"4px solid {res['color']}", "paddingLeft": "0.5rem"},
            className="fw-bold mb-1"
        ),
        html.H6(res["subtitle"], className="mb-3"),
        html.P(res["rationale"], className="small border-bottom border-secondary pb-3"),
        html.H6("Required Azure & GitHub Control Points:", className="fw-bold mt-3 mb-2"),
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
    State("backlog-table", "data"),
    prevent_initial_call=True
)
def manage_backlog(n_clicks, timestamp, task_name, blast, irrev, comp, current_table_data):
    triggered_id = ctx.triggered_id

    if triggered_id == "backlog-table":
        return current_table_data, current_table_data, dash.no_update

    res = evaluate_autonomy(blast, irrev, comp)
    clean_name = task_name.strip() if task_name and task_name.strip() else f"DevOps Task #{len(current_table_data) + 1}"

    new_row = {
        "Task": clean_name,
        "Blast Radius": LEVEL_MAP[blast],
        "Irreversibility": LEVEL_MAP[irrev],
        "Complexity": LEVEL_MAP[comp],
        "Score": res["score"],
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