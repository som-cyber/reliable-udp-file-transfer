#!/usr/bin/env python3

import os

from packet import Packet, PACKET_TYPE_DATA

# Default size of each chunk
DEFAULT_CHUNK_SIZE = 1024

# Split a file into small pieces
def chunk_file(filepath, chunk_size=DEFAULT_CHUNK_SIZE):

    chunks = []

    # Open the file in binary mode
    with open(filepath, "rb") as file:

        while True:

            # Read one chunk
            chunk = file.read(chunk_size)

            # Stop when there is nothing left to read
            if not chunk:
                break

            # Add the chunk to the list
            chunks.append(chunk)

    return chunks


# Rebuild a file using packet objects
def reconstruct_file_from_packets(packets, output_filepath):

    # Keep only DATA packets
    data_packets = []

    for packet in packets:
        if packet.packet_type == PACKET_TYPE_DATA:
            data_packets.append(packet)

    # If there are no DATA packets, stop
    if not data_packets:
        return False

    # Sort packets using their sequence number
    data_packets.sort(key=lambda packet: packet.sequence_number)

    # Check for missing sequence numbers
    for i in range(len(data_packets) - 1):

        current = data_packets[i].sequence_number
        next_packet = data_packets[i + 1].sequence_number

        if next_packet != current + 1:
            print("Warning: Missing packet:", current, "->", next_packet)
            # Return False to indicate reconstruction failed due to missing packets
            return False
    
    # Check for duplicate sequence numbers
    sequence_numbers = [p.sequence_number for p in data_packets]
    if len(sequence_numbers) != len(set(sequence_numbers)):
        print("Warning: Duplicate sequence numbers detected")
        # Return False to indicate reconstruction failed due to duplicate packets
        return False

    # Join all packet data together
    file_data = b""

    for packet in data_packets:
        file_data += packet.payload

    # Write the data to the output file
    with open(output_filepath, "wb") as file:
        file.write(file_data)

    return True


# Rebuild a file using a dictionary of packets
def reconstruct_file_from_dict(packet_dict, output_filepath, expected_packet_count=None):

    # If the dictionary is empty, stop
    if not packet_dict:
        return False

    # Check the number of packets if expected count is given
    if expected_packet_count is not None:

        if len(packet_dict) != expected_packet_count:
            print( "Warning: Expected", expected_packet_count, "packets, got", len(packet_dict) )

    # Sort packets using their sequence numbers
    sorted_packets = []

    for sequence in sorted(packet_dict.keys()):
        sorted_packets.append(packet_dict[sequence])

    # Check for missing sequence numbers
    for i in range(len(sorted_packets) - 1):

        current = sorted_packets[i].sequence_number
        next_packet = sorted_packets[i + 1].sequence_number

        if next_packet != current + 1:
            print("Warning: Missing packet:", current, "->", next_packet)

    # Join all packet data together
    file_data = b""

    for packet in sorted_packets:
        file_data += packet.payload

    # Write the data to the output file
    with open(output_filepath, "wb") as file:
        file.write(file_data)

    return True


# Find how many chunks a file will have
def get_file_chunk_count(filepath, chunk_size=DEFAULT_CHUNK_SIZE):

    # Get the file size
    file_size = os.path.getsize(filepath)

    # Calculate the number of chunks
    return (file_size + chunk_size - 1) // chunk_size


# Main program
if __name__ == "__main__":

    print("Testing file chunking...")

    # Name of the test file
    test_file = "test_chunking.txt"

    # Data for the test file
    test_data = b"This is a test file for chunking. " * 20

    # Create the test file
    with open(test_file, "wb") as file:
        file.write(test_data)

    # Split the file into chunks of 100 bytes
    chunks = chunk_file(test_file, 100)

    print("File split into", len(chunks), "chunks")

    # Show the size of each chunk
    for i, chunk in enumerate(chunks):
        print("Chunk", i, ":", len(chunk), "bytes")

    # Join the chunks back together
    reconstructed_data = b""

    for chunk in chunks:
        reconstructed_data += chunk

    # Check if reconstructed data is the same as original data
    print(
        "Reconstructed data matches original:",
        reconstructed_data == test_data
    )

    # Delete the test file
    os.remove(test_file)

    print("Test completed!")
