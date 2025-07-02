# CLAUDE.md

## Cookie Extraction

Before navigating to any domain with Playwright:
1. Run `./getcookie.py <domain>` to extract cookies
2. Open the domain in Playwright, but notify the user they may need to restart Claude Code with `claude -r` to pick up the new cookies

Setup: Run `./setup.sh` once to configure MCP.