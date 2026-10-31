# Reliable UDP File Transfer

A comprehensive implementation of reliable file transfer over UDP with sliding window protocol, network emulation, and performance analysis. This project demonstrates the complete lifecycle of building a reliable transport protocol from scratch, including packetization, acknowledgments, retransmissions, flow control, and experimental evaluation.

## 🎯 Project Overview

This project implements a reliable UDP file transfer protocol with the following key features:

- **Reliable Data Transfer**: ACK-based reliability with timeout-based retransmissions
- **Sliding Window Protocol**: Go-Back-N flow control with configurable window sizes
- **Network Emulation**: Software-based emulator simulating packet loss, delay, reordering, and corruption
- **Performance Analysis**: Automated benchmarking with comprehensive metrics and visualization
- **Packet Integrity**: CRC32 checksums for end-to-end data verification

## 📁 Project Structure

```
reliable-udp-file-transfer/
├── src/
│   ├── udp_sender.py           # UDP sender with reliability & sliding window
│   ├── udp_receiver.py         # UDP receiver with packet reconstruction
│   ├── packet.py               # Packet structure, serialization, and integrity
│   ├── checksum.py             # CRC32 checksum generation/verification
│   ├── file_utils.py           # File chunking and reconstruction
│   ├── network_emulator.py     # Network impairment simulation (loss, delay, etc.)
│   └── metrics.py              # Performance metrics collection and analysis
├── experiments/
│   ├── run_experiments.py      # Automated experiment runner
│   ├── plots.py                # Performance visualization and dashboard generation
│   ├── analyze_results.py      # Statistical analysis and report generation
│   ├── load_generator.py       # Test file generation and unreliable UDP baseline
│   └── test_emulator.py        # Network emulator unit tests
├── test-data/                  # Sample test files
├── results/
│   ├── csv/                    # Experiment results (CSV format)
│   ├── graphs/                 # Performance graphs and dashboards
│   └── performance_analysis_report.md
├── PACKET_FORMAT.md            # Packet format documentation
├── Worksplit.md                # Team member responsibilities
└── README.md
```

## 🚀 Setup and Execution

### 1. Clone the Repository

```bash
git clone https://github.com/som-cyber/reliable-udp-file-transfer.git
cd reliable-udp-file-transfer
```

### 2. Create and Activate Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Windows PowerShell:**
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not available, install the required packages manually:
```bash
pip install pandas matplotlib numpy
```

### 4. Run Tests

Verify the implementation with the test suite:

```bash
# Run emulator tests
python experiments/test_emulator.py

# Run reliability tests
python src/test_reliability.py
```

## 🎬 Presentation Demo 

```bash
# Run presentation experiments
python experiments/run_experiments.py --presentation

# Run with automatic dashboard opening
python experiments/run_experiments.py --presentation --open
```

This mode runs a minimal set of experiments for demonstration:
- 10KB test file
- Network delays: 0ms, 20ms, 50ms

### Generate Dashboard from Existing Results

```bash
python experiments/plots.py --csv results/csv/presentation_results.csv --presentation --open
```

## 📊 Experiment Modes

### Quick Mode (28 experiments, ~60 seconds)

For faster benchmarking with reduced parameter space:

```bash
python experiments/run_experiments.py --quick
```

Parameters:
- Loss rates: 0%, 5%, 10%
- Delays: 0ms, 20ms, 50ms
- Window sizes: 1, 4, 8
- File sizes: small, medium

### Full Mode (Comprehensive Evaluation)

For complete performance analysis:

```bash
python experiments/run_experiments.py
```

Parameters:
- Loss rates: 0%, 2%, 5%, 10%, 15%
- Delays: 0ms, 20ms, 50ms, 100ms
- Window sizes: 1, 2, 4, 8, 16
- File sizes: small, medium, large
- Additional: Reordering, corruption, unreliable UDP baseline

## 📈 Visualization and Analysis

### Generate All Graphs

```bash
python experiments/plots.py
```

This generates 8 performance graphs:
1. Loss vs Transfer Time
2. Loss vs Throughput
3. Window Size vs Throughput
4. Delay vs Completion Time
5. Loss vs Retransmissions
6. File Size vs Transfer Time
7. Unreliable vs Reliable UDP
8. Performance Dashboard

### Generate Analysis Report

```bash
python experiments/analyze_results.py
```

Generates a comprehensive markdown report with statistical analysis and key findings.

### Custom Graph Generation

```bash
# Generate from specific CSV
python experiments/plots.py --csv results/csv/raw_experiment_results.csv

# Specify output directory
python experiments/plots.py --output custom_graphs_dir

# Generate presentation dashboard only
python experiments/plots.py --presentation
```

## 📁 Generated Output Files

| File | Description |
|------|-------------|
| `results/csv/presentation_results.csv` | Six presentation experiment results |
| `results/graphs/presentation_dashboard.png` | Presentation dashboard with timing comparisons |
| `results/csv/raw_experiment_results.csv` | Full experiment results (all configurations) |
| `results/csv/summary_experiment_results.csv` | Aggregated statistics by configuration |
| `results/performance_analysis_report.md` | Comprehensive performance analysis report |
| `results/graphs/*.png` | Individual performance graphs |

## 📋 Protocol Specifications

### Packet Format

The implementation uses a fixed binary packet format:

| Field | Size | Description |
|-------|------|-------------|
| Type | 1 byte | START (0x01), DATA (0x02), END (0x03), ACK (0x04) |
| Sequence Number | 4 bytes | Packet sequence number (unsigned int) |
| Payload Length | 4 bytes | Length of payload in bytes |
| Checksum | 4 bytes | CRC32 checksum (header + payload) |
| Payload | Variable | File chunk data (max 1024 bytes) |

See `PACKET_FORMAT.md` for detailed specifications.

### Sliding Window Protocol

- **Go-Back-N**: Retransmits entire window on timeout
- **Window Size**: Configurable (1 = Stop-and-Wait, >1 = Sliding Window)
- **ACK Handling**: Cumulative acknowledgments
- **Timeout**: Dynamic based on RTT

### Network Emulator

The network emulator simulates real-world network conditions:
- **Packet Loss**: Configurable loss rate (0-100%)
- **Delay**: One-way propagation delay (0-1000ms)
- **Reordering**: Out-of-order delivery rate
- **Corruption**: Bit-level corruption simulation
- **Duplication**: Packet duplication rate

## 🧪 Test Coverage

All test cases have passed:

### Emulator Tests (`experiments/test_emulator.py`)
- ✅ Clean forwarding (no impairments)
- ✅ Packet loss simulation
- ✅ Delay simulation
- ✅ Reordering simulation
- ✅ Corruption simulation

### Reliability Tests (`src/test_reliability.py`)
- ✅ Out-of-order packet reconstruction
- ✅ Duplicate packet handling
- ✅ Corrupted packet rejection

## 👥 Module Owners

- **Somprakash**: UDP Communication & Packet Format
- **Abhipsa**: Reliability (ACKs, Retransmission)
- **Sahil**: Sliding Window / Flow Control
- **Protanu**: Network Simulation & Performance Testing

## 📝 Project Milestones

### Week 2: Packetization and Packet Format
- Fixed binary packet format
- Sequence numbers and checksums
- File chunking and reconstruction
- Basic UDP communication

### Week 3: Reliability Mechanisms
- ACK-based protocol
- Timeout-based retransmissions
- Checksum verification
- Error recovery

### Week 4: Sliding Window Flow Control
- Go-Back-N implementation
- Configurable window sizes
- Cumulative acknowledgments
- Performance optimization

### Week 5: Network Emulation and Testing
- Software network emulator
- Impairment simulation (loss, delay, reordering)
- Automated benchmarking suite
- Performance visualization

## 🎓 Key Findings

### Stop-and-Wait vs Sliding Window
- Sliding Window (W=4) achieves **2-5x throughput improvement** over Stop-and-Wait
- Performance gap increases with network delay
- Optimal window size depends on Bandwidth-Delay Product (BDP)

### Impact of Packet Loss
- Even 5% loss causes significant throughput degradation
- Go-Back-N retransmits entire window on loss
- Higher window sizes provide better throughput at moderate loss rates

### Network Delay Impact
- Stop-and-Wait throughput is bounded by `Packet Size / RTT`
- Sliding Window effectively utilizes higher delay links
- 100ms delay reduces Stop-and-Wait throughput by ~80%

### Reliable vs Unreliable UDP
- Plain UDP fails with any packet loss (100% corruption)
- Reliable UDP guarantees 100% data integrity
- Reliability overhead is acceptable for critical transfers

## 📖 References

- Tanenbaum, A. S., & Wetherall, D. J. (2011). *Computer Networks* (5th ed.). Prentice Hall.
- Kurose, J. F., & Ross, K. W. (2017). *Computer Networking: A Top-Down Approach* (7th ed.). Pearson.

## 📄 License

[To be determined]

---

**Recommended Command for Live Presentation:**
```bash
python experiments/run_experiments.py --presentation --open
```

This is the shortest demonstration workflow that completes in ~7 seconds and automatically opens the dashboard.
