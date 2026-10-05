#!/usr/bin/env python3
"""
Standalone tests for duplicate / out-of-order / corruption handling.
Tests the receiver's core logic directly, without sockets, so this
doesn't depend on Sahil's sliding window being finished.
"""

from packet import create_data_packet, create_ack_packet, PACKET_TYPE_DATA
from file_utils import reconstruct_file_from_dict
import os


def test_out_of_order_reconstruction():
    print("\n--- Test: Out-of-order packet reconstruction ---")

    # Simulate packets arriving in the WRONG order
    p0 = create_data_packet(0, b"Hello, ")
    p1 = create_data_packet(1, b"World")
    p2 = create_data_packet(2, b"!")

    received_packets = {}

    # Deliberately insert out of order: 2, 0, 1
    for pkt in [p2, p0, p1]:
        received_packets[pkt.sequence_number] = pkt
        print(f"Received (out of order): seq={pkt.sequence_number}")

    success = reconstruct_file_from_dict(received_packets, "test_out_of_order.txt", expected_packet_count=3)
    assert success, "Reconstruction should succeed despite out-of-order arrival"

    with open("test_out_of_order.txt", "rb") as f:
        result = f.read()

    assert result == b"Hello, World!", f"Expected 'Hello, World!', got {result}"
    print("PASS: file correctly reassembled despite out-of-order arrival")

    os.remove("test_out_of_order.txt")


def test_duplicate_packet_ignored():
    print("\n--- Test: Duplicate packet does not corrupt data ---")

    received_packets = {}

    p0 = create_data_packet(0, b"ABC")
    p0_dup = create_data_packet(0, b"ABC")  # same seq, arrives twice

    for pkt in [p0, p0_dup]:
        if pkt.sequence_number in received_packets:
            print(f"Duplicate DATA packet {pkt.sequence_number} ignored")
        else:
            received_packets[pkt.sequence_number] = pkt
            print(f"Stored packet seq={pkt.sequence_number}")

    assert len(received_packets) == 1, "Duplicate should not create a second entry"
    print("PASS: duplicate packet did not corrupt the store")


def test_corrupted_packet_rejected():
    print("\n--- Test: Corrupted packet fails integrity check ---")

    p = create_data_packet(5, b"Important data")
    serialized = p.serialize()

    # Flip a bit in the payload to simulate corruption in transit
    corrupted_bytes = bytearray(serialized)
    corrupted_bytes[-1] ^= 0xFF
    corrupted_bytes = bytes(corrupted_bytes)

    from packet import Packet
    corrupted = Packet.deserialize(corrupted_bytes)
    valid, status = corrupted.verify_integrity()

    assert not valid, "Corrupted packet should fail integrity check"
    print(f"PASS: corrupted packet correctly rejected (status={status})")


if __name__ == "__main__":
    test_out_of_order_reconstruction()
    test_duplicate_packet_ignored()
    test_corrupted_packet_rejected()
    print("\nAll reliability tests passed.")