#!/usr/bin/env python3
# Load Generator Module - Reliable UDP File Transfer - Author: Protanu

import os
import sys
import time
import socket
import random
import string
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from packet import (
    create_start_packet,
    create_data_packet,
    create_end_packet,
    Packet,
    PACKET_TYPE_DATA,
    PACKET_TYPE_START,
    PACKET_TYPE_END,
)
from file_utils import chunk_file, DEFAULT_CHUNK_SIZE, reconstruct_file_from_dict
from metrics import calculate_file_crc32, calculate_file_hash


TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "test-data")

# File size benchmarks
BENCHMARK_FILES = {
    "small": {
        "filename": "sample_small.txt",
        "size_bytes": 48_000,       # ~48 KB (~47 packets)
        "description": "Small text file (Week 2 baseline)",
    },
    "medium": {
        "filename": "sample_medium.txt",
        "size_bytes": 512_000,      # 500 KB (~500 packets)
        "description": "Medium file for throughput benchmarking",
    },
    "large": {
        "filename": "sample_large.txt",
        "size_bytes": 2_097_152,    # 2 MB (~2048 packets)
        "description": "Large file for stress and window scaling",
    },
}


def ensure_test_files() -> Dict[str, str]:
    # Ensures benchmark test files exist and returns dictionary mapping size names to paths
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    paths = {}

    for size_name, info in BENCHMARK_FILES.items():
        filepath = os.path.join(TEST_DATA_DIR, info["filename"])
        paths[size_name] = filepath

        if not os.path.exists(filepath):
            print(f"[LOAD_GEN] Creating benchmark file '{info['filename']}' ({info['size_bytes']:,} bytes)...")
            generate_test_file(filepath, info["size_bytes"])
        else:
            actual_size = os.path.getsize(filepath)
            # If empty or unexpectedly small for medium/large, regenerate
            if size_name != "small" and actual_size < info["size_bytes"] // 2:
                print(f"[LOAD_GEN] Regenerating '{info['filename']}' to full size ({info['size_bytes']:,} bytes)...")
                generate_test_file(filepath, info["size_bytes"])

    return paths


def generate_test_file(filepath: str, size_bytes: int, seed: int = 42) -> str:
    # Generates a reproducible text/binary content file of the specified size
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    rng = random.Random(seed)
    
    # Generate structured readable text lines with line numbers and padding
    chunk_pattern = string.ascii_letters + string.digits + " \n.,!?:;"
    bytes_written = 0
    buffer_size = 65536

    with open(filepath, "wb") as f:
        while bytes_written < size_bytes:
            remaining = size_bytes - bytes_written
            to_write = min(buffer_size, remaining)
            # Generate deterministic pseudo-random chunk
            chunk_str = "".join(rng.choice(chunk_pattern) for _ in range(to_write))
            f.write(chunk_str.encode("utf-8")[:to_write])
            bytes_written += to_write

    return filepath


# ============================================================================
# UNRELIABLE UDP FILE TRANSFER (Baseline for Comparison)
# ============================================================================

def send_file_unreliable(
    host: str,
    port: int,
    filepath: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    packet_delay_sec: float = 0.001,
) -> Tuple[bool, int, float]:
    # Sends file over plain UDP without ACKs, timeouts, or retransmissions
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    chunks = chunk_file(filepath, chunk_size)
    chunk_count = len(chunks)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    start_time = time.time()
    packets_sent = 0

    try:
        # Send START packet
        start_packet = create_start_packet(0)
        sock.sendto(start_packet.serialize(), (host, port))

        # Send all DATA packets at maximum blast (with tiny pacing delay to avoid OS buffer overflow)
        for seq_num, chunk in enumerate(chunks):
            pkt = create_data_packet(seq_num, chunk)
            sock.sendto(pkt.serialize(), (host, port))
            packets_sent += 1
            if packet_delay_sec > 0:
                time.sleep(packet_delay_sec)

        # Send END packet
        end_packet = create_end_packet(chunk_count)
        sock.sendto(end_packet.serialize(), (host, port))

    finally:
        sock.close()

    elapsed = time.time() - start_time
    return True, packets_sent, elapsed


def receive_file_unreliable(
    host: str,
    port: int,
    output_filepath: str,
    timeout_sec: float = 5.0,
) -> Tuple[bool, int, int]:
    # Receives packets over plain UDP without sending ACKs
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(timeout_sec)

    received_packets = {}
    expected_count = 0
    active = False

    try:
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                # Transfer timed out
                break

            pkt = Packet.deserialize(data)
            if not pkt or not pkt.verify_integrity()[0]:
                continue

            if pkt.packet_type == PACKET_TYPE_START:
                active = True
                received_packets.clear()
            elif pkt.packet_type == PACKET_TYPE_DATA:
                if active:
                    received_packets[pkt.sequence_number] = pkt
            elif pkt.packet_type == PACKET_TYPE_END:
                expected_count = pkt.sequence_number
                break

    finally:
        sock.close()

    # Attempt reconstruction
    if received_packets and output_filepath:
        # Write received packets in order, padding missing chunks with zeros or skipping
        sorted_seqs = sorted(received_packets.keys())
        with open(output_filepath, "wb") as f:
            for s in sorted_seqs:
                f.write(received_packets[s].payload)

    completed = (expected_count > 0 and len(received_packets) == expected_count)
    return completed, len(received_packets), expected_count


if __name__ == "__main__":
    print("[LOAD_GEN] Initializing benchmark test files...")
    created = ensure_test_files()
    for name, path in created.items():
        sz = os.path.getsize(path)
        print(f"  - {name.upper()}: {path} ({sz:,} bytes)")
    print("[LOAD_GEN] Test files ready.")
