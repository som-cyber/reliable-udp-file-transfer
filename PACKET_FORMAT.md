# Packet Format Documentation

## Overview
This document describes the binary packet format used for the Reliable UDP File Transfer project. All sender and receiver implementations must use this exact format to ensure compatibility.

## Packet Structure

### Binary Layout
```
+------------------+
| Packet Type      |   1 byte  (unsigned char)
+------------------+
| Sequence Number  |   4 bytes (unsigned int, big-endian)
+------------------+
| Payload Length   |   2 bytes (unsigned short, big-endian)
+------------------+
| Checksum         |   4 bytes (CRC32, big-endian)
+------------------+
| Payload / Data   |   variable length (0-65535 bytes)
+------------------+
```

**Total Header Size: 11 bytes**

### Field Specifications

#### Packet Type (1 byte)
- **Type**: `unsigned char`
- **Values**:
  - `1` = DATA packet (contains file chunk)
  - `2` = START packet (signals beginning of file transfer)
  - `3` = END packet (signals end of file transfer)
- **Extensibility**: Values 4-255 are reserved for future use (e.g., ACK packets)

#### Sequence Number (4 bytes)
- **Type**: `unsigned int` (big-endian)
- **Purpose**: Identifies the order of packets for reconstruction
- **Range**: 0 to 4,294,967,295
- **Usage**: 
  - DATA packets: Sequential numbering starting from 0
  - START packet: Always 0
  - END packet: Contains total number of DATA packets sent

#### Payload Length (2 bytes)
- **Type**: `unsigned short` (big-endian)
- **Purpose**: Length of the payload in bytes
- **Range**: 0 to 65,535
- **Note**: Does not include header size

#### Checksum (4 bytes)
- **Type**: `unsigned int` (big-endian)
- **Algorithm**: CRC32
- **Purpose**: Detect corrupted packets
- **Calculation**: CRC32 of the payload bytes only
- **Verification**: Receiver recalculates CRC32 and compares with this field

#### Payload (variable)
- **Type**: Raw bytes
- **Length**: 0 to 65,535 bytes (specified by Payload Length field)
- **Content**:
  - DATA packets: File chunk data
  - START/END packets: Empty (0 bytes)

## Serialization Format

### Python struct Format
```python
HEADER_FORMAT = "!BIHI"
HEADER_SIZE = 11  # struct.calcsize(HEADER_FORMAT)
```

Where:
- `!` = network byte order (big-endian)
- `B` = unsigned char (1 byte) - Packet Type
- `I` = unsigned int (4 bytes) - Sequence Number
- `H` = unsigned short (2 bytes) - Payload Length
- `I` = unsigned int (4 bytes) - Checksum

### Serialization Example
```python
import struct

# Serialize header
header = struct.pack(
    "!BIHI",
    packet_type,      # 1 byte
    sequence_number,  # 4 bytes
    payload_length,   # 2 bytes
    checksum          # 4 bytes
)

# Full packet = header + payload
serialized_packet = header + payload
```

### Deserialization Example
```python
# Unpack header
header = data[:11]
packet_type, sequence_number, payload_length, checksum = struct.unpack("!BIHI", header)

# Extract payload
payload = data[11:11 + payload_length]
```

## Implementation Files

### Core Modules
- **`src/packet.py`**: Packet class with serialize/deserialize methods
- **`src/checksum.py`**: CRC32 checksum generation and verification
- **`src/file_utils.py`**: File chunking and reconstruction utilities

### Configuration
- **Default Chunk Size**: 1024 bytes (configurable via `--chunk-size` argument)
- **Maximum UDP Payload**: 65,535 bytes (standard UDP limit)

## Usage Examples

### Creating a DATA Packet
```python
from packet import create_data_packet

# Create packet with sequence number 5 and payload data
packet = create_data_packet(5, b"file chunk data")
serialized = packet.serialize()
```

### Creating START/END Packets
```python
from packet import create_start_packet, create_end_packet

# Start packet (signals beginning of transfer)
start = create_start_packet(0)

# End packet (signals completion, contains total packet count)
end = create_end_packet(total_packet_count)
```

### Verifying Packet Integrity
```python
# Deserialize received data
packet = Packet.deserialize(received_data)

# Verify checksum
is_valid, status = packet.verify_integrity()
if status == "CORRUPTED":
    # Handle corrupted packet
    pass
```

## Coordination Notes

### For Abhipsa (Reliability Module)
- The packet format includes sequence numbers for ACK/retransmission logic
- Checksum field is already implemented for corruption detection
- Packet Type field has reserved values (4-255) for future ACK packet types
- Current implementation: corrupted packets are flagged but not retransmitted (your module will handle this)

### For Sahil (Sliding Window Module)
- Sequence numbers are sequential starting from 0
- Chunk size is configurable (default 1024 bytes)
- Window size should be based on chunk size and network conditions
- The receiver stores packets by sequence number, supporting out-of-order delivery

### For Protanu (Network Simulation Module)
- Packet format is fixed-size header + variable payload
- Total packet size = 11 bytes header + payload length
- Maximum packet size = 11 + 65,535 = 65,546 bytes
- Can simulate loss, delay, reordering at the packet level

## Testing

All test cases from Week 2 milestone have passed:
- TC-1: Serialize/deserialize round trip
- TC-2: Single-chunk file transfer
- TC-3: Multi-chunk file transfer
- TC-4: Large file with many chunks
- TC-5: Out-of-order packet reconstruction
- TC-6: Corrupted packet detection

## Version History
- **v1.0** (Week 2): Initial packet format with basic fields
