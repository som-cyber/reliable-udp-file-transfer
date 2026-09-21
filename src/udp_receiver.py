#!/usr/bin/env python3
"""UDP Receiver - Listens for incoming UDP datagrams and displays or saves them."""

import argparse
from pathlib import Path
import socket


def receive_messages(host: str, port: int, output_file: str = None) -> None:
    """Listens for incoming UDP datagrams continuously until interrupted."""
    # Create a UDP socket and automatically close it when finished
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            # Bind the socket to the chosen IP address and port
            sock.bind((host, port))
            print(f"Listening on {host}:{port}")
            print("Waiting for datagrams... (Press Ctrl+C to stop)")

            # Keep listening for messages indefinitely
            while True:
                # Receive up to 65,535 bytes (maximum size of a UDP datagram)
                data, addr = sock.recvfrom(65535)

                # Try to decode the received raw bytes into readable text
                try:
                    message = data.decode("utf-8")
                    print(f"Received from {addr}: {message}")
                except UnicodeDecodeError:
                    # If decoding fails, the data is binary (e.g., a file)
                    print(f"Received {len(data)} bytes from {addr}")
                    if not output_file:
                        print(
                            "(Binary data - use --output to save to file)"
                        )

                # Save the raw data to a file if an output path was provided
                if output_file:
                    Path(output_file).write_bytes(data)
                    print(f"Saved to: {output_file}")

        except KeyboardInterrupt:
            # Gracefully handle Ctrl+C exit without dumping stack traces
            print("\nReceiver stopped by user")
        except Exception as e:
            print(f"Error: {e}")


def main():
    # Set up command-line arguments parser
    parser = argparse.ArgumentParser(
        description="UDP Receiver - Receive messages or files over UDP"
    )

    # Define arguments with default values
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host IP address to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Port number to bind to (default: 5001)",
    )
    parser.add_argument(
        "--output",
        help="Optional file path to save received data",
    )

    # Parse inputs given in command line
    args = parser.parse_args()

    # Start listening for messages
    receive_messages(args.host, args.port, args.output)


# Run main function when executing the script directly
if __name__ == "__main__":
    main()