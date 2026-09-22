#!/usr/bin/env python3

import os
import random
import sys

# Use files from the src folder
sys.path.insert(0, "src")

from packet import Packet, create_data_packet
from file_utils import chunk_file, reconstruct_file_from_packets

INPUT_FILE = "test-data/sample_small.txt"

# Maximum data carried by one packet
CHUNK_SIZE = 15


# TC-1: Packet Serialization
def test_1():
    print("\nTC-1: Packet Serialization")

    original = create_data_packet(0, b"Hello, World!")

    # Packet -> bytes
    data = original.serialize()

    # bytes -> Packet
    new_packet = Packet.deserialize(data)

    if (
        new_packet.packet_type == original.packet_type
        and new_packet.sequence_number == original.sequence_number
        and new_packet.payload == original.payload
        and new_packet.checksum == original.checksum
    ):
        print("PASS")
        return True

    print("FAIL")
    return False


# File -> chunks -> packets
def create_packets(file_path, chunk_size):
    chunks = chunk_file(file_path, chunk_size)

    packets = []

    # Sequence number = position of the chunk
    for sequence, chunk in enumerate(chunks):
        packets.append(create_data_packet(sequence, chunk))

    return packets


# TC-2: File Reconstruction
# Works for small files and files larger than 1 MB.
def test_2():
    print("\nTC-2: File Reconstruction")

    output_file = "test-data/output_test.txt"

    with open(INPUT_FILE, "rb") as file:
        original_data = file.read()

    packets = create_packets(INPUT_FILE, CHUNK_SIZE)

    reconstruct_file_from_packets(packets, output_file)

    with open(output_file, "rb") as file:
        reconstructed_data = file.read()

    result = reconstructed_data == original_data

    print("Original size      :", len(original_data), "bytes")
    print("Number of packets  :", len(packets))
    print("Reconstructed size :", len(reconstructed_data), "bytes")
    print("PASS" if result else "FAIL")

    if os.path.exists(output_file):
        os.remove(output_file)

    return result


# TC-3: Packet Size / Threshold Test
#
# With CHUNK_SIZE = 1024:
# 1023 bytes -> 1 packet
# 1024 bytes -> 1 packet
# 1025 bytes -> 2 packets
# 1 MB        -> 1024 packets
def test_3():
    print("\nTC-3: Packet Size / Threshold Test")

    file_size = os.path.getsize(INPUT_FILE)
    packets = create_packets(INPUT_FILE, CHUNK_SIZE)

    # Expected number of packets = ceil(file_size / CHUNK_SIZE)
    expected_packets = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    actual_packets = len(packets)

    print("Input size         :", file_size, "bytes")
    print("Chunk size         :", CHUNK_SIZE, "bytes")
    print("Expected packets   :", expected_packets)
    print("Actual packets     :", actual_packets)

    if actual_packets != expected_packets:
        print("FAIL")
        return False

    # No packet should be larger than the configured chunk size
    for packet in packets:
        if len(packet.payload) > CHUNK_SIZE:
            print("FAIL: packet payload is too large")
            return False

    print("PASS")
    return True


# TC-4: Out-of-Order Packets
def test_4():
    print("\nTC-4: Out-of-Order Packets")

    output_file = "test-data/output_test.txt"

    with open(INPUT_FILE, "rb") as file:
        original_data = file.read()

    packets = create_packets(INPUT_FILE, CHUNK_SIZE)

    # Simulate packets arriving in a different order
    random.shuffle(packets)

    reconstruct_file_from_packets(packets, output_file)

    with open(output_file, "rb") as file:
        reconstructed_data = file.read()

    result = reconstructed_data == original_data

    print("Packets received in shuffled order")
    print("PASS" if result else "FAIL")

    if os.path.exists(output_file):
        os.remove(output_file)

    return result


# TC-5: Checksum / Corrupted Packet
def test_5():
    print("\nTC-5: Corrupted Packet Detection")

    packet = create_data_packet(0, b"This data will be corrupted.")

    # Convert packet to bytes
    data = packet.serialize()

    # Change one byte in the payload
    corrupted = bytearray(data)

    # Current packet header is 11 bytes
    corrupted[11] ^= 0xFF

    corrupted = bytes(corrupted)

    # Convert corrupted bytes back into a packet
    new_packet = Packet.deserialize(corrupted)

    valid, status = new_packet.verify_integrity()

    print("Checksum result:", status)

    if status == "CORRUPTED":
        print("PASS")
        return True

    print("FAIL")
    return False


# TC-6: Sequence Number Check
def test_6():
    print("\nTC-6: Sequence Numbers")

    packets = create_packets(INPUT_FILE, CHUNK_SIZE)

    # Sequence numbers should be 0, 1, 2, 3, ...
    for expected, packet in enumerate(packets):
        if packet.sequence_number != expected:
            print(
                "FAIL: expected sequence",
                expected,
                "but got",
                packet.sequence_number
            )
            return False

    print("Packets:", len(packets))
    print("Sequence numbers are correct")
    print("PASS")
    return True


# Run all tests
def main():

    print("=" * 50)
    print("UDP Packetization Test Suite")
    print("=" * 50)

    print("\nInput file :", INPUT_FILE)
    print("Chunk size :", CHUNK_SIZE, "bytes")

    results = []

    results.append(("TC-1", test_1()))
    results.append(("TC-2", test_2()))
    results.append(("TC-3", test_3()))
    results.append(("TC-4", test_4()))
    results.append(("TC-5", test_5()))
    results.append(("TC-6", test_6()))

    print("\n" + "=" * 50)
    print("FINAL RESULTS")
    print("=" * 50)

    passed = 0

    for name, result in results:
        print(name, ":", "PASS" if result else "FAIL")

        if result:
            passed += 1

    print("\n", passed, "/", len(results), "tests passed")

    # The test program succeeds only if every test passes
    return passed == len(results)


if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
