#!/usr/bin/env bash
# ── DIGITAL LABOUR — Railway Deployment Helper ──
# Usage: bash scripts/deploy.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================"
echo "  DIGITAL LABOUR — Railway Deployment"
echo "================================================"
echo ""

# ── 1. Check for Railway CLI ──
if ! command -v railway &> /dev/null; then
    echo -e "${RED}ERROR: Railway CLI not found.${NC}"
    echo "Install it with: npm install -g @railway/cli"
    echo "  or: brew install railway (macOS)"
    echo "  or: curl -fsSL https://railway.app/install.sh | sh"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Railway CLI found: $(railway --version 2>/dev/null || echo 'installed')"

# ── 2. Check Railway login ──
if ! railway whoami &> /dev/null 2>&1; then
    echo -e "${YELLOW}WARNING: Not logged in to Railway. Running 'railway login'...${NC}"
    railway login
fi
echo -e "${GREEN}[OK]${NC} Railway authenticated"

# ── 3. Validate .env has required keys ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

REQUIRED_KEYS=(
    "ANTHROPIC_API_KEY"
    "OPENAI_API_KEY"
    "STRIPE_SECRET_KEY"
)

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}ERROR: .env file not found at $ENV_FILE${NC}"
    echo "Create one from .env.example or set variables in Railway dashboard."
    exit 1
fi

echo ""
echo "Checking required environment variables..."
MISSING=0
for key in "${REQUIRED_KEYS[@]}"; do
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        VALUE=$(grep "^${key}=" "$ENV_FILE" | cut -d'=' -f2-)
        if [ -z "$VALUE" ] || [ "$VALUE" = '""' ] || [ "$VALUE" = "''" ]; then
            echo -e "  ${YELLOW}[EMPTY]${NC} $key is set but empty"
            MISSING=$((MISSING + 1))
        else
            echo -e "  ${GREEN}[OK]${NC}    $key"
        fi
    else
        echo -e "  ${RED}[MISS]${NC}  $key not found in .env"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}WARNING: $MISSING required key(s) missing or empty.${NC}"
    echo "Set them in the Railway dashboard under Variables."
    read -p "Continue anyway? (y/N): " CONTINUE
    if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
        echo "Aborted."
        exit 1
    fi
fi

# ── 4. Deploy to Railway ──
echo ""
echo "Deploying to Railway..."
echo ""
cd "$PROJECT_ROOT"
railway up --detach

# ── 5. Print deployment info ──
echo ""
echo "================================================"
echo -e "${GREEN}Deployment initiated!${NC}"
echo "================================================"
echo ""
echo "Useful commands:"
echo "  railway status        — Check deployment status"
echo "  railway logs          — View live logs"
echo "  railway open          — Open app in browser"
echo "  railway domain        — Show/add custom domain"
echo "  railway variables     — Manage env variables"
echo ""
echo "Set environment variables in Railway dashboard:"
echo "  ANTHROPIC_API_KEY, OPENAI_API_KEY, STRIPE_SECRET_KEY"
echo "  (never commit these to git)"
echo ""
