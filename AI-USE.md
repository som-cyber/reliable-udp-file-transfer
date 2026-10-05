## Abhipsa — Reliability Mechanism module

Used AI assistants (ChatGPT, Claude) to:
- Explain Jacobson/Karels adaptive RTO estimation and Karn's Algorithm,
  and provide guidance for integrating RTT/RTO estimation into the existing
  reliability mechanism.
- Review and improve the existing timeout and retransmission logic,
  including adding a maximum retransmission limit to prevent indefinite
  retransmission attempts.
- Identify and resolve issues related to duplicate packet handling,
  ensuring that duplicate DATA packets are acknowledged correctly.
- Design and guide controlled reliability tests for timeout detection,
  retransmission, duplicate packets, and ACK-loss recovery.
- Review the reliability implementation and suggest appropriate test cases
  for corrupted, duplicate, and out-of-order packets.

All core packet structure, socket communication, reliability workflow,
variable naming, and project structure were developed as part of the
project implementation. AI was used for technical guidance, debugging,
algorithm explanations, implementation support, and test design.