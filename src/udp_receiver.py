#!/usr/bin/env python3
# UDP Receiver - Week 2 Milestone (Packetization)

import socket
import argparse
import sys
import random
from packet import Packet, PACKET_TYPE_START, PACKET_TYPE_DATA, PACKET_TYPE_END, create_ack_packet
from file_utils import reconstruct_file_from_dict


def receive_packets(host: str, port: int, output_file: str = None) -> None:

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Storage for received packets keyed by sequence number
    received_packets = {}
    expected_packet_count = None
    transfer_active = False

    # Sliding-window / Go-Back-N state
    expected_seq = 0
    
    try:
        # Bind socket to host and port
        sock.bind((host, port))
        sock.settimeout(1.0)
        print(f"Listening on {host}:{port}")
        print("Waiting for packets... (Press Ctrl+C to stop)")
        
        while True:
            # Receive data
            try:
                data, addr = sock.recvfrom(65535)  # Max UDP datagram size
            except socket.timeout:
                continue   # no packet in the last 1s, just loop and check for Ctrl+C again
            
            # Deserialize packet
            packet = Packet.deserialize(data)
            
            if packet is None:
                print(f"Received invalid packet from {addr}")
                continue
            
            # Verify checksum
            is_valid, status = packet.verify_integrity()
            
            if not is_valid:
                print(f"Received CORRUPTED packet from {addr}: {packet}")
                continue
            
            # Handle different packet types
            if packet.packet_type == PACKET_TYPE_START:
                print(f"Received START packet from {addr}")

                received_packets.clear()
                expected_packet_count = None
                transfer_active = True

                 # Reset receiver's sliding-window state
                expected_seq = 0

                print(f"Receiver window initialized. Expected packet: {expected_seq}")

            elif packet.packet_type == PACKET_TYPE_DATA:

                if not transfer_active:
                    print(f"Received DATA packet before START from {addr}")
                    continue

                seq_num = packet.sequence_number
                                

                # ------------------------------------------------------------
                # Expected packet received
                # ------------------------------------------------------------
                if seq_num == expected_seq:

                    received_packets[seq_num] = packet

                    status, _ = packet.verify_integrity()

                    print(
                        f"Received DATA packet {seq_num} from {addr} "
                        f"({packet.payload_length} bytes) - {status}"
                    )

                    # ACK the correctly received packet
                    ack = create_ack_packet(seq_num)
                    sock.sendto(ack.serialize(), addr)

                    print(f"Sent ACK {seq_num} to {addr}")

                    # Move receiver window forward
                    expected_seq += 1

                    print(
                        f"Receiver window moved. "
                        f"Next expected packet: {expected_seq}"
                    )

                # ------------------------------------------------------------
                # Duplicate packet
                # ------------------------------------------------------------
                elif seq_num < expected_seq:

                    print(
                        f"Duplicate DATA packet {seq_num} received. "
                        f"Expected {expected_seq}"
                    )

                    # Re-send ACK for the duplicate
                    ack = create_ack_packet(seq_num)
                    sock.sendto(ack.serialize(), addr)

                    print(f"Re-sent ACK {seq_num} to {addr}")

                # ------------------------------------------------------------
                # Out-of-order packet
                # ------------------------------------------------------------
                else:

                    print(
                        f"Out-of-order DATA packet {seq_num} received. "
                        f"Expected {expected_seq}"
                    )

                    # Go-Back-N receiver does not accept this packet.
                    # ACK the last correctly received packet.
                    if expected_seq > 0:

                        last_ack = expected_seq - 1

                        ack = create_ack_packet(last_ack)
                        sock.sendto(ack.serialize(), addr)

                        print(
                            f"Sent duplicate ACK {last_ack} "
                            f"to request packet {expected_seq}"
                        )

                    else:
                        print(
                            "No valid ACK to send yet; "
                            "waiting for packet 0"
                        )
               

            elif packet.packet_type == PACKET_TYPE_END:
                print(f"Received END packet from {addr}")

                expected_packet_count = packet.sequence_number
                transfer_active = False

                # Reset receiver sliding-window state
                expected_seq = 0

                print(
                    f"Transfer complete. "
                    f"Expected packet count: {expected_packet_count}"
                )

                # Reconstruct file if output file specified
                if output_file and received_packets:
                    print(
                        f"Reconstructing file from "
                        f"{len(received_packets)} packets..."
                    )

                    success = reconstruct_file_from_dict(
                        received_packets,
                        output_file,
                        expected_packet_count
                    )

                    if success:
                        print(f"File reconstructed successfully: {output_file}")
                    else:
                        print("File reconstruction failed")

                    # Clear for next transfer
                    received_packets.clear()

                else:
                    print(
                        f"Received {len(received_packets)} data packets"
                    )

                    if not output_file:
                        print(
                            "(No output file specified - data not saved)"
                        )

                    received_packets.clear()

            else:
                print(
                    f"Received unknown packet type "
                    f"{packet.packet_type} from {addr}"
                )   
    except KeyboardInterrupt:
        print("\nReceiver stopped by user")
        if received_packets:
            print(f"Received {len(received_packets)} packets before stopping")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(
        description='UDP Receiver - Receive packetized messages or files over UDP'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host IP address to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5001,
        help='Port number to bind to (default: 5001)'
    )
    parser.add_argument(
        '--output',
        help='Optional file path to save reconstructed data'
    )
    
    args = parser.parse_args()
    
    receive_packets(args.host, args.port, args.output)


if __name__ == '__main__':
    main()
