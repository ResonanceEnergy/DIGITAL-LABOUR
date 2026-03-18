#!/bin/bash
# Bit Rage Labour Unified Mobile Launcher
# Run locally and access from anywhere with phone/iPad

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

log_mobile() {
    echo -e "${PURPLE}[📱 MOBILE]${NC} $1"
}

log_launch() {
    echo -e "${CYAN}[🚀 LAUNCH]${NC} $1"
}

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

# Get local IP
get_local_ip() {
    case $PLATFORM in
        macos)
            ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost"
            ;;
        linux)
            hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost"
            ;;
        windows)
            # Will be handled by PowerShell
            echo "localhost"
            ;;
        *)
            echo "localhost"
            ;;
    esac
}

LOCAL_IP=$(get_local_ip)

# Check if mobile setup exists
check_mobile_setup() {
    if [ ! -f "mobile_command_center.py" ]; then
        log_warning "Mobile command center not set up. Running setup..."
        if [ "$PLATFORM" = "windows" ]; then
            powershell -ExecutionPolicy Bypass -File mobile_setup.ps1 -Setup
        else
            ./mobile_setup.sh
        fi
    fi
}

# Start local services
start_local_services() {
    log_launch "Starting local Bit Rage Labour services..."

    # Start Matrix Monitor
    if [ -f "matrix_monitor.py" ] || [ -d "matrix_monitor" ]; then
        log_info "Starting Matrix Monitor..."
        python -c "
import subprocess
import sys
try:
    # Try to start matrix monitor
    proc = subprocess.Popen([sys.executable, 'matrix_monitor.py'] if __import__('os').path.isfile('matrix_monitor.py') else [sys.executable, '-m', 'matrix_monitor'])
    with open('.matrix_monitor.pid', 'w') as f:
        f.write(str(proc.pid))
    print('Matrix Monitor started (PID: ' + str(proc.pid) + ')')
except:
    print('Matrix Monitor start attempted')
" 2>/dev/null || log_warning "Matrix Monitor start attempted"
    fi

    # Start Operations Interface
    if [ -f "operations_launcher.py" ]; then
        log_info "Starting Operations Interface..."
        python operations_launcher.py &
        echo $! > .operations.pid
        log_success "Operations Interface started (PID: $(cat .operations.pid))"
    fi

    # Start AAC System
    if [ -d "repos/AAC" ] && [ -f "repos/AAC/aac_dashboard.py" ]; then
        log_info "Starting AAC System..."
        cd repos/AAC
        python aac_dashboard.py &
        echo $! > ../../.aac.pid
        cd ../..
        log_success "AAC System started (PID: $(cat .aac.pid))"
    fi
}

# Start mobile command center
start_mobile_center() {
    log_mobile "Starting mobile command center..."

    if [ -f "mobile_command_center.py" ]; then
        python mobile_command_center.py &
        echo $! > .mobile_server.pid
        log_success "Mobile command center started (PID: $(cat .mobile_server.pid))"
    else
        log_error "Mobile command center not found. Run setup first."
        exit 1
    fi
}

# Start remote tunnel
start_remote_tunnel() {
    log_mobile "Starting remote access tunnel..."

    # Try ngrok first
    if command -v ngrok &> /dev/null; then
        log_info "Starting ngrok tunnel..."
        ngrok http 8080 &
        echo $! > .ngrok.pid
        sleep 3
        log_success "ngrok tunnel started (PID: $(cat .ngrok.pid))"
        return
    fi

    # Try cloudflared
    if command -v cloudflared &> /dev/null; then
        log_info "Starting Cloudflare tunnel..."
        cloudflared tunnel run Digital-Labour-mobile &
        echo $! > .cloudflare.pid
        sleep 3
        log_success "Cloudflare tunnel started (PID: $(cat .cloudflare.pid))"
        return
    fi

    log_warning "No tunnel service found. Install ngrok or cloudflared for remote access."
    log_info "You can still access locally at http://$LOCAL_IP:8080"
}

# Show access information
show_access_info() {
    echo ""
    log_success "🎉 Bit Rage Labour Mobile Command Center is RUNNING!"
    echo ""
    echo "📱 ACCESS YOUR COMMAND CENTER FROM ANYWHERE:"
    echo ""

    echo "🏠 LOCAL ACCESS (same WiFi network):"
    echo -e "   ${CYAN}http://$LOCAL_IP:8080${NC}"
    echo ""

    # Check for tunnel URLs
    if [ -f ".ngrok.pid" ] && kill -0 $(cat .ngrok.pid) 2>/dev/null; then
        echo "🌐 REMOTE ACCESS (from anywhere):"
        # Try to get ngrok URL
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | grep -o 'https://[^"]*' 2>/dev/null || echo "")
        if [ -n "$NGROK_URL" ]; then
            echo -e "   ${CYAN}$NGROK_URL${NC}"
        else
            echo -e "   ${CYAN}https://BIT RAGE LABOUR.ngrok.io${NC} (check ngrok dashboard)"
        fi
        echo ""
    elif [ -f ".cloudflare.pid" ] && kill -0 $(cat .cloudflare.pid) 2>/dev/null; then
        echo "🌐 REMOTE ACCESS (from anywhere):"
        echo -e "   ${CYAN}https://mobile.BIT RAGE LABOUR.local${NC}"
        echo ""
    fi

    echo "📱 MOBILE SETUP INSTRUCTIONS:"
    echo "1. Open Safari/Chrome on your phone/iPad"
    echo "2. Navigate to one of the URLs above"
    echo "3. Tap share button → Add to Home Screen"
    echo "4. Name it 'Bit Rage Labour Command'"
    echo ""
    echo "🎮 MOBILE FEATURES:"
    echo "   • Touch-optimized controls"
    echo "   • Pull-to-refresh dashboard"
    echo "   • Real-time system monitoring"
    echo "   • One-tap command execution"
    echo "   • Offline-capable interface"
    echo ""

    echo "🛑 TO STOP: ./mobile_launcher.sh --stop"
    echo "📊 STATUS:  ./mobile_launcher.sh --status"
}

# Stop all services
stop_services() {
    log_info "Stopping all Bit Rage Labour services..."

    # Stop mobile server
    if [ -f ".mobile_server.pid" ]; then
        kill $(cat .mobile_server.pid) 2>/dev/null && log_success "Mobile server stopped" || log_warning "Mobile server stop attempted"
        rm -f .mobile_server.pid
    fi

    # Stop tunnels
    if [ -f ".ngrok.pid" ]; then
        kill $(cat .ngrok.pid) 2>/dev/null && log_success "ngrok tunnel stopped" || log_warning "ngrok tunnel stop attempted"
        rm -f .ngrok.pid
    fi

    if [ -f ".cloudflare.pid" ]; then
        kill $(cat .cloudflare.pid) 2>/dev/null && log_success "Cloudflare tunnel stopped" || log_warning "Cloudflare tunnel stop attempted"
        rm -f .cloudflare.pid
    fi

    # Stop local services
    for pid_file in .*.pid; do
        if [ -f "$pid_file" ] && [ "$pid_file" != ".mobile_server.pid" ] && [ "$pid_file" != ".ngrok.pid" ] && [ "$pid_file" != ".cloudflare.pid" ]; then
            kill $(cat "$pid_file") 2>/dev/null && log_success "$(basename "$pid_file" .pid) stopped" || log_warning "$(basename "$pid_file" .pid) stop attempted"
            rm -f "$pid_file"
        fi
    done

    log_success "All services stopped"
}

# Show status
show_status() {
    echo ""
    log_mobile "Bit Rage Labour Mobile Command Center Status"
    echo "=========================================="
    echo ""

    echo "Local Services:"
    for pid_file in .*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            service_name=$(basename "$pid_file" .pid | sed 's/_/ /g')
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "  ✅ $service_name: Running (PID: $pid)"
            else
                echo -e "  ❌ $service_name: Not running (stale PID)"
            fi
        fi
    done

    echo ""
    echo "Network Access:"
    echo -e "  🏠 Local: http://$LOCAL_IP:8080"

    if [ -f ".ngrok.pid" ] && kill -0 $(cat .ngrok.pid) 2>/dev/null; then
        echo -e "  🌐 Remote: Check ngrok dashboard (localhost:4040)"
    elif [ -f ".cloudflare.pid" ] && kill -0 $(cat .cloudflare.pid) 2>/dev/null; then
        echo -e "  🌐 Remote: https://mobile.BIT RAGE LABOUR.local"
    else
        echo -e "  ❌ Remote: No tunnel active"
    fi

    echo ""
    echo "System Health:"
    # Check if mobile server is responding
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "  ✅ Mobile Interface: Online"
    else
        echo -e "  ❌ Mobile Interface: Offline"
    fi
}

# Main execution
main() {
    echo "🚀📱 Bit Rage Labour Unified Mobile Launcher"
    echo "========================================"
    echo ""
    echo "Run your command center locally and access from anywhere!"
    echo ""

    case "${1:-}" in
        --start|--launch)
            check_mobile_setup
            start_local_services
            start_mobile_center
            start_remote_tunnel
            show_access_info
            ;;
        --stop)
            stop_services
            ;;
        --status)
            show_status
            ;;
        --local-only)
            check_mobile_setup
            start_local_services
            start_mobile_center
            echo ""
            log_success "Local-only mode started!"
            echo -e "Access at: ${CYAN}http://$LOCAL_IP:8080${NC}"
            ;;
        --remote-only)
            check_mobile_setup
            start_mobile_center
            start_remote_tunnel
            show_access_info
            ;;
        --setup)
            if [ "$PLATFORM" = "windows" ]; then
                powershell -ExecutionPolicy Bypass -File mobile_setup.ps1 -Setup
            else
                ./mobile_setup.sh
            fi
            ;;
        --help|*)
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  --start, --launch    Start everything (local + remote)"
            echo "  --local-only         Start local access only"
            echo "  --remote-only        Start remote access only"
            echo "  --stop               Stop all services"
            echo "  --status             Show current status"
            echo "  --setup              Run mobile setup"
            echo "  --help               Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --start          # Start everything"
            echo "  $0 --local-only     # Local access only"
            echo "  $0 --status         # Check status"
            echo "  $0 --stop           # Stop everything"
            ;;
    esac
}

# Run main function
main "$@"