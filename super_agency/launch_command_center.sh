#!/bin/bash
# DIGITAL LABOUR Distributed Command Center Launcher
# One-command setup and launch for the entire distributed system

set -e

echo "🚀 DIGITAL LABOUR Distributed Command Center"
echo "=========================================="
echo ""

# Detect platform
detect_platform() {
    case "$(uname -s)" in
        Darwin)
            echo "macos"
            ;;
        Linux)
            echo "linux"
            ;;
        CYGWIN*|MINGW32*|MSYS*|MINGW*)
            echo "windows"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

PLATFORM=$(detect_platform)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    case $PLATFORM in
        macos)
            if ! command -v brew &> /dev/null; then
                log_error "Homebrew not found. Install from https://brew.sh/"
                exit 1
            fi
            ;;
        linux)
            if ! command -v apt-get &> /dev/null && ! command -v yum &> /dev/null; then
                log_warning "Package manager not detected. Manual installation may be required."
            fi
            ;;
        windows)
            if ! command -v choco &> /dev/null; then
                log_error "Chocolatey not found. Install from https://chocolatey.org/"
                exit 1
            fi
            ;;
    esac

    log_success "Prerequisites check passed"
}

# Setup local environment
setup_local() {
    log_info "Setting up local environment..."

    case $PLATFORM in
        macos)
            # Run macOS setup
            if [ -f "setup/macos-setup.sh" ]; then
                chmod +x setup/macos-setup.sh
                ./setup/macos-setup.sh
            else
                log_error "macOS setup script not found"
                exit 1
            fi
            ;;
        windows)
            # Run Windows setup
            if [ -f "setup/windows-setup.ps1" ]; then
                powershell -ExecutionPolicy Bypass -File setup/windows-setup.ps1
            else
                log_error "Windows setup script not found"
                exit 1
            fi
            ;;
        linux)
            log_warning "Linux setup not yet implemented. Please set up manually."
            ;;
    esac

    log_success "Local environment setup complete"
}

# Setup cloud infrastructure
setup_cloud() {
    log_info "Setting up cloud infrastructure..."

    if ! command -v terraform &> /dev/null; then
        log_error "Terraform not found. Install from https://terraform.io/"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Install from https://aws.amazon.com/cli/"
        exit 1
    fi

    cd infrastructure

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure'"
        exit 1
    fi

    # Initialize and apply Terraform
    terraform init
    terraform validate
    terraform plan -out=tfplan
    terraform apply tfplan

    cd ..
    log_success "Cloud infrastructure setup complete"
}

# Launch services
launch_services() {
    log_info "Launching command center services..."

    # Launch Matrix Monitor
    if [ -f "matrix_maximizer.py" ]; then
        log_info "Starting Matrix Maximizer..."
        python3 matrix_maximizer.py &
        echo $! > .matrix_monitor.pid
    fi

    # Launch Operations Interface
    if [ -f "operations_api.py" ]; then
        log_info "Starting Operations API..."
        python3 operations_api.py &
        echo $! > .operations.pid
    fi

    # Launch Galactia Doctrine (if configured)
    if [ -f "galactia_config.json" ]; then
        log_info "Starting Galactia Doctrine..."
        python3 -m galactia_integration &
        echo $! > .galactia.pid
    fi

    # Launch iOS app (if on macOS)
    if [ "$PLATFORM" = "macos" ] && [ -d "ios/DIGITAL LABOURCommand" ]; then
        log_info "Opening iOS project..."
        open ios/DIGITAL LABOURCommand/DIGITAL LABOURCommand.xcodeproj
    fi

    log_success "Services launched successfully"
}

# Show status
show_status() {
    echo ""
    log_success "DIGITAL LABOUR Command Center Status"
    echo "====================================="

    # Check local services
    echo "Local Services:"
    if [ -f ".matrix_monitor.pid" ] && kill -0 $(cat .matrix_monitor.pid) 2>/dev/null; then
        echo "  ✅ Matrix Monitor: Running (PID: $(cat .matrix_monitor.pid))"
    else
        echo "  ❌ Matrix Monitor: Not running"
    fi

    if [ -f ".operations.pid" ] && kill -0 $(cat .operations.pid) 2>/dev/null; then
        echo "  ✅ Operations Interface: Running (PID: $(cat .operations.pid))"
    else
        echo "  ❌ Operations Interface: Not running"
    fi

    if [ -f ".galactia.pid" ] && kill -0 $(cat .galactia.pid) 2>/dev/null; then
        echo "  ✅ Galactia Doctrine: Running (PID: $(cat .galactia.pid))"
    else
        echo "  ❌ Galactia Doctrine: Not running"
    fi

    # Check cloud status
    echo ""
    echo "Cloud Infrastructure:"
    if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
        echo "  ✅ AWS: Configured"

        # Check EC2 instances
        INSTANCE_COUNT=$(aws ec2 describe-instances --filters "Name=tag:Project,Values=DIGITAL LABOUR" "Name=instance-state-name,Values=running" --query 'length(Reservations[*].Instances[*])' --output text 2>/dev/null || echo "0")
        echo "  📊 EC2 Instances: $INSTANCE_COUNT running"

        # Check S3 bucket
        if aws s3 ls s3://Digital-Labour-storage &> /dev/null; then
            echo "  ✅ S3 Storage: Available"
        else
            echo "  ❌ S3 Storage: Not accessible"
        fi
    else
        echo "  ❌ AWS: Not configured"
    fi

    echo ""
    echo "Access Points:"
    echo "  🌐 Matrix Monitor: http://localhost:3000"
    echo "  🎯 Operations: http://localhost:5000"
    echo "  📱 iOS App: Open in Xcode (macOS only)"
    echo "  ☁️  Cloud API: Check Terraform outputs"
}

# Stop services
stop_services() {
    log_info "Stopping command center services..."

    # Stop local services
    for pid_file in .*.pid; do
        if [ -f "$pid_file" ]; then
            PID=$(cat "$pid_file")
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                log_success "Stopped $(basename "$pid_file" .pid) (PID: $PID)"
            fi
            rm "$pid_file"
        fi
    done

    log_success "All services stopped"
}

# Main menu
show_menu() {
    echo ""
    echo "DIGITAL LABOUR Command Center Menu"
    echo "================================="
    echo "1. Setup Everything (Local + Cloud)"
    echo "2. Setup Local Only"
    echo "3. Setup Cloud Only"
    echo "4. Launch Services"
    echo "5. Show Status"
    echo "6. Stop Services"
    echo "7. Quick Start (Setup + Launch)"
    echo "8. Exit"
    echo ""
    read -p "Choose an option (1-8): " choice
    echo ""
}

# Main logic
main() {
    # Parse command line arguments
    case "${1:-}" in
        --setup-all)
            check_prerequisites
            setup_local
            setup_cloud
            launch_services
            show_status
            ;;
        --setup-local)
            check_prerequisites
            setup_local
            ;;
        --setup-cloud)
            setup_cloud
            ;;
        --launch)
            launch_services
            show_status
            ;;
        --status)
            show_status
            ;;
        --stop)
            stop_services
            ;;
        --quick-start)
            check_prerequisites
            setup_local
            launch_services
            show_status
            ;;
        *)
            # Interactive menu
            while true; do
                show_menu
                case $choice in
                    1)
                        check_prerequisites
                        setup_local
                        setup_cloud
                        launch_services
                        show_status
                        ;;
                    2)
                        check_prerequisites
                        setup_local
                        ;;
                    3)
                        setup_cloud
                        ;;
                    4)
                        launch_services
                        show_status
                        ;;
                    5)
                        show_status
                        ;;
                    6)
                        stop_services
                        ;;
                    7)
                        check_prerequisites
                        setup_local
                        launch_services
                        show_status
                        ;;
                    8)
                        log_success "Goodbye! 👋"
                        exit 0
                        ;;
                    *)
                        log_error "Invalid option. Please choose 1-8."
                        ;;
                esac
                echo ""
                read -p "Press Enter to continue..."
            done
            ;;
    esac
}

# Run main function
main "$@"
