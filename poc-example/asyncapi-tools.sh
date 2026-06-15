#!/bin/bash
# AsyncAPI tooling script for validation and documentation generation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}AsyncAPI Tooling${NC}"
echo "================================"

# Check if AsyncAPI CLI is installed
if ! command -v asyncapi &> /dev/null; then
  echo -e "${RED}Error: AsyncAPI CLI not found${NC}"
  echo "Install it with: npm install -g @asyncapi/cli"
  exit 1
fi

# Validate the AsyncAPI spec
echo -e "\n${YELLOW}Validating AsyncAPI specification...${NC}"
if asyncapi validate asyncapi.yaml; then
  echo -e "${GREEN}✓ AsyncAPI spec is valid${NC}"
else
  echo -e "${RED}✗ AsyncAPI spec validation failed${NC}"
  exit 1
fi

# Show how to view documentation
echo -e "\n${YELLOW}To view interactive documentation with live reload:${NC}"
echo -e "  ${GREEN}make docs-preview${NC}"
echo -e "\n${YELLOW}Or run Docker command directly:${NC}"
echo -e "  ${GREEN}docker run --rm -it --user=root \\\\${NC}"
echo -e "  ${GREEN}  -p 3001:3001 \\\\${NC}"
echo -e "  ${GREEN}  -v /home/jsl/mezcada/poc/johl-nats:/app \\\\${NC}"
echo -e "  ${GREEN}  -w /app \\\\${NC}"
echo -e "  ${GREEN}  asyncapi/cli start studio /app/asyncapi.yaml --port 3001${NC}"
echo -e "\n${YELLOW}Then open: ${GREEN}http://localhost:3001?liveServer=3001&studio-version=1.2.0${NC}"
echo -e "\n${YELLOW}Edit asyncapi.yaml in VS Code - changes auto-reload in browser!${NC}"
echo -e "\n${YELLOW}For static HTML generation:${NC}"
echo -e "  ${GREEN}make docs-generate${NC} ${YELLOW}(currently broken - shows workaround)${NC}"

echo -e "\n${GREEN}All AsyncAPI tasks completed successfully!${NC}"
