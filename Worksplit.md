# Work Split and Weekly Development Plan

## Project: Reliable UDP File Transfer with Sliding Window

The project will build a reliable file-transfer system over UDP. Since UDP does not guarantee delivery, ordering, or duplicate prevention, our system will add reliability mechanisms such as packetization, sequence
numbers, checksums, acknowledgements, timeouts, retransmissions, sliding-window flow control, and network emulation.


## 1. Team Members and Main Responsibilities

  Member                  Main Module             Primary Responsibility
  
  **Somprakash**          UDP Communication and   UDP sender/receiver, packet
                          Packet Format           structure, sequence numbers,
                                                  serialization/deserialization,
                                                  checksum, and file
                                                  reconstruction

  **Abhipsa**             Reliability Mechanism   ACK handling, timeout/RTO,
                                                  packet-loss detection,
                                                  retransmission, duplicate
                                                  packets, and out-of-order
                                                  packets

  **Sahil**               Sliding Window and Flow Sliding-window protocol,
                          Control                 Go-Back-N/Selective Repeat,
                                                  sender/receiver window
                                                  management, and transfer
                                                  synchronization

  **Protanu**             Network Emulator and    Packet loss/delay/reordering
                          Performance Analysis    emulator, load testing,
                                                  performance measurement,
                                                  experiment automation, graphs,
                                                  and result analysis
                                                  


# 2. Detailed Work Responsibilities

## 2.1 Somprakash --- UDP Communication and Packet Format

### Main Goal:-
Build the basic UDP communication layer and define how data will be divided into packets, transmitted, received, checked, and reconstructed.

### Detailed Responsibilities

#### A. UDP Sender

-   Create a UDP socket.
-   Read the selected file from storage.
-   Divide the file into smaller chunks.
-   Create packets from those chunks.
-   Send packets to the receiver.
-   Track the packet sequence number.
-   Handle the end of file-transfer process.

#### B. UDP Receiver

-   Create a UDP socket and bind it to a port.
-   Receive UDP packets.
-   Extract packet information.
-   Pass received data to the reliability and reconstruction modules.
-   Save the received file to disk.

#### C. Packet Structure

Design a common packet format for communication between sender and receiver.

A packet may contain:

``` text
+------------------+
| Packet Type      |
+------------------+
| Sequence Number  |
+------------------+
| Acknowledgement  |
+------------------+
| Payload Length   |
+------------------+
| Checksum         |
+------------------+
| Payload/Data     |
+------------------+
```

Possible packet types:

-   `DATA`
-   `ACK`
-   `START`
-   `END`
-   `FINISH`
-   `ERROR`

#### D. Sequence Numbers

-   Assign a unique sequence number to each data packet.
-   Use sequence numbers to identify missing packets.
-   Support detection of duplicate and out-of-order packets.

#### E. Serialization and Deserialization

-   Convert packet fields into bytes before transmission.
-   Convert received bytes back into packet fields.
-   Validate packet length and packet format.

#### F. Checksum

-   Calculate a checksum for packet contents.
-   Attach the checksum to each packet.
-   Recalculate and verify the checksum at the receiver.
-   Reject corrupted packets.

#### G. File Reconstruction

-   Store valid received packet data.
-   Arrange packet data in the correct order.
-   Reconstruct the original file.
-   Verify that the reconstructed file matches the original file.

### Expected Output

By the end of this module, the team should have:

-   A working UDP sender.
-   A working UDP receiver.
-   A documented packet format.
-   Packet serialization/deserialization functions.
-   Sequence-number handling.
-   Checksum verification.
-   Basic file reconstruction.


## 2.2 Abhipsa --- Reliability Mechanism

### Main Goal

Make UDP file transfer reliable by detecting lost packets and requesting or performing retransmission.

### Detailed Responsibilities

#### A. ACK Handling

-   Receive acknowledgements from the receiver.
-   Identify which packet has been acknowledged.
-   Maintain the acknowledgement status of packets.
-   Handle repeated or duplicate ACKs.

Example:

``` text
Sender                  Receiver

DATA 1  -------------------->
        <-------------------- ACK 1

DATA 2  -------------------->
        <-------------------- ACK 2
```

#### B. Packet-Loss Detection

-   Detect when an expected ACK is not received.
-   Identify missing packet sequence numbers.
-   Detect packet loss using timeout or acknowledgement information.

#### C. Timeout Mechanism

-   Start a timer after sending a packet or window.
-   Wait for the expected ACK.
-   Retransmit if the timer expires.
-   Stop the timer when the expected ACK arrives.

#### D. RTO Calculation

RTO means **Retransmission Timeout**.

The module will initially use a simple timeout value. If time permits, it may estimate timeout using measured round-trip time.

The system should avoid:

-   Waiting forever for an ACK.
-   Retransmitting too quickly.
-   Sending unnecessary duplicate packets.

#### E. Retransmission

-   Retransmit lost packets.
-   Handle retransmission after timeout.
-   Keep track of the number of retransmissions.
-   Avoid losing already received data.

#### F. Duplicate Packet Handling

-   Detect packets that have already been received.
-   Avoid writing duplicate data into the output file.
-   Send an ACK again when necessary.

#### G. Out-of-Order Packet Handling

-   Detect packets that arrive before earlier packets.
-   Temporarily store out-of-order packets if required.
-   Deliver data to the file reconstruction module in the correct order.

#### H. Error Handling

Handle situations such as:

-   Invalid packet format.
-   Wrong checksum.
-   Missing ACK.
-   Duplicate ACK.
-   Unexpected packet sequence.
-   Receiver timeout.

### Expected Output

By the end of this module, the team should have:

-   ACK processing.
-   Timeout handling.
-   Packet-loss detection.
-   Retransmission logic.
-   Duplicate packet handling.
-   Out-of-order packet handling.
-   Retransmission statistics.


## 2.3 Sahil --- Sliding Window and Flow Control

### Main Goal

Improve transfer performance by allowing multiple packets to be in
transit instead of waiting for an ACK after every packet.

### Detailed Responsibilities

#### A. Sliding Window

Implement a sender window that controls how many packets can be sent
without receiving individual acknowledgements.

Example:

``` text
Window Size = 4

[1] [2] [3] [4]  → packets currently allowed to be sent
```

After ACK for packet 1:

``` text
[2] [3] [4] [5]
```

The window moves forward. This is why it is called a sliding window.

#### B. Sender Window Management

Maintain:

-   Base sequence number.
-   Next sequence number.
-   Window size.
-   Packets currently in transit.
-   Acknowledged packets.
-   Unacknowledged packets.

#### C. Receiver Window Management

Maintain:

-   Expected packet number.
-   Received packet buffer.
-   Out-of-order packets.
-   Acknowledgement status.
-   Delivery order.

#### D. Go-Back-N or Selective Repeat

The team will implement one main sliding-window retransmission strategy.

##### Go-Back-N

If one packet is lost, retransmit the lost packet and all later
unacknowledged packets.

Example:

``` text
Sent:       1  2  3  4  5
Received:   1  2     4  5

Packet 3 is lost.

Retransmit: 3  4  5
```

##### Selective Repeat

If one packet is lost, retransmit only the missing packet.

Example:

``` text
Sent:       1  2  3  4  5
Received:   1  2     4  5

Retransmit: 3 only
```


#### E. Flow Control

-   Prevent the sender from overwhelming the receiver.
-   Limit the number of packets in transit.
-   Adjust sending according to the receiver window.
-   Avoid buffer overflow.

#### F. Transfer Synchronization

-   Coordinate the sender and receiver.
-   Handle start and end of transfer.
-   Ensure all required packets are acknowledged.
-   Confirm successful file completion.




## 2.4 Protanu --- Network Emulator and Performance Analysis

### Main Goal

Create controlled network conditions and measure how the reliable UDP
protocol performs under packet loss, delay, and reordering.

### Detailed Responsibilities

#### A. Network Emulator

Build a software layer between sender and receiver that can simulate unreliable network conditions.

The emulator should support:

-   Packet loss.
-   Artificial delay.
-   Packet reordering.
-   Optional packet duplication.
-   Configurable network conditions.

Example:

``` text
Sender
   |
   v
Network Emulator
   |
   +-- 10% packet loss
   +-- 50 ms delay
   +-- Packet reordering
   |
   v
Receiver
```

#### B. Packet-Loss Simulation

Allow the user to set packet-loss probability.

Example values:

``` text
0%
2%
5%
10%
15%
```

#### C. Delay Simulation

Add artificial delay to packets.

Example values:

``` text
0 ms
20 ms
50 ms
100 ms
```

#### D. Reordering Simulation

Change the order of selected packets to check whether the receiver can handle out-of-order delivery.

#### E. Load Testing

Create a test tool that can run multiple file transfers or repeated transfers.

Test variables may include:

-   File size.
-   Packet size.
-   Packet-loss percentage.
-   Network delay.
-   Window size.
-   Number of transfers.

#### F. Performance Metrics

Collect the following metrics:

-   Total transfer time.
-   Average latency.
-   Throughput.
-   Number of packets sent.
-   Number of packets received.
-   Number of retransmissions.
-   Packet-loss rate.
-   File completion status.
-   Checksum verification result.

#### G. Experiment Automation

Create scripts that automatically:

1.  Set network conditions.
2.  Run the file transfer.
3.  Collect results.
4.  Save results in CSV format.
5.  Repeat the experiment for different values.

#### H. Graphs and Analysis

Generate graphs such as:

-   Packet loss vs. transfer time.
-   Packet loss vs. throughput.
-   Window size vs. throughput.
-   Delay vs. completion time.
-   Packet loss vs. retransmission count.
-   File size vs. transfer time.
-   UDP without reliability vs. Reliable UDP.

### Expected Output

By the end of this module, the team should have:

-   A working network emulator.
-   Automated experiments.
-   CSV result files.
-   Performance graphs.
-   A comparison report.
-   A clear explanation of the results.



## Final Statement

This work split gives each member a separate technical responsibility while ensuring that the complete project is developed collaboratively.
The team will first create a basic UDP file-transfer system, then add reliability, sliding-window flow control, network emulation, and
performance analysis. The final outcome will be a working reliable file-transfer protocol implemented over UDP and evaluated under different network conditions
