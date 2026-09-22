#!/usr/bin/env python3

import zlib

# This function creates a checksum for the data
def generate_checksum(data):
    return zlib.crc32(data) & 0xFFFFFFFF


# This function checks if the checksum is correct
def verify_checksum(data, expected_checksum):

    # Generate a new checksum from the data
    actual_checksum = generate_checksum(data)

    # Compare the new checksum with the expected checksum
    if actual_checksum == expected_checksum:
        return True, "VALID"
    else:
        return False, "CORRUPTED"


# Program starts here
if __name__ == "__main__":

    # Data to be checked
    data = b"Hello, World!"

    # Generate checksum for the data
    checksum = generate_checksum(data)

    print("Data:", data)
    print("Checksum:", checksum)

    # Check with the correct checksum
    valid, status = verify_checksum(data, checksum)
    print("Verification (correct):", status)

    # Check with a wrong checksum
    valid, status = verify_checksum(data, checksum + 1)
    print("Verification (incorrect):", status)
