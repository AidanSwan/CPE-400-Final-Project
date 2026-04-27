import json
import os
import sys
import glob
import argparse
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import pandas as pd
except ImportError:
    print("[ERROR] Missing dependencies. Run: pip install matplotlib pandas")
    sys.exit(1)

RESULTS_DIR  = Path("../results")
CAPTURES_DIR = Path("../captures")
REPORT_DIR   = Path("../report")

SCENARIO_ORDER = [
    "baseline", "loss_1pct", "loss_5pct", "loss_10pct",
    "latency_hi", "throttled", "combined"
]

SCENARIO_LABELS = {
    "baseline":    "Baseline\n(no impairment)",
    "loss_1pct":   "1% Loss",
    "loss_5pct":   "5% Loss",
    "loss_10pct":  "10% Loss",
    "latency_hi":  "200ms Latency",
    "throttled":   "500 Kbps\nThrottle",
    "combined":    "5% Loss\n+50ms +1Mbps",
}

COLORS = {
    "baseline":    "#4CAF50",
    "loss_1pct":   "#8BC34A",
    "loss_5pct":   "#FFC107",
    "loss_10pct":  "#FF5722",
    "latency_hi":  "#2196F3",
    "throttled":   "#9C27B0",
    "combined":    "#F44336",
}

def parse_iperf3(json_path: Path) -> dict:
    """Extract key metrics from an iperf3 JSON output file."""
    with open(json_path) as f:
        data = json.load(f)

    end = data.get("end", {})
    streams = end.get("streams", [{}])
    sender = streams[0].get("sender", {}) if streams else {}
    receiver = streams[0].get("receiver", {}) if streams else {}
    sum_sent = end.get("sum_sent", {})
    sum_recv = end.get("sum_received", {})

    intervals = data.get("intervals", [])
    throughput_series = [
        iv["sum"]["bits_per_second"] / 1e6
        for iv in intervals
        if "sum" in iv
    ]

    retransmits = sender.get("retransmits", sum_sent.get("retransmits", 0))
    throughput_mbps = sum_recv.get("bits_per_second", 0) / 1e6
    mean_rtt_us = sender.get("mean_rtt", None)
    max_rtt_us  = sender.get("max_rtt", None)

    return {
        "throughput_mbps":    throughput_mbps,
        "retransmits":        retransmits,
        "mean_rtt_ms":        mean_rtt_us / 1000 if mean_rtt_us else None,
        "max_rtt_ms":         max_rtt_us  / 1000 if max_rtt_us  else None,
        "throughput_series":  throughput_series,
        "bytes_transferred":  sum_recv.get("bytes", 0),
    }

def load_all_results() -> dict:
    """Load all iperf3 JSON results from the results directory."""
    results = {}
    for scenario in SCENARIO_ORDER:
        json_file = RESULTS_DIR / f"{scenario}.json"
        if json_file.exists():
            try:
                results[scenario] = parse_iperf3(json_file)
                print(f"  ✓ Loaded: {scenario}")
            except Exception as e:
                print(f"  ✗ Failed to parse {scenario}: {e}")
        else:
            print(f"  - Missing: {scenario}.json")
    return results

def parse_pcap(pcap_path: Path) -> dict:
    """Extract TCP retransmission stats from a pcap file using pyshark."""
    try:
        import pyshark
    except ImportError:
        print("  [WARN] pyshark not installed — skipping pcap analysis.")
        print("         Install with: pip install pyshark (also needs tshark)")
        return {}

    retransmissions = 0
    dup_acks = 0
    fast_retransmits = 0
    packets = 0

    try:
        cap = pyshark.FileCapture(
            str(pcap_path),
            display_filter="tcp",
            keep_packets=False
        )
        for pkt in cap:
            packets += 1
            if hasattr(pkt, 'tcp'):
                analysis = getattr(pkt.tcp, 'analysis', None)
                if analysis:
                    flags = str(analysis)
                    if 'retransmission' in flags.lower():
                        retransmissions += 1
                    if 'duplicate_ack' in flags.lower():
                        dup_acks += 1
                    if 'fast_retransmission' in flags.lower():
                        fast_retransmits += 1
        cap.close()
    except Exception as e:
        print(f"  [WARN] pcap parse error for {pcap_path.name}: {e}")

    return {
        "total_packets":   packets,
        "retransmissions": retransmissions,
        "dup_acks":        dup_acks,
        "fast_retransmits": fast_retransmits,
    }

def load_all_pcaps() -> dict:
    """Load all pcap files."""
    pcap_data = {}
    for scenario in SCENARIO_ORDER:
        # Try both server-side and client-side captures
        for suffix in ["", "_client"]:
            pcap_file = CAPTURES_DIR / f"{scenario}{suffix}.pcap"
            if pcap_file.exists():
                print(f"  Parsing pcap: {pcap_file.name} ...")
                pcap_data[scenario] = parse_pcap(pcap_file)
                break
    return pcap_data

def plot_throughput_bar(results: dict, ax):
    scenarios = [s for s in SCENARIO_ORDER if s in results]
    throughputs = [results[s]["throughput_mbps"] for s in scenarios]
    colors = [COLORS[s] for s in scenarios]
    labels = [SCENARIO_LABELS[s] for s in scenarios]

    bars = ax.bar(range(len(scenarios)), throughputs, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Throughput (Mbps)")
    ax.set_title("Average Throughput by Scenario")
    ax.set_ylim(0, max(throughputs) * 1.2 if throughputs else 1)

    for bar, val in zip(bars, throughputs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{val:.2f}", ha='center', va='bottom', fontsize=7)


def plot_retransmits_bar(results: dict, ax):
    scenarios = [s for s in SCENARIO_ORDER if s in results]
    retransmits = [results[s]["retransmits"] for s in scenarios]
    colors = [COLORS[s] for s in scenarios]
    labels = [SCENARIO_LABELS[s] for s in scenarios]

    ax.bar(range(len(scenarios)), retransmits, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Retransmissions")
    ax.set_title("TCP Retransmissions by Scenario")


def plot_rtt(results: dict, ax):
    scenarios = [s for s in SCENARIO_ORDER if s in results and results[s]["mean_rtt_ms"] is not None]
    if not scenarios:
        ax.text(0.5, 0.5, "RTT data not available\n(iperf3 version may not report it)",
                ha='center', va='center', transform=ax.transAxes, fontsize=9, color='gray')
        ax.set_title("Mean RTT by Scenario")
        return

    mean_rtts = [results[s]["mean_rtt_ms"] for s in scenarios]
    labels = [SCENARIO_LABELS[s] for s in scenarios]
    colors = [COLORS[s] for s in scenarios]

    ax.bar(range(len(scenarios)), mean_rtts, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Mean RTT (ms)")
    ax.set_title("Mean Round-Trip Time by Scenario")


def plot_throughput_over_time(results: dict, ax):
    for scenario in SCENARIO_ORDER:
        if scenario not in results:
            continue
        series = results[scenario]["throughput_series"]
        if not series:
            continue
        time_axis = list(range(1, len(series) + 1))
        ax.plot(time_axis, series, label=SCENARIO_LABELS[scenario].replace("\n", " "),
                color=COLORS[scenario], linewidth=1.5)

    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Throughput (Mbps)")
    ax.set_title("Throughput Over Time (All Scenarios)")
    ax.legend(fontsize=7, loc="upper right")


def generate_plots(results: dict, pcap_data: dict):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("CPE 400 — TCP Reliability Analysis Results", fontsize=14, fontweight='bold')
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    plot_throughput_bar(results, ax1)
    plot_retransmits_bar(results, ax2)
    plot_rtt(results, ax3)
    plot_throughput_over_time(results, ax4)

    out_path = REPORT_DIR / "tcp_analysis_results.png"
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"\n  ✓ Plot saved → {out_path}")
    plt.show()

def print_summary(results: dict, pcap_data: dict):
    print("\n" + "═" * 70)
    print(f"{'Scenario':<18} {'Throughput':>12} {'Retransmits':>13} {'Mean RTT':>10}")
    print("─" * 70)
    for scenario in SCENARIO_ORDER:
        if scenario not in results:
            continue
        r = results[scenario]
        rtt = f"{r['mean_rtt_ms']:.1f} ms" if r['mean_rtt_ms'] else "N/A"
        print(f"{scenario:<18} {r['throughput_mbps']:>9.2f} Mbps"
              f" {r['retransmits']:>12}  {rtt:>10}")
    print("═" * 70)

    if pcap_data:
        print("\n── pcap Analysis ──────────────────────────────────────────")
        print(f"{'Scenario':<18} {'Packets':>8} {'Retransmits':>13} {'Dup ACKs':>10}")
        print("─" * 55)
        for scenario in SCENARIO_ORDER:
            if scenario not in pcap_data:
                continue
            p = pcap_data[scenario]
            print(f"{scenario:<18} {p['total_packets']:>8} {p['retransmissions']:>13} {p['dup_acks']:>10}")
        print("─" * 55)

def main():
    parser = argparse.ArgumentParser(description="CPE 400 TCP Analysis — Result Parser & Plotter")
    parser.add_argument("--no-pcap", action="store_true", help="Skip pcap parsing")
    parser.add_argument("--no-plot", action="store_true", help="Skip plot generation")
    args = parser.parse_args()

    print("\n CPE 400 TCP Reliability Analysis")
    print("═" * 40)

    print("\n[1/3] Loading iperf3 results...")
    results = load_all_results()

    if not results:
        print("\n[ERROR] No result JSON files found in ../results/")
        print("        Run the test scripts first, then copy results here.")
        sys.exit(1)

    pcap_data = {}
    if not args.no_pcap:
        print("\n[2/3] Parsing pcap captures...")
        pcap_data = load_all_pcaps()
    else:
        print("\n[2/3] Skipping pcap analysis (--no-pcap)")

    print_summary(results, pcap_data)

    if not args.no_plot:
        print("\n[3/3] Generating plots...")
        generate_plots(results, pcap_data)
    else:
        print("\n[3/3] Skipping plot generation (--no-plot)")

    print("\n Done. Check ../report/ for output figures.")


if __name__ == "__main__":
    main()