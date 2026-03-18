#!/bin/bash
# Bit Rage Labour GitHub Integration Runner
# Usage: ./run_github_integration.sh [command] [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') - $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if GitHub CLI is installed
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed. Please install it first:"
        log_error "  - Download from: https://cli.github.com/"
        log_error "  - Or run: brew install gh (macOS)"
        exit 1
    fi

    # Check if user is authenticated
    if ! gh auth status &> /dev/null; then
        log_warning "GitHub CLI is not authenticated. Running setup..."
        gh auth login
    fi

    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not available. Please install Python 3."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Setup virtual environment
setup_venv() {
    log_info "Setting up virtual environment..."

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "Virtual environment created"
    fi

    source venv/bin/activate
    pip install -q -r ../requirements.txt
    log_success "Dependencies installed"
}

# Main command processing
COMMAND="${1:-help}"
shift

case "$COMMAND" in
    "sync")
        log_info "Syncing portfolio repositories..."
        check_prerequisites
        setup_venv
        python3 github_integration_system.py
        ;;

    "create")
        REPO_NAME="$1"
        if [ -z "$REPO_NAME" ]; then
            log_error "Repository name required. Usage: ./run_github_integration.sh create <repo-name>"
            exit 1
        fi
        log_info "Creating repository: $REPO_NAME"
        check_prerequisites
        setup_venv
        python3 -c "
from github_integration_system import GitHubIntegrationSystem
system = GitHubIntegrationSystem()
system.create_repository('$REPO_NAME', '$REPO_NAME - Bit Rage Labour Project', True)
        "
        ;;

    "setup")
        REPO_NAME="$1"
        if [ -z "$REPO_NAME" ]; then
            log_error "Repository name required. Usage: ./run_github_integration.sh setup <repo-name>"
            exit 1
        fi
        log_info "Setting up repository: $REPO_NAME"
        check_prerequisites
        setup_venv
        python3 -c "
from github_integration_system import GitHubIntegrationSystem
system = GitHubIntegrationSystem()
system.setup_repository_protection('$REPO_NAME')
system.setup_security_features('$REPO_NAME')
        "
        ;;

    "pr")
        REPO_NAME="$1"
        TITLE="$2"
        BODY="$3"
        if [ -z "$REPO_NAME" ] || [ -z "$TITLE" ]; then
            log_error "Usage: ./run_github_integration.sh pr <repo-name> <title> <body>"
            exit 1
        fi
        log_info "Creating PR in $REPO_NAME: $TITLE"
        check_prerequisites
        setup_venv
        python3 -c "
from github_integration_system import GitHubIntegrationSystem
system = GitHubIntegrationSystem()
system.create_pull_request('$REPO_NAME', '$TITLE', '$BODY', 'feature-branch')
        "
        ;;

    "help"|*)
        echo "Bit Rage Labour GitHub Integration Runner"
        echo "Usage: ./run_github_integration.sh <command> [options]"
        echo ""
        echo "Commands:"
        echo "  sync                    Sync all portfolio repositories"
        echo "  create <repo-name>      Create a new repository"
        echo "  setup <repo-name>       Setup protection and security for repository"
        echo "  pr <repo-name> <title> <body>  Create a pull request"
        echo "  help                    Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_github_integration.sh sync"
        echo "  ./run_github_integration.sh create my-new-project"
        echo "  ./run_github_integration.sh setup my-project"
        ;;
esac