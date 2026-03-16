# Golden Path for YouTube Drop + Second Brain Integration
URL ?= https://www.youtube.com/watch?v=0TpON5T-Sw4
VID ?= $(shell python3 -c "import re,sys;print(re.search(r'v=([^&]+)', '$(URL)').group(1))" 2>/dev/null || echo "unknown")
REPO_ROOT := $(shell cd .. && pwd)
BASE_DIR := $(REPO_ROOT)/knowledge/secondbrain/$(shell date +%Y/%m)/$(VID)
PYTHON := $(REPO_ROOT)/.venv/bin/python3

.PHONY: all ingest enrich commit brief clean

all: ingest enrich commit brief

ingest:
	@echo "=== INGEST: $(URL) ==="
	@mkdir -p $(BASE_DIR)
	cd $(REPO_ROOT) && $(PYTHON) tools/youtubedrop/fetch.py "$(URL)" --out "$(BASE_DIR)"
	@test -f "$(BASE_DIR)/raw.txt" || (echo "ERROR: Transcript missing"; exit 1)
	@echo "Done - Ingest complete: $(BASE_DIR)"

enrich:
	@echo "=== ENRICH: $(VID) ==="
	cd $(REPO_ROOT) && $(PYTHON) tools/enrich.py "$(BASE_DIR)" "$(VID)" "$(URL)"

commit:
	@echo "=== CATALOG COMMIT: $(VID) ==="
	cd $(REPO_ROOT) && $(PYTHON) -m agents.ncl_catalog "$(BASE_DIR)/enrich.json"
	@echo "Done - Catalog commit complete"

brief:
	@echo "=== OPS BRIEF: $(VID) ==="
	cd $(REPO_ROOT) && $(PYTHON) tools/queue_brief.py "$(BASE_DIR)/enrich.json"

clean:
	@echo "Cleaning $(BASE_DIR)..."
	@rm -rf $(BASE_DIR)

status:
	@echo "Video ID: $(VID)"
	@echo "Base dir: $(BASE_DIR)"
	@echo "Files present:"
	@ls -la $(BASE_DIR) 2>/dev/null || echo "  (directory not created yet)"
