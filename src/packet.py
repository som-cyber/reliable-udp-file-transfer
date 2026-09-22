#!/usr/bin/env python3

import struct
from checksum import generate_checksum, verify_checksum

# Packet types
PACKET_TYPE_DATA = 1
PACKET_TYPE_START = 2
PACKET_TYPE_END = 3


# Header contains:
# 1 byte  -> packet type
# 4 bytes -> sequence number
# 2 bytes -> payload length
# 4 bytes -> checksum
HEADER_FORMAT = "!BIHI"

# Find the size of the header
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


# Packet class
class Packet:

    # Create a packet
    def __init__(self, packet_type, sequence_number, payload):

        self.packet_type = packet_type
        self.sequence_number = sequence_number
        self.payload = payload

        # Find the size of the payload
        self.payload_length = len(payload)

        # Create checksum for the payload
        self.checksum = generate_checksum(payload)

    # Convert the packet into bytes
    def serialize(self):

        # Create the header
        header = struct.pack(
            HEADER_FORMAT,
            self.packet_type,
            self.sequence_number,
            self.payload_length,
            self.checksum
        )

        # Return header + payload
        return header + self.payload

    # Convert bytes back into a Packet
    @staticmethod
    def deserialize(data):

        # If data is smaller than the header, packet is invalid
        if len(data) < HEADER_SIZE:
            return None

        # Get the header
        header = data[:HEADER_SIZE]

        # Read values from the header
        packet_type, sequence_number, payload_length, checksum = struct.unpack(
            HEADER_FORMAT, header
        )

        # Get the payload
        payload = data[HEADER_SIZE:HEADER_SIZE + payload_length]

        # Check if payload size is correct
        if len(payload) != payload_length:
            return None

        # Create a packet using the received information
        packet = Packet(packet_type, sequence_number, payload)

        # Use the checksum received from the packet
        packet.checksum = checksum

        return packet

    # Check whether the packet data is valid
    def verify_integrity(self):

        return verify_checksum(self.payload, self.checksum)

    # Display packet information
    def __repr__(self):

        # Give names to packet types
        type_names = {
            PACKET_TYPE_START: "START",
            PACKET_TYPE_DATA: "DATA",
            PACKET_TYPE_END: "END"
        }

        # Get the packet type name
        type_name = type_names.get(
            self.packet_type,
            f"UNKNOWN({self.packet_type})"
        )

        return (
            f"Packet(type={type_name}, "
            f"seq={self.sequence_number}, "
            f"payload_len={self.payload_length}, "
            f"checksum={self.checksum})"
        )


# Create a START packet
def create_start_packet(sequence_number=0):
    return Packet(PACKET_TYPE_START, sequence_number, b"")


# Create a DATA packet
def create_data_packet(sequence_number, payload):
    return Packet(PACKET_TYPE_DATA, sequence_number, payload)


# Create an END packet
def create_end_packet(sequence_number):
    return Packet(PACKET_TYPE_END, sequence_number, b"")


# Main program
if __name__ == "__main__":

    print("Testing packet serialization/deserialization...")

    # Create a data packet
    original = create_data_packet(5, b"Hello, World!")
    print("Original packet:", original)

    # Convert packet into bytes
    serialized = original.serialize()
    print("Serialized size:", len(serialized), "bytes")

    # Convert bytes back into a packet
    deserialized = Packet.deserialize(serialized)
    print("Deserialized packet:", deserialized)

    # Check if the packet is valid
    valid, status = deserialized.verify_integrity()
    print("Integrity check:", status)

    # Change the last byte to corrupt the data
    corrupted = serialized[:-1] + bytes([serialized[-1] ^ 0xFF])

    # Convert corrupted data back into a packet
    corrupted_packet = Packet.deserialize(corrupted)

    # Check the corrupted packet
    valid, status = corrupted_packet.verify_integrity()
    print("Corrupted packet integrity:", status)
