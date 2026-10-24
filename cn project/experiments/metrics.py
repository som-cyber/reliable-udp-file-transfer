#!/usr/bin/env python3
# Performance Metrics Module - Reliable UDP File Transfer - Author: Protanu

import os
import sys
import time
import hashlib
import zlib
import csv
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
try:
    from checksum import generate_checksum
except ImportError:
    def generate_checksum(data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF


def calculate_file_hash(filepath: str, algorithm: str = "sha256") -> str:
    # Calculates cryptographic hash (sha256 or md5) of a file
    if not os.path.exists(filepath):
        return ""
    hasher = hashlib.sha256() if algorithm == "sha256" else hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_file_crc32(filepath: str) -> int:
    # Calculates CRC32 of a file
    if not os.path.exists(filepath):
        return 0
    crc = 0
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            crc = zlib.crc32(chunk, crc)
    return crc & 0xFFFFFFFF


def verify_file_integrity(original_path: str, received_path: str) -> Dict[str, Any]:
    # Compares original and received files byte-for-byte and checks CRC32 and SHA-256 hashes
    if not os.path.exists(original_path) or not os.path.exists(received_path):
        return {
            "match": False,
            "orig_size": os.path.getsize(original_path) if os.path.exists(original_path) else -1,
            "recv_size": os.path.getsize(received_path) if os.path.exists(received_path) else -1,
            "status": "MISSING_FILE",
        }

    orig_size = os.path.getsize(original_path)
    recv_size = os.path.getsize(received_path)

    orig_crc = calculate_file_crc32(original_path)
    recv_crc = calculate_file_crc32(received_path)

    orig_sha = calculate_file_hash(original_path)
    recv_sha = calculate_file_hash(received_path)

    size_match = (orig_size == recv_size)
    crc_match = (orig_crc == recv_crc)
    sha_match = (orig_sha == recv_sha)

    # Exact byte comparison
    exact_match = size_match and crc_match and sha_match
    if exact_match and orig_size > 0:
        with open(original_path, "rb") as f1, open(received_path, "rb") as f2:
            exact_match = (f1.read() == f2.read())

    return {
        "match": exact_match,
        "orig_size": orig_size,
        "recv_size": recv_size,
        "orig_crc": orig_crc,
        "recv_crc": recv_crc,
        "orig_sha256": orig_sha,
        "recv_sha256": recv_sha,
        "status": "PASS" if exact_match else "FAIL",
    }


@dataclass
class TransferMetrics:
    # Dataclass holding all metrics for a single file transfer run
    experiment_id: str = ""
    timestamp: str = ""
    protocol: str = "Reliable_UDP_GBN"  # Reliable_UDP_GBN, Stop_and_Wait, Unreliable_UDP
    file_name: str = ""
    file_size_bytes: int = 0
    chunk_size_bytes: int = 1024
    window_size: int = 4
    simulated_loss_rate: float = 0.0
    simulated_delay_ms: float = 0.0
    simulated_reorder_rate: float = 0.0
    simulated_duplicate_rate: float = 0.0

    # Measured outcomes
    transfer_time_sec: float = 0.0
    throughput_kb_per_sec: float = 0.0
    throughput_mbps: float = 0.0
    data_packets_expected: int = 0
    packets_sent_total: int = 0
    packets_received: int = 0
    retransmissions: int = 0
    retransmission_rate_pct: float = 0.0
    emulator_dropped: int = 0
    emulator_reordered: int = 0
    emulator_duplicated: int = 0
    completion_status: str = "SUCCESS"  # SUCCESS, FAILED, TIMEOUT
    checksum_result: str = "PASS"       # PASS, FAIL
    avg_latency_ms: float = 0.0

    def compute_derived_metrics(self) -> None:
        # Calculates throughput and retransmission rates from base fields
        if self.transfer_time_sec > 0 and self.file_size_bytes > 0:
            self.throughput_kb_per_sec = (self.file_size_bytes / 1024.0) / self.transfer_time_sec
            self.throughput_mbps = (self.file_size_bytes * 8.0 / 1_000_000.0) / self.transfer_time_sec
        else:
            self.throughput_kb_per_sec = 0.0
            self.throughput_mbps = 0.0

        if self.data_packets_expected > 0:
            self.retransmission_rate_pct = (self.retransmissions / float(self.data_packets_expected)) * 100.0
        else:
            self.retransmission_rate_pct = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


CSV_FIELDNAMES = [
    "experiment_id",
    "timestamp",
    "protocol",
    "file_name",
    "file_size_bytes",
    "chunk_size_bytes",
    "window_size",
    "simulated_loss_rate",
    "simulated_delay_ms",
    "simulated_reorder_rate",
    "simulated_duplicate_rate",
    "transfer_time_sec",
    "throughput_kb_per_sec",
    "throughput_mbps",
    "data_packets_expected",
    "packets_sent_total",
    "packets_received",
    "retransmissions",
    "retransmission_rate_pct",
    "emulator_dropped",
    "emulator_reordered",
    "emulator_duplicated",
    "completion_status",
    "checksum_result",
    "avg_latency_ms",
]


def save_metrics_to_csv(metric: TransferMetrics, csv_filepath: str) -> None:
    # Appends a single TransferMetrics record to a CSV file
    metric.compute_derived_metrics()
    os.makedirs(os.path.dirname(os.path.abspath(csv_filepath)), exist_ok=True)
    file_exists = os.path.exists(csv_filepath) and os.path.getsize(csv_filepath) > 0

    with open(csv_filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(metric.to_dict())


def save_metrics_batch_to_csv(metrics: List[TransferMetrics], csv_filepath: str) -> None:
    # Appends multiple TransferMetrics records to a CSV file
    os.makedirs(os.path.dirname(os.path.abspath(csv_filepath)), exist_ok=True)
    file_exists = os.path.exists(csv_filepath) and os.path.getsize(csv_filepath) > 0

    with open(csv_filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for m in metrics:
            m.compute_derived_metrics()
            writer.writerow(m.to_dict())


def print_metric_summary(m: TransferMetrics) -> None:
    # Prints a neat formatted summary box of the transfer metrics
    m.compute_derived_metrics()
    print("------------------------------------------------------------")
    print(f" Experiment: {m.experiment_id} | Protocol: {m.protocol}")
    print(f" File Size: {m.file_size_bytes:,} bytes | Window Size: {m.window_size}")
    print(f" Network: Loss={m.simulated_loss_rate*100:.1f}%, Delay={m.simulated_delay_ms}ms, Reorder={m.simulated_reorder_rate*100:.1f}%")
    print(f" Transfer Time: {m.transfer_time_sec:.4f} s")
    print(f" Throughput:    {m.throughput_kb_per_sec:.2f} KB/s ({m.throughput_mbps:.3f} Mbps)")
    print(f" Packets:       {m.data_packets_expected} expected | {m.retransmissions} retransmitted ({m.retransmission_rate_pct:.1f}%)")
    print(f" Status:        {m.completion_status} | Checksum: {m.checksum_result}")
    print("------------------------------------------------------------")
