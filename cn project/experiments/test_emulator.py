#!/usr/bin/env python3
# Test Suite for Network Emulator - Author: Protanu - Validates emulator features

import sys
import os
import time
import socket
import unittest
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from packet import create_data_packet, Packet
from network_emulator import NetworkEmulator
from metrics import verify_file_integrity


class TestNetworkEmulator(unittest.TestCase):

    def setUp(self):
        self.listen_port = 61001
        self.forward_port = 61002

    def test_clean_forwarding(self):
        # Test that packets pass through unaltered when loss=0, delay=0
        print("\n--- Test: Clean Forwarding (No Impairments) ---")
        emu = NetworkEmulator(
            listen_port=self.listen_port,
            forward_port=self.forward_port,
            loss_rate=0.0,
            delay_ms=0.0,
        )
        emu.start()

        # Receiver socket
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(("127.0.0.1", self.forward_port))
        recv_sock.settimeout(2.0)

        # Sender socket
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        num_packets = 20
        for seq in range(num_packets):
            pkt = create_data_packet(seq, f"Data {seq}".encode("utf-8"))
            send_sock.sendto(pkt.serialize(), ("127.0.0.1", self.listen_port))

        received = []
        for _ in range(num_packets):
            try:
                data, _ = recv_sock.recvfrom(4096)
                p = Packet.deserialize(data)
                received.append(p.sequence_number)
            except socket.timeout:
                break

        emu.stop()
        send_sock.close()
        recv_sock.close()

        self.assertEqual(len(received), num_packets, f"Expected {num_packets} packets, got {len(received)}")
        self.assertEqual(received, list(range(num_packets)), "Packets should arrive in sequential order")
        print(f"PASS: All {num_packets} packets forwarded cleanly in order.")

    def test_loss_simulation(self):
        # Test that packet loss drops packets according to configured rate
        print("\n--- Test: Packet Loss Simulation ---")
        loss_rate = 0.25  # 25% loss
        emu = NetworkEmulator(
            listen_port=self.listen_port,
            forward_port=self.forward_port,
            loss_rate=loss_rate,
            delay_ms=0.0,
            protect_control=False,
        )
        emu.start()

        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(("127.0.0.1", self.forward_port))
        recv_sock.settimeout(0.5)

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        num_packets = 200

        for seq in range(num_packets):
            pkt = create_data_packet(seq, b"Test payload for loss")
            send_sock.sendto(pkt.serialize(), ("127.0.0.1", self.listen_port))

        received_count = 0
        while True:
            try:
                data, _ = recv_sock.recvfrom(4096)
                received_count += 1
            except socket.timeout:
                break

        stats = emu.get_stats()
        emu.stop()
        send_sock.close()
        recv_sock.close()

        dropped_count = stats["forward_dropped"]
        measured_loss = dropped_count / float(num_packets)
        print(f"Sent: {num_packets}, Dropped: {dropped_count}, Delivered: {received_count}")
        print(f"Configured Loss: {loss_rate*100:.1f}%, Measured Loss: {measured_loss*100:.1f}%")

        self.assertEqual(received_count + dropped_count, num_packets)
        self.assertGreater(dropped_count, 0, "At least some packets should have been dropped")
        self.assertTrue(0.12 <= measured_loss <= 0.40, f"Measured loss {measured_loss:.2f} within statistical bounds")
        print("PASS: Packet loss simulation verified.")

    def test_delay_simulation(self):
        # Test that artificial delay is added to packets
        print("\n--- Test: Delay Simulation ---")
        delay_ms = 60.0
        emu = NetworkEmulator(
            listen_port=self.listen_port,
            forward_port=self.forward_port,
            loss_rate=0.0,
            delay_ms=delay_ms,
        )
        emu.start()

        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(("127.0.0.1", self.forward_port))
        recv_sock.settimeout(2.0)

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pkt = create_data_packet(1, b"Delayed message")

        start = time.time()
        send_sock.sendto(pkt.serialize(), ("127.0.0.1", self.listen_port))

        data, _ = recv_sock.recvfrom(4096)
        elapsed_ms = (time.time() - start) * 1000.0

        emu.stop()
        send_sock.close()
        recv_sock.close()

        print(f"Configured Delay: {delay_ms:.1f} ms, Measured Elapsed: {elapsed_ms:.1f} ms")
        self.assertGreaterEqual(elapsed_ms, 50.0, "Packet transit time should reflect configured delay")
        print("PASS: Delay simulation verified.")

    def test_reordering_simulation(self):
        # Test that packets are delivered out-of-order when reordering is enabled
        print("\n--- Test: Reordering Simulation ---")
        emu = NetworkEmulator(
            listen_port=self.listen_port,
            forward_port=self.forward_port,
            loss_rate=0.0,
            delay_ms=0.0,
            reorder_rate=0.50,
            protect_control=False,
        )
        emu.start()

        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(("127.0.0.1", self.forward_port))
        recv_sock.settimeout(1.0)

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        num_packets = 15

        for seq in range(num_packets):
            pkt = create_data_packet(seq, f"Reorder payload {seq}".encode("utf-8"))
            send_sock.sendto(pkt.serialize(), ("127.0.0.1", self.listen_port))
            time.sleep(0.01)

        received_seqs = []
        while True:
            try:
                data, _ = recv_sock.recvfrom(4096)
                p = Packet.deserialize(data)
                if p:
                    received_seqs.append(p.sequence_number)
            except socket.timeout:
                break

        stats = emu.get_stats()
        emu.stop()
        send_sock.close()
        recv_sock.close()

        print(f"Sent seqs:     {list(range(num_packets))}")
        print(f"Received seqs: {received_seqs}")
        print(f"Reorder stats: {stats['forward_reordered']} events")

        is_reordered = (received_seqs != list(range(num_packets)))
        self.assertTrue(is_reordered, "Packets should arrive in non-sequential order due to reordering")
        print("PASS: Out-of-order reordering simulation verified.")

    def test_corruption_simulation(self):
        # Test that payload corruption triggers CRC32 failure
        print("\n--- Test: Corruption Simulation ---")
        emu = NetworkEmulator(
            listen_port=self.listen_port,
            forward_port=self.forward_port,
            loss_rate=0.0,
            delay_ms=0.0,
            corrupt_rate=1.0,
            protect_control=False,
        )
        emu.start()

        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(("127.0.0.1", self.forward_port))
        recv_sock.settimeout(2.0)

        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pkt = create_data_packet(1, b"Payload to be corrupted by bit flip")
        send_sock.sendto(pkt.serialize(), ("127.0.0.1", self.listen_port))

        data, _ = recv_sock.recvfrom(4096)
        corrupted_pkt = Packet.deserialize(data)

        emu.stop()
        send_sock.close()
        recv_sock.close()

        valid, status = corrupted_pkt.verify_integrity()
        print(f"Integrity check status: {status}")
        self.assertFalse(valid, "Corrupted packet should fail CRC32 verification")
        self.assertEqual(status, "CORRUPTED")
        print("PASS: Corruption simulation verified.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
