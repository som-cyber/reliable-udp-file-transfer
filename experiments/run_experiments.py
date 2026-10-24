#!/usr/bin/env python3
# Automated Experiment Runner - Reliable UDP File Transfer - Author: Protanu

import sys
import os
import time
import subprocess
import argparse
import datetime
import re
import pandas as pd
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from network_emulator import NetworkEmulator
from metrics import (
    TransferMetrics,
    save_metrics_to_csv,
    save_metrics_batch_to_csv,
    verify_file_integrity,
    print_metric_summary,
    calculate_file_hash,
)
from load_generator import (
    ensure_test_files,
    send_file_unreliable,
    receive_file_unreliable,
    BENCHMARK_FILES,
)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
CSV_DIR = os.path.join(RESULTS_DIR, "csv")
GRAPHS_DIR = os.path.join(RESULTS_DIR, "graphs")
RAW_CSV = os.path.join(CSV_DIR, "raw_experiment_results.csv")
SUMMARY_CSV = os.path.join(CSV_DIR, "summary_experiment_results.csv")


def parse_sender_retransmissions(stdout_text: str) -> int:
    # Extracts total retransmissions count reported by sender stdout
    # Look for 'Total retransmissions:  X'
    match = re.search(r"Total retransmissions:\s*(\d+)", stdout_text)
    if match:
        return int(match.group(1))
    
    # Fallback: check if retransmission_stats.csv exists in current dir
    stats_file = "retransmission_stats.csv"
    if os.path.exists(stats_file):
        try:
            total = 0
            with open(stats_file, "r") as f:
                lines = f.readlines()[1:]
                for line in lines:
                    parts = line.strip().split(",")
                    if len(parts) >= 2 and parts[1].isdigit():
                        total += int(parts[1])
            return total
        except Exception:
            pass
    return 0


def run_single_transfer(
    file_path: str,
    window_size: int = 4,
    loss_rate: float = 0.0,
    delay_ms: float = 0.0,
    reorder_rate: float = 0.0,
    duplicate_rate: float = 0.0,
    corrupt_rate: float = 0.0,
    is_unreliable: bool = False,
    timeout_sec: float = 45.0,
    emulator_port: int = 5101,
    receiver_port: int = 5102,
    experiment_id: str = "exp",
) -> TransferMetrics:
    # Executes a single controlled file transfer run through the network emulator
    os.makedirs(CSV_DIR, exist_ok=True)
    # Prevent a previous run's CSV from contaminating retransmission metrics.
    # The sender writes this file in its current working directory.
    stale_stats_file = os.path.abspath("retransmission_stats.csv")
    if os.path.exists(stale_stats_file):
        try:
            os.remove(stale_stats_file)
        except OSError:
            pass

    temp_received_file = os.path.join(RESULTS_DIR, f"temp_recv_{int(time.time()*1000)}.tmp")
    if os.path.exists(temp_received_file):
        os.remove(temp_received_file)

    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    protocol_name = (
        "Unreliable_UDP" if is_unreliable else
        ("Stop_and_Wait" if window_size == 1 else f"Sliding_Window_GBN_W{window_size}")
    )

    # 1. Start Network Emulator
    emulator = NetworkEmulator(
        listen_host="127.0.0.1",
        listen_port=emulator_port,
        forward_host="127.0.0.1",
        forward_port=receiver_port,
        loss_rate=loss_rate,
        delay_ms=delay_ms,
        reorder_rate=reorder_rate,
        duplicate_rate=duplicate_rate,
        corrupt_rate=corrupt_rate,
        protect_control=True,
        verbose=False,
    )
    emulator.start()

    # 2. Start Receiver
    rec_proc = None
    rec_log = None
    send_log = None
    rec_log_path = os.path.join(RESULTS_DIR, "receiver.log")
    send_log_path = os.path.join(RESULTS_DIR, "sender.log")

    if not is_unreliable:
        receiver_script = os.path.join(os.path.dirname(__file__), "..", "src", "udp_receiver.py")
        rec_cmd = [
            sys.executable,
            receiver_script,
            "--host", "127.0.0.1",
            "--port", str(receiver_port),
            "--output", temp_received_file,
        ]
        rec_log = open(rec_log_path, "w", encoding="utf-8")
        rec_proc = subprocess.Popen(rec_cmd, stdout=rec_log, stderr=subprocess.STDOUT)
    
    # Allow sockets to bind
    time.sleep(0.3)

    # 3. Start Sender & Measure Transfer Time
    start_time = time.time()
    completion_status = "SUCCESS"
    retransmissions = 0

    try:
        if is_unreliable:
            # Plain UDP without reliability
            import threading
            rec_result = [False, 0, 0]
            def run_unrec():
                rec_result[0], rec_result[1], rec_result[2] = receive_file_unreliable(
                    "127.0.0.1", receiver_port, temp_received_file, timeout_sec=max(3.0, delay_ms/1000.0 * 2)
                )
            rt = threading.Thread(target=run_unrec, daemon=True)
            rt.start()
            time.sleep(0.1)

            # Send through emulator
            send_file_unreliable("127.0.0.1", emulator_port, file_path, packet_delay_sec=0.0005)
            rt.join(timeout=timeout_sec)
            elapsed_time = time.time() - start_time
            if not rec_result[0]:
                # A missing/incomplete receive is a failure regardless of the
                # configured impairment probability. Verify checksum separately.
                completion_status = "FAILED"
        else:
            sender_script = os.path.join(os.path.dirname(__file__), "..", "src", "udp_sender.py")
            send_cmd = [
                sys.executable,
                sender_script,
                "--host", "127.0.0.1",
                "--port", str(emulator_port),
                "--file", file_path,
                "--window-size", str(window_size),
            ]
            send_log = open(send_log_path, "w", encoding="utf-8")
            send_proc = subprocess.run(
                send_cmd,
                stdout=send_log,
                stderr=subprocess.STDOUT,
                timeout=timeout_sec,
            )
            elapsed_time = time.time() - start_time

            if send_proc.returncode != 0:
                completion_status = "FAILED"
            else:
                completion_status = "SUCCESS"

            # Parse retransmissions from stats file or log
            retransmissions = 0
            if os.path.exists("retransmission_stats.csv"):
                try:
                    with open("retransmission_stats.csv", "r") as f:
                        lines = f.readlines()[1:]
                        for line in lines:
                            parts = line.strip().split(",")
                            if len(parts) >= 2 and parts[1].isdigit():
                                retransmissions += int(parts[1])
                except Exception:
                    pass
            if retransmissions == 0 and os.path.exists(send_log_path):
                try:
                    with open(send_log_path, "r", encoding="utf-8", errors="ignore") as f:
                        retransmissions = parse_sender_retransmissions(f.read())
                except Exception:
                    pass

    except subprocess.TimeoutExpired:
        elapsed_time = timeout_sec
        completion_status = "TIMEOUT"
    except Exception as e:
        elapsed_time = time.time() - start_time
        completion_status = f"ERROR: {str(e)[:30]}"

    finally:
        # Give receiver time to flush file write
        wait_deadline = time.time() + 3.0
        while time.time() < wait_deadline:
            if os.path.exists(temp_received_file) and os.path.getsize(temp_received_file) >= file_size:
                break
            time.sleep(0.1)

        if rec_proc:
            try:
                rec_proc.terminate()
                rec_proc.wait(timeout=1.0)
            except Exception:
                pass

        if rec_log:
            try:
                rec_log.close()
            except Exception:
                pass

        if send_log:
            try:
                send_log.close()
            except Exception:
                pass

        emulator.stop()

    # 4. Verify Integrity
    integrity = verify_file_integrity(file_path, temp_received_file)
    checksum_result = integrity["status"]

    if completion_status == "SUCCESS" and not integrity["match"]:
        completion_status = "CHECKSUM_FAILED"

    # Clean temporary received file
    if os.path.exists(temp_received_file):
        try:
            os.remove(temp_received_file)
        except Exception:
            pass

    # 5. Extract Emulator Statistics
    emu_stats = emulator.get_stats()
    expected_packets = (file_size + 1024 - 1) // 1024

    metrics = TransferMetrics(
        experiment_id=experiment_id,
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        protocol=protocol_name,
        file_name=file_name,
        file_size_bytes=file_size,
        chunk_size_bytes=1024,
        window_size=window_size,
        simulated_loss_rate=loss_rate,
        simulated_delay_ms=delay_ms,
        simulated_reorder_rate=reorder_rate,
        simulated_duplicate_rate=duplicate_rate,
        transfer_time_sec=round(elapsed_time, 4),
        data_packets_expected=expected_packets,
        packets_sent_total=emu_stats["total_forward_packets"],
        packets_received=emu_stats["forward_delivered"],
        retransmissions=retransmissions,
        emulator_dropped=emu_stats["forward_dropped"],
        emulator_reordered=emu_stats["forward_reordered"],
        emulator_duplicated=emu_stats["forward_duplicated"],
        completion_status=completion_status,
        checksum_result=checksum_result,
        # No end-to-end latency samples are collected by this runner. Do not
        # label a configured delay estimate as a measured average latency.
        avg_latency_ms=0.0,
    )
    metrics.compute_derived_metrics()

    # Clean temporary stats file
    if os.path.exists("retransmission_stats.csv"):
        try:
            os.remove("retransmission_stats.csv")
        except Exception:
            pass

    return metrics


def run_experiment_matrix(quick: bool = False, runs_per_config: int = 1) -> List[TransferMetrics]:
    # Runs the experimental test matrix according to project specifications
    print("\n============================================================")
    print(" Reliable UDP File Transfer - Automated Benchmark Suite")
    print(" Author: Protanu | Role: Network Emulator & Performance Analysis")
    print("============================================================\n")

    test_files = ensure_test_files()
    all_metrics: List[TransferMetrics] = []

    # Configure experiment parameter ranges
    if quick:
        loss_rates = [0.0, 0.05, 0.10]
        delays = [0.0, 20.0, 50.0]
        window_sizes = [1, 4, 8]
        file_sizes = ["small", "medium"]
    else:
        loss_rates = [0.0, 0.02, 0.05, 0.10, 0.15]
        delays = [0.0, 20.0, 50.0, 100.0]
        window_sizes = [1, 2, 4, 8, 16]
        file_sizes = ["small", "medium", "large"]

    exp_counter = 1

    # ========================================================================
    # EXPERIMENT 1: Packet Loss vs Performance (Stop-and-Wait vs Sliding Window)
    # Fixed: delay=0ms, file=small/medium, variable: loss_rate & window_size
    # ========================================================================
    print("\n>>> EXPERIMENT 1: Packet Loss Evaluation (0% - 15%) <<<")
    for size_key in (["small"] if quick else ["small", "medium"]):
        file_path = test_files[size_key]
        for loss in loss_rates:
            for w in ([1, 4] if quick else [1, 4, 8]):
                for r in range(runs_per_config):
                    exp_id = f"EXP1_loss_{int(loss*100)}pct_W{w}_{size_key}_r{r+1}"
                    print(f"[{exp_counter:03d}] Running {exp_id} (Loss={loss*100:.1f}%, W={w}, File={size_key})...")
                    m = run_single_transfer(
                        file_path=file_path,
                        window_size=w,
                        loss_rate=loss,
                        delay_ms=0.0,
                        experiment_id=exp_id,
                    )
                    all_metrics.append(m)
                    save_metrics_to_csv(m, RAW_CSV)
                    print_metric_summary(m)
                    exp_counter += 1

    # ========================================================================
    # EXPERIMENT 2: Window Size Scaling Benchmark (W=1, 2, 4, 8, 16)
    # Fixed: loss=0% and loss=5%, delay=20ms, file=medium/small
    # ========================================================================
    print("\n>>> EXPERIMENT 2: Window Size Scaling Benchmark <<<")
    for w in window_sizes:
        for loss in [0.0, 0.05]:
            exp_id = f"EXP2_window_W{w}_loss{int(loss*100)}pct"
            print(f"[{exp_counter:03d}] Running {exp_id} (Window={w}, Loss={loss*100:.1f}%, Delay=20ms)...")
            m = run_single_transfer(
                file_path=test_files["small"],
                window_size=w,
                loss_rate=loss,
                delay_ms=20.0,
                experiment_id=exp_id,
            )
            all_metrics.append(m)
            save_metrics_to_csv(m, RAW_CSV)
            print_metric_summary(m)
            exp_counter += 1

    # ========================================================================
    # EXPERIMENT 3: Network Delay Impact (0ms, 20ms, 50ms, 100ms)
    # Fixed: loss=0%, window=1 (Stop-and-Wait) vs window=4 (Sliding Window)
    # ========================================================================
    print("\n>>> EXPERIMENT 3: Delay Impact Evaluation (0ms - 100ms) <<<")
    for d in delays:
        for w in ([1, 4] if quick else [1, 4, 8]):
            exp_id = f"EXP3_delay_{int(d)}ms_W{w}"
            print(f"[{exp_counter:03d}] Running {exp_id} (Delay={d}ms, W={w})...")
            m = run_single_transfer(
                file_path=test_files["small"],
                window_size=w,
                loss_rate=0.0,
                delay_ms=d,
                experiment_id=exp_id,
            )
            all_metrics.append(m)
            save_metrics_to_csv(m, RAW_CSV)
            print_metric_summary(m)
            exp_counter += 1

    # ========================================================================
    # EXPERIMENT 4: File Size Scaling (Small vs Medium vs Large)
    # ========================================================================
    print("\n>>> EXPERIMENT 4: File Size Scaling Benchmark <<<")
    for size_key in file_sizes:
        exp_id = f"EXP4_filesize_{size_key}"
        print(f"[{exp_counter:03d}] Running {exp_id} ({size_key.upper()}, W=4, Delay=0ms)...")
        m = run_single_transfer(
            file_path=test_files[size_key],
            window_size=4,
            loss_rate=0.0,
            delay_ms=0.0,
            timeout_sec=90.0,
            experiment_id=exp_id,
        )
        all_metrics.append(m)
        save_metrics_to_csv(m, RAW_CSV)
        print_metric_summary(m)
        exp_counter += 1

    # ========================================================================
    # EXPERIMENT 5: Packet Reordering & Jitter Resilience
    # ========================================================================
    print("\n>>> EXPERIMENT 5: Reordering & Jitter Resilience <<<")
    for reorder_p in [0.05, 0.15]:
        exp_id = f"EXP5_reorder_{int(reorder_p*100)}pct"
        print(f"[{exp_counter:03d}] Running {exp_id} (Reorder={reorder_p*100:.1f}%, Delay=10ms)...")
        m = run_single_transfer(
            file_path=test_files["small"],
            window_size=4,
            loss_rate=0.0,
            delay_ms=10.0,
            reorder_rate=reorder_p,
            experiment_id=exp_id,
        )
        all_metrics.append(m)
        save_metrics_to_csv(m, RAW_CSV)
        print_metric_summary(m)
        exp_counter += 1

    # ========================================================================
    # EXPERIMENT 6: Baseline Comparison - Unreliable UDP vs Reliable UDP
    # ========================================================================
    print("\n>>> EXPERIMENT 6: Unreliable UDP vs Reliable UDP <<<")
    for loss in [0.0, 0.05, 0.10]:
        # Unreliable run
        exp_id_unrel = f"EXP6_unreliable_loss{int(loss*100)}pct"
        print(f"[{exp_counter:03d}] Running {exp_id_unrel} (Unreliable UDP, Loss={loss*100:.1f}%)...")
        m_unrel = run_single_transfer(
            file_path=test_files["small"],
            window_size=1,
            loss_rate=loss,
            delay_ms=0.0,
            is_unreliable=True,
            experiment_id=exp_id_unrel,
        )
        all_metrics.append(m_unrel)
        save_metrics_to_csv(m_unrel, RAW_CSV)
        print_metric_summary(m_unrel)
        exp_counter += 1

        # Reliable run for comparison
        exp_id_rel = f"EXP6_reliable_loss{int(loss*100)}pct"
        print(f"[{exp_counter:03d}] Running {exp_id_rel} (Reliable UDP W=4, Loss={loss*100:.1f}%)...")
        m_rel = run_single_transfer(
            file_path=test_files["small"],
            window_size=4,
            loss_rate=loss,
            delay_ms=0.0,
            is_unreliable=False,
            experiment_id=exp_id_rel,
        )
        all_metrics.append(m_rel)
        save_metrics_to_csv(m_rel, RAW_CSV)
        print_metric_summary(m_rel)
        exp_counter += 1

    # ========================================================================
    # GENERATE AGGREGATED SUMMARY CSV
    # ========================================================================
    print("\n[EXPERIMENTS] Generating aggregated summary CSV...")
    generate_summary_csv(RAW_CSV, SUMMARY_CSV)

    print(f"\n[DONE] All experiments completed successfully!")
    print(f"  - Raw Results CSV    : {RAW_CSV}")
    print(f"  - Summary Results CSV: {SUMMARY_CSV}")

    return all_metrics


def generate_summary_csv(raw_csv_path: str, summary_csv_path: str) -> None:
    # Aggregates raw experiment metrics by configuration parameters
    if not os.path.exists(raw_csv_path):
        return

    df = pd.read_csv(raw_csv_path)
    if df.empty:
        return

    group_cols = [
        "protocol",
        "file_name",
        "file_size_bytes",
        "window_size",
        "simulated_loss_rate",
        "simulated_delay_ms",
        "simulated_reorder_rate",
    ]

    # Filter only available grouping columns
    valid_groups = [c for c in group_cols if c in df.columns]

    agg_dict = {
        "transfer_time_sec": ["mean", "std", "min", "max"],
        "throughput_kb_per_sec": ["mean", "std"],
        "throughput_mbps": ["mean", "std"],
        "retransmissions": ["mean", "max"],
        "retransmission_rate_pct": ["mean"],
        "emulator_dropped": ["mean"],
        "completion_status": ["count"],
    }

    summary_df = df.groupby(valid_groups).agg(agg_dict).reset_index()
    # Flatten multi-level headers
    summary_df.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col
        for col in summary_df.columns.values
    ]

    os.makedirs(os.path.dirname(os.path.abspath(summary_csv_path)), exist_ok=True)
    summary_df.to_csv(summary_csv_path, index=False)


def main():
    parser = argparse.ArgumentParser(description="Automated Network Experiment Runner")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark subset")
    parser.add_argument("--runs", type=int, default=1, help="Repetitions per configuration")
    parser.add_argument("--skip-plots", action="store_true", help="Skip graph generation")
    args = parser.parse_args()

    # Clear prior raw CSV if fresh run is desired
    # (or preserve if appending)
    metrics = run_experiment_matrix(quick=args.quick, runs_per_config=args.runs)

    if not args.skip_plots:
        try:
            print("\n[EXPERIMENTS] Triggering automated plot generation...")
            import plots
            plots.generate_all_plots(RAW_CSV, GRAPHS_DIR)
        except Exception as e:
            print(f"[WARNING] Could not generate plots automatically: {e}")

        try:
            print("\n[EXPERIMENTS] Triggering automated result analysis...")
            import analyze_results
            analyze_results.generate_analysis_report(RAW_CSV, RESULTS_DIR)
        except Exception as e:
            print(f"[WARNING] Could not generate analysis report: {e}")


if __name__ == "__main__":
    main()
