# Reliability Mechanism Module — Documentation

**Module owner:** Abhipsa Rath (2405777)
**Component:** Reliability Mechanism (ACK handling, timeout/RTO, retransmission, duplicate & out-of-order packet handling)
**Files:** `src/udp_sender.py`, `src/udp_receiver.py`, `src/packet.py`, `src/checksum.py`, `src/test_reliability.py`

---

## 1. What this module does

This module sits on top of the basic UDP send/receive layer and makes file transfer **reliable** — meaning the sender can detect when data is lost, corrupted, or unacknowledged, and recover from it without losing or duplicating data at the receiver.

It currently implements **Stop-and-Wait** reliability: the sender sends one packet, waits for its ACK, and only then sends the next. This is the foundation the sliding-window module (Sahil's component) will extend to allow multiple packets in flight at once.

### Core guarantees provided
- Every DATA packet sent is eventually either acknowledged or the transfer fails explicitly (never hangs forever).
- Corrupted packets (detected via checksum) are rejected, never written to the output file.
- Duplicate packets (same sequence number arriving twice) do not corrupt the output file.
- Packets arriving out of order are correctly reassembled in sequence order.
- The sender's retransmission timeout adapts to actual measured network conditions instead of using one fixed value.

---

## 2. Packet format (owned by Somprakash, used here)

```
+------------------+------------------+------------------+------------------+
| Packet Type (1B) | Sequence Num(4B) | Payload Len (2B) | Checksum (4B)    | + Payload
+------------------+------------------+------------------+------------------+
```

Defined in `packet.py` via `HEADER_FORMAT = "!BIHI"` (network byte order).

Packet types: `START` (1), `DATA` (2), `END` (3), `ACK` (4) — see `PACKET_TYPE_*` constants in `packet.py`.

The checksum is CRC32 over the payload only (`checksum.py`, using `zlib.crc32`). Every received packet's checksum is re-verified before it's trusted; if it doesn't match, the packet is silently dropped as if it never arrived (the sender's timeout will eventually catch the loss and retransmit).

---

## 3. Transfer flow (Stop-and-Wait)

```
Sender                                   Receiver
  |-------- START ------------------------->|   (clears any old transfer state)
  |                                          |
  |-------- DATA seq=0 --------------------->|
  |                                          |  verify checksum
  |                                          |  store packet[0]
  |<------- ACK seq=0 -----------------------|
  | (match confirmed, advance to seq=1)      |
  |                                          |
  |-------- DATA seq=1 --------------------->|
  |<------- ACK seq=1 -----------------------|
  |            ... repeats ...               |
  |                                          |
  |-------- END (count=N) ------------------>|
  |                                          |  reconstruct file from
  |                                          |  stored packets, in order
```

Only one DATA packet is ever "in flight" (unacknowledged) at a time — this is what "Stop-and-Wait" means, and it's why out-of-order delivery can't naturally occur yet over the real network. That capability is tested separately (see Section 6).

---

## 4. ACK handling

- The sender, after sending DATA packet `seq_num`, blocks on `recvfrom()` with a timeout.
- Any reply is validated before being trusted:
  1. Does it deserialize correctly? (`Packet.deserialize()` returns `None` if malformed)
  2. Does its checksum verify? (`verify_integrity()`)
  3. Is it actually type `ACK`?
  4. Does its sequence number match the packet we're currently waiting on?
- If any check fails, the sender logs it and keeps listening (it does **not** treat an invalid/stale ACK as the real one) — this handles duplicate ACKs or ACKs left over from a previous run safely.
- The receiver sends an ACK for every valid DATA packet it processes — including duplicates (if packet 3 arrives twice, the receiver still re-sends ACK 3 the second time, in case the first ACK was the one that got lost).

---

## 5. Timeout & Adaptive RTO (Jacobson/Karels + Karn's Algorithm)

### Why adaptive, not fixed?
A fixed timeout (e.g. always 1 second) is wrong in both directions: too short on a slow/congested link (causes unnecessary retransmissions), too long on a fast link (wastes time waiting after a real loss). The sender instead **measures** round-trip time and adjusts.

### The formulas (RFC 6298)
On every **clean** ACK (see Karn's Algorithm below):

```
sample_rtt = time_ack_received - time_packet_sent

if first sample:
    SRTT   = sample_rtt
    RTTVAR = sample_rtt / 2
else:
    RTTVAR = (1 - BETA)  * RTTVAR + BETA  * |SRTT - sample_rtt|
    SRTT   = (1 - ALPHA) * SRTT   + ALPHA * sample_rtt

RTO = SRTT + 4 * RTTVAR        (clamped between MIN_RTO and MAX_RTO)
```

`ALPHA = 0.125`, `BETA = 0.25` — standard RFC 6298 values. `SRTT` = smoothed RTT, `RTTVAR` = RTT variance estimate. The more a connection's RTT jitters, the bigger the RTO grows, since `RTTVAR` captures that volatility.

### Karn's Algorithm — why it matters
If a packet had to be **retransmitted**, and an ACK then arrives, you cannot tell whether that ACK is answering the *original* transmission or the *retransmission* — this is called **retransmission ambiguity**. Using that RTT sample would poison the RTO estimate with a bogus number.

**Rule implemented:** only feed an RTT sample into the SRTT/RTTVAR formulas when `retransmissions == 0` for that packet (i.e., it succeeded on the very first try). If a packet needed retries, its timeout is instead grown by simple exponential backoff (`attempt_rto = min(attempt_rto * 2, MAX_RTO)`) for that packet only, and the *persistent* `current_rto` estimate used for the next fresh packet is left untouched.

---

## 6. Retransmission & failure handling

- `MAX_RETRANSMISSIONS = 5` — a packet is retried at most 5 times before the sender gives up and raises `RuntimeError`, stopping the transfer. This guarantees the sender never hangs forever waiting on a packet that will never be acknowledged (e.g., receiver crashed).
- Every retransmission is counted both per-packet (`retransmission_stats` dict) and as a running total (`total_retransmissions`).
- At the end of a successful transfer, the sender prints and saves:
  - Total packets sent, total retransmissions, retransmission rate (%)
  - Final SRTT / RTTVAR / RTO values
  - A `retransmission_stats.csv` file (`seq_num,retransmissions` per row) — this is meant for Protanu's performance-analysis module to plot "packet loss vs retransmission count" and similar graphs later.

---

## 7. Duplicate and out-of-order handling

**Receiver side (`udp_receiver.py`):**
- Received packets are stored in a dict keyed by sequence number (`received_packets[seq] = packet`), not a list — this means storage order doesn't depend on arrival order.
- If a sequence number is already in the dict, it's recognized as a duplicate, logged, and *not* overwritten — but the receiver still re-sends the ACK, in case the original ACK was the one lost in transit.
- At `END`, `reconstruct_file_from_dict()` (in `file_utils.py`, Somprakash's module) sorts by sequence number before writing the file, so arrival order never matters for correctness.

**Why this can't be demonstrated live yet:** Stop-and-Wait only ever has one unacknowledged packet at a time, so true out-of-order arrival can't happen over the real socket until the sliding-window module (multiple packets in flight) is integrated. Until then, this logic is verified with direct unit tests instead (see below).

---

## 8. Testing

### 8.1 Automated unit tests — `test_reliability.py`
Run:
```bash
cd src
python test_reliability.py
```
Tests included (no sockets, no network — tests the logic directly):
1. **Out-of-order reconstruction** — feeds packets to `reconstruct_file_from_dict()` in scrambled order (2, 0, 1), confirms the output file is still byte-correct.
2. **Duplicate packet handling** — confirms a duplicate sequence number doesn't create a second entry or corrupt the store.
3. **Corrupted packet rejection** — flips a bit in a serialized packet, confirms `verify_integrity()` correctly flags it as invalid.

Expected output ends with: `All reliability tests passed.`

### 8.2 Manual end-to-end test (normal case)
Terminal 1:
```bash
python udp_receiver.py --output received.txt
```
Terminal 2:
```bash
python udp_sender.py --file test.txt
```
Then verify byte-for-byte match:
```bash
fc.exe test.txt received.txt      # Windows
# or
diff test.txt received.txt        # Linux/Mac
```
Expected: no differences / "FC: no differences encountered".

### 8.3 Manual test — forced retransmission / failure
1. Start the receiver, let it print `Listening on ...`.
2. Start the sender.
3. Immediately kill the receiver (`Ctrl+C`) before it can ACK.
4. The sender should print 5 timeout/retransmit attempts, then fail cleanly with `Maximum retransmissions reached for packet 0` instead of hanging forever.

---

## 9. Known limitations (by design, for this stage)

- Only Stop-and-Wait is implemented here — one packet in flight at a time. This is intentional; sliding window / Go-Back-N / Selective Repeat is Sahil's module and will sit on top of this reliability logic, not replace it.
- No flow control (receiver can't signal "slow down") — also part of the sliding-window module.
- The RTO estimate resets every time `send_file()` is called fresh (no persistence across separate transfer runs) — acceptable since each transfer is independent in the current design.
- Receiver listens indefinitely for new transfers (by design — it's meant to act like a small server); use `Ctrl+C` to stop it. A 1-second socket timeout loop was added so Ctrl+C is actually responsive on Windows.

---

## 10. Notes for the next person extending this (sliding window / integration)

If you're building the sliding-window layer on top of this:
- The per-packet retry logic here (`while True: send → wait with timeout → retry or give up`) is the pattern each packet in a window will need, just run concurrently for multiple in-flight sequence numbers instead of one.
- `received_packets` is already a dict keyed by sequence number at the receiver — this is exactly the structure needed to support a receive window buffering out-of-order arrivals; no rework needed there.
- The adaptive RTO state (`srtt`, `rttvar`, `current_rto`) is currently scoped to one `send_file()` call. If the sliding-window sender keeps a persistent connection across many packets concurrently, make sure RTT sampling still only happens on non-retransmitted packets (Karn's Algorithm) per packet, feeding into one shared RTO estimate.
- `MAX_RETRANSMISSIONS`, `MIN_RTO`, `MAX_RTO`, `ALPHA`, `BETA`, `K` are all at the top of `udp_sender.py` as named constants — reuse them rather than hardcoding new values.

---

## 11. AI use disclosure

See `AI-USE.md` in the repository root for a full record of what AI assistance was used for in this module (RTO/Karn's Algorithm formulas, a dead-code bug fix, a Windows socket-timeout fix, and test design). All core logic and integration into the existing codebase was done and understood by the module owner.
