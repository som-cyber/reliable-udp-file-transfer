#!/usr/bin/env python3
# Network Emulator Module - Reliable UDP File Transfer - Author: Protanu

import sys
import os
import time
import socket
import random
import threading
import queue
import argparse
from typing import Optional, Dict, Any, Tuple

# Add src to sys.path so we can deserialize packets for logging/inspection
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
try:
    from packet import Packet, PACKET_TYPE_DATA, PACKET_TYPE_START, PACKET_TYPE_END, PACKET_TYPE_ACK
except ImportError:
    Packet = None
    PACKET_TYPE_DATA = 1
    PACKET_TYPE_START = 2
    PACKET_TYPE_END = 3
    PACKET_TYPE_ACK = 4


class NetworkEmulator:
    # Transparent UDP Network Emulator Proxy with Deterministic FIFO Timed Queue

    def __init__(
        self,
        listen_host: str = "127.0.0.1",
        listen_port: int = 5001,
        forward_host: str = "127.0.0.1",
        forward_port: int = 5002,
        loss_rate: float = 0.0,
        delay_ms: float = 0.0,
        jitter_ms: float = 0.0,
        reorder_rate: float = 0.0,
        duplicate_rate: float = 0.0,
        corrupt_rate: float = 0.0,
        ack_loss_rate: float = 0.0,
        ack_delay_ms: float = 0.0,
        protect_control: bool = True,
        verbose: bool = False,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.forward_host = forward_host
        self.forward_port = forward_port
        self.forward_addr = (forward_host, forward_port)

        # Impairment parameters
        self.loss_rate = max(0.0, min(1.0, loss_rate))
        self.delay_ms = max(0.0, delay_ms)
        self.jitter_ms = max(0.0, jitter_ms)
        self.reorder_rate = max(0.0, min(1.0, reorder_rate))
        self.duplicate_rate = max(0.0, min(1.0, duplicate_rate))
        self.corrupt_rate = max(0.0, min(1.0, corrupt_rate))

        # Reverse path impairments (ACKs)
        self.ack_loss_rate = max(0.0, min(1.0, ack_loss_rate))
        self.ack_delay_ms = max(0.0, ack_delay_ms)

        # Keep START / END packets safe so connection boundary remains stable
        self.protect_control = protect_control
        self.verbose = verbose

        # Sockets
        self.sender_sock: Optional[socket.socket] = None
        self.receiver_sock: Optional[socket.socket] = None

        # Threading & state
        self.running = False
        self.sender_thread: Optional[threading.Thread] = None
        self.receiver_thread: Optional[threading.Thread] = None
        self.forward_worker_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.sender_addr: Optional[Tuple[str, int]] = None

        # Timed priority queue: (delivery_timestamp, counter, sock, data, dest)
        self.transmit_queue = queue.PriorityQueue()
        self.queue_counter = 0

        # Reordering hold-buffer
        self.reorder_buffer: Optional[Tuple[bytes, Tuple[str, int]]] = None
        self.reorder_timer: Optional[threading.Timer] = None

        # Detailed metrics/statistics
        self.stats = {
            "total_forward_packets": 0,
            "forward_data_packets": 0,
            "forward_control_packets": 0,
            "forward_dropped": 0,
            "forward_delayed": 0,
            "forward_reordered": 0,
            "forward_duplicated": 0,
            "forward_corrupted": 0,
            "forward_delivered": 0,
            "total_reverse_packets": 0,
            "reverse_dropped": 0,
            "reverse_delayed": 0,
            "reverse_delivered": 0,
        }

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[EMULATOR] {message}", flush=True)

    def _parse_packet(self, data: bytes) -> Optional[Any]:
        if Packet:
            try:
                return Packet.deserialize(data)
            except Exception:
                return None
        return None

    def _format_packet_info(self, data: bytes) -> str:
        pkt = self._parse_packet(data)
        if pkt:
            type_names = {
                PACKET_TYPE_DATA: "DATA",
                PACKET_TYPE_START: "START",
                PACKET_TYPE_END: "END",
                PACKET_TYPE_ACK: "ACK",
            }
            name = type_names.get(pkt.packet_type, f"TYPE_{pkt.packet_type}")
            return f"{name}(seq={pkt.sequence_number}, len={pkt.payload_length})"
        return f"RAW({len(data)}B)"

    def _is_control_packet(self, data: bytes) -> bool:
        pkt = self._parse_packet(data)
        if pkt:
            return pkt.packet_type in (PACKET_TYPE_START, PACKET_TYPE_END)
        return False

    def _corrupt_payload(self, data: bytes) -> bytes:
        if len(data) <= 11:
            return data
        corrupted = bytearray(data)
        corrupted[-1] ^= 0xFF
        return bytes(corrupted)

    def _schedule_transmission(self, sock: socket.socket, data: bytes, dest: Tuple[str, int], delay_sec: float) -> None:
        delivery_time = time.time() + max(0.0, delay_sec)
        with self.lock:
            self.queue_counter += 1
            item = (delivery_time, self.queue_counter, sock, data, dest)
            self.transmit_queue.put(item)

    def _worker_transmit_loop(self) -> None:
        # Single worker thread that executes queued packet transmissions in strictly timed FIFO order
        while self.running:
            try:
                item = self.transmit_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            delivery_time, _, sock, data, dest = item
            now = time.time()
            if delivery_time > now:
                time.sleep(delivery_time - now)

            try:
                sock.sendto(data, dest)
                # Count a forward packet only after the local UDP stack accepts it.
                # This is not proof that the receiver application consumed it.
                if sock is self.receiver_sock:
                    with self.lock:
                        self.stats["forward_delivered"] += 1
                elif sock is self.sender_sock:
                    with self.lock:
                        self.stats["reverse_delivered"] += 1
            except Exception as e:
                self._log(f"Transmission error to {dest}: {e}")
            finally:
                self.transmit_queue.task_done()

    def _flush_reorder_buffer(self) -> None:
        # Detach the held packet while locked, then process it after releasing
        # the lock. _send_to_receiver() also acquires self.lock, so calling it
        # inside this critical section deadlocks with threading.Lock.
        with self.lock:
            held = self.reorder_buffer
            self.reorder_buffer = None
            self.reorder_timer = None

        if held is not None:
            data, dest = held
            self._log(f"Flushing reorder buffer: {self._format_packet_info(data)} -> {dest}")
            self._send_to_receiver(data, dest, skip_reorder=True)

    def _send_to_receiver(self, data: bytes, dest: Tuple[str, int], skip_reorder: bool = False) -> None:
        pkt_info = self._format_packet_info(data)

        # 1. Packet Loss Check
        if self.loss_rate > 0 and random.random() < self.loss_rate:
            with self.lock:
                self.stats["forward_dropped"] += 1
            self._log(f"DROPPED forward packet: {pkt_info}")
            return

        # 2. Corruption Check
        data_to_send = data
        if self.corrupt_rate > 0 and random.random() < self.corrupt_rate:
            data_to_send = self._corrupt_payload(data)
            with self.lock:
                self.stats["forward_corrupted"] += 1
            self._log(f"CORRUPTED forward packet: {pkt_info}")

        # 3. Packet Reordering Check
        if not skip_reorder and self.reorder_rate > 0 and random.random() < self.reorder_rate:
            with self.lock:
                if self.reorder_buffer is None:
                    self.reorder_buffer = (data_to_send, dest)
                    self.stats["forward_reordered"] += 1
                    self._log(f"HELD packet for reordering: {pkt_info}")

                    if self.reorder_timer:
                        self.reorder_timer.cancel()
                    self.reorder_timer = threading.Timer(0.2, self._flush_reorder_buffer)
                    self.reorder_timer.daemon = True
                    self.reorder_timer.start()
                    return

        packets_to_send = [data_to_send]
        with self.lock:
            if not skip_reorder and self.reorder_buffer is not None:
                held_data, _ = self.reorder_buffer
                self.reorder_buffer = None
                if self.reorder_timer:
                    self.reorder_timer.cancel()
                self._log(f"REORDERED DELIVERY: current {pkt_info} ahead of held {self._format_packet_info(held_data)}")
                packets_to_send = [data_to_send, held_data]

        # 4. Duplication Check
        if self.duplicate_rate > 0 and random.random() < self.duplicate_rate:
            with self.lock:
                self.stats["forward_duplicated"] += 1
            packets_to_send.append(data_to_send)
            self._log(f"DUPLICATED forward packet: {pkt_info}")

        # 5. Delay Scheduling
        for idx, pkt_bytes in enumerate(packets_to_send):
            delay_sec = 0.0
            if self.delay_ms > 0:
                jitter = random.uniform(-self.jitter_ms, self.jitter_ms) if self.jitter_ms > 0 else 0.0
                delay_sec = max(0.0, (self.delay_ms + jitter) / 1000.0)
                with self.lock:
                    self.stats["forward_delayed"] += 1

            if idx > 0 and delay_sec == 0.0:
                delay_sec = 0.001

            self._log(f"FORWARDING to receiver (delay={delay_sec*1000:.1f}ms): {self._format_packet_info(pkt_bytes)}")
            self._schedule_transmission(self.receiver_sock, pkt_bytes, dest, delay_sec)

    def _handle_sender_traffic(self) -> None:
        while self.running:
            try:
                data, addr = self.sender_sock.recvfrom(65535)
            except (socket.timeout, BlockingIOError):
                continue
            except OSError:
                break

            with self.lock:
                self.sender_addr = addr
                self.stats["total_forward_packets"] += 1

            is_ctrl = self._is_control_packet(data)
            if is_ctrl:
                with self.lock:
                    self.stats["forward_control_packets"] += 1
                if self.protect_control:
                    self._flush_reorder_buffer()
                    self._log(f"FORWARDING protected control packet: {self._format_packet_info(data)}")
                    # Use the same ordered transmit queue as flushed data so
                    # END cannot overtake a held/reordered DATA packet. Control
                    # packets bypass impairment, but not queue ordering.
                    self._schedule_transmission(
                        self.receiver_sock, data, self.forward_addr, 0.0
                    )
                    continue

            with self.lock:
                self.stats["forward_data_packets"] += 1

            self._send_to_receiver(data, self.forward_addr)

    def _handle_receiver_traffic(self) -> None:
        while self.running:
            try:
                data, addr = self.receiver_sock.recvfrom(65535)
            except (socket.timeout, BlockingIOError):
                continue
            except OSError:
                break

            with self.lock:
                self.stats["total_reverse_packets"] += 1
                dest = self.sender_addr

            if not dest:
                continue

            pkt_info = self._format_packet_info(data)

            if self.ack_loss_rate > 0 and random.random() < self.ack_loss_rate:
                with self.lock:
                    self.stats["reverse_dropped"] += 1
                self._log(f"DROPPED reverse packet (ACK): {pkt_info}")
                continue

            delay_sec = 0.0
            if self.ack_delay_ms > 0:
                delay_sec = self.ack_delay_ms / 1000.0
                with self.lock:
                    self.stats["reverse_delayed"] += 1

            self._log(f"FORWARDING to sender (delay={delay_sec*1000:.1f}ms): {pkt_info}")
            if delay_sec <= 0:
                try:
                    self.sender_sock.sendto(data, dest)
                    with self.lock:
                        self.stats["reverse_delivered"] += 1
                except Exception as e:
                    self._log(f"Error forwarding ACK immediately: {e}")
            else:
                self._schedule_transmission(self.sender_sock, data, dest, delay_sec)

    def start(self) -> None:
        if self.running:
            return

        self.sender_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sender_sock.bind((self.listen_host, self.listen_port))
        self.sender_sock.settimeout(0.2)

        self.receiver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver_sock.bind(("", 0))
        self.receiver_sock.settimeout(0.2)

        self.running = True

        self.forward_worker_thread = threading.Thread(target=self._worker_transmit_loop, daemon=True)
        self.sender_thread = threading.Thread(target=self._handle_sender_traffic, daemon=True)
        self.receiver_thread = threading.Thread(target=self._handle_receiver_traffic, daemon=True)

        self.forward_worker_thread.start()
        self.sender_thread.start()
        self.receiver_thread.start()

        self._log(f"Network Emulator started on {self.listen_host}:{self.listen_port} -> {self.forward_host}:{self.forward_port}")

    def stop(self) -> None:
        if not self.running:
            return

        self._flush_reorder_buffer()
        self.running = False

        if self.sender_sock:
            try:
                self.sender_sock.close()
            except Exception:
                pass

        if self.receiver_sock:
            try:
                self.receiver_sock.close()
            except Exception:
                pass

        if self.sender_thread and self.sender_thread.is_alive():
            self.sender_thread.join(timeout=1.0)

        if self.receiver_thread and self.receiver_thread.is_alive():
            self.receiver_thread.join(timeout=1.0)

        if self.forward_worker_thread and self.forward_worker_thread.is_alive():
            self.forward_worker_thread.join(timeout=1.0)

        self._log("Network Emulator stopped.")

    def reset_stats(self) -> None:
        with self.lock:
            for k in self.stats:
                self.stats[k] = 0

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.stats)

    def print_summary(self) -> None:
        stats = self.get_stats()
        print("\n================ Network Emulator Summary ================")
        print(f"Listen Address       : {self.listen_host}:{self.listen_port}")
        print(f"Forward Target       : {self.forward_host}:{self.forward_port}")
        print(f"Configured Loss Rate : {self.loss_rate * 100:.1f}%")
        print(f"Configured Delay     : {self.delay_ms:.1f} ms (+/- {self.jitter_ms:.1f} ms)")
        print(f"Configured Reorder   : {self.reorder_rate * 100:.1f}%")
        print("---------------- Forward Traffic (Sender -> Receiver) ----")
        print(f"Total Packets Seen   : {stats['total_forward_packets']}")
        print(f"Control Packets (S/E): {stats['forward_control_packets']}")
        print(f"Data Packets         : {stats['forward_data_packets']}")
        print(f"Packets Dropped      : {stats['forward_dropped']}")
        print(f"Packets Delayed      : {stats['forward_delayed']}")
        print(f"Packets Reordered    : {stats['forward_reordered']}")
        print(f"Packets Duplicated   : {stats['forward_duplicated']}")
        print(f"Packets Corrupted    : {stats['forward_corrupted']}")
        print(f"Packets Delivered    : {stats['forward_delivered']}")
        print("---------------- Reverse Traffic (Receiver -> Sender) ----")
        print(f"Total ACKs Seen      : {stats['total_reverse_packets']}")
        print(f"ACKs Dropped         : {stats['reverse_dropped']}")
        print(f"ACKs Delivered       : {stats['reverse_delivered']}")
        print("==========================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Network Emulator Proxy for Reliable UDP File Transfer")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Host IP to listen on (default: 127.0.0.1)")
    parser.add_argument("--listen-port", type=int, default=5001, help="Port to listen for sender on (default: 5001)")
    parser.add_argument("--forward-host", default="127.0.0.1", help="Target receiver host IP (default: 127.0.0.1)")
    parser.add_argument("--forward-port", type=int, default=5002, help="Target receiver port (default: 5002)")
    parser.add_argument("--loss-rate", type=float, default=0.0, help="Packet loss probability 0.0-1.0 (default: 0.0)")
    parser.add_argument("--delay-ms", type=float, default=0.0, help="Forward artificial delay in ms (default: 0.0)")
    parser.add_argument("--jitter-ms", type=float, default=0.0, help="Delay jitter +/- ms (default: 0.0)")
    parser.add_argument("--reorder-rate", type=float, default=0.0, help="Reorder probability 0.0-1.0 (default: 0.0)")
    parser.add_argument("--duplicate-rate", type=float, default=0.0, help="Duplicate probability 0.0-1.0 (default: 0.0)")
    parser.add_argument("--corrupt-rate", type=float, default=0.0, help="Corruption probability 0.0-1.0 (default: 0.0)")
    parser.add_argument("--ack-loss-rate", type=float, default=0.0, help="ACK loss probability 0.0-1.0 (default: 0.0)")
    parser.add_argument("--ack-delay-ms", type=float, default=0.0, help="ACK delay in ms (default: 0.0)")
    parser.add_argument("--unprotect-control", action="store_true", help="Allow loss/delay on START/END packets")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed per-packet logs")

    args = parser.parse_args()

    emulator = NetworkEmulator(
        listen_host=args.listen_host,
        listen_port=args.listen_port,
        forward_host=args.forward_host,
        forward_port=args.forward_port,
        loss_rate=args.loss_rate,
        delay_ms=args.delay_ms,
        jitter_ms=args.jitter_ms,
        reorder_rate=args.reorder_rate,
        duplicate_rate=args.duplicate_rate,
        corrupt_rate=args.corrupt_rate,
        ack_loss_rate=args.ack_loss_rate,
        ack_delay_ms=args.ack_delay_ms,
        protect_control=not args.unprotect_control,
        verbose=args.verbose,
    )

    try:
        emulator.start()
        print("Emulator running. Press Ctrl+C to stop.")
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping emulator...")
    finally:
        emulator.stop()
        emulator.print_summary()


if __name__ == "__main__":
    main()
