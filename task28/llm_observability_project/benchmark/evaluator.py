import json
import csv
from pathlib import Path


def export_report(report: dict, fmt: str = "json"):
    Path("reports").mkdir(exist_ok=True)

    if fmt == "json":
        path = "reports/benchmark_report.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        return path

    if fmt == "csv":
        path = "reports/benchmark_report.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            headers = ["config"] + list(next(iter(report.values())).keys())
            writer.writerow(headers)
            for label, metrics in report.items():
                writer.writerow([label] + list(metrics.values()))
        return path

    if fmt == "markdown":
        path = "reports/benchmark_report.md"
        with open(path, "w") as f:
            f.write("| Config | LLM Calls | Total Tokens | Avg Latency | Total Cost | Savings |\n")
            f.write("|---|---|---|---|---|---|\n")
            for label, m in report.items():
                f.write(
                    f"| {label} | {m['llm_calls']} | {m['total_tokens']} | "
                    f"{m['avg_latency_ms']}ms | ${m['total_cost_usd']} | "
                    f"{m.get('cost_savings_pct', 0)}% |\n"
                )
        return path

    raise ValueError(f"Unsupported format: {fmt}")
