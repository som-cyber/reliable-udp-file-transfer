#!/usr/bin/env python3
# UDP Sender - Week 2 Milestone (Packetization)

import time
import socket
import argparse
import sys
import os
import csv
from packet import Packet, create_start_packet, create_data_packet, create_end_packet, PACKET_TYPE_ACK
from file_utils import chunk_file, get_file_chunk_count, DEFAULT_CHUNK_SIZE
MAX_RETRANSMISSIONS = 5
INITIAL_RTO = 1.0
DEFAULT_WINDOW_SIZE = 4
MIN_RTO = 0.1
MAX_RTO = 5.0
ALPHA = 0.125   # SRTT smoothing factor (RFC 6298: 1/8)
BETA = 0.25     # RTTVAR smoothing factor (RFC 6298: 1/4)
K = 4           # RTO = SRTT + K * RTTVAR

def send_message(host: str, port: int, message: str) -> None:

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # Create a data packet with the message
        packet = create_data_packet(0, message.encode('utf-8'))
        serialized = packet.serialize()
        
        sock.sendto(serialized, (host, port))
        print(f"Sent message to {host}:{port}")
        print(f"Message: {message}")
        print(f"Packet: {packet}")
    finally:
        sock.close()


def send_file(host: str, port: int, filepath: str, chunk_size: int = DEFAULT_CHUNK_SIZE, window_size: int = DEFAULT_WINDOW_SIZE) -> None:
    if window_size <= 0:
        raise ValueError("Window size must be greater than 0")
    """
    Send a file's contents via UDP using packetization.

    Args:
        host: Target host IP address
        port: Target port number
        filepath: Path to the file to send
        chunk_size: Size of each chunk in bytes
    """
    try:
        # Check if file exists
        if not os.path.exists(filepath):
            print(f"Error: File '{filepath}' not found")
            sys.exit(1)

        # Get file size and chunk count
        file_size = os.path.getsize(filepath)
        chunk_count = get_file_chunk_count(filepath, chunk_size)

        print(f"Sending file: {filepath}")
        print(f"File size: {file_size} bytes")
        print(f"Chunk size: {chunk_size} bytes")
        print(f"Number of packets: {chunk_count}")

        # Chunk the file
        chunks = chunk_file(filepath, chunk_size)

        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # Send START packet
            start_packet = create_start_packet(0)
            sock.sendto(start_packet.serialize(), (host, port))
            print("Sent START packet")

            # Set timeout for ACK
            sock.settimeout(INITIAL_RTO)

            # Send DATA packets reliably
                        # ============================================================
            # SLIDING WINDOW - GO-BACK-N
            # ============================================================

            # RTT/RTO state — persists across the whole transfer
            srtt = None
            rttvar = None
            current_rto = INITIAL_RTO

            total_retransmissions = 0
            retransmission_stats = {}

            # Create all DATA packets first
            packets = {}

            for seq_num, chunk in enumerate(chunks):
                packet = create_data_packet(seq_num, chunk)
                packets[seq_num] = packet.serialize()

            # Go-Back-N variables
            base = 0
            next_seq_num = 0

            print(f"Sliding window size: {window_size}")

            while base < chunk_count:

                # --------------------------------------------------------
                # Send packets while there is space in the window
                # --------------------------------------------------------
                while next_seq_num < base + window_size and next_seq_num < chunk_count:

                    sock.sendto(
                        packets[next_seq_num],
                        (host, port)
                    )

                    print(
                        f"Sent DATA packet {next_seq_num + 1}/{chunk_count} "
                        f"[window: {base}-{min(base + window_size - 1, chunk_count - 1)}]"
                    )

                    next_seq_num += 1

                # --------------------------------------------------------
                # Wait for ACK
                # --------------------------------------------------------
                sock.settimeout(current_rto)

                try:

                    while True:

                        ack_data, ack_addr = sock.recvfrom(65535)

                        ack = Packet.deserialize(ack_data)

                        if ack is None:
                            print("Received invalid ACK")
                            continue

                        if not ack.verify_integrity()[0]:
                            print("Received corrupted ACK")
                            continue

                        if ack.packet_type != PACKET_TYPE_ACK:
                            print("Received non-ACK packet")
                            continue

                        ack_seq = ack.sequence_number

                        # ACK for a packet already acknowledged
                        if ack_seq < base:
                            print(f"Ignoring duplicate ACK {ack_seq}")
                            continue

                        # ACK for a packet currently inside the window
                        if ack_seq >= base and ack_seq < next_seq_num:

                            print(f"Received ACK {ack_seq}")

                            # ------------------------------------------------
                            # Slide the window
                            # ------------------------------------------------
                            old_base = base
                            base = ack_seq + 1

                            print(
                                f"Window moved: "
                                f"{old_base}-{next_seq_num - 1} "
                                f"-> {base}-{min(base + window_size - 1, chunk_count - 1)}"
                            )

                            break

                        else:
                            print(
                                f"Ignoring ACK {ack_seq} "
                                f"(current window: {base}-{next_seq_num - 1})"
                            )

                except socket.timeout:

                    # ------------------------------------------------------
                    # TIMEOUT
                    # Go-Back-N: retransmit every unacknowledged packet
                    # ------------------------------------------------------

                    print(
                        f"\nTimeout! No ACK received for window "
                        f"starting at packet {base}"
                    )

                    retransmissions = 0

                    # Retransmit all packets currently in the window
                    for seq_num in range(base, next_seq_num):

                        retransmissions += 1
                        total_retransmissions += 1

                        retransmission_stats[seq_num] = (
                            retransmission_stats.get(seq_num, 0) + 1
                        )

                        print(
                            f"Retransmitting DATA packet {seq_num} "
                            f"(Go-Back-N)"
                        )

                        sock.sendto(
                            packets[seq_num],
                            (host, port)
                        )

                    # Exponential timeout backoff
                    current_rto = min(
                        current_rto * 2,
                        MAX_RTO
                    )

                    print(
                        f"New RTO after timeout: "
                        f"{current_rto:.3f}s"
                    )

                    # Check retransmission limit
                    if any(
                        count >= MAX_RETRANSMISSIONS
                        for count in retransmission_stats.values()
                    ):
                        raise RuntimeError(
                            "Maximum retransmissions reached"
                        )

            print("\nAll DATA packets acknowledged.")

            # ============================================================
            # END SLIDING WINDOW
            # ============================================================

            # Send END packet
            end_packet = create_end_packet(chunk_count)
            sock.sendto(end_packet.serialize(), (host, port))
            print("Sent END packet")
            print(f"File transfer completed: {chunk_count} packets sent")
            print(f"Total retransmissions: {total_retransmissions}")

            # --- Statistics summary ---
            print("\n--- Reliability Statistics ---")
            print(f"Total packets:          {chunk_count}")
            print(f"Total retransmissions:  {total_retransmissions}")
            if chunk_count > 0:
                rate = (total_retransmissions / chunk_count) * 100
                print(f"Retransmission rate:    {rate:.2f}%")
            if srtt is not None:
                print(f"Final SRTT:             {srtt*1000:.1f} ms")
                print(f"Final RTTVAR:           {rttvar*1000:.1f} ms")
                print(f"Final RTO:              {current_rto:.3f} s")

            stats_file = "retransmission_stats.csv"
            with open(stats_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["seq_num", "retransmissions"])
                for seq, count in retransmission_stats.items():
                    writer.writerow([seq, count])
            print(f"Per-packet stats saved to {stats_file}")

            return True
        
        finally:
            sock.close()

    except Exception as e:
        print(f"Error sending file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='UDP Sender - Send messages or files over UDP with packetization'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Target host IP address (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5001,
        help='Target port number (default: 5001)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f'Chunk size in bytes (default: {DEFAULT_CHUNK_SIZE})'
    )
    parser.add_argument(
    '--window-size',
    type=int,
    default=DEFAULT_WINDOW_SIZE,
    help=f'Sliding window size (default: {DEFAULT_WINDOW_SIZE})'
    )
    
    # Either message or file must be provided
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--message',
        help='Text message to send'
    )
    group.add_argument(
        '--file',
        help='Path to file to send'
    )
    
    args = parser.parse_args()
    
    if args.message:
        send_message(args.host, args.port, args.message)
    elif args.file:
        send_file(args.host, args.port, args.file, args.chunk_size, args.window_size)


if __name__ == '__main__':
    main()
