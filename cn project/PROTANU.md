# Protanu — Network Emulator & Performance Analysis

## 1. My Role

**Main responsibility:** Build the network emulator, run controlled experiments, collect performance metrics, generate graphs, and analyze the results of the Reliable UDP File Transfer project.

The main flow of my work is:

```text
Sender
   ↓
Network Emulator
   ↓
Receiver
   ↓
Metrics / Results
   ↓
Graphs + Performance Analysis
```

My work should test how the reliable UDP system behaves under different network conditions.

---

## 2. What I Actually Need to Build

### A. Network Emulator

Create a software layer between the sender and receiver that can simulate unreliable network conditions.

The emulator must support:

- Packet loss
- Artificial delay
- Packet reordering
- Configurable network conditions

**Optional:** Packet duplication. This is not a priority and should only be added if the main system is already stable.

### B. Packet-Loss Simulation

Allow the experiment to specify a packet-loss probability.

Example values:

```text
0%
2%
5%
10%
15%
```

The emulator should randomly drop packets according to the configured loss rate.

### C. Delay Simulation

Add configurable artificial delay to packets.

Example values:

```text
0 ms
20 ms
50 ms
100 ms
```

### D. Packet-Reordering Simulation

Change the order of selected packets before forwarding them to the receiver.

This is used to test whether the team's receiver/reliability logic correctly handles out-of-order packets.

### E. Experiment Runner

Create scripts that automatically:

1. Set the required network conditions.
2. Start/run the file transfer.
3. Collect performance data.
4. Save the results as CSV.
5. Repeat the experiment for different configurations.

Experiment variables include:

- File size
- Packet-loss rate
- Network delay
- Window size
- Number of transfers

### F. Performance Metrics

Collect at least:

- Total transfer time
- Average latency
- Throughput
- Packets sent
- Packets received
- Retransmission count
- Packet-loss rate
- File completion status
- Checksum verification result

### G. Graphs

Generate graphs for:

- Packet loss vs. transfer time
- Packet loss vs. throughput
- Window size vs. throughput
- Delay vs. completion time
- Packet loss vs. retransmission count
- File size vs. transfer time
- UDP without reliability vs. Reliable UDP

### H. Result Analysis

After running experiments:

- Organize the results.
- Compare different network conditions.
- Compare Stop-and-Wait and Sliding Window.
- Explain how packet loss and delay affect performance.
- Prepare tables and graphs for the final report.
- Prepare the performance-analysis section for the presentation/viva.

---

## 3. Tech Stack — Only What I Need

### Required

| Technology | Why I need it |
|---|---|
| **Python 3** | Implement the network emulator and experiment scripts |
| **Python `socket` API** | Send/forward UDP packets through the emulator |
| **Python `random`** | Random packet-loss and reordering simulation |
| **Python `time`** | Delay simulation and transfer-time measurement |
| **Pandas** | Store and analyze experiment results |
| **NumPy** | Numerical calculations for performance analysis |
| **Matplotlib** | Generate performance graphs |
| **CSV** | Store experiment results |
| **Linux/Ubuntu** | Run the UDP project and experiments |
| **Git/GitHub** | Version control and submit my weekly work |

### Useful Python modules

```python
socket
random
time
csv
subprocess
os
```

### Not necessary for my main part

I do **not** need to focus on:

- Flask/Django
- React
- TensorFlow
- Database systems
- Docker
- Cloud platforms
- Advanced networking frameworks

The project is primarily a **Python UDP + network simulation + performance analysis** task.

---

## 4. Suggested Files for My Part

```text
experiments/
├── network_emulator.py
├── load_generator.py
├── metrics.py
├── run_experiments.py
├── analyze_results.py
└── plots.py

results/
├── csv/
└── graphs/
```

### `network_emulator.py`

Responsible for:

- Receiving packets from the sender
- Applying configured packet loss
- Applying delay
- Reordering packets
- Forwarding packets to the receiver

### `metrics.py`

Responsible for:

- Transfer time
- Throughput
- Packet counts
- Retransmission count
- Packet-loss rate
- Completion status
- Checksum result

### `run_experiments.py`

Responsible for:

- Running experiments automatically
- Trying different loss rates
- Trying different delays
- Trying different window sizes
- Running multiple file sizes
- Saving results

### `analyze_results.py`

Responsible for:

- Loading CSV results
- Calculating useful statistics
- Comparing experiments
- Producing summary tables

### `plots.py`

Responsible for:

- Creating Matplotlib graphs
- Saving graphs into `results/graphs/`

### `load_generator.py`

Responsible for:

- Repeated file-transfer tests
- Different file sizes
- Multiple experiment runs

---

# 5. Week-by-Week Work

## Week 1 — Setup and Measurement

### Do:

- Set up the GitHub repository/project folders.
- Prepare README/contribution rules if assigned.
- Create the first test script.
- Create a basic transfer-time measurement method.
- Define the metrics that will be collected later.

### Deliverable:

- Initial experiment structure
- Basic transfer-time measurement
- Defined performance metrics

---

## Week 2 — Testing + Experiment Design

### Do:

- Create file-transfer test cases.
- Measure transfer time for different file sizes.
- Create the basic CSV result format.
- Design the network emulator.

### Deliverable:

- Test cases
- Initial CSV format
- Network-emulator design

---

## Week 3 — Basic Packet-Loss Emulator

### Do:

- Add packet-loss simulation.
- Start with small loss rates.
- Test the reliable UDP system under packet loss.
- Record transfer completion and retransmission counts.
- Create initial performance graphs.

### Deliverable:

- Basic packet-loss emulator
- Initial reliability/performance results

---

## Week 4 — Baseline Measurements

### Do:

Measure the stable Stop-and-Wait system.

Record:

- Transfer time
- Throughput
- Retransmission count
- Completion status

Compare:

```text
No packet loss
       vs.
Packet loss
```

Generate the first baseline graphs.

### Deliverable:

- Baseline dataset
- Initial graphs
- Performance test report

---

## Week 5 — Sliding Window Comparison

### Do:

- Compare Stop-and-Wait with Sliding Window.
- Test different window sizes.
- Record throughput and completion time.
- Check performance under packet loss.
- Prepare comparison graphs.

### Deliverable:

- Window-size experiment results
- Stop-and-Wait vs Sliding Window comparison

---

## Week 6 — Complete Network Emulator

### Do:

Implement:

- Packet-loss simulation
- Delay simulation
- Reordering simulation

Then:

- Connect the emulator between sender and receiver.
- Create automated experiment scripts.
- Test the complete integrated system.

### Deliverable:

- Working network emulator
- Automated experiments
- Loss/delay/reordering test results

---

## Week 7 — Main Performance Experiments

This is the main data-collection week.

### Run experiments using different:

**File sizes**

```text
Small
Medium
Large
```

**Packet-loss rates**

```text
0%
2%
5%
10%
15%
```

**Delay values**

```text
0 ms
20 ms
50 ms
100 ms
```

**Window sizes**

Use the window sizes supported by the team's sliding-window implementation.

### Do:

- Automate the experiments.
- Save all results as CSV.
- Generate graphs.
- Prepare comparison tables.
- Identify performance trends.

### Deliverable:

- Complete experiment dataset
- CSV files
- Graphs
- Comparison tables
- Preliminary conclusions

---

## Week 8 — Final Analysis

### Do:

- Finalize all graphs.
- Clean and organize CSV files.
- Finalize result analysis.
- Prepare experiment methodology.
- Organize screenshots/results.
- Prepare the performance-analysis part of the presentation.
- Help with final integration testing.

### Deliverable:

- Final graphs
- Final experiment dataset
- Performance-analysis section
- Experiment methodology
- Presentation material

---

# 6. My Main GitHub Contributions

I should make meaningful commits related to my actual work.

Examples:

```text
Week 1:
chore: initialize repository and test structure

Week 2:
feat: add transfer timing and CSV logging

Week 3:
feat: add basic packet loss emulator

Week 4:
docs: add baseline performance graphs

Week 5:
feat: add window size benchmark

Week 6:
feat: add delay and reordering simulation

Week 7:
feat: automate performance experiments

Week 8:
docs: finalize graphs and experiment analysis
```

---

# 7. What I Should NOT Take Ownership Of

These belong mainly to the other team members:

### Somprakash

- UDP sender/receiver core
- Packet structure
- Sequence numbers
- Serialization/deserialization
- Checksum
- File reconstruction

### Abhipsa

- ACK handling
- Timeout/RTO
- Packet-loss detection inside the reliability protocol
- Retransmission
- Duplicate packet handling
- Out-of-order packet handling

### Sahil

- Sliding-window implementation
- Sender/receiver window management
- Go-Back-N / Selective Repeat
- Flow control
- Transfer synchronization

### My part

```text
Network conditions
        ↓
Experiments
        ↓
Metrics
        ↓
CSV results
        ↓
Graphs
        ↓
Performance analysis
```

I will integrate with the other modules, but I should not duplicate their core implementation.

---

# 8. Final Definition of Done for My Part

My part is complete when:

- [ ] Network emulator can simulate packet loss.
- [ ] Network emulator can simulate delay.
- [ ] Network emulator can simulate packet reordering.
- [ ] Network conditions are configurable.
- [ ] Experiments can be run automatically.
- [ ] Results are saved in CSV format.
- [ ] Transfer time is measured.
- [ ] Throughput is measured.
- [ ] Retransmissions are recorded.
- [ ] Packet-loss rate is recorded.
- [ ] File completion status is recorded.
- [ ] Checksum verification result is recorded.
- [ ] Different file sizes have been tested.
- [ ] Different packet-loss rates have been tested.
- [ ] Different delay values have been tested.
- [ ] Different window sizes have been tested.
- [ ] Stop-and-Wait vs Sliding Window has been compared.
- [ ] Required graphs have been generated.
- [ ] Results have been analyzed.
- [ ] CSV files and graphs are organized.
- [ ] Performance-analysis material is ready for the report/presentation.

---

# 9. Priority Order

If time becomes limited, implement in this order:

1. **Basic metrics collection**
2. **Packet-loss simulation**
3. **Delay simulation**
4. **Automated experiments**
5. **CSV result storage**
6. **Performance graphs**
7. **Sliding-window performance comparison**
8. **Packet reordering**
9. **Optional packet duplication**

The core requirement is a working emulator + reliable experiment data + meaningful performance analysis. Optional features should only be added after the core system is stable.
