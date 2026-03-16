# 🚀 DIGITAL LABOUR Distributed Command Center

A comprehensive, AI-powered command and control system for distributed operations across macOS, Windows, and AWS cloud infrastructure.

## 🌟 Overview

The DIGITAL LABOUR Command Center provides real-time operational intelligence, conversational interfaces, and automated deployment capabilities across multiple platforms. It integrates Matrix Monitor for visualization, Galactia Doctrine for AI insights, and a distributed architecture for maximum scalability.

## 🏗️ Architecture

### Platform Distribution
- **macOS**: Live operations and iOS development
- **Windows**: Build infrastructure and CI/CD pipelines
- **AWS Cloud**: Compute scaling, storage, and API services

### Core Components
- **Operations Command Interface (OCI)**: Conversational AI for department access
- **Matrix Monitor**: Real-time visualization and monitoring
- **Galactia Doctrine**: AI-powered decision support
- **Distributed Infrastructure**: Auto-scaling cloud resources
- **Cross-Platform CI/CD**: Automated testing and deployment

## 🚀 Quick Start

### One-Command Launch

**macOS/Linux:**
```bash
./launch_command_center.sh --quick-start
```

**Windows:**
```powershell
.\launch_command_center.ps1 -QuickStart
```

This will:
1. Check prerequisites
2. Setup local environment
3. Launch all services
4. Display status and access points

### Manual Setup

1. **Setup Local Environment:**
   ```bash
   # macOS/Linux
   ./launch_command_center.sh --setup-local

   # Windows
   .\launch_command_center.ps1 -SetupLocal
   ```

2. **Setup Cloud Infrastructure:**
   ```bash
   # macOS/Linux
   ./launch_command_center.sh --setup-cloud

   # Windows
   .\launch_command_center.ps1 -SetupCloud
   ```

3. **Launch Services:**
   ```bash
   # macOS/Linux
   ./launch_command_center.sh --launch

   # Windows
   .\launch_command_center.ps1 -Launch
   ```

## 📋 Prerequisites

### macOS
- Homebrew (install from https://brew.sh/)
- Xcode Command Line Tools
- Python 3.8+

### Windows
- Chocolatey (install from https://chocolatey.org/)
- PowerShell 5.1+
- Python 3.8+

### Cloud
- AWS Account with appropriate permissions
- Terraform CLI (install from https://terraform.io/)
- AWS CLI (install from https://aws.amazon.com/cli/)

## 🎯 Access Points

After launching, access the command center through:

- **Matrix Monitor**: http://localhost:3000
- **Operations Interface**: http://localhost:5000
- **iOS Command App**: Open in Xcode (macOS only)
- **Cloud API**: Check Terraform outputs for endpoints

## 🛠️ Command Reference

### Launcher Options

**Interactive Mode:**
```bash
# macOS/Linux
./launch_command_center.sh

# Windows
.\launch_command_center.ps1 -Interactive
```

**Command Line Options:**
- `--setup-all` / `-SetupAll`: Complete setup (local + cloud)
- `--setup-local` / `-SetupLocal`: Local environment only
- `--setup-cloud` / `-SetupCloud`: Cloud infrastructure only
- `--launch` / `-Launch`: Start services
- `--status` / `-Status`: Show system status
- `--stop` / `-Stop`: Stop all services
- `--quick-start` / `-QuickStart`: Setup and launch

### Menu Options (Interactive)
1. Setup Everything (Local + Cloud)
2. Setup Local Only
3. Setup Cloud Only
4. Launch Services
5. Show Status
6. Stop Services
7. Quick Start (Setup + Launch)
8. Exit

## 📁 Project Structure

```
Digital-Labour/
├── launch_command_center.sh      # macOS/Linux launcher
├── launch_command_center.ps1     # Windows launcher
├── setup/
│   ├── macos-setup.sh           # macOS environment setup
│   └── windows-setup.ps1        # Windows environment setup
├── infrastructure/
│   ├── main.tf                  # AWS infrastructure (Terraform)
│   └── variables.tf             # Infrastructure variables
├── .github/
│   └── workflows/
│       └── distributed-ci-cd.yml # CI/CD pipeline
├── operations_*.py              # Operations Command Interface
├── matrix_monitor/              # Real-time monitoring
├── ios/                         # iOS command center app
└── galactia_integration/        # AI decision support
```

## 🔧 Configuration

### AWS Setup
1. Configure AWS CLI: `aws configure`
2. Set appropriate IAM permissions for Terraform
3. Review `infrastructure/variables.tf` for customization

### Environment Variables
Create a `.env` file for local configuration:
```bash
# Matrix Monitor
MATRIX_MONITOR_PORT=3000

# Operations Interface
OPERATIONS_PORT=5000

# AWS Region
AWS_REGION=us-east-1

# Galactia Doctrine
GALACTIA_API_KEY=your_api_key
```

### VS Code Extensions
The setup scripts install recommended extensions:
- Python
- AWS Toolkit
- Terraform
- GitHub Actions
- Matrix Monitor extension

## 📊 Monitoring & Status

Check system status anytime:
```bash
# macOS/Linux
./launch_command_center.sh --status

# Windows
.\launch_command_center.ps1 -Status
```

Status includes:
- Local service health (PIDs)
- Cloud infrastructure status
- Access points and endpoints
- Resource utilization

## 🛑 Troubleshooting

### Common Issues

**Services not starting:**
- Check Python dependencies: `pip install -r requirements.txt`
- Verify port availability
- Check log files in `logs/` directory

**Cloud setup fails:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check IAM permissions
- Review Terraform state: `cd infrastructure && terraform state list`

**Build failures:**
- Clear build cache: `rm -rf build/ dist/`
- Reinstall dependencies
- Check platform-specific requirements

### Logs
- Local logs: `logs/` directory
- Cloud logs: AWS CloudWatch
- CI/CD logs: GitHub Actions

## 🔒 Security

- AWS resources use least-privilege IAM roles
- Secrets managed via AWS Secrets Manager
- CI/CD includes security scanning
- Network traffic encrypted in transit
- Multi-factor authentication required for admin access

## 📈 Scaling

The system auto-scales based on:
- CPU utilization (>70% triggers scale-up)
- Memory usage (>80% triggers scale-up)
- Request latency (>500ms triggers scale-up)
- Custom metrics from Matrix Monitor

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request
5. CI/CD will run automated tests

## 📄 License

This project is proprietary to DIGITAL LABOUR operations.

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section
2. Review logs and status output
3. Create an issue in the repository
4. Contact the operations team

---

**Built with ❤️ by DIGITAL LABOUR Operations Team**