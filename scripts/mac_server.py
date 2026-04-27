import os
import sys
import time
import signal
import subprocess
import shutil
from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
BASE_DIR     = SCRIPT_DIR.parent
CAPTURE_DIR  = BASE_DIR / "captures"
RESULTS_DIR  = BASE_DIR / "results"

INTERFACE    = "en0"     # change if needed — check with: ifconfig
PORT         = 5201
TEST_DURATION = 30       # seconds per iperf3 test
SCENARIO_WAIT = TEST_DURATION + 5  # wait slightly longer than the test

SCENARIOS = [
    ("baseline",   0,   0,   0),
    ("loss_1pct",  1,   0,   0),
    ("loss_5pct",  5,   0,   0),
    ("loss_10pct", 10,  0,   0),
    ("latency_hi", 0,   200, 0),
    ("throttled",  0,   0,   500),
    ("combined",   5,   50,  1000),
]

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def info(msg):  print(f"{GREEN}[INFO]{RESET}  {msg}")
def warn(msg):  print(f"{YELLOW}[WARN]{RESET}  {msg}")
def error(msg): print(f"{RED}[ERROR]{RESET} {msg}"); sys.exit(1)
def header(msg):print(f"\n{BOLD}{CYAN}{msg}{RESET}")

def check_deps():
    missing = []
    for cmd, install_hint in [
        ("iperf3",  "brew install iperf3"),
        ("tshark",  "brew install --cask wireshark"),
        ("comcast", "brew install go && go install github.com/tylertreat/comcast@latest"),
    ]:
        if not shutil.which(cmd):
            missing.append(f"  ✗ {cmd:<12} → {install_hint}")
        else:
            info(f"✓ {cmd}")

    if missing:
        print()
        error("Missing dependencies:\n" + "\n".join(missing))


def get_local_ip():
    """Get the IP address of the active interface."""
    result = subprocess.run(
        ["ifconfig", INTERFACE],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("inet ") and not line.startswith("inet6"):
            return line.split()[1]
    return "unknown"

def apply_impairment(loss: int, delay: int, bw: int):
    cmd = ["sudo", "comcast", f"--device={INTERFACE}", f"--port-dst={PORT}"]
    if loss  > 0: cmd.append(f"--packet-loss={loss}")
    if delay > 0: cmd.append(f"--latency={delay}")
    if bw    > 0: cmd.append(f"--target-bw={bw}")

    bw_str = f"{bw}kbps" if bw > 0 else "unlimited"
    info(f"Applying impairment: loss={loss}%  delay={delay}ms  bw={bw_str}")
    subprocess.run(cmd, check=True)
    info("Impairment active.")


def clear_impairment():
    info("Clearing Comcast impairment...")
    subprocess.run(
        ["sudo", "comcast", f"--device={INTERFACE}", "--stop"],
        capture_output=True  # suppress output if nothing to clear
    )
    info("Network restored.")

def start_capture(scenario: str) -> subprocess.Popen:
    pcap_path = CAPTURE_DIR / f"{scenario}.pcap"
    info(f"Starting capture → {pcap_path}")
    proc = subprocess.Popen(
        ["sudo", "tshark", "-i", INTERFACE,
         "-f", f"tcp port {PORT}",
         "-w", str(pcap_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1)  # let tshark initialize
    return proc


def stop_capture(proc: subprocess.Popen):
    if proc and proc.poll() is None:
        proc.terminate()
        proc.wait()
        info("Capture stopped.")

def start_iperf3_server() -> subprocess.Popen:
    info(f"Starting iperf3 server on port {PORT}...")
    proc = subprocess.Popen(
        ["iperf3", "-s", "-p", str(PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    return proc


def stop_iperf3_server(proc: subprocess.Popen):
    if proc and proc.poll() is None:
        proc.terminate()
        proc.wait()
        info("iperf3 server stopped.")

def run_scenario(name: str, loss: int, delay: int, bw: int):
    header(f"━━━ Scenario: {name} ━━━")

    tshark_proc = start_capture(name)

    if loss > 0 or delay > 0 or bw > 0:
        apply_impairment(loss, delay, bw)
    else:
        info("No impairment — baseline test.")

    info(f"Waiting {SCENARIO_WAIT}s for Windows client to complete test...")
    time.sleep(SCENARIO_WAIT)

    clear_impairment()
    stop_capture(tshark_proc)

    info(f"Scenario '{name}' complete. Capture saved.")
    print()
    time.sleep(2)

def mode_server_only():
    """Just run iperf3 interactively — useful for manual testing."""
    info(f"Starting iperf3 server on port {PORT} (Ctrl+C to stop)...")
    subprocess.run(["iperf3", "-s", "-p", str(PORT)])


def mode_all_scenarios():
    warn("Start this FIRST, then immediately run win_client.py on Windows.")
    warn(f"Each scenario takes ~{SCENARIO_WAIT}s. Total: ~{len(SCENARIOS) * SCENARIO_WAIT // 60} min.")
    print()

    server_proc = start_iperf3_server()

    # Graceful Ctrl+C cleanup
    def handle_interrupt(sig, frame):
        print()
        warn("Interrupted — cleaning up...")
        clear_impairment()
        stop_iperf3_server(server_proc)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_interrupt)

    for name, loss, delay, bw in SCENARIOS:
        run_scenario(name, loss, delay, bw)

    stop_iperf3_server(server_proc)

    header("════ All scenarios complete! ════")
    info("Copy results/*.json from Windows → this machine's results/")
    info("Then run: python3 analysis/analyze.py")


def mode_reset():
    clear_impairment()

def main():
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"""
{BOLD}╔══════════════════════════════════════════════╗
║   CPE 400 TCP Analysis — macOS Server        ║
║   Impairment via: Comcast                    ║
╚══════════════════════════════════════════════╝{RESET}

  Interface : {INTERFACE}
  Your IP   : {get_local_ip()}  ← give this to Windows client
  Port      : {PORT}

  Modes:
    1) Server only       (manual / single test)
    2) All scenarios     (coordinate with Windows client)
    3) Reset impairment  (emergency clear)
""")

    check_deps()

    choice = input("  Choice [1-3]: ").strip()
    print()

    if   choice == "1": mode_server_only()
    elif choice == "2": mode_all_scenarios()
    elif choice == "3": mode_reset()
    else: error("Invalid choice.")


if __name__ == "__main__":
    main()
