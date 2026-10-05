#!/usr/bin/env python3
"""
UDP Sender - Week 2 Milestone (Packetization)

A UDP sender that sends text messages or file contents using packetization.
This implementation includes chunking, sequence numbering, and checksums.
"""

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


def send_file(host: str, port: int, filepath: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
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
            # RTT/RTO state — persists across all packets in this transfer
            srtt = None
            rttvar = None
            current_rto = INITIAL_RTO

            total_retransmissions = 0
            retransmission_stats = {}   # seq_num -> number of retransmissions for that packet

            for seq_num, chunk in enumerate(chunks):
                packet = create_data_packet(seq_num, chunk)
                serialized = packet.serialize()

                retransmissions = 0
                attempt_rto = current_rto   # starts at the latest smoothed estimate

                while True:
                    send_time = time.time()        # timestamp THIS specific attempt
                    sock.sendto(serialized, (host, port))
                    print(
                        f"Sent DATA packet {seq_num + 1}/{chunk_count} "
                        f"({len(chunk)} bytes) [rto={attempt_rto:.3f}s]"
                    )

                    sock.settimeout(attempt_rto)

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

                            if ack.sequence_number != seq_num:
                                print(f"Ignoring stale/duplicate ACK {ack.sequence_number} "
                                      f"(expecting {seq_num})")
                                continue

                            # Correct ACK received
                            print(f"Received ACK {seq_num}")

                            # --- Karn's Algorithm ---
                            # Only trust this RTT sample if the packet was NOT retransmitted.
                            if retransmissions == 0:
                                sample_rtt = time.time() - send_time

                                if srtt is None:
                                    # First ever sample
                                    srtt = sample_rtt
                                    rttvar = sample_rtt / 2
                                else:
                                    rttvar = (1 - BETA) * rttvar + BETA * abs(srtt - sample_rtt)
                                    srtt = (1 - ALPHA) * srtt + ALPHA * sample_rtt

                                current_rto = srtt + K * rttvar
                                current_rto = max(MIN_RTO, min(current_rto, MAX_RTO))

                                print(f"  RTT sample={sample_rtt*1000:.1f}ms  "
                                    f"SRTT={srtt*1000:.1f}ms  RTTVAR={rttvar*1000:.1f}ms  "
                                      f"new RTO={current_rto:.3f}s")
                            else:
                                print(f"  (packet was retransmitted {retransmissions}x — "
                                      f"RTT sample discarded per Karn's Algorithm)")

                            break  # exit the ACK-reading loop

                        break  # exit the retry loop — this packet is done

                    except socket.timeout:
                        retransmissions += 1
                        total_retransmissions += 1

                        # Karn's Algorithm: back off the timeout exponentially on retry,
                        # but don't touch the smoothed current_rto estimate
                        attempt_rto = min(attempt_rto * 2, MAX_RTO)

                        print(f"Timeout waiting for ACK {seq_num}")
                        print(f"Retransmitting DATA packet {seq_num} "
                              f"(attempt {retransmissions}/{MAX_RETRANSMISSIONS}, "
                              f"next rto={attempt_rto:.3f}s)")

                        if retransmissions >= MAX_RETRANSMISSIONS:
                            print(f"Maximum retransmissions reached for DATA packet {seq_num}")
                            raise RuntimeError(
                                f"Maximum retransmissions reached for packet {seq_num}"
                                )

                retransmission_stats[seq_num] = retransmissions

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
        send_file(args.host, args.port, args.file, args.chunk_size)


if __name__ == '__main__':
    main()
