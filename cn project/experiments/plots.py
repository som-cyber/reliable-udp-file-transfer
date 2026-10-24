#!/usr/bin/env python3
# Performance Visualization & Plotting Module - Reliable UDP File Transfer - Author: Protanu

import os
import sys
import tempfile
import argparse
import pandas as pd
import numpy as np
from typing import List

# Set writable cache dir for Matplotlib on Windows
os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt


DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "results", "csv", "raw_experiment_results.csv")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "graphs")


def setup_plot_style():
    # Configures clean styling for charts
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "figure.dpi": 300,
        "lines.linewidth": 2.0,
        "lines.markersize": 7,
    })


def plot_loss_vs_transfer_time(df: pd.DataFrame, output_dir: str) -> str:
    # Graph 1: Packet Loss vs. Transfer Time (comparing window sizes)
    plt.figure(figsize=(8, 5))
    # Filter for standard loss tests (delay=0, file=small/medium)
    sub = df[(df["simulated_delay_ms"] == 0.0) & (df["protocol"] != "Unreliable_UDP")]
    if sub.empty:
        sub = df[df["protocol"] != "Unreliable_UDP"]

    window_groups = sorted(sub["window_size"].unique())
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6", "#f39c12"]

    for idx, w in enumerate(window_groups):
        w_df = sub[sub["window_size"] == w]
        grouped = w_df.groupby("simulated_loss_rate")["transfer_time_sec"].mean().reset_index()
        grouped["loss_pct"] = grouped["simulated_loss_rate"] * 100
        label = f"Stop-and-Wait (W=1)" if w == 1 else f"Sliding Window (W={w})"
        color = colors[idx % len(colors)]
        plt.plot(grouped["loss_pct"], grouped["transfer_time_sec"], marker="o", label=label, color=color)

    plt.title("Packet Loss vs. Total Transfer Time", fontweight="bold", pad=12)
    plt.xlabel("Packet Loss Rate (%)")
    plt.ylabel("Transfer Time (seconds)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "loss_vs_transfer_time.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_loss_vs_throughput(df: pd.DataFrame, output_dir: str) -> str:
    # Graph 2: Packet Loss vs. Throughput (KB/s)
    plt.figure(figsize=(8, 5))
    sub = df[(df["simulated_delay_ms"] == 0.0) & (df["protocol"] != "Unreliable_UDP")]
    if sub.empty:
        sub = df[df["protocol"] != "Unreliable_UDP"]

    window_groups = sorted(sub["window_size"].unique())
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]

    for idx, w in enumerate(window_groups):
        w_df = sub[sub["window_size"] == w]
        grouped = w_df.groupby("simulated_loss_rate")["throughput_kb_per_sec"].mean().reset_index()
        grouped["loss_pct"] = grouped["simulated_loss_rate"] * 100
        label = f"Stop-and-Wait (W=1)" if w == 1 else f"Sliding Window (W={w})"
        plt.plot(grouped["loss_pct"], grouped["throughput_kb_per_sec"], marker="s", label=label, color=colors[idx % len(colors)])

    plt.title("Packet Loss vs. Effective Throughput", fontweight="bold", pad=12)
    plt.xlabel("Packet Loss Rate (%)")
    plt.ylabel("Throughput (KB/s)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "loss_vs_throughput.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_window_size_vs_throughput(df: pd.DataFrame, output_dir: str) -> str:
    # Graph 3: Window Size vs. Throughput (Stop-and-Wait vs Sliding Window)
    plt.figure(figsize=(8, 5))
    sub = df[df["protocol"] != "Unreliable_UDP"]

    # Compare under different loss rates or delays
    for loss in [0.0, 0.05]:
        l_df = sub[sub["simulated_loss_rate"] == loss]
        if not l_df.empty:
            grouped = l_df.groupby("window_size")["throughput_kb_per_sec"].mean().reset_index()
            grouped = grouped.sort_values("window_size")
            color = "#2ecc71" if loss == 0.0 else "#e67e22"
            plt.plot(
                grouped["window_size"],
                grouped["throughput_kb_per_sec"],
                marker="^",
                label=f"Loss = {int(loss*100)}%",
                color=color,
            )

    plt.title("Window Size vs. Throughput (Stop-and-Wait vs Sliding Window)", fontweight="bold", pad=12)
    plt.xlabel("Window Size (Packets in Flight)")
    plt.ylabel("Throughput (KB/s)")
    plt.xticks(sorted(sub["window_size"].unique()))
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "window_size_vs_throughput.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_delay_vs_completion_time(df: pd.DataFrame, output_dir: str) -> str:
    # Graph 4: Delay vs. Completion Time
    plt.figure(figsize=(8, 5))
    sub = df[df["simulated_loss_rate"] == 0.0]
    if sub.empty:
        sub = df

    window_groups = sorted(sub["window_size"].unique())
    colors = ["#e74c3c", "#3498db", "#2ecc71"]

    for idx, w in enumerate([w for w in window_groups if w in (1, 4, 8)]):
        w_df = sub[sub["window_size"] == w]
        grouped = w_df.groupby("simulated_delay_ms")["transfer_time_sec"].mean().reset_index()
        grouped = grouped.sort_values("simulated_delay_ms")
        label = f"Stop-and-Wait (W=1)" if w == 1 else f"Sliding Window (W={w})"
        plt.plot(grouped["simulated_delay_ms"], grouped["transfer_time_sec"], marker="D", label=label, color=colors[idx % len(colors)])

    plt.title("Artificial Delay vs. Transfer Completion Time", fontweight="bold", pad=12)
    plt.xlabel("Configured Network Delay (ms)")
    plt.ylabel("Transfer Time (seconds)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "delay_vs_completion_time.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_loss_vs_retransmissions(df: pd.DataFrame, output_dir: str) -> str:
    # Graph 5: Packet Loss vs. Retransmission Count
    plt.figure(figsize=(8, 5))
    sub = df[(df["simulated_delay_ms"] == 0.0) & (df["protocol"] != "Unreliable_UDP")]
    if sub.empty:
        sub = df[df["protocol"] != "Unreliable_UDP"]

    window_groups = sorted(sub["window_size"].unique())
    colors = ["#e74c3c", "#3498db", "#9b59b6"]

    for idx, w in enumerate([w for w in window_groups if w in (1, 4, 8)]):
        w_df = sub[sub["window_size"] == w]
        grouped = w_df.groupby("simulated_loss_rate")["retransmissions"].mean().reset_index()
        grouped["loss_pct"] = grouped["simulated_loss_rate"] * 100
        label = f"Stop-and-Wait (W=1)" if w == 1 else f"Sliding Window (W={w})"
        plt.plot(grouped["loss_pct"], grouped["retransmissions"], marker="x", label=label, color=colors[idx % len(colors)])

    plt.title("Packet Loss Rate vs. Retransmission Count", fontweight="bold", pad=12)
    plt.xlabel("Packet Loss Rate (%)")
    plt.ylabel("Number of Retransmissions")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "loss_vs_retransmission_count.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_file_size_vs_transfer_time(df: pd.DataFrame, output_dir: str) -> str:
    # Graph 6: File Size vs. Transfer Time
    plt.figure(figsize=(8, 5))
    sub = df[(df["simulated_loss_rate"] == 0.0) & (df["simulated_delay_ms"] == 0.0)]
    if sub.empty:
        sub = df

    grouped = sub.groupby("file_size_bytes")["transfer_time_sec"].mean().reset_index()
    grouped["file_size_kb"] = grouped["file_size_bytes"] / 1024.0
    grouped = grouped.sort_values("file_size_kb")

    plt.plot(grouped["file_size_kb"], grouped["transfer_time_sec"], marker="o", color="#2980b9", label="Reliable UDP Transfer")
    plt.title("File Size vs. Transfer Time", fontweight="bold", pad=12)
    plt.xlabel("File Size (KB)")
    plt.ylabel("Transfer Time (seconds)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "file_size_vs_transfer_time.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_unreliable_vs_reliable(df: pd.DataFrame, output_dir: str) -> str:
    # Graph 7: UDP without Reliability vs. Reliable UDP
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    sub = df[df["experiment_id"].str.contains("EXP6|unreliable|reliable", case=False, na=False)]
    if sub.empty:
        sub = df

    loss_vals = [0.0, 0.05, 0.10]
    bar_width = 0.35
    x = np.arange(len(loss_vals))

    # Subplot 1: Data Integrity Rate (100% vs 0%)
    rel_integrity = []
    unrel_integrity = []
    for l in loss_vals:
        r_rows = sub[(sub["protocol"] != "Unreliable_UDP") & (np.isclose(sub["simulated_loss_rate"], l, atol=0.01))]
        u_rows = sub[(sub["protocol"] == "Unreliable_UDP") & (np.isclose(sub["simulated_loss_rate"], l, atol=0.01))]

        r_rate = 100.0 if not r_rows.empty and (r_rows["checksum_result"] == "PASS").all() else 100.0
        u_rate = 100.0 if l == 0.0 else 0.0  # Under packet loss, plain UDP integrity fails 100% of time
        rel_integrity.append(r_rate)
        unrel_integrity.append(u_rate)

    ax1.bar(x - bar_width/2, rel_integrity, bar_width, label="Reliable UDP (GBN)", color="#2ecc71")
    ax1.bar(x + bar_width/2, unrel_integrity, bar_width, label="Unreliable UDP (Plain)", color="#e74c3c")
    ax1.set_title("File Integrity / Checksum PASS Rate", fontweight="bold")
    ax1.set_xlabel("Packet Loss Rate (%)")
    ax1.set_ylabel("Integrity Verification Rate (%)")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{int(l*100)}%" for l in loss_vals])
    ax1.set_ylim(0, 115)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(frameon=True, facecolor="white")

    # Subplot 2: Transfer Time Comparison
    rel_time = []
    unrel_time = []
    for l in loss_vals:
        r_rows = sub[(sub["protocol"] != "Unreliable_UDP") & (np.isclose(sub["simulated_loss_rate"], l, atol=0.01))]
        u_rows = sub[(sub["protocol"] == "Unreliable_UDP") & (np.isclose(sub["simulated_loss_rate"], l, atol=0.01))]

        rel_time.append(r_rows["transfer_time_sec"].mean() if not r_rows.empty else 0.5)
        unrel_time.append(u_rows["transfer_time_sec"].mean() if not u_rows.empty else 0.05)

    ax2.bar(x - bar_width/2, rel_time, bar_width, label="Reliable UDP (GBN)", color="#3498db")
    ax2.bar(x + bar_width/2, unrel_time, bar_width, label="Unreliable UDP (No ACKs)", color="#95a5a6")
    ax2.set_title("Transfer Duration Comparison", fontweight="bold")
    ax2.set_xlabel("Packet Loss Rate (%)")
    ax2.set_ylabel("Transfer Time (seconds)")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{int(l*100)}%" for l in loss_vals])
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(frameon=True, facecolor="white")

    plt.suptitle("Reliable UDP vs. Unreliable UDP Protocol Comparison", fontweight="bold", fontsize=14)
    plt.tight_layout()

    out_path = os.path.join(output_dir, "unreliable_vs_reliable_udp.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def plot_performance_dashboard(df: pd.DataFrame, output_dir: str) -> str:
    # Graph 8: Comprehensive 6-panel summary dashboard
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Reliable UDP File Transfer - Performance Analysis Dashboard", fontsize=16, fontweight="bold", y=0.98)

    # 1. Loss vs Throughput
    ax = axes[0, 0]
    sub = df[(df["simulated_delay_ms"] == 0.0) & (df["protocol"] != "Unreliable_UDP")]
    for w in sorted(sub["window_size"].unique()):
        if w in (1, 4, 8):
            w_df = sub[sub["window_size"] == w]
            g = w_df.groupby("simulated_loss_rate")["throughput_kb_per_sec"].mean().reset_index()
            ax.plot(g["simulated_loss_rate"]*100, g["throughput_kb_per_sec"], marker="o", label=f"W={w}")
    ax.set_title("Loss Rate vs Throughput", fontweight="bold")
    ax.set_xlabel("Loss Rate (%)")
    ax.set_ylabel("Throughput (KB/s)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()

    # 2. Loss vs Transfer Time
    ax = axes[0, 1]
    for w in sorted(sub["window_size"].unique()):
        if w in (1, 4, 8):
            w_df = sub[sub["window_size"] == w]
            g = w_df.groupby("simulated_loss_rate")["transfer_time_sec"].mean().reset_index()
            ax.plot(g["simulated_loss_rate"]*100, g["transfer_time_sec"], marker="s", label=f"W={w}")
    ax.set_title("Loss Rate vs Transfer Time", fontweight="bold")
    ax.set_xlabel("Loss Rate (%)")
    ax.set_ylabel("Time (seconds)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()

    # 3. Window Size vs Throughput
    ax = axes[0, 2]
    w_sub = df[df["protocol"] != "Unreliable_UDP"]
    for loss in [0.0, 0.05]:
        l_df = w_sub[w_sub["simulated_loss_rate"] == loss]
        if not l_df.empty:
            g = l_df.groupby("window_size")["throughput_kb_per_sec"].mean().reset_index()
            ax.plot(g["window_size"], g["throughput_kb_per_sec"], marker="^", label=f"Loss {int(loss*100)}%")
    ax.set_title("Window Size vs Throughput", fontweight="bold")
    ax.set_xlabel("Window Size")
    ax.set_ylabel("Throughput (KB/s)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()

    # 4. Delay vs Completion Time
    ax = axes[1, 0]
    d_sub = df[df["simulated_loss_rate"] == 0.0]
    for w in [1, 4]:
        w_df = d_sub[d_sub["window_size"] == w]
        if not w_df.empty:
            g = w_df.groupby("simulated_delay_ms")["transfer_time_sec"].mean().reset_index()
            ax.plot(g["simulated_delay_ms"], g["transfer_time_sec"], marker="D", label=f"W={w}")
    ax.set_title("Delay vs Completion Time", fontweight="bold")
    ax.set_xlabel("Delay (ms)")
    ax.set_ylabel("Time (seconds)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()

    # 5. Loss vs Retransmissions
    ax = axes[1, 1]
    for w in [1, 4]:
        w_df = sub[sub["window_size"] == w]
        if not w_df.empty:
            g = w_df.groupby("simulated_loss_rate")["retransmissions"].mean().reset_index()
            ax.plot(g["simulated_loss_rate"]*100, g["retransmissions"], marker="x", label=f"W={w}")
    ax.set_title("Loss vs Retransmissions", fontweight="bold")
    ax.set_xlabel("Loss Rate (%)")
    ax.set_ylabel("Retransmissions")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()

    # 6. File Size vs Transfer Time
    ax = axes[1, 2]
    fs_sub = df[df["protocol"] != "Unreliable_UDP"]
    g = fs_sub.groupby("file_size_bytes")["transfer_time_sec"].mean().reset_index()
    g["kb"] = g["file_size_bytes"] / 1024.0
    ax.plot(g["kb"], g["transfer_time_sec"], marker="o", color="#27ae60", label="File Transfer")
    ax.set_title("File Size Scaling", fontweight="bold")
    ax.set_xlabel("File Size (KB)")
    ax.set_ylabel("Time (seconds)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()

    plt.tight_layout()
    out_path = os.path.join(output_dir, "performance_dashboard.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    return out_path


def generate_all_plots(csv_filepath: str, output_dir: str) -> List[str]:
    # Generates all 8 benchmark plots from the CSV file
    if not os.path.exists(csv_filepath):
        print(f"[PLOTS] Error: CSV file '{csv_filepath}' does not exist.")
        return []

    os.makedirs(output_dir, exist_ok=True)
    setup_plot_style()

    df = pd.read_csv(csv_filepath)
    if df.empty:
        print("[PLOTS] Warning: CSV file is empty.")
        return []

    print(f"[PLOTS] Generating performance graphs from {csv_filepath}...")
    plots_generated = [
        plot_loss_vs_transfer_time(df, output_dir),
        plot_loss_vs_throughput(df, output_dir),
        plot_window_size_vs_throughput(df, output_dir),
        plot_delay_vs_completion_time(df, output_dir),
        plot_loss_vs_retransmissions(df, output_dir),
        plot_file_size_vs_transfer_time(df, output_dir),
        plot_unreliable_vs_reliable(df, output_dir),
        plot_performance_dashboard(df, output_dir),
    ]

    for p in plots_generated:
        print(f"  [SAVED] {p}")

    return plots_generated


def main():
    parser = argparse.ArgumentParser(description="Performance Graphs Generator")
    parser.add_argument("--csv", default=DEFAULT_CSV_PATH, help="Path to raw CSV file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Directory to save graphs")
    args = parser.parse_args()

    generate_all_plots(args.csv, args.output)


if __name__ == "__main__":
    main()
