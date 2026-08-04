import plotly.graph_objects as go


def cost_comparison_chart(report: dict):
    labels = list(report.keys())
    costs = [report[l]["total_cost_usd"] for l in labels]
    fig = go.Figure(go.Bar(x=labels, y=costs, marker_color="indianred"))
    fig.update_layout(title="Total Cost by Configuration", yaxis_title="Cost (USD)")
    return fig


def latency_chart(report: dict):
    labels = list(report.keys())
    lat = [report[l]["avg_latency_ms"] for l in labels]
    fig = go.Figure(go.Bar(x=labels, y=lat, marker_color="steelblue"))
    fig.update_layout(title="Average Latency by Configuration", yaxis_title="ms")
    return fig


def token_usage_chart(report: dict):
    labels = list(report.keys())
    fig = go.Figure()
    fig.add_bar(name="Input", x=labels, y=[report[l]["total_input_tokens"] for l in labels])
    fig.add_bar(name="Output", x=labels, y=[report[l]["total_output_tokens"] for l in labels])
    fig.update_layout(barmode="stack", title="Token Usage")
    return fig


def cache_hit_chart(report: dict):
    labels = list(report.keys())
    rates = [report[l].get("cache_hit_rate_pct", 0) for l in labels]
    fig = go.Figure(go.Bar(x=labels, y=rates, marker_color="seagreen"))
    fig.update_layout(title="Cache Hit Rate (%)", yaxis_title="%")
    return fig
