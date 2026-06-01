import time
import requests
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.live import Live
from rich.text import Text
from rich import box

API_URL = "http://localhost:8000"
STORE_ID = "STORE_BLR_002"
REFRESH_SEC = 5

console = Console()

def fetch_metrics():
    try:
        r = requests.get(f"{API_URL}/stores/{STORE_ID}/metrics", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def fetch_funnel():
    try:
        r = requests.get(f"{API_URL}/stores/{STORE_ID}/funnel", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def fetch_anomalies():
    try:
        r = requests.get(f"{API_URL}/stores/{STORE_ID}/anomalies", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def fetch_health():
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def build_dashboard():
    metrics   = fetch_metrics()
    funnel    = fetch_funnel()
    anomalies = fetch_anomalies()
    health    = fetch_health()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Header ────────────────────────────────────────────────────────
    header = Panel(
        f"[bold cyan]Apex Retail — Store Intelligence Dashboard[/bold cyan]\n"
        f"[dim]Store: {STORE_ID} | Last updated: {now} | Refreshing every {REFRESH_SEC}s[/dim]",
        box=box.DOUBLE_EDGE,
        style="cyan"
    )

    # ── Metrics ───────────────────────────────────────────────────────
    if metrics:
        metrics_table = Table(title="📊 Live Metrics", box=box.ROUNDED, style="green")
        metrics_table.add_column("Metric", style="bold")
        metrics_table.add_column("Value", justify="right")

        metrics_table.add_row("Unique Visitors",   str(metrics.get("unique_visitors", 0)))
        metrics_table.add_row("Conversion Rate",   f"{round(metrics.get('conversion_rate', 0) * 100, 1)}%")
        metrics_table.add_row("Queue Depth",       str(metrics.get("queue_depth", 0)))
        metrics_table.add_row("Abandonment Rate",  f"{round(metrics.get('abandonment_rate', 0) * 100, 1)}%")

        dwell = metrics.get("avg_dwell_seconds_per_zone", {})
        for zone, secs in dwell.items():
            metrics_table.add_row(f"Dwell — {zone}", f"{secs}s")
    else:
        metrics_table = Panel("[red]Metrics unavailable[/red]")

    # ── Funnel ────────────────────────────────────────────────────────
    if funnel:
        funnel_table = Table(title="🔽 Conversion Funnel", box=box.ROUNDED, style="blue")
        funnel_table.add_column("Stage", style="bold")
        funnel_table.add_column("Visitors", justify="right")
        funnel_table.add_column("Drop-off", justify="right", style="red")

        for stage in funnel.get("funnel", []):
            funnel_table.add_row(
                stage["stage"],
                str(stage["visitors"]),
                f"{stage['drop_off_pct']}%" if stage["drop_off_pct"] > 0 else "-"
            )
    else:
        funnel_table = Panel("[red]Funnel unavailable[/red]")

    # ── Anomalies ─────────────────────────────────────────────────────
    if anomalies:
        anomaly_list = anomalies.get("anomalies", [])
        if anomaly_list:
            anomaly_table = Table(title="⚠️  Active Anomalies", box=box.ROUNDED, style="red")
            anomaly_table.add_column("Type", style="bold")
            anomaly_table.add_column("Severity")
            anomaly_table.add_column("Message")
            anomaly_table.add_column("Action", style="dim")

            severity_colors = {"CRITICAL": "red", "WARN": "yellow", "INFO": "green"}
            for a in anomaly_list:
                color = severity_colors.get(a["severity"], "white")
                anomaly_table.add_row(
                    a["type"],
                    f"[{color}]{a['severity']}[/{color}]",
                    a["message"],
                    a["suggested_action"]
                )
        else:
            anomaly_table = Panel("[green]✅ No active anomalies[/green]", style="green")
    else:
        anomaly_table = Panel("[red]Anomalies unavailable[/red]")

    # ── Health ────────────────────────────────────────────────────────
    if health:
        status = health.get("status", "unknown")
        color  = "green" if status == "healthy" else "red"
        health_panel = Panel(
            f"[{color}]API Status: {status.upper()}[/{color}]\n"
            f"[dim]Timestamp: {health.get('timestamp', 'N/A')}[/dim]",
            title="💚 Health",
            style=color
        )
    else:
        health_panel = Panel("[red]API unreachable[/red]", title="Health", style="red")

    return header, metrics_table, funnel_table, anomaly_table, health_panel

def run_dashboard():
    console.print("[bold cyan]Starting Apex Retail Live Dashboard...[/bold cyan]")
    console.print(f"[dim]Connecting to {API_URL}[/dim]\n")

    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            try:
                header, metrics, funnel, anomalies, health = build_dashboard()
                from rich.layout import Layout
                layout = Layout()
                layout.split_column(
                    Layout(header, size=5),
                    Layout(name="middle"),
                    Layout(anomalies, size=10),
                    Layout(health, size=4)
                )
                layout["middle"].split_row(
                    Layout(metrics),
                    Layout(funnel)
                )
                live.update(layout)
            except Exception as e:
                live.update(Panel(f"[red]Dashboard error: {e}[/red]"))
            time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run_dashboard()
