#!/bin/bash
# Bit Rage Labour macOS Command Center Setup
# This script sets up the complete macOS development and production environment

set -e

echo "🚀 Bit Rage Labour macOS Command Center Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    log_error "This script is designed for macOS only"
    exit 1
fi

# Install Homebrew if not installed
install_homebrew() {
    log_info "Checking Homebrew installation..."
    if ! command -v brew &> /dev/null; then
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
        log_success "Homebrew installed"
    else
        log_success "Homebrew already installed"
    fi
}

# Install development tools
install_dev_tools() {
    log_info "Installing development tools..."

    # Update Homebrew
    brew update

    # Install Python
    brew install python@3.11
    log_success "Python 3.11 installed"

    # Install Git and GitHub CLI
    brew install git
    brew install gh
    log_success "Git and GitHub CLI installed"

    # Install Node.js
    brew install node
    log_success "Node.js installed"

    # Install Docker
    brew install --cask docker
    log_success "Docker installed"

    # Install VS Code
    brew install --cask visual-studio-code
    log_success "VS Code installed"

    # Install iOS development tools
    brew install --cask xcode
    log_success "Xcode installed"
}

# Set up Bit Rage Labour project
setup_bit_rage_labour() {
    log_info "Setting up Bit Rage Labour project..."

    # Create Bit Rage Labour directory
    bit_rage_labour_dir="$HOME/Digital-Labour"
    if [ ! -d "$bit_rage_labour_dir" ]; then
        mkdir -p "$bit_rage_labour_dir"
        log_success "Bit Rage Labour directory created"
    else
        log_warning "Bit Rage Labour directory already exists"
    fi

    cd "$bit_rage_labour_dir"

    # Clone or update repository
    if [ ! -d ".git" ]; then
        log_info "Cloning Bit Rage Labour repository..."
        gh repo clone ResonanceEnergy/Digital-Labour .
        log_success "Repository cloned"
    else
        log_info "Updating existing repository..."
        git pull origin main
        log_success "Repository updated"
    fi

    # Set up Python virtual environment
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
        log_success "Virtual environment created"
    fi

    # Activate virtual environment and install dependencies
    log_info "Installing Python dependencies..."
    source venv/bin/activate
    pip install --upgrade pip

    # Install requirements if they exist
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "Python dependencies installed"
    else
        log_warning "requirements.txt not found, installing basic packages"
        pip install requests python-dotenv pyyaml
    fi

    # Install development dependencies
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
    fi
}

# Configure VS Code
setup_vscode() {
    log_info "Configuring VS Code..."

    # Install essential extensions
    code --install-extension ms-python.python
    code --install-extension ms-vscode.vscode-json
    code --install-extension github.copilot
    code --install-extension ms-vscode-remote.remote-ssh
    code --install-extension ms-vscode.vscode-typescript-next
    code --install-extension esbenp.prettier-vscode
    code --install-extension ms-vscode-remote.remote-containers
    code --install-extension github.copilot-chat

    log_success "VS Code extensions installed"

    # Create workspace settings
    cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "git.autofetch": true,
    "git.enableSmartCommit": true,
    "github.copilot.enable": {
        "*": true
    }
}
EOF

    log_success "VS Code workspace settings configured"
}

# Set up Matrix Monitor
setup_matrix_monitor() {
    log_info "Setting up Matrix Monitor..."

    # Create matrix monitor configuration
    mkdir -p matrix_monitor/panels

    cat > matrix_monitor/config.json << EOF
{
  "matrix_monitor": {
    "title": "Bit Rage Labour Command Center",
    "refresh_interval": 30,
    "panels": [
      {
        "id": "system_status",
        "title": "System Status",
        "type": "status_grid",
        "position": {"x": 0, "y": 0, "width": 12, "height": 4},
        "sources": ["macos_live", "windows_build", "aws_compute"],
        "metrics": ["health", "cpu", "memory", "disk"]
      },
      {
        "id": "operations_interface",
        "title": "Operations Interface",
        "type": "operations_dashboard",
        "position": {"x": 0, "y": 4, "width": 8, "height": 6},
        "source": "operations_api",
        "features": ["department_status", "recent_activity", "alerts"]
      },
      {
        "id": "build_pipeline",
        "title": "Build Pipeline",
        "type": "ci_cd_status",
        "position": {"x": 8, "y": 4, "width": 4, "height": 6},
        "source": "github_actions",
        "workflows": ["test", "build", "deploy"]
      },
      {
        "id": "galactia_insights",
        "title": "Galactia Doctrine",
        "type": "ai_insights",
        "position": {"x": 0, "y": 10, "width": 12, "height": 4},
        "source": "galactia_api",
        "features": ["decisions", "predictions", "recommendations"]
      }
    ],
    "alerts": {
      "system_down": {
        "condition": "any_system_health != 'operational'",
        "severity": "critical",
        "notification": ["email", "slack", "push"]
      },
      "build_failure": {
        "condition": "build_status == 'failed'",
        "severity": "high",
        "notification": ["email", "github_issue"]
      },
      "high_resource_usage": {
        "condition": "cpu_usage > 90 OR memory_usage > 90",
        "severity": "medium",
        "notification": ["email"]
      }
    }
  }
}
EOF

    log_success "Matrix Monitor configured"
}

# Set up Galactia Doctrine integration
setup_galactia() {
    log_info "Setting up Galactia Doctrine integration..."

    # Create Galactia configuration
    cat > galactia_config.json << EOF
{
  "galactia": {
    "api_url": "https://api.galactia.doctrine",
    "api_key": "${GALACTIA_API_KEY:-}",
    "features": {
      "decision_support": true,
      "strategic_analysis": true,
      "predictive_analytics": true,
      "risk_assessment": true
    },
    "integration": {
      "operations_interface": true,
      "matrix_monitor": true,
      "ncl_system": true
    }
  }
}
EOF

    log_success "Galactia Doctrine integration configured"
}

# Set up iOS development
setup_ios_dev() {
    log_info "Setting up iOS development environment..."

    # Install CocoaPods
    sudo gem install cocoapods

    # Create iOS app template
    mkdir -p ios/BIT RAGE LABOURCommand
    cd ios/BIT RAGE LABOURCommand

    # Initialize Xcode project
    cat > BIT RAGE LABOURCommand.xcodeproj/project.pbxproj << EOF
// !$*UTF8*$!
{
	archiveVersion = 1;
	classes = {
	};
	objectVersion = 55;
	objects = {

/* Begin PBXBuildFile section */
		1D60589B238F83C700BF7E4D /* BIT RAGE LABOURCommandApp.swift in Sources */ = {isa = PBXBuildFile; fileRef = 1D60589A238F83C700BF7E4D /* BIT RAGE LABOURCommandApp.swift */; };
		1D60589D238F83C700BF7E4D /* ContentView.swift in Sources */ = {isa = PBXBuildFile; fileRef = 1D60589C238F83C700BF7E4D /* ContentView.swift */; };
		1D60589F238F83C700BF7E4D /* Assets.xcassets in Resources */ = {isa = PBXBuildFile; fileRef = 1D60589E238F83C700BF7E4D /* Assets.xcassets */; };
		1D6058A2238F83C700BF7E4D /* Preview Assets.xcassets in Resources */ = {isa = PBXBuildFile; fileRef = 1D6058A1238F83C700BF7E4D /* Preview Assets.xcassets */; };
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
		1D605897238F83C700BF7E4D /* BIT RAGE LABOURCommand.app */ = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = BIT RAGE LABOURCommand.app; sourceTree = BUILT_PRODUCTS_DIR; };
		1D60589A238F83C700BF7E4D /* BIT RAGE LABOURCommandApp.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = BIT RAGE LABOURCommandApp.swift; sourceTree = "<group>"; };
		1D60589C238F83C700BF7E4D /* ContentView.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = ContentView.swift; sourceTree = "<group>"; };
		1D60589E238F83C700BF7E4D /* Assets.xcassets */ = {isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = "<group>"; };
		1D6058A1238F83C700BF7E4D /* Preview Assets.xcassets */ = {isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Preview Assets.xcassets; sourceTree = "<group>"; };
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		1D605894238F83C700BF7E4D /* Frameworks */ = {
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		1D60588E238F83C700BF7E4D = {
			isa = PBXGroup;
			children = (
				1D605899238F83C700BF7E4D /* BIT RAGE LABOURCommand */,
				1D6058A0238F83C700BF7E4D /* Products */,
			);
			sourceTree = "<group>";
		};
		1D605899238F83C700BF7E4D /* BIT RAGE LABOURCommand */ = {
			isa = PBXGroup;
			children = (
				1D60589A238F83C700BF7E4D /* BIT RAGE LABOURCommandApp.swift */,
				1D60589C238F83C700BF7E4D /* ContentView.swift */,
				1D60589E238F83C700BF7E4D /* Assets.xcassets */,
				1D6058A1238F83C700BF7E4D /* Preview Assets.xcassets */,
			);
			path = BIT RAGE LABOURCommand;
			sourceTree = "<group>";
		};
		1D6058A0238F83C700BF7E4D /* Products */ = {
			isa = PBXGroup;
			children = (
				1D605897238F83C700BF7E4D /* BIT RAGE LABOURCommand.app */,
			);
			name = Products;
			sourceTree = "<group>";
		};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		1D605896238F83C700BF7E4D /* BIT RAGE LABOURCommand */ = {
			isa = PBXNativeTarget;
			buildConfigurationList = 1D6058AA238F83C700BF7E4D /* Build configuration list for PBXNativeTarget "BIT RAGE LABOURCommand" */;
			buildPhases = (
				1D605893238F83C700BF7E4D /* Sources */,
				1D605894238F83C700BF7E4D /* Frameworks */,
				1D605895238F83C700BF7E4D /* Resources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = BIT RAGE LABOURCommand;
			productName = BIT RAGE LABOURCommand;
			productReference = 1D605897238F83C700BF7E4D /* BIT RAGE LABOURCommand.app */;
			productType = "com.apple.product-type.application";
		};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		1D60588F238F83C700BF7E4D /* Project object */ = {
			isa = PBXProject;
			attributes = {
				LastSwiftUpdateCheck = 1320;
				LastUpgradeCheck = 1320;
				TargetAttributes = {
					1D605896238F83C700BF7E4D = {
						CreatedOnToolsVersion = 13.2;
					};
				};
			};
			buildConfigurationList = 1D605892238F83C700BF7E4D /* Build configuration list for PBXProject "BIT RAGE LABOURCommand" */;
			compatibilityVersion = "Xcode 13.0";
			developmentRegion = en;
			hasScannedForEncodings = 0;
			knownRegions = (
				en,
				Base,
			);
			mainGroup = 1D60588E238F83C700BF7E4D;
			productRefGroup = 1D6058A0238F83C700BF7E4D /* Products */;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				1D605896238F83C700BF7E4D /* BIT RAGE LABOURCommand */,
			);
		};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
		1D605895238F83C700BF7E4D /* Resources */ = {
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				1D60589F238F83C700BF7E4D /* Assets.xcassets in Resources */,
				1D6058A2238F83C700BF7E4D /* Preview Assets.xcassets in Resources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
		1D605893238F83C700BF7E4D /* Sources */ = {
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				1D60589B238F83C700BF7E4D /* BIT RAGE LABOURCommandApp.swift in Sources */,
				1D60589D238F83C700BF7E4D /* ContentView.swift in Sources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXSourcesBuildPhase section */

/* Begin PBXVariantGroup section */
		1D6058A3238F83C700BF7E4D /* LaunchScreen.storyboard */ = {
			isa = PBXVariantGroup;
			children = (
				1D6058A4238F83C700BF7E4D /* Base */,
			);
			name = LaunchScreen.storyboard;
			sourceTree = "<group>";
		};
/* End PBXVariantGroup section */

/* Begin XCBuildConfiguration section */
		1D6058A5238F83C700BF7E4D /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++17";
				CLANG_CXX_LIBRARY = "libc++";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				CLANG_ENABLE_OBJC_WEAK = YES;
				CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING = YES;
				CLANG_WARN_BOOL_CONVERSION = YES;
				CLANG_WARN_COMMA = YES;
				CLANG_WARN_CONSTANT_CONVERSION = YES;
				CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS = YES;
				CLANG_WARN_DIRECT_OBJC_ISA_USAGE = YES_ERROR;
				CLANG_WARN_EMPTY_BODY = YES;
				CLANG_WARN_ENUM_CONVERSION = YES;
				CLANG_WARN_INFINITE_RECURSION = YES;
				CLANG_WARN_INT_CONVERSION = YES;
				CLANG_WARN_NON_LITERAL_NULL_CONVERSION = YES;
				CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES;
				CLANG_WARN_OBJC_LITERAL_CONVERSION = YES;
				CLANG_WARN_OBJC_ROOT_CLASS = YES_ERROR;
				CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER = YES;
				CLANG_WARN_RANGE_LOOP_ANALYSIS = YES;
				CLANG_WARN_STRICT_PROTOTYPES = YES;
				CLANG_WARN_SUSPICIOUS_MOVE = YES;
				CLANG_WARN_UNREACHABLE_CODE = YES;
				CLANG_WARN__DUPLICATED_BRANCHES = YES;
				CLANG_WARN__DUPLICATED_METHOD_MATCH = YES;
				"ENABLE_HARDENED_RUNTIME[arch=*]" = YES;
				"ENABLE_PREVIEWS[arch=*]" = YES;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				GCC_C_LANGUAGE_STANDARD = gnu11;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_WARN_64_TO_32_BIT_CONVERSION = YES;
				GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;
				GCC_WARN_UNDECLARED_SELECTOR = YES;
				GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
				GCC_WARN_UNUSED_FUNCTION = YES;
				GCC_WARN_UNUSED_VARIABLE = YES;
				MTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;
				MTL_FAST_MATH = YES;
				ONLY_ACTIVE_ARCH = YES;
				SDKROOT = iphoneos;
				SUPPORTED_PLATFORMS = "iphonesimulator iphoneos macosx";
				SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
				SWIFT_VERSION = 5.0;
			};
			name = Debug;
		};
		1D6058A6238F83C700BF7E4D /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++17";
				CLANG_CXX_LIBRARY = "libc++";
				CLANG_ANALYZER_LOCALIZABILITY_NONLOCALIZED = YES;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++17";
				CLANG_CXX_LIBRARY = "libc++";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				CLANG_ENABLE_OBJC_WEAK = YES;
				CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING = YES;
				CLANG_WARN_BOOL_CONVERSION = YES;
				CLANG_WARN_COMMA = YES;
				CLANG_WARN_CONSTANT_CONVERSION = YES;
				CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS = YES;
				CLANG_WARN_DIRECT_OBJC_ISA_USAGE = YES_ERROR;
				CLANG_WARN_EMPTY_BODY = YES;
				CLANG_WARN_ENUM_CONVERSION = YES;
				CLANG_WARN_INFINITE_RECURSION = YES;
				CLANG_WARN_INT_CONVERSION = YES;
				CLANG_WARN_NON_LITERAL_NULL_CONVERSION = YES;
				CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES;
				CLANG_WARN_OBJC_LITERAL_CONVERSION = YES;
				CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER = YES;
				CLANG_WARN_RANGE_LOOP_ANALYSIS = YES;
				CLANG_WARN_STRICT_PROTOTYPES = YES;
				CLANG_WARN_SUSPICIOUS_MOVE = YES;
				CLANG_WARN_UNREACHABLE_CODE = YES;
				CLANG_WARN__DUPLICATED_BRANCHES = YES;
				CLANG_WARN__DUPLICATED_METHOD_MATCH = YES;
				"ENABLE_HARDENED_RUNTIME[arch=*]" = YES;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				GCC_C_LANGUAGE_STANDARD = gnu11;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_WARN_64_TO_32_BIT_CONVERSION = YES;
				GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;
				GCC_WARN_UNDECLARED_SELECTOR = YES;
				GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
				GCC_WARN_UNUSED_FUNCTION = YES;
				GCC_WARN_UNUSED_VARIABLE = YES;
				MTL_ENABLE_DEBUG_INFO = NO;
				MTL_FAST_MATH = YES;
				SDKROOT = iphoneos;
				SUPPORTED_PLATFORMS = "iphonesimulator iphoneos macosx";
				SWIFT_ACTIVE_COMPILCTION_CONDITIONS = RELEASE;
				SWIFT_OPTIMIZATION_LEVEL = "-O";
				SWIFT_VERSION = 5.0;
				VALIDATE_PRODUCT = YES;
			};
			name = Release;
		};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		1D605892238F83C700BF7E4D /* Build configuration list for PBXProject "BIT RAGE LABOURCommand" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				1D6058A5238F83C700BF7E4D /* Debug */,
				1D6058A6238F83C700BF7E4D /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
		1D6058AA238F83C700BF7E4D /* Build configuration list for PBXNativeTarget "BIT RAGE LABOURCommand" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				1D6058A7238F83C700BF7E4D /* Debug */,
				1D6058A8238F83C700BF7E4D /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
/* End XCConfigurationList section */
	};
	rootObject = 1D60588F238F83C700BF7E4D /* Project object */;
}
EOF

    # Create Swift files
    cat > BIT RAGE LABOURCommandApp.swift << EOF
//
//  BIT RAGE LABOURCommandApp.swift
//  BIT RAGE LABOURCommand
//
//  Created by Bit Rage Labour Setup on 2026-02-20.
//

import SwiftUI

@main
struct BIT RAGE LABOURCommandApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
EOF

    cat > ContentView.swift << EOF
//
//  ContentView.swift
//  BIT RAGE LABOURCommand
//
//  Created by Bit Rage Labour Setup on 2026-02-20.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = CommandCenterViewModel()

    var body: some View {
        NavigationView {
            ZStack {
                // Background
                Color(.systemBackground)
                    .edgesIgnoringSafeArea(.all)

                VStack(spacing: 20) {
                    // Header
                    HStack {
                        Image(systemName: "command.circle.fill")
                            .font(.system(size: 40))
                            .foregroundColor(.blue)
                        VStack(alignment: .leading) {
                            Text("Bit Rage Labour")
                                .font(.title)
                                .fontWeight(.bold)
                            Text("Command Center")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        Spacer()
                    }
                    .padding(.horizontal)

                    // System Status Cards
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 15) {
                            SystemStatusCard(
                                title: "macOS Live",
                                status: viewModel.macosStatus,
                                icon: "desktopcomputer"
                            )
                            SystemStatusCard(
                                title: "Windows Build",
                                status: viewModel.windowsStatus,
                                icon: "pc"
                            )
                            SystemStatusCard(
                                title: "AWS Cloud",
                                status: viewModel.awsStatus,
                                icon: "cloud.fill"
                            )
                        }
                        .padding(.horizontal)
                    }

                    // Operations Interface
                    VStack(alignment: .leading) {
                        Text("Operations")
                            .font(.headline)
                            .padding(.horizontal)

                        OperationsView()
                            .frame(height: 200)
                    }

                    Spacer()
                }
            }
            .navigationBarHidden(true)
        }
        .onAppear {
            viewModel.startMonitoring()
        }
    }
}

struct SystemStatusCard: View {
    let title: String
    let status: SystemStatus
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(status.color)
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)
            }

            Text(status.description)
                .font(.caption)
                .foregroundColor(.secondary)

            RoundedRectangle(cornerRadius: 2)
                .fill(status.color)
                .frame(height: 4)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
        .frame(width: 150)
    }
}

struct OperationsView: View {
    @State private var selectedDepartment = "NCC"

    var body: some View {
        VStack {
            Picker("Department", selection: $selectedDepartment) {
                Text("NCC").tag("NCC")
                Text("Council 52").tag("Council 52")
                Text("Portfolio Ops").tag("Portfolio Ops")
                Text("AI Research").tag("AI Research")
            }
            .pickerStyle(SegmentedPickerStyle())
            .padding(.horizontal)

            // Operations content would go here
            Text("Operations interface for \(selectedDepartment)")
                .foregroundColor(.secondary)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }
}

struct SystemStatus {
    let description: String
    let color: Color

    static let operational = SystemStatus(description: "Operational", color: .green)
    static let degraded = SystemStatus(description: "Degraded", color: .yellow)
    static let offline = SystemStatus(description: "Offline", color: .red)
    static let unknown = SystemStatus(description: "Unknown", color: .gray)
}

class CommandCenterViewModel: ObservableObject {
    @Published var macosStatus: SystemStatus = .operational
    @Published var windowsStatus: SystemStatus = .operational
    @Published var awsStatus: SystemStatus = .operational

    func startMonitoring() {
        // Start monitoring systems
        // This would connect to the Bit Rage Labour APIs
        Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { _ in
            self.checkSystemStatus()
        }
    }

    private func checkSystemStatus() {
        // Check system statuses from APIs
        // For now, simulate status updates
        let statuses: [SystemStatus] = [.operational, .degraded, .offline]
        self.macosStatus = statuses.randomElement() ?? .operational
        self.windowsStatus = statuses.randomElement() ?? .operational
        self.awsStatus = statuses.randomElement() ?? .operational
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
EOF

    cd ../..
    log_success "iOS development environment set up"
}

# Create launch scripts
create_launch_scripts() {
    log_info "Creating launch scripts..."

    # Create main launch script
    cat > launch_command_center.sh << 'EOF'
#!/bin/bash
# Bit Rage Labour Command Center Launcher

echo "🚀 Bit Rage Labour Command Center"
echo "=============================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Launch Matrix Monitor
echo "📊 Starting Matrix Monitor..."
python -m matrix_monitor &

# Launch Operations Interface
echo "🎯 Starting Operations Interface..."
python operations_launcher.py &

# Launch Galactia Doctrine (if configured)
if [ -f "galactia_config.json" ]; then
    echo "🧠 Starting Galactia Doctrine integration..."
    python -m galactia_integration &
fi

echo "✅ Command Center launched!"
echo "🌐 Matrix Monitor: http://localhost:3000"
echo "🎯 Operations: Running in terminal"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
trap 'echo "🛑 Shutting down Command Center..."; kill 0' INT
wait
EOF

    chmod +x launch_command_center.sh
    log_success "Launch scripts created"
}

# Main setup function
main() {
    echo ""
    log_info "Starting Bit Rage Labour macOS Command Center Setup..."
    echo ""

    install_homebrew
    install_dev_tools
    setup_bit_rage_labour
    setup_vscode
    setup_matrix_monitor
    setup_galactia
    setup_ios_dev
    create_launch_scripts

    echo ""
    log_success "🎉 Bit Rage Labour macOS Command Center Setup Complete!"
    echo ""
    echo "Next steps:"
    echo "1. Run: ./launch_command_center.sh"
    echo "2. Open VS Code: code ."
    echo "3. Configure API keys in environment variables"
    echo "4. Set up GitHub authentication: gh auth login"
    echo ""
    echo "Happy commanding! 🏛️⚡🤖"
}

# Run main setup
main
EOF