
PYTHON     := python3
PIP        := pip3
SCRIPTS    := scripts
ANALYSIS   := analysis
RESULTS    := results
CAPTURES   := captures
REPORT     := report

.PHONY: all setup check server analyze clean help

all: help

setup:
	@echo "━━━ Setting up CPE 400 TCP Analysis ━━━"
	@mkdir -p $(RESULTS) $(CAPTURES) $(REPORT)
	@echo "[1/3] Installing Python dependencies..."
	$(PIP) install matplotlib pandas pyshark 2>/dev/null || \
		$(PIP) install --user matplotlib pandas pyshark
	@echo "[2/3] Checking iperf3..."
	@command -v iperf3 >/dev/null 2>&1 || \
		(echo "  iperf3 not found. Installing..." && brew install iperf3)
	@echo "[3/3] Checking tshark..."
	@command -v tshark >/dev/null 2>&1 || \
		(echo "  tshark not found. Installing Wireshark..." && brew install --cask wireshark)
	@echo ""
	@echo "  Setup complete."
	@echo "  Next: run 'make check' to verify, then 'make server' to start."

check:
	@echo "━━━ Dependency Check ━━━"
	@command -v iperf3 >/dev/null 2>&1  && echo "  ✓ iperf3"    || echo "  ✗ iperf3    (brew install iperf3)"
	@command -v tshark >/dev/null 2>&1  && echo "  ✓ tshark"    || echo "  ✗ tshark    (brew install --cask wireshark)"
	@command -v pfctl  >/dev/null 2>&1  && echo "  ✓ pfctl"     || echo "  ✗ pfctl     (should be built-in on macOS)"
	@command -v dnctl  >/dev/null 2>&1  && echo "  ✓ dnctl"     || echo "  ✗ dnctl     (should be built-in on macOS)"
	@$(PYTHON) -c "import matplotlib" 2>/dev/null && echo "  ✓ matplotlib" || echo "  ✗ matplotlib (pip install matplotlib)"
	@$(PYTHON) -c "import pandas"     2>/dev/null && echo "  ✓ pandas"     || echo "  ✗ pandas     (pip install pandas)"
	@$(PYTHON) -c "import pyshark"    2>/dev/null && echo "  ✓ pyshark"    || echo "  ✗ pyshark    (pip install pyshark)"
	@echo ""
	@echo "  Windows client also needs:"
	@echo "    iperf3  → https://iperf.fr/iperf-download.php"
	@echo "    clumsy  → https://jagt.github.io/clumsy/"
	@echo "    tshark  → https://www.wireshark.org/download.html"

server:
	@echo "━━━ Starting macOS Server ━━━"
	$(PYTHON) $(SCRIPTS)/mac_server.py

analyze:
	@echo "━━━ Analyzing Results ━━━"
	@ls $(RESULTS)/*.json 2>/dev/null | head -1 >/dev/null || \
		(echo "[ERROR] No result JSON files found in $(RESULTS)/"; \
		 echo "        Copy Windows client results here first."; exit 1)
	$(PYTHON) $(ANALYSIS)/analyze.py

analyze-no-pcap:
	$(PYTHON) $(ANALYSIS)/analyze.py --no-pcap

analyze-no-plot:
	$(PYTHON) $(ANALYSIS)/analyze.py --no-plot

reset:
	@echo "Clearing all network impairment..."
	@sudo pfctl -d 2>/dev/null || true
	@sudo dnctl -q flush 2>/dev/null || true
	@echo "Done. Network restored."

clean-results:
	@echo "Removing all results and captures..."
	@rm -f $(RESULTS)/*.json $(CAPTURES)/*.pcap
	@echo "Done."

clean: clean-results
	@rm -f $(REPORT)/*.png

help:
	@echo ""
	@echo "  CPE 400 TCP Reliability Analysis"
	@echo "  ─────────────────────────────────────────────────────"
	@echo "  make setup          Install dependencies (macOS)"
	@echo "  make check          Verify all tools are installed"
	@echo "  make server         Start macOS server (interactive)"
	@echo "  make analyze        Parse results + generate plots"
	@echo "  make analyze-no-pcap  Analyze without pcap parsing"
	@echo "  make reset          Emergency: clear network impairment"
	@echo "  make clean          Remove results, captures, plots"
	@echo ""
	@echo "  ─────────────────────────────────────────────────────"
	@echo "  Workflow:"
	@echo "    macOS:   make setup → make server (choose mode 2)"
	@echo "    Windows: python scripts/win_client.py"
	@echo "    macOS:   copy results/ from Windows → make analyze"
	@echo ""
