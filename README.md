# TCP Reliability Analysis

**CPE 400 Computer Networks Final Project**  
University of Nevada, Reno

---

## Overview

This project analyzes TCP's reliability mechanisms under simulated network impairment conditions. Using **iperf3** as a traffic generator, **Comcast** as a network impairment tool (packet loss, delay, bandwidth throttling), and **Wireshark** for packet capture and analysis, the project evaluates how TCP responds to degraded network conditions through retransmissions, congestion window adjustments, and throughput changes.

---

## Setup

### Prerequisites

Ensure the following tools are installed on your system:

| Tool | Purpose | Install |
|------|---------|---------|
| [iperf3](https://iperf.fr/) | TCP traffic generation | `brew install iperf3` / `apt install iperf3` |
| [Comcast](https://github.com/tylertreat/Comcast) | Network impairment simulation | `go install github.com/tylertreat/comcast@latest` |
| [Wireshark](https://www.wireshark.org/) / `tshark` | Packet capture & analysis | [wireshark.org/download](https://www.wireshark.org/download.html) |
| Python 3 (optional) | Result parsing / plotting | `brew install python` |


### Network Interface

Identify the network interface you'll be impairting (e.g., `eth0`, `en0`):

```bash
# Linux
ip link show

# macOS & Windows
ifconfig
```

---

## Authors

- **Aidan** – University of Nevada, Reno  
- CPE 400 – Computer Networks (Prof. Igor Remizov)
