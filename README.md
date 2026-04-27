# CPE 400 — TCP Reliability Analysis
**University of Nevada, Reno — Computer Networks Final Project**

Analyzes TCP reliability mechanisms under simulated network impairment using iperf3, Comcast, and Wireshark/tshark. Impairment (packet loss, delay, bandwidth throttling) is applied on the macOS side via Comcast. The Windows machine acts purely as a traffic source.

## Prerequisites

Both devices must be on the **same local network** (same WiFi or router).

### macOS
```bash
make setup    # installs iperf3, tshark, Python deps
make check    # verify everything is ready
```

Or manually:
```bash
brew install iperf3
brew install go && go install github.com/tylertreat/comcast@latest
brew install --cask wireshark        # provides tshark
pip3 install matplotlib pandas pyshark
```

### Windows
| Tool | Link | Notes |
|------|------|-------|
| Python 3 | https://python.org/downloads | Check "Add to PATH" during install |
| iperf3 | https://iperf.fr/iperf-download.php | Add the folder to PATH |
| Wireshark (tshark) | https://wireshark.org/download.html | Optional — enables packet captures |

---

## Step 1 — Find your Mac's IP

`mac_server.py` prints it automatically when it starts, but you can also check manually:
```bash
ifconfig en0 | grep "inet "
```
Note the IP (e.g. `192.168.1.45`).

---

## Step 2 — Edit the Windows client config

Open `scripts/win_client.py` and update line 33:
```python
SERVER_IP = "192.168.1.45"   # ← replace with your Mac's IP
```

---

## Step 3 — Run the tests

**On macOS first:**
```bash
make server
# Choose option 2 — "Run ALL scenarios in sequence"
```

**On Windows immediately after:**
```bash
python scripts/win_client.py
```

The Mac runs each 30-second test with a 5-second buffer between scenarios. 7 scenarios total — about 4 minutes end to end.

---

## Step 4 — Transfer results to macOS

After all tests complete, copy from Windows to macOS:
- `results/*.json` → into `results/` on macOS
- `captures/*_client.pcap` → into `captures/` on macOS *(optional)*

Transfer via USB, a shared folder, or email.

---

## Step 5 — Analyze

```bash
make analyze           # full analysis with plots
make analyze-no-pcap   # skip pcap parsing (if tshark wasn't used)
```

Plots are saved to `report/tcp_analysis_results.png`.

---

## Scenarios

| Scenario | Packet Loss | Latency | Bandwidth |
|----------|------------|---------|-----------|
| Baseline | 0% | 0ms | Unlimited |
| Low Loss | 1% | 0ms | Unlimited |
| Med Loss | 5% | 0ms | Unlimited |
| High Loss | 10% | 0ms | Unlimited |
| High Latency | 0% | 200ms | Unlimited |
| Throttled | 0% | 0ms | 500 Kbps |
| Combined | 5% | 50ms | 1 Mbps |

---

## Troubleshooting

**iperf3 connection refused (Windows):**
- Make sure `make server` is already running on macOS before starting the client
- macOS firewall: System Settings → Network → Firewall → allow iperf3

**Comcast impairment not applying:**
- Make sure `comcast` is in your PATH: `which comcast`
- Try running `mac_server.py` with `sudo python3` if permission errors occur

**tshark permission denied (macOS):**
- Run `sudo chmod o+r /dev/bpf*` then retry

**Comcast stuck after a failed run:**
- Run `make reset` or `sudo comcast --device=en0 --stop`

**Wrong interface (`en0`):**
- Check your active interface with `ifconfig` and update `INTERFACE` at the top of `mac_server.py`
