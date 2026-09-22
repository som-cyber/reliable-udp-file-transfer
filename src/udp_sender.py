#!/usr/bin/env python3
"""
UDP Sender - Week 2 Milestone (Packetization)

A UDP sender that sends text messages or file contents using packetization.
This implementation includes chunking, sequence numbering, and checksums.
"""

import socket
import argparse
import sys
import os
from packet import create_start_packet, create_data_packet, create_end_packet
from file_utils import chunk_file, get_file_chunk_count, DEFAULT_CHUNK_SIZE


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
            print(f"Sent START packet")
            
            # Send DATA packets
            for seq_num, chunk in enumerate(chunks):
                packet = create_data_packet(seq_num, chunk)
                serialized = packet.serialize()
                sock.sendto(serialized, (host, port))
                print(f"Sent DATA packet {seq_num + 1}/{chunk_count} ({len(chunk)} bytes)")
            
            # Send END packet
            end_packet = create_end_packet(chunk_count)
            sock.sendto(end_packet.serialize(), (host, port))
            print(f"Sent END packet")
            
            print(f"File transfer completed: {chunk_count} packets sent")
            
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
