# Reliable UDP File Transfer

A project implementing reliable file transfer over UDP with sliding window protocol.

## Project Structure

```
project-root/
├── src/
│   ├── udp_sender.py      # UDP sender with packetization
│   ├── udp_receiver.py    # UDP receiver with packet reconstruction
│   ├── packet.py          # Packet structure and serialization
│   ├── checksum.py        # CRC32 checksum generation/verification
│   └── file_utils.py      # File chunking and reconstruction
├── test-data/
│   ├── sample_small.txt   # Sample test file (323 bytes)
│   ├── single_chunk.txt   # Single-chunk test file (113 bytes)
│   └── large_file.txt     # Large test file (1778 bytes)
├── PACKET_FORMAT.md       # Packet format documentation
├── README.md
└── .gitignore
```

## Week 2 Milestone: Packetization and Packet Format

This milestone implements packet-based communication with sequence numbers, checksums, and file reconstruction.

### Prerequisites

- Python 3.x
- No third-party packages required (uses only standard library)

### Usage

#### Running the Receiver

Start the receiver first to listen for incoming packets:

```bash
python src/udp_receiver.py --output test-data/received.txt
```

The receiver will listen on `127.0.0.1:5001` by default and reconstruct received packets into the specified output file.

#### Running the Sender

In a separate terminal, run the sender:

```bash
# Send a simple text message
python src/udp_sender.py --message "Hello"

# Send a file with default chunk size (1024 bytes)
python src/udp_sender.py --file test-data/sample_small.txt

# Send a file with custom chunk size
python src/udp_sender.py --file test-data/large_file.txt --chunk-size 512
```

The sender will send to `127.0.0.1:5001` by default.

### Custom Host/Port

Both scripts accept optional `--host` and `--port` arguments:

```bash
python src/udp_receiver.py --host 127.0.0.1 --port 5001 --output test-data/received.txt
python src/udp_sender.py --host 127.0.0.1 --port 5001 --file test-data/sample_small.txt
```

### Packet Format

The implementation uses a fixed binary packet format:
- **Header**: 11 bytes (Type + Sequence Number + Payload Length + Checksum)
- **Payload**: Variable length (file chunk data)

See `PACKET_FORMAT.md` for detailed specifications.

### Expected Output

**For message transmission:**
- Sender creates a single DATA packet with the message
- Receiver prints packet information and status

**For file transmission:**
- Sender chunks file and sends START, DATA (multiple), and END packets
- Receiver stores packets by sequence number and reconstructs the file
- Reconstructed file is saved to the specified output path
- You can verify integrity by comparing files:
  ```bash
  diff test-data/original.txt test-data/received.txt
  ```

### Testing

All Week 2 test cases have passed:
- TC-1: Serialize/deserialize round trip
- TC-2: Single-chunk file transfer
- TC-3: Multi-chunk file transfer
- TC-4: Large file with many chunks
- TC-5: Out-of-order packet reconstruction
- TC-6: Corrupted packet detection

### Module Components

- **packet.py**: Packet class with serialize/deserialize methods
- **checksum.py**: CRC32 checksum generation and verification
- **file_utils.py**: File chunking and reconstruction utilities
- **udp_sender.py**: Updated sender with packetization
- **udp_receiver.py**: Updated receiver with packet reconstruction

## Module Owners

- Somprakash: UDP Communication & Packet Format
- Abhipsa: Reliability (ACKs, retransmission)
- Sahil: Sliding Window / Flow Control
- Protanu: Network Simulation & Performance Testing

## License

[To be determined]
