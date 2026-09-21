#!/usr/bin/env python3
"""UDP Sender - Sends a text message or file over a network using UDP."""

import argparse
from pathlib import Path
import socket
import sys


def send_bytes(host: str, port: int, data: bytes) -> None:
    """Helper function to open a socket, send raw data, and automatically close the socket."""
    # Create a UDP socket (SOCK_DGRAM means UDP)
    # Using 'with' guarantees the socket safely closes when done
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(data, (host, port))


def send_message(host: str, port: int, message: str) -> None:
    """Encodes a text string to bytes and sends it over UDP."""
    # Convert text string to raw bytes (UDP only sends bytes)
    data = message.encode("utf-8")

    # Send the data over the network
    send_bytes(host, port, data)

    # Print success details
    print(f"Sent message to {host}:{port}")
    print(f"Message: {message}")


def send_file(host: str, port: int, filepath: str) -> None:
    """Reads a file's contents as bytes and sends it over UDP."""
    # Read the whole file directly as bytes
    try:
        data = Path(filepath).read_bytes()
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found")
        sys.exit(1)  # Stop the program if the file doesn't exist
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)  # Stop the program if reading fails

    # Send the file bytes over the network
    send_bytes(host, port, data)

    # Print success details
    print(f"Sent file to {host}:{port}")
    print(f"File: {filepath}")
    print(f"Size: {len(data)} bytes")


def main():
    # Set up command-line arguments parser
    parser = argparse.ArgumentParser(
        description="UDP Sender - Send messages or files over UDP"
    )

    # Define optional flags with default values
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Target IP address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Target port number (default: 5001)",
    )

    # Ensure the user provides EITHER --message OR --file, but not both
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--message", help="Text message to send")
    group.add_argument("--file", help="Path to file to send")

    # Parse arguments passed from terminal
    args = parser.parse_args()

    # Route request depending on what the user asked to send
    if args.message:
        send_message(args.host, args.port, args.message)
    elif args.file:
        send_file(args.host, args.port, args.file)


# Run the main function when script is executed directly
if __name__ == "__main__":
    main()