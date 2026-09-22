#!/usr/bin/env python3
"""
UDP Receiver - Week 2 Milestone (Packetization)

A UDP receiver that handles packetized data with sequence numbers,
checksums, and file reconstruction supporting out-of-order arrival.
"""

import socket
import argparse
import sys
from packet import Packet, PACKET_TYPE_START, PACKET_TYPE_DATA, PACKET_TYPE_END
from file_utils import reconstruct_file_from_dict


def receive_packets(host: str, port: int, output_file: str = None) -> None:

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Storage for received packets keyed by sequence number
    received_packets = {}
    expected_packet_count = None
    transfer_active = False
    
    try:
        # Bind socket to host and port
        sock.bind((host, port))
        print(f"Listening on {host}:{port}")
        print("Waiting for packets... (Press Ctrl+C to stop)")
        
        while True:
            # Receive data
            data, addr = sock.recvfrom(65535)  # Max UDP datagram size
            
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
                
            elif packet.packet_type == PACKET_TYPE_DATA:
                if not transfer_active:
                    print(f"Received DATA packet before START from {addr}")
                    continue
                    
                # Store packet by sequence number
                received_packets[packet.sequence_number] = packet
                print(f"Received DATA packet {packet.sequence_number} from {addr} " f"({packet.payload_length} bytes) - {status}")
                
            elif packet.packet_type == PACKET_TYPE_END:
                print(f"Received END packet from {addr}")
                expected_packet_count = packet.sequence_number
                transfer_active = False
                
                # Reconstruct file if output file specified
                if output_file and received_packets:
                    print(f"Reconstructing file from {len(received_packets)} packets...")
                    success = reconstruct_file_from_dict(
                        received_packets, 
                        output_file, 
                        expected_packet_count
                    )
                    
                    if success:
                        print(f"File reconstructed successfully: {output_file}")
                    else:
                        print(f"File reconstruction failed")
                    
                    # Clear for next transfer
                    received_packets.clear()
                else:
                    print(f"Received {len(received_packets)} data packets")
                    if not output_file:
                        print("(No output file specified - data not saved)")
                    
                    received_packets.clear()
            
            else:
                print(f"Received unknown packet type {packet.packet_type} from {addr}")
                
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
