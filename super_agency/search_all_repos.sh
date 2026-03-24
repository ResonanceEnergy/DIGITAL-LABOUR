#!/bin/bash
# Bit Rage Systems Repository Search Tool
# Searches across all repositories in the ResonanceEnergy portfolio

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Repository list from portfolio.json
REPOS=(
    "NATEBJONES"
    "NCL"
    "TESLACALLS2026"
    "future-predictor-council"
    "AAC"
    "ADVENTUREHEROAUTO"
    "Crimson-Compass"
    "YOUTUBEDROP"
    "CIVIL-FORGE-TECHNOLOGIES-"
    "GEET-PLASMA-PROJECT"
    "TESLA-TECH"
    "ELECTRIC-UNIVERSE"
    "VORTEX-HUNTER"
    "MircoHydro"
    "electric-ice"
    "SUPERSTONK-TRADER"
    "HUMAN-HEALTH"
    "Adventure-Hero-Chronicles-Of-Glory"
    "QDFG1"
    "NCC-Doctrine"
    "NCC"
    "resonance-uy-py"
    "perpetual-flow-cube"
    "demo"
    "Resonance-Energy-Systems"
    "ResonanceEnergy_Enterprise"
    "Super-Agency"
)

ORG="ResonanceEnergy"

# Function to display usage
usage() {
    echo -e "${BLUE}Bit Rage Systems Repository Search Tool${NC}"
    echo "=========================================="
    echo ""
    echo "Usage: $0 [OPTIONS] SEARCH_TERM"
    echo ""
    echo "Options:"
    echo "  -f, --file PATTERN    Search for files matching PATTERN"
    echo "  -c, --content TERM    Search for content containing TERM (default)"
    echo "  -r, --repo REPO       Search only in specific repository"
    echo "  -t, --type EXT        Search only files with extension EXT"
    echo "  -l, --list            List all repositories"
    echo "  -h, --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 'Agent AZ'                    # Search for 'Agent AZ' in all repos"
    echo "  $0 -f '*.py'                     # Find all Python files"
    echo "  $0 -r NCL -c 'neural'            # Search for 'neural' only in NCL repo"
    echo "  $0 -t '.md' -c 'roadmap'         # Search for 'roadmap' in markdown files"
    echo ""
    echo "Total repositories: ${#REPOS[@]}"
}

# Function to list all repositories
list_repos() {
    echo -e "${BLUE}ResonanceEnergy Repository Portfolio${NC}"
    echo "====================================="
    echo ""
    echo "Total repositories: ${#REPOS[@]}"
    echo ""

    for repo in "${REPOS[@]}"; do
        echo "• $repo"
    done
    echo ""
}

# Function to search GitHub API for content
search_github_content() {
    local query="$1"
    local repo="$2"
    local file_type="$3"

    echo -e "${YELLOW}Searching GitHub for '$query' in $repo...${NC}"

    # Construct GitHub search URL
    local url="https://api.github.com/search/code?q=$query+repo:$ORG/$repo"
    if [ -n "$file_type" ]; then
        url="$url+extension:$file_type"
    fi

    # Make API request (requires GitHub token for higher rate limits)
    if [ -n "$GITHUB_TOKEN" ]; then
        response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "$url")
    else
        response=$(curl -s "$url")
    fi

    # Check for rate limiting
    if echo "$response" | jq -e '.message' >/dev/null 2>&1; then
        message=$(echo "$response" | jq -r '.message')
        if [[ "$message" == *"rate limit"* ]]; then
            echo -e "${RED}GitHub API rate limit exceeded. Set GITHUB_TOKEN environment variable for higher limits.${NC}"
            return 1
        fi
    fi

    # Parse results
    total_count=$(echo "$response" | jq -r '.total_count // 0')

    if [ "$total_count" -gt 0 ]; then
        echo -e "${GREEN}Found $total_count matches in $repo:${NC}"

        # Show first 10 results
        echo "$response" | jq -r '.items[0:10][] | "  📄 \(.name) - \(.path)\n    🔗 \(.html_url)"'

        if [ "$total_count" -gt 10 ]; then
            echo -e "${YELLOW}  ... and $((total_count - 10)) more results${NC}"
        fi
    else
        echo -e "${YELLOW}No matches found in $repo${NC}"
    fi

    echo ""
}

# Function to search local workspace (current directory)
search_local_workspace() {
    local search_term="$1"
    local search_type="$2"
    local file_pattern="$3"

    echo -e "${YELLOW}Searching local workspace...${NC}"

    case "$search_type" in
        "file")
            # Search for files matching pattern
            find . -name "$search_term" -type f 2>/dev/null | head -20 | while read -r file; do
                echo -e "${GREEN}Found file:${NC} $file"
            done
            ;;
        "content")
            # Search for content
            if [ -n "$file_pattern" ]; then
                grep -r "$search_term" . --include="$file_pattern" 2>/dev/null | head -20 | while read -r line; do
                    file=$(echo "$line" | cut -d: -f1)
                    content=$(echo "$line" | cut -d: -f2-)
                    echo -e "${GREEN}$file:${NC} $content"
                done
            else
                grep -r "$search_term" . 2>/dev/null | grep -v ".git/" | grep -v "__pycache__" | head -20 | while read -r line; do
                    file=$(echo "$line" | cut -d: -f1)
                    content=$(echo "$line" | cut -d: -f2-)
                    echo -e "${GREEN}$file:${NC} $content"
                done
            fi
            ;;
    esac
}

# Main search function
perform_search() {
    local search_term="$1"
    local search_type="$2"
    local specific_repo="$3"
    local file_type="$4"

    echo -e "${BLUE}🔍 Bit Rage Systems Repository Search${NC}"
    echo "=================================="
    echo "Search term: '$search_term'"
    echo "Search type: $search_type"
    if [ -n "$specific_repo" ]; then
        echo "Repository: $specific_repo"
    else
        echo "Scope: All ${#REPOS[@]} repositories"
    fi
    if [ -n "$file_type" ]; then
        echo "File type: $file_type"
    fi
    echo ""

    # URL encode search term for GitHub API
    encoded_term=$(echo "$search_term" | sed 's/ /%20/g' | sed 's/"/%22/g')

    if [ -n "$specific_repo" ]; then
        # Search specific repository
        search_github_content "$encoded_term" "$specific_repo" "$file_type"
    else
        # Search all repositories (but limit to avoid rate limits)
        echo -e "${YELLOW}Note: Searching all 27 repos via GitHub API. This may take time and hit rate limits.${NC}"
        echo -e "${YELLOW}Consider using -r flag to search specific repositories.${NC}"
        echo ""
        for repo in "${REPOS[@]}"; do
            search_github_content "$encoded_term" "$repo" "$file_type"
            # Add small delay to avoid rate limiting
            sleep 0.5
        done
    fi

    # Always search local workspace
    echo -e "${BLUE}📁 Local Workspace Search${NC}"
    echo "=========================="
    search_local_workspace "$search_term" "$search_type" "$file_type"
}

# Parse command line arguments
SEARCH_TYPE="content"
SEARCH_TERM=""
SPECIFIC_REPO=""
FILE_TYPE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file)
            SEARCH_TYPE="file"
            SEARCH_TERM="$2"
            shift 2
            ;;
        -c|--content)
            SEARCH_TYPE="content"
            SEARCH_TERM="$2"
            shift 2
            ;;
        -r|--repo)
            SPECIFIC_REPO="$2"
            shift 2
            ;;
        -t|--type)
            FILE_TYPE="$2"
            shift 2
            ;;
        -l|--list)
            list_repos
            exit 0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -z "$SEARCH_TERM" ]; then
                SEARCH_TERM="$1"
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [ -z "$SEARCH_TERM" ] && [ "$SEARCH_TYPE" != "list" ]; then
    echo -e "${RED}Error: Search term required${NC}"
    echo ""
    usage
    exit 1
fi

# Perform search
perform_search "$SEARCH_TERM" "$SEARCH_TYPE" "$SPECIFIC_REPO" "$FILE_TYPE"
