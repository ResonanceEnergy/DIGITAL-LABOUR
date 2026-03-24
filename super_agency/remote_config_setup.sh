#!/bin/bash
# Remote Configuration Setup for Bit Rage Systems Mobile Command Center
# This script sets environment variables for remote Windows connectivity

echo "🔧 Bit Rage Systems Remote Configuration Setup"
echo "=========================================="

# Default configuration (local)
export MATRIX_HOST="localhost"
export MATRIX_PORT="3000"
export WINDOWS_HOST=""
export ENABLE_REMOTE="false"
export AAC_PORT="8081"

echo "Current Configuration:"
echo "  MATRIX_HOST: $MATRIX_HOST"
echo "  MATRIX_PORT: $MATRIX_PORT"
echo "  WINDOWS_HOST: $WINDOWS_HOST"
echo "  ENABLE_REMOTE: $ENABLE_REMOTE"
echo "  AAC_PORT: $AAC_PORT"
echo ""

# Function to configure for remote Windows
configure_remote() {
    echo "🌐 Configuring for Remote Windows Connection"
    echo "Enter your Windows machine's public IP address or hostname:"
    read -r windows_ip

    if [ -n "$windows_ip" ]; then
        export MATRIX_HOST="$windows_ip"
        export WINDOWS_HOST="$windows_ip"
        export ENABLE_REMOTE="true"

        echo "✅ Remote configuration updated:"
        echo "  MATRIX_HOST: $MATRIX_HOST"
        echo "  WINDOWS_HOST: $WINDOWS_HOST"
        echo "  ENABLE_REMOTE: $ENABLE_REMOTE"
        echo ""
        echo "📝 To apply these settings, restart the mobile command center:"
        echo "   pkill -f mobile_command_center_simple.py"
        echo "   python3 mobile_command_center_simple.py"
        echo ""
        echo "🔒 Security Note: Ensure your Windows machine has proper firewall rules"
        echo "   and VPN configuration for secure remote access."
    else
        echo "❌ No IP address provided. Configuration unchanged."
    fi
}

# Function to reset to local configuration
configure_local() {
    echo "🏠 Configuring for Local Operation"
    export MATRIX_HOST="localhost"
    export WINDOWS_HOST=""
    export ENABLE_REMOTE="false"

    echo "✅ Local configuration restored:"
    echo "  MATRIX_HOST: $MATRIX_HOST"
    echo "  WINDOWS_HOST: $WINDOWS_HOST"
    echo "  ENABLE_REMOTE: $ENABLE_REMOTE"
}

# Menu
echo "Choose configuration:"
echo "1) Configure for Remote Windows Connection"
echo "2) Reset to Local Configuration"
echo "3) Show Current Configuration"
echo "4) Exit"
echo ""

while true; do
    read -r -p "Enter choice (1-4): " choice
    case $choice in
        1)
            configure_remote
            ;;
        2)
            configure_local
            ;;
        3)
            echo "Current Configuration:"
            echo "  MATRIX_HOST: $MATRIX_HOST"
            echo "  MATRIX_PORT: $MATRIX_PORT"
            echo "  WINDOWS_HOST: $WINDOWS_HOST"
            echo "  ENABLE_REMOTE: $ENABLE_REMOTE"
            echo "  AAC_PORT: $AAC_PORT"
            ;;
        4)
            echo "Exiting..."
            break
            ;;
        *)
            echo "Invalid choice. Please enter 1-4."
            ;;
    esac
    echo ""
done
