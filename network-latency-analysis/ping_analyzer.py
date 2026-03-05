#!/usr/bin/env python3
import re
import csv
import math
import statistics
from pathlib import Path
from typing import List, Dict, Optional

# Regex patterns for macOS ping output
TIME_RE = re.compile(r"time=([\d.]+)\s*ms")
TIMEOUT_RE = re.compile(r"Request timeout", re.IGNORECASE)
DUP_RE = re.compile(r"\(DUP!\)")


def percentile(sorted_vals: List[float], p: float) -> Optional[float]:
    """Nearest-rank percentile (0-100). Expects a sorted list."""
    if not sorted_vals:
        return None
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]
    k = math.ceil((p / 100.0) * len(sorted_vals)) - 1
    k = max(0, min(k, len(sorted_vals) - 1))
    return sorted_vals[k]


def parse_ping_file(path: Path) -> Dict[str, object]:
    """Parse a ping log file and return summary metrics."""
    latencies: List[float] = []
    timeouts = 0
    dups = 0
    total_lines = 0

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            total_lines += 1

            if TIMEOUT_RE.search(line):
                timeouts += 1
                continue

            m = TIME_RE.search(line)
            if m:
                try:
                    latencies.append(float(m.group(1)))
                except ValueError:
                    pass

            if DUP_RE.search(line):
                dups += 1

    received = len(latencies)
    sent_est = received + timeouts  # estimate of sent pings
    loss_rate = (timeouts / sent_est) if sent_est > 0 else 0.0

    lat_sorted = sorted(latencies)
    avg = statistics.mean(latencies) if latencies else None
    med = statistics.median(latencies) if latencies else None
    stdev = statistics.pstdev(latencies) if len(latencies) >= 2 else None
    p95 = percentile(lat_sorted, 95) if lat_sorted else None
    p99 = percentile(lat_sorted, 99) if lat_sorted else None
    maxv = max(latencies) if latencies else None
    minv = min(latencies) if latencies else None

    # Jitter estimate: mean absolute difference between consecutive samples
    jitter = None
    if len(latencies) >= 2:
        diffs = [abs(latencies[i] - latencies[i - 1]) for i in range(1, len(latencies))]
        jitter = statistics.mean(diffs) if diffs else None

    # Basic anomaly counts
    spike_100 = sum(1 for x in latencies if x >= 100.0)
    spike_200 = sum(1 for x in latencies if x >= 200.0)

    return {
        "file": path.name,
        "received_replies": received,
        "timeouts": timeouts,
        "loss_rate": loss_rate,
        "dups": dups,
        "min_ms": minv,
        "avg_ms": avg,
        "median_ms": med,
        "p95_ms": p95,
        "p99_ms": p99,
        "max_ms": maxv,
        "stdev_ms": stdev,
        "jitter_ms": jitter,
        "spikes_ge_100ms": spike_100,
        "spikes_ge_200ms": spike_200,
        "total_lines": total_lines,
    }


def format_ms(x: Optional[float]) -> str:
    return "-" if x is None else f"{x:.1f}"


def format_pct(x: float) -> str:
    return f"{x * 100:.2f}%"


def print_table(rows: List[Dict[str, object]]) -> None:
    headers = [
        "file", "avg_ms", "p95_ms", "max_ms",
        "timeouts", "loss_rate", "jitter_ms", "dups",
        "spikes_ge_100ms", "spikes_ge_200ms"
    ]

    display = []
    for r in rows:
        display.append({
            "file": str(r["file"]),
            "avg_ms": format_ms(r["avg_ms"]),
            "p95_ms": format_ms(r["p95_ms"]),
            "max_ms": format_ms(r["max_ms"]),
            "timeouts": str(r["timeouts"]),
            "loss_rate": format_pct(float(r["loss_rate"])),
            "jitter_ms": format_ms(r["jitter_ms"]),
            "dups": str(r["dups"]),
            "spikes_ge_100ms": str(r["spikes_ge_100ms"]),
            "spikes_ge_200ms": str(r["spikes_ge_200ms"]),
        })

    col_w = {h: max(len(h), max((len(d[h]) for d in display), default=0)) for h in headers}

    line = "  ".join(h.ljust(col_w[h]) for h in headers)
    sep = "  ".join("-" * col_w[h] for h in headers)
    print(line)
    print(sep)
    for d in display:
        print("  ".join(d[h].ljust(col_w[h]) for h in headers))


def write_csv(rows: List[Dict[str, object]], out_path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def plot_latency_timeline(path: Path) -> None:
    """Create a per-file latency timeline PNG."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    latencies: List[float] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = TIME_RE.search(line)
            if m:
                try:
                    latencies.append(float(m.group(1)))
                except ValueError:
                    pass

    if not latencies:
        return

    plt.figure(figsize=(10, 4))
    plt.plot(latencies)
    plt.title(path.name)
    plt.xlabel("Ping reply #")
    plt.ylabel("Latency (ms)")
    plt.grid(True)
    plt.tight_layout()
    out = path.with_name(path.stem + "_graph.png")
    plt.savefig(out)
    plt.close()


def plot_summaries(rows: List[Dict[str, object]], folder: Path) -> None:
    """Create 2 summary plots across all files."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("\n[plot] matplotlib not installed; skipping plots.")
        print("[plot] If you want graphs: pip3 install matplotlib")
        return

    labels = [str(r["file"]) for r in rows]
    avg = [float(r["avg_ms"] or 0) if r["avg_ms"] is not None else 0 for r in rows]
    p95 = [float(r["p95_ms"] or 0) if r["p95_ms"] is not None else 0 for r in rows]
    mx = [float(r["max_ms"] or 0) if r["max_ms"] is not None else 0 for r in rows]
    timeouts = [int(r["timeouts"]) for r in rows]
    loss = [float(r["loss_rate"]) * 100 for r in rows]

    x = list(range(len(labels)))

    # Latency summary
    plt.figure(figsize=(12, 5))
    plt.plot(x, avg, marker="o", label="avg ms")
    plt.plot(x, p95, marker="o", label="p95 ms")
    plt.plot(x, mx, marker="o", label="max ms")
    plt.xticks(x, labels, rotation=30, ha="right")
    plt.ylabel("ms")
    plt.title("Ping latency summary per log")
    plt.legend()
    plt.tight_layout()
    out1 = folder / "summary_latency.png"
    plt.savefig(out1)
    plt.close()

    # Loss summary
    plt.figure(figsize=(12, 5))
    plt.bar(x, timeouts, label="timeouts (count)")
    plt.twinx()
    plt.plot(x, loss, color="red", marker="o", label="loss rate (%)")
    plt.xticks(x, labels, rotation=30, ha="right")
    plt.title("Packet loss indicators per log")
    plt.tight_layout()
    out2 = folder / "summary_loss.png"
    plt.savefig(out2)
    plt.close()

    print(f"\n[plot] Saved: {out1.name}, {out2.name}")


def main() -> None:
    folder = Path(".").resolve()
    txt_files = sorted(folder.glob("*.txt"))

    if not txt_files:
        print("No .txt files found in this folder. Put your ping logs here and try again.")
        return

    # Parse + summarize
    rows = [parse_ping_file(p) for p in txt_files]

    # Print summary table
    print("\n=== Ping Log Summary ===\n")
    print_table(rows)

    # Write CSV summary
    out_csv = folder / "ping_summary.csv"
    write_csv(rows, out_csv)
    print(f"\nWrote CSV: {out_csv.name}")

    # Per-file timeline graphs
    for p in txt_files:
        plot_latency_timeline(p)

    # Two cross-file summary graphs
    plot_summaries(rows, folder)


if __name__ == "__main__":
    main()
