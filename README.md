# Reliable UDP File Transfer

A project implementing reliable file transfer over UDP with sliding window protocol.

## Project Structure

```
project-root/
├── src/
│   ├── udp_sender.py      # UDP sender implementation
│   └── udp_receiver.py    # UDP receiver implementation
├── test-data/
│   └── sample_small.txt   # Sample test file
├── README.md
└── .gitignore
```

## Week 1 Milestone: Basic UDP Communication

This milestone implements basic UDP communication between a sender and receiver.

### Prerequisites

- Python 3.x
- No third-party packages required (uses only standard library)

### Usage

#### Running the Receiver

Start the receiver first to listen for incoming datagrams:

```bash
python src/udp_receiver.py
```

The receiver will listen on `127.0.0.1:5001` by default.

#### Running the Sender

In a separate terminal, run the sender:

```bash
# Send a simple text message
python src/udp_sender.py --message "Hello"

# Send a file
python src/udp_sender.py --file test-data/sample_small.txt
```

The sender will send to `127.0.0.1:5001` by default.

### Custom Host/Port

Both scripts accept optional `--host` and `--port` arguments:

```bash
python src/udp_receiver.py --host 127.0.0.1 --port 5001
python src/udp_sender.py --host 127.0.0.1 --port 5001 --message "Hello"
```

### Expected Output

**For message transmission:**
- Receiver prints: `Received: Hello`

**For file transmission:**
- Receiver writes received bytes to `test-data/sample_small.received`
- You can verify integrity by comparing files:
  ```bash
  diff test-data/sample_small.txt test-data/sample_small.received
  ```

### Testing

See the PRD for detailed test cases. Basic tests include:
- TC-1: Send "Hello" message
- TC-2: Send empty message
- TC-3: Send small file (<1 KB)
- TC-4: Sender runs before receiver (expected: datagram silently dropped)

## Module Owners

- Somprakash: UDP Communication & Packet Format
- Abhipsa: Reliability (ACKs, retransmission)
- Sahil: Sliding Window / Flow Control
- Protanu: Network Simulation & Performance Testing

## License

[To be determined]
