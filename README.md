# Chrome Cookie Copy for Playwright

Use your Chrome browser cookies with Playwright in Claude Code - no manual login needed!

## Setup

```bash
git clone https://github.com/nsthorat/claude-playwright-cookie-copy
cd claude-playwright-cookie-copy
./setup.sh
```

## Usage

Just ask Claude to open any website:

```
You: Open github.com in playwright
Claude: [Automatically extracts cookies and opens GitHub with your authenticated session]
```

**Note:** After visiting a new domain for the first time, restart Claude Code with `claude -r` to load the cookies.

## Requirements

- macOS (for Chrome cookie decryption)
- Chrome browser
- Claude Code

## Troubleshooting

- **"No cookies found"**: Make sure you're logged into the website in Chrome first
- **Cookies not working**: Try a different Chrome profile with `./getcookie.py domain "Profile 1"`

## How it Works

1. Extracts cookies from your Chrome browser
2. Decrypts them using macOS Keychain
3. Saves them in Playwright's storage format
4. Configures Claude's Playwright MCP server to use these cookies

Claude automatically extracts cookies when navigating to a domain, but you need to restart Claude Code after the first visit to load them.