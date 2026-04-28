import os
import sys
import time
import json
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
BASE_DIR    = SCRIPT_DIR.parent
RESULTS_DIR = BASE_DIR / "results"
CAPTURE_DIR = BASE_DIR / "captures"

SERVER_IP     = "10.171.211.94"   # ← Replace with macOS IP shown by mac_server.py
PORT          = 5201
DURATION      = 30                # seconds per test
INTERVAL      = 1                 # iperf3 reporting interval (seconds)

SCENARIOS = [
    "baseline",
    "loss_1pct",
    "loss_5pct",
    "loss_10pct",
    "latency_hi",
    "throttled",
    "combined",
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
    if not shutil.which("iperf3"):
        error(
            "iperf3 not found in PATH.\n"
            "  Download: https://iperf.fr/iperf-download.php\n"
            "  Then add the folder to your system PATH."
        )
    info("✓ iperf3 found")

    if shutil.which("tshark"):
        info("✓ tshark found (captures enabled)")
        return True
    else:
        warn("tshark not found — packet captures will be skipped.")
        warn("Install Wireshark to enable: https://wireshark.org/download.html")
        return False

def start_capture(scenario: str) -> subprocess.Popen | None:
    pcap_path = CAPTURE_DIR / f"{scenario}_client.pcap"
    info(f"Starting capture → {pcap_path}")
    try:
        proc = subprocess.Popen(
            ["tshark", "-i", "1",           # interface index 1 — adjust if needed
             "-f", f"tcp port {PORT}",
             "-w", str(pcap_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)
        return proc
    except Exception as e:
        warn(f"Could not start tshark: {e}")
        return None


def stop_capture(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        proc.wait()
        info("Capture stopped.")

def run_iperf3(scenario: str) -> bool:
    result_path = RESULTS_DIR / f"{scenario}.json"
    info(f"Running iperf3 for {DURATION}s → {result_path}")

    cmd = [
        "iperf3",
        "-c", SERVER_IP,
        "-p", str(PORT),
        "-t", str(DURATION),
        "-i", str(INTERVAL),
        "--json",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            warn(f"iperf3 exited with code {result.returncode}")
            if result.stderr:
                warn(result.stderr.strip())
            return False

        # Validate it's real JSON before saving
        json.loads(result.stdout)

        result_path.write_text(result.stdout)
        info(f"Result saved → {result_path}")
        return True

    except json.JSONDecodeError:
        warn("iperf3 output was not valid JSON — server may not have been ready.")
        return False
    except FileNotFoundError:
        error("iperf3 not found. Make sure it's in your PATH.")
        return False

def run_scenario(scenario: str, has_tshark: bool):
    header(f"━━━ Scenario: {scenario} ━━━")

    tshark_proc = start_capture(scenario) if has_tshark else None

    success = run_iperf3(scenario)
    if not success:
        warn(f"Scenario '{scenario}' may have failed — check results file.")

    stop_capture(tshark_proc)

    info(f"Scenario '{scenario}' done.")
    print()
    time.sleep(2)  # brief pause — gives Mac time to clear impairment

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"""
{BOLD}╔══════════════════════════════════════════════╗
║  CPE 400 TCP Analysis — Windows Client       ║
║  All impairment applied on macOS via Comcast  ║
╚══════════════════════════════════════════════╝{RESET}

  Server IP : {SERVER_IP}
  Port      : {PORT}
  Duration  : {DURATION}s per scenario
  Scenarios : {len(SCENARIOS)}
""")

    if SERVER_IP == "192.168.1.100":
        warn("SERVER_IP is still the default placeholder!")
        warn("Edit win_client.py line 33 with your Mac's actual IP.")
        warn("(mac_server.py prints the IP when it starts)")
        print()
        input("  Press Enter to continue anyway, or Ctrl+C to exit and fix it first...")
        print()

    has_tshark = check_deps()
    print()

    warn("Make sure mac_server.py is running in mode 2 on your Mac before continuing.")
    input("  Press Enter when ready...")
    print()

    passed = []
    failed = []

    for scenario in SCENARIOS:
        run_scenario(scenario, has_tshark)
        result_file = RESULTS_DIR / f"{scenario}.json"
        if result_file.exists():
            passed.append(scenario)
        else:
            failed.append(scenario)
    header("════ All scenarios complete! ════")
    info(f"Passed : {len(passed)}/{len(SCENARIOS)}")

    if failed:
        warn(f"Failed : {', '.join(failed)}")

    print(f"""
  Next steps:
    1. Copy  {BASE_DIR / 'results'}\\*.json  to your Mac's results/ folder
    2. On Mac, run: python3 analysis/analyze.py
""")


if __name__ == "__main__":
    main()