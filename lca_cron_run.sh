#!/bin/bash
# LCA status check — runs lca_notify_direct.py via uv
# Called by system crontab
#
# Setup:
#   1. Run `python3 lca_notify_direct.py --setup` once to create lca_config.json
#   2. Add to crontab: crontab -e
#      Example (PT times):
#        0 6  * * 1  /path/to/lca_cron_run.sh   # Mon 6AM
#        0 10 * * 1  /path/to/lca_cron_run.sh   # Mon 10AM
#        0 13 * * 1  /path/to/lca_cron_run.sh   # Mon 1PM
#        0 17 * * 5  /path/to/lca_cron_run.sh   # Fri 5PM

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GMAIL_MCP_DIR="/Users/t/workspace/gmail-tools-mcp"

cd "$GMAIL_MCP_DIR" || exit 1

uv run python3 "$SCRIPT_DIR/lca_notify_direct.py" >> "$SCRIPT_DIR/lca_cron.log" 2>&1
