#!/bin/bash
set -e

echo "Chrome Cookie Copy for Playwright - Setup"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check for uv
echo -e "${YELLOW}Checking for uv...${NC}"
if ! command -v uv >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi
echo -e "${GREEN}✓ uv is ready${NC}"

# Create cookies directory and storage.json
echo -e "${YELLOW}Creating cookies directory...${NC}"
mkdir -p "$SCRIPT_DIR/cookies"
cat > "$SCRIPT_DIR/cookies/storage.json" << 'EOF'
{
  "cookies": [],
  "origins": []
}
EOF
echo -e "${GREEN}✓ Created cookies/storage.json${NC}"

# Create .mcp.json for Claude
echo -e "${YELLOW}Creating MCP configuration...${NC}"
cat > "$SCRIPT_DIR/.mcp.json" << 'EOF'
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--isolated",
        "--storage-state=cookies/storage.json"
      ],
      "env": {}
    }
  }
}
EOF
echo -e "${GREEN}✓ Created .mcp.json${NC}"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo "==============="
echo ""

# Pre-load cookies for domains
echo -e "${YELLOW}Pre-load cookies (optional)${NC}"
echo "You can now extract cookies from domains you're logged into."
echo ""

while true; do
    echo -n "Domain to extract cookies from (or press Enter to skip): "
    read domain
    
    if [ -z "$domain" ]; then
        break
    fi
    
    echo "Extracting cookies for $domain..."
    if ./getcookie.py "$domain" 2>/dev/null; then
        echo -e "${GREEN}✓ Successfully extracted cookies for $domain${NC}"
    else
        echo -e "${RED}✗ Failed to extract cookies for $domain${NC}"
        echo "  Make sure you're logged into https://$domain in Chrome"
    fi
    
    echo ""
done

echo ""
echo "To use Chrome cookies with Playwright:"
echo ""
echo "1. Load cookies from a website:"
echo "   ./getcookie.py <domain>"
echo "   Example: ./getcookie.py github.com"
echo ""
echo "2. Restart Claude Code to load the MCP server"
echo ""
echo "3. Use Playwright tools to navigate - cookies will be included!"
echo ""
echo "Note: Make sure you're logged into the website in Chrome first."