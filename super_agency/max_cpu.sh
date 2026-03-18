#!/usr/bin/env bash
# Bit Rage Labour CPU Maximizer Quick Start
# Maximum CPU utilization for all repositories

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔥 Bit Rage Labour CPU Maximizer Quick Start"
echo "=========================================="
echo "Root Directory: $ROOT_DIR"
echo "CPU Cores: $(nproc 2>/dev/null || echo 'Unknown')"
echo ""

# Function to run command with timing
run_with_timing() {
    local name="$1"
    local cmd="$2"

    echo "🚀 Running $name..."
    local start_time=$(date +%s)

    if eval "$cmd"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo "✅ $name completed in ${duration}s"
        return 0
    else
        echo "❌ $name failed"
        return 1
    fi
}

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.7+"
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "Using Python: $($PYTHON_CMD --version)"
echo ""

# Option 1: Single CPU Maximizer
run_single() {
    echo "📊 Option 1: Single CPU Maximizer"
    run_with_timing "CPU Maximizer" "cd '$ROOT_DIR' && $PYTHON_CMD cpu_maximizer.py"
}

# Option 2: Parallel Orchestrator
run_parallel() {
    echo "📊 Option 2: Parallel Orchestrator"
    run_with_timing "Parallel Orchestrator" "cd '$ROOT_DIR' && $PYTHON_CMD parallel_orchestrator.py"
}

# Option 3: Batch Processing
run_batch() {
    local cycles="${1:-5}"
    echo "📊 Option 3: Batch Processing ($cycles cycles)"
    run_with_timing "Batch Processor" "cd '$ROOT_DIR' && $PYTHON_CMD batch_processor.py --cycles $cycles"
}

# Option 4: CPU Control Center
run_control_center() {
    local mode="${1:-balanced}"
    local duration="${2:-5}"
    echo "📊 Option 4: CPU Control Center (Mode: $mode, Duration: ${duration}m)"
    run_with_timing "CPU Control Center" "cd '$ROOT_DIR' && $PYTHON_CMD cpu_control_center.py $mode --duration $duration"
}

# Option 5: Maximum Overdrive (All systems simultaneously)
run_maximum_overdrive() {
    local duration="${1:-3}"
    echo "🚀 Option 5: MAXIMUM OVERDRIVE MODE ($duration minutes)"
    echo "Warning: This will launch all systems simultaneously!"
    echo "Press Ctrl+C to stop early"
    echo ""

    # Launch all systems in background
    run_with_timing "Maximum CPU Mode" "cd '$ROOT_DIR' && timeout ${duration}m $PYTHON_CMD cpu_control_center.py maximum --duration $duration" &
    MAX_PID=$!

    # Wait for completion
    wait $MAX_PID
}

# Option 6: Continuous Processing
run_continuous() {
    local duration="${1:-10}"
    echo "📊 Option 6: Continuous Processing ($duration minutes)"
    run_with_timing "Continuous Batch" "cd '$ROOT_DIR' && $PYTHON_CMD batch_processor.py --continuous $duration"
}

# Main menu
show_menu() {
    echo "Select CPU maximization option:"
    echo "1) Single CPU Maximizer (Basic)"
    echo "2) Parallel Orchestrator (Agents)"
    echo "3) Batch Processing (Multiple cycles)"
    echo "4) CPU Control Center (Advanced)"
    echo "5) MAXIMUM OVERDRIVE (All systems - Use with caution!)"
    echo "6) Continuous Processing (Long-running)"
    echo "7) Run All Options Sequentially"
    echo "8) Exit"
    echo ""
}

# Run all options sequentially
run_all() {
    echo "🔄 Running all CPU maximization options sequentially..."
    echo ""

    run_single
    echo ""
    run_parallel
    echo ""
    run_batch 3
    echo ""
    run_control_center diagnostic
    echo ""
    run_continuous 2
    echo ""
    echo "🎯 All CPU maximization options completed!"
}

# Main logic
if [ $# -eq 0 ]; then
    # Interactive mode
    while true; do
        show_menu
        read -p "Enter choice (1-8): " choice
        echo ""

        case $choice in
            1) run_single ;;
            2) run_parallel ;;
            3)
                read -p "Number of cycles [5]: " cycles
                cycles=${cycles:-5}
                run_batch $cycles
                ;;
            4)
                read -p "Mode (maximum/balanced/diagnostic) [balanced]: " mode
                mode=${mode:-balanced}
                read -p "Duration in minutes [5]: " duration
                duration=${duration:-5}
                run_control_center $mode $duration
                ;;
            5)
                read -p "Duration in minutes [3]: " duration
                duration=${duration:-3}
                run_maximum_overdrive $duration
                ;;
            6)
                read -p "Duration in minutes [10]: " duration
                duration=${duration:-10}
                run_continuous $duration
                ;;
            7) run_all ;;
            8) echo "Goodbye!"; exit 0 ;;
            *) echo "Invalid option. Please try again." ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
        clear
    done
else
    # Command line mode
    case $1 in
        single) run_single ;;
        parallel) run_parallel ;;
        batch) run_batch "${2:-5}" ;;
        control) run_control_center "${2:-balanced}" "${3:-5}" ;;
        maximum) run_maximum_overdrive "${2:-3}" ;;
        continuous) run_continuous "${2:-10}" ;;
        all) run_all ;;
        *)
            echo "Usage: $0 [single|parallel|batch [cycles]|control [mode] [duration]|maximum [duration]|continuous [duration]|all]"
            echo ""
            echo "Examples:"
            echo "  $0 single                    # Basic CPU maximizer"
            echo "  $0 batch 10                  # Batch processing with 10 cycles"
            echo "  $0 control maximum 15        # Control center in maximum mode for 15 min"
            echo "  $0 maximum 5                 # Maximum overdrive for 5 minutes"
            echo "  $0 all                       # Run all options sequentially"
            exit 1
            ;;
    esac
fi