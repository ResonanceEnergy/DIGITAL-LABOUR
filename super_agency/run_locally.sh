#!/usr/bin/env bash
# Bit Rage Systems Local Runner
# Comprehensive step-by-step execution and monitoring

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
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

log_header() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}========================================${NC}"
}

# Progress tracking
PROGRESS_FILE="$ROOT_DIR/.super_agency_progress"
MONITORING_DIR="$ROOT_DIR/monitoring"
REPORTS_DIR="$ROOT_DIR/reports"

mkdir -p "$MONITORING_DIR"
mkdir -p "$REPORTS_DIR"

update_progress() {
    local step="$1"
    local status="$2"
    local details="$3"

    echo "$(date '+%Y-%m-%d %H:%M:%S')|$step|$status|$details" >> "$PROGRESS_FILE"

    if [ "$status" = "STARTED" ]; then
        log_info "Started: $step"
    elif [ "$status" = "COMPLETED" ]; then
        log_success "Completed: $step"
    elif [ "$status" = "FAILED" ]; then
        log_error "Failed: $step - $details"
    fi
}

check_dependencies() {
    log_header "CHECKING DEPENDENCIES"

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$(python3 --version)
        log_success "Python found: $PYTHON_VERSION"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        PYTHON_VERSION=$(python --version)
        log_success "Python found: $PYTHON_VERSION"
    else
        log_error "Python not found. Please install Python 3.7+"
        exit 1
    fi

    # Check required Python packages
    log_info "Checking Python packages..."
    $PYTHON_CMD -c "import flask, multiprocessing, sqlite3, json" 2>/dev/null
    if [ $? -eq 0 ]; then
        log_success "Required Python packages available"
    else
        log_warning "Some Python packages may be missing. Installing requirements..."
        if [ -f "$ROOT_DIR/repos/AAC/requirements.txt" ]; then
            pip install -r "$ROOT_DIR/repos/AAC/requirements.txt" || log_warning "Could not install AAC requirements"
        fi
    fi

    # Check system resources
    CPU_CORES=$(nproc 2>/dev/null || echo "4")
    TOTAL_MEM=$(free -h | awk 'NR==2{printf "%.0f", $2}' 2>/dev/null || echo "8")
    log_info "System Resources: $CPU_CORES CPU cores, ${TOTAL_MEM}GB RAM"
}

start_inner_council() {
    log_header "STARTING INNER COUNCIL"

    update_progress "inner_council" "STARTED" "Deploying autonomous agents"

    cd "$ROOT_DIR/inner_council"

    # Start Inner Council agents
    log_info "Deploying Inner Council agents..."
    if $PYTHON_CMD deploy_agents.py --mode deploy --duration 300; then
        update_progress "inner_council" "COMPLETED" "Agents deployed successfully"
        log_success "Inner Council agents deployed"
    else
        update_progress "inner_council" "FAILED" "Agent deployment failed"
        log_error "Inner Council deployment failed"
        return 1
    fi
}

start_aac_system() {
    log_header "STARTING AAC FINANCIAL SYSTEM"

    update_progress "aac_system" "STARTED" "Initializing financial operations"

    cd "$ROOT_DIR/repos/AAC"

    # Initialize AAC database
    log_info "Initializing AAC accounting engine..."
    if $PYTHON_CMD aac_engine.py; then
        log_success "AAC engine initialized"
    else
        log_error "AAC engine initialization failed"
        update_progress "aac_system" "FAILED" "Engine initialization failed"
        return 1
    fi

    # Start compliance monitoring
    log_info "Starting compliance monitoring..."
    $PYTHON_CMD aac_compliance.py &
    COMPLIANCE_PID=$!
    echo $COMPLIANCE_PID > "$MONITORING_DIR/compliance.pid"

    # Start financial intelligence
    log_info "Starting financial intelligence..."
    $PYTHON_CMD aac_intelligence.py &
    INTEL_PID=$!
    echo $INTEL_PID > "$MONITORING_DIR/intelligence.pid"

    # Start web dashboard
    log_info "Starting AAC web dashboard..."
    $PYTHON_CMD run_aac.py --web &
    WEB_PID=$!
    echo $WEB_PID > "$MONITORING_DIR/aac_web.pid"

    update_progress "aac_system" "COMPLETED" "AAC system fully operational"
    log_success "AAC system started - Dashboard at http://localhost:5000"
}

start_cpu_maximization() {
    local mode="${1:-balanced}"
    local duration="${2:-10}"

    log_header "STARTING CPU MAXIMIZATION ($mode mode, ${duration}min)"

    update_progress "cpu_maximization" "STARTED" "Mode: $mode, Duration: ${duration}min"

    cd "$ROOT_DIR"

    log_info "Starting CPU maximization in $mode mode..."
    if $PYTHON_CMD cpu_control_center.py "$mode" --duration "$duration"; then
        update_progress "cpu_maximization" "COMPLETED" "CPU maximization completed successfully"
        log_success "CPU maximization completed"
    else
        update_progress "cpu_maximization" "FAILED" "CPU maximization failed"
        log_error "CPU maximization failed"
        return 1
    fi
}

run_daily_operations() {
    log_header "RUNNING DAILY OPERATIONS"

    update_progress "daily_operations" "STARTED" "Executing daily operational cycle"

    cd "$ROOT_DIR"

    log_info "Running daily operations cycle..."
    if ./bin/run_daily.sh; then
        update_progress "daily_operations" "COMPLETED" "Daily operations completed"
        log_success "Daily operations completed"
    else
        update_progress "daily_operations" "FAILED" "Daily operations failed"
        log_error "Daily operations failed"
        return 1
    fi
}

monitor_system() {
    log_header "SYSTEM MONITORING ACTIVE"

    local duration="${1:-300}"

    log_info "Starting system monitoring for ${duration}s..."

    local start_time=$(date +%s)
    local end_time=$((start_time + duration))

    while [ $(date +%s) -lt $end_time ]; do
        # CPU and Memory monitoring
        local cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
        local mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')

        # Process monitoring
        local active_processes=$(ps aux | grep -E "(python|cpu_maximizer|aac_|inner_council)" | grep -v grep | wc -l)

        # Log metrics
        echo "$(date '+%Y-%m-%d %H:%M:%S')|CPU:${cpu_usage}%|MEM:${mem_usage}%|PROCESSES:$active_processes" >> "$MONITORING_DIR/system_metrics.log"

        # Display current status
        echo -ne "\r${CYAN}[MONITOR]${NC} CPU: ${cpu_usage}%% | MEM: ${mem_usage}%% | PROCESSES: $active_processes | Time: $(($(date +%s) - start_time))/${duration}s"

        sleep 5
    done

    echo "" # New line after progress
    log_success "Monitoring completed - check $MONITORING_DIR/system_metrics.log"
}

generate_reports() {
    log_header "GENERATING SYSTEM REPORTS"

    update_progress "report_generation" "STARTED" "Creating comprehensive reports"

    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local report_file="$REPORTS_DIR/super_agency_report_$timestamp.md"

    cat > "$report_file" << EOF
# Bit Rage Systems System Report
**Generated:** $(date)
**Duration:** Session run
**Status:** Active

## System Status
EOF

    # Add system information
    echo "### System Resources" >> "$report_file"
    echo "- CPU Cores: $(nproc 2>/dev/null || echo 'Unknown')" >> "$report_file"
    echo "- Total Memory: $(free -h | awk 'NR==2{print $2}' 2>/dev/null || echo 'Unknown')" >> "$report_file"
    echo "- Disk Free: $(df -h . | awk 'NR==2{print $4}' 2>/dev/null || echo 'Unknown')" >> "$report_file"

    # Add progress information
    echo "" >> "$report_file"
    echo "### Progress Summary" >> "$report_file"
    if [ -f "$PROGRESS_FILE" ]; then
        echo "| Timestamp | Step | Status | Details |" >> "$report_file"
        echo "|-----------|------|--------|---------|" >> "$report_file"
        tail -20 "$PROGRESS_FILE" | while IFS='|' read -r ts step status details; do
            echo "| $ts | $step | $status | $details |" >> "$report_file"
        done
    fi

    # Add performance metrics
    if [ -f "$MONITORING_DIR/system_metrics.log" ]; then
        echo "" >> "$report_file"
        echo "### Performance Metrics" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
        tail -10 "$MONITORING_DIR/system_metrics.log" >> "$report_file"
        echo "\`\`\`" >> "$report_file"
    fi

    log_success "Report generated: $report_file"
    update_progress "report_generation" "COMPLETED" "Report saved to $report_file"
}

cleanup_processes() {
    log_header "CLEANING UP PROCESSES"

    log_info "Stopping background processes..."

    # Kill AAC processes
    for pid_file in "$MONITORING_DIR"/*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
                log_info "Stopped process $(basename "$pid_file" .pid) (PID: $pid)"
            fi
            rm -f "$pid_file"
        fi
    done

    # Kill any remaining Bit Rage Systems processes
    pkill -f "cpu_maximizer\|aac_\|inner_council" 2>/dev/null || true

    log_success "Cleanup completed"
}

show_menu() {
    echo
    log_header "Bit Rage Systems LOCAL RUNNER"
    echo "1) Run Full System (Recommended)"
    echo "2) Start Inner Council Only"
    echo "3) Start AAC System Only"
    echo "4) Run CPU Maximization Only"
    echo "5) Run Daily Operations"
    echo "6) Monitor System (5 minutes)"
    echo "7) Generate Reports"
    echo "8) Cleanup Processes"
    echo "9) Exit"
    echo
}

run_full_system() {
    log_header "RUNNING FULL Bit Rage Systems SYSTEM"

    update_progress "full_system" "STARTED" "Complete system deployment"

    # Step 1: Check dependencies
    check_dependencies

    # Step 2: Start Inner Council
    if start_inner_council; then
        log_success "Inner Council operational"
    else
        log_error "Inner Council failed - continuing with other systems"
    fi

    # Step 3: Start AAC System
    if start_aac_system; then
        log_success "AAC system operational"
    else
        log_error "AAC system failed - continuing with other systems"
    fi

    # Step 4: Run CPU Maximization
    if start_cpu_maximization "balanced" 5; then
        log_success "CPU maximization completed"
    else
        log_error "CPU maximization failed"
    fi

    # Step 5: Run Daily Operations
    if run_daily_operations; then
        log_success "Daily operations completed"
    else
        log_error "Daily operations failed"
    fi

    # Step 6: Generate Reports
    generate_reports

    update_progress "full_system" "COMPLETED" "Full system run completed"
    log_success "Full Bit Rage Systems system run completed!"
}

# Main execution
case "${1:-}" in
    "full")
        run_full_system
        ;;
    "council")
        check_dependencies
        start_inner_council
        ;;
    "aac")
        check_dependencies
        start_aac_system
        ;;
    "cpu")
        check_dependencies
        start_cpu_maximization "${2:-balanced}" "${3:-10}"
        ;;
    "daily")
        check_dependencies
        run_daily_operations
        ;;
    "monitor")
        monitor_system "${2:-300}"
        ;;
    "reports")
        generate_reports
        ;;
    "cleanup")
        cleanup_processes
        ;;
    "deps")
        check_dependencies
        ;;
    *)
        # Interactive mode
        while true; do
            show_menu
            read -p "Select option (1-9): " choice
            echo

            case $choice in
                1) run_full_system ;;
                2) check_dependencies && start_inner_council ;;
                3) check_dependencies && start_aac_system ;;
                4)
                    read -p "Mode (maximum/balanced/diagnostic) [balanced]: " mode
                    mode=${mode:-balanced}
                    read -p "Duration in minutes [5]: " duration
                    duration=${duration:-5}
                    check_dependencies && start_cpu_maximization "$mode" "$duration"
                    ;;
                5) check_dependencies && run_daily_operations ;;
                6)
                    read -p "Monitoring duration in seconds [300]: " duration
                    duration=${duration:-300}
                    monitor_system "$duration"
                    ;;
                7) generate_reports ;;
                8) cleanup_processes ;;
                9) log_info "Goodbye!"; exit 0 ;;
                *) log_warning "Invalid option. Please try again." ;;
            esac

            echo
            read -p "Press Enter to continue..."
        done
        ;;
esac