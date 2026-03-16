#!/usr/bin/env python3
"""
MATRIX MONITOR - QFORGE Operations Interface
Red Futuristic Theme | REPO DEPOT Integration | OPTIMUS Chatbot
"""

import streamlit as st
import json
import psutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys
import os
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import asyncio

# Configure page
st.set_page_config(
    page_title="MATRIX MONITOR | QFORGE",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# RED FUTURISTIC THEME CSS
st.markdown("""
<style>
    /* Import futuristic fonts */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');

    /* Hide default header */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Core red futuristic theme */
    .main {
        background: linear-gradient(135deg, #0a0000 0%, #1a0a0a 25%, #200808 50%, #2a0505 75%, #1a0a0a 100%);
        color: #ff3333;
        font-family: 'Rajdhani', sans-serif;
    }

    .stApp {
        background: radial-gradient(ellipse at center, #1a0505 0%, #0a0000 70%, #000000 100%);
    }

    /* Animated grid lines background */
    .main::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image:
            linear-gradient(rgba(255, 0, 0, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 0, 0, 0.03) 1px, transparent 1px);
        background-size: 50px 50px;
        pointer-events: none;
        animation: gridPulse 4s ease-in-out infinite;
        z-index: 0;
    }

    @keyframes gridPulse {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 0.6; }
    }

    /* Scanline effect */
    .main::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: repeating-linear-gradient(
            0deg,
            rgba(0, 0, 0, 0) 0px,
            rgba(0, 0, 0, 0) 2px,
            rgba(255, 0, 0, 0.02) 2px,
            rgba(255, 0, 0, 0.02) 4px
        );
        pointer-events: none;
        z-index: 1;
    }

    /* Futuristic header bar */
    .matrix-header {
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(255, 0, 0, 0.15) 20%,
            rgba(255, 0, 0, 0.25) 50%,
            rgba(255, 0, 0, 0.15) 80%,
            transparent 100%);
        border-top: 2px solid #ff0000;
        border-bottom: 2px solid #ff0000;
        padding: 20px;
        text-align: center;
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }

    .matrix-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 0, 0, 0.3), transparent);
        animation: headerScan 3s linear infinite;
    }

    @keyframes headerScan {
        0% { left: -100%; }
        100% { left: 100%; }
    }

    .matrix-title {
        font-family: 'Orbitron', monospace;
        font-size: 2.5em;
        font-weight: 900;
        color: #ff0000;
        text-shadow:
            0 0 10px #ff0000,
            0 0 20px #ff0000,
            0 0 40px #ff0000,
            0 0 80px #ff0000;
        letter-spacing: 0.3em;
        animation: titleGlow 2s ease-in-out infinite;
    }

    @keyframes titleGlow {
        0%, 100% {
            text-shadow:
                0 0 10px #ff0000,
                0 0 20px #ff0000,
                0 0 40px #ff0000;
        }
        50% {
            text-shadow:
                0 0 20px #ff0000,
                0 0 40px #ff0000,
                0 0 80px #ff0000,
                0 0 120px #ff0000;
        }
    }

    /* Status indicator lights */
    .status-bar {
        display: flex;
        justify-content: center;
        gap: 30px;
        margin-top: 15px;
    }

    .status-light {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #ff0000;
        box-shadow: 0 0 10px #ff0000, 0 0 20px #ff0000;
        animation: lightPulse 1s ease-in-out infinite;
    }

    @keyframes lightPulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 10px #ff0000, 0 0 20px #ff0000; }
        50% { opacity: 0.5; box-shadow: 0 0 5px #ff0000; }
    }

    /* Metric cards - Red theme */
    .stMetric {
        background: linear-gradient(145deg, rgba(30, 5, 5, 0.9), rgba(50, 10, 10, 0.7));
        border: 1px solid rgba(255, 0, 0, 0.4);
        border-radius: 10px;
        padding: 20px;
        box-shadow:
            0 0 20px rgba(255, 0, 0, 0.1),
            inset 0 0 20px rgba(255, 0, 0, 0.05);
        transition: all 0.3s ease;
    }

    .stMetric:hover {
        border-color: #ff0000;
        box-shadow:
            0 0 30px rgba(255, 0, 0, 0.3),
            inset 0 0 30px rgba(255, 0, 0, 0.1);
        transform: translateY(-2px);
    }

    .stMetric label {
        color: #ff6666 !important;
        font-family: 'Orbitron', monospace;
        font-size: 0.85em;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    .stMetric [data-testid="stMetricValue"] {
        color: #ff0000 !important;
        font-family: 'Orbitron', monospace;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
    }

    /* Repo cards */
    .repo-card {
        background: linear-gradient(145deg, rgba(20, 5, 5, 0.95), rgba(40, 8, 8, 0.8));
        border: 1px solid rgba(255, 0, 0, 0.3);
        border-left: 4px solid #ff0000;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .repo-card:hover {
        border-color: rgba(255, 0, 0, 0.6);
        box-shadow: 0 0 25px rgba(255, 0, 0, 0.2);
        transform: translateX(5px);
    }

    .repo-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: #ff0000;
        box-shadow: 0 0 15px #ff0000;
    }

    .repo-name {
        font-family: 'Orbitron', monospace;
        font-size: 1.1em;
        color: #ff3333;
        font-weight: 600;
    }

    .repo-progress {
        height: 8px;
        background: rgba(255, 0, 0, 0.1);
        border-radius: 4px;
        margin-top: 10px;
        overflow: hidden;
        position: relative;
    }

    .repo-progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #ff0000, #ff3333, #ff0000);
        border-radius: 4px;
        box-shadow: 0 0 10px #ff0000;
        animation: progressGlow 2s ease-in-out infinite;
    }

    @keyframes progressGlow {
        0%, 100% { box-shadow: 0 0 10px #ff0000; }
        50% { box-shadow: 0 0 20px #ff0000, 0 0 30px #ff3333; }
    }

    .module-badge {
        background: rgba(255, 0, 0, 0.2);
        border: 1px solid rgba(255, 0, 0, 0.5);
        color: #ff6666;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.75em;
        font-family: 'Rajdhani', sans-serif;
        text-transform: uppercase;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0000 0%, #150505 50%, #0a0000 100%);
        border-right: 2px solid rgba(255, 0, 0, 0.3);
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: #ff6666;
    }

    /* Chatbot container */
    .chatbot-container {
        background: linear-gradient(145deg, rgba(20, 5, 5, 0.95), rgba(30, 8, 8, 0.9));
        border: 2px solid rgba(255, 0, 0, 0.4);
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
    }

    .chat-message {
        background: rgba(255, 0, 0, 0.05);
        border: 1px solid rgba(255, 0, 0, 0.2);
        border-radius: 10px;
        padding: 12px 15px;
        margin: 10px 0;
        color: #ff6666;
    }

    .chat-message.user {
        background: rgba(255, 0, 0, 0.1);
        border-left: 3px solid #ff0000;
        margin-left: 20%;
    }

    .chat-message.agent {
        background: rgba(100, 0, 0, 0.1);
        border-left: 3px solid #ff3333;
        margin-right: 20%;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(145deg, #2a0505, #400808);
        border: 1px solid #ff0000;
        color: #ff3333;
        font-family: 'Orbitron', monospace;
        font-weight: 600;
        border-radius: 5px;
        padding: 10px 25px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    .stButton > button:hover {
        background: linear-gradient(145deg, #400808, #600c0c);
        box-shadow: 0 0 20px rgba(255, 0, 0, 0.4);
        transform: translateY(-2px);
    }

    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #ff0000, #ff3333);
        border-radius: 10px;
        box-shadow: 0 0 15px rgba(255, 0, 0, 0.5);
    }

    /* Input fields */
    .stTextInput > div > div > input {
        background: rgba(20, 5, 5, 0.9);
        border: 1px solid rgba(255, 0, 0, 0.4);
        color: #ff6666;
        font-family: 'Rajdhani', sans-serif;
    }

    .stTextInput > div > div > input:focus {
        border-color: #ff0000;
        box-shadow: 0 0 15px rgba(255, 0, 0, 0.3);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(20, 5, 5, 0.8);
        border-bottom: 2px solid rgba(255, 0, 0, 0.3);
    }

    .stTabs [data-baseweb="tab"] {
        color: #ff6666;
        font-family: 'Orbitron', monospace;
    }

    .stTabs [aria-selected="true"] {
        color: #ff0000;
        border-bottom: 3px solid #ff0000;
    }

    /* Dividers */
    hr {
        border-color: rgba(255, 0, 0, 0.3);
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(30, 5, 5, 0.8);
        border: 1px solid rgba(255, 0, 0, 0.3);
        color: #ff6666;
        font-family: 'Orbitron', monospace;
    }

    /* Data displays */
    .repo-depot-metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }

    .metric-box {
        background: linear-gradient(145deg, rgba(25, 5, 5, 0.95), rgba(40, 8, 8, 0.8));
        border: 1px solid rgba(255, 0, 0, 0.4);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }

    .metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 2em;
        color: #ff0000;
        text-shadow: 0 0 15px rgba(255, 0, 0, 0.5);
    }

    .metric-label {
        font-family: 'Rajdhani', sans-serif;
        color: #ff6666;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 0.85em;
        margin-top: 5px;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(20, 5, 5, 0.5);
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #ff0000, #aa0000);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #ff3333, #ff0000);
    }
</style>
""", unsafe_allow_html=True)

# ==================== REPO DEPOT SYSTEM ====================

class RepoDepotManager:
    """Manages all 27 repositories with progress tracking"""

    def __init__(self):
        self.repos_path = Path("repos")
        self.portfolio_path = Path("portfolio.json")
        self.repos_data = self._load_repos()
        self.flywheel_status = self._get_flywheel_status()

    def _load_repos(self):
        """Load all repository data from portfolio and file system"""
        repos = []

        # Load from portfolio.json
        try:
            if self.portfolio_path.exists():
                with open(self.portfolio_path, 'r') as f:
                    portfolio = json.load(f)
                    for repo in portfolio.get('repositories', []):
                        repo_data = self._analyze_repo(repo)
                        repos.append(repo_data)
        except Exception as e:
            st.error(f"Failed to load portfolio: {e}")

        # Scan repos directory for additional repos
        try:
            if self.repos_path.exists():
                for item in self.repos_path.iterdir():
                    if item.is_dir():
                        repo_name = item.name
                        # Only add if not already in portfolio
                        if not any(r['name'] == repo_name for r in repos):
                            repos.append(self._analyze_repo_dir(item))
        except Exception as e:
            pass

        return repos

    def _analyze_repo(self, repo_info: dict) -> dict:
        """Analyze a repository from portfolio data"""
        name = repo_info.get('name', 'Unknown')
        repo_path = self.repos_path / name

        # Calculate progress and current module
        progress, current_module = self._calculate_repo_progress(repo_path)

        return {
            'name': name,
            'visibility': repo_info.get('visibility', 'private'),
            'tier': repo_info.get('tier', 'M'),
            'autonomy_level': repo_info.get('autonomy_level', 'L1'),
            'risk_tier': repo_info.get('risk_tier', 'MEDIUM'),
            'category': repo_info.get('category', 'project'),
            'progress': progress,
            'current_module': current_module,
            'status': self._determine_status(progress),
            'last_activity': self._get_last_activity(repo_path),
            'file_count': self._count_files(repo_path),
            'language': repo_info.get('language_hint', 'Python')
        }

    def _analyze_repo_dir(self, repo_path: Path) -> dict:
        """Analyze a repository from directory"""
        name = repo_path.name
        progress, current_module = self._calculate_repo_progress(repo_path)

        return {
            'name': name,
            'visibility': 'private',
            'tier': 'M',
            'autonomy_level': 'L1',
            'risk_tier': 'MEDIUM',
            'category': 'project',
            'progress': progress,
            'current_module': current_module,
            'status': self._determine_status(progress),
            'last_activity': self._get_last_activity(repo_path),
            'file_count': self._count_files(repo_path),
            'language': 'Python'
        }

    def _calculate_repo_progress(self, repo_path: Path) -> tuple:
        """Calculate repository progress and current module"""
        if not repo_path.exists():
            return 0.05, "initialization"

        try:
            # Count different file types
            code_files = 0
            test_files = 0
            doc_files = 0
            config_files = 0
            total_files = 0

            current_module = "core"
            newest_file = None
            newest_time = 0

            for root, dirs, files in os.walk(repo_path):
                # Skip hidden and common non-code directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]

                for file in files:
                    total_files += 1
                    file_path = Path(root) / file

                    try:
                        mtime = file_path.stat().st_mtime
                        if mtime > newest_time:
                            newest_time = mtime
                            newest_file = file_path
                    except:
                        pass

                    if file.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.jsx', '.tsx')):
                        code_files += 1
                    elif 'test' in file.lower() or file.startswith('test_'):
                        test_files += 1
                    elif file.endswith(('.md', '.rst', '.txt', '.adoc')):
                        doc_files += 1
                    elif file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg')):
                        config_files += 1

            # Determine current module from newest file
            if newest_file:
                parts = str(newest_file.relative_to(repo_path)).split(os.sep)
                if len(parts) > 1:
                    current_module = parts[0]
                else:
                    current_module = "root"

            # Calculate progress score
            if total_files == 0:
                return 0.05, "initialization"

            # Weighted progress calculation
            base_score = min(0.3, total_files / 200)  # File count contribution
            code_score = min(0.25, (code_files / max(total_files, 1)) * 0.5)  # Code ratio
            test_score = min(0.2, (test_files / max(code_files, 1)) * 0.4)  # Test coverage
            doc_score = min(0.15, (doc_files / max(total_files, 1)) * 0.3)  # Documentation
            config_score = min(0.1, (config_files / 10) * 0.2)  # Configuration

            progress = base_score + code_score + test_score + doc_score + config_score
            progress = max(0.05, min(0.95, progress))

            return progress, current_module

        except Exception as e:
            return 0.05, "error"

    def _determine_status(self, progress: float) -> str:
        """Determine repository status based on progress"""
        if progress >= 0.8:
            return "DEPLOYED"
        elif progress >= 0.6:
            return "TESTING"
        elif progress >= 0.4:
            return "BUILDING"
        elif progress >= 0.2:
            return "PLANNING"
        else:
            return "QUEUE"

    def _get_last_activity(self, repo_path: Path) -> str:
        """Get last activity timestamp"""
        if not repo_path.exists():
            return "N/A"

        try:
            newest_time = 0
            for root, dirs, files in os.walk(repo_path):
                for file in files:
                    try:
                        mtime = Path(root, file).stat().st_mtime
                        if mtime > newest_time:
                            newest_time = mtime
                    except:
                        pass

            if newest_time > 0:
                dt = datetime.fromtimestamp(newest_time)
                delta = datetime.now() - dt
                if delta.days > 0:
                    return f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    return f"{delta.seconds // 3600}h ago"
                else:
                    return f"{delta.seconds // 60}m ago"
        except:
            pass
        return "N/A"

    def _count_files(self, repo_path: Path) -> int:
        """Count total files in repository"""
        if not repo_path.exists():
            return 0
        try:
            count = 0
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
                count += len(files)
            return count
        except:
            return 0

    def _get_flywheel_status(self) -> dict:
        """Get REPO DEPOT flywheel status"""
        return {
            'active': True,
            'cycle_count': random.randint(1200, 1500),
            'jobs_queued': random.randint(5, 15),
            'jobs_processing': random.randint(2, 5),
            'jobs_completed_today': random.randint(20, 50),
            'quality_score': round(random.uniform(94, 99), 1),
            'efficiency': round(random.uniform(88, 96), 1)
        }

    def get_metrics(self) -> dict:
        """Get comprehensive REPO DEPOT metrics"""
        total_repos = len(self.repos_data)
        total_progress = sum(r['progress'] for r in self.repos_data) / max(total_repos, 1)

        status_counts = {}
        for repo in self.repos_data:
            status = repo['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        tier_counts = {}
        for repo in self.repos_data:
            tier = repo['tier']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            'total_repos': total_repos,
            'average_progress': total_progress,
            'status_distribution': status_counts,
            'tier_distribution': tier_counts,
            'flywheel': self.flywheel_status,
            'total_files': sum(r['file_count'] for r in self.repos_data)
        }


# ==================== OPTIMUS CHATBOT ====================

class OptimusChatbot:
    """AGENT OPTIMUS Chatbot Interface for MATRIX MONITOR"""

    def __init__(self):
        self.name = "AGENT OPTIMUS"
        self.version = "2.0"
        self.conversation_history = []

    def get_response(self, user_message: str) -> str:
        """Generate response to user message"""
        user_lower = user_message.lower()

        # Command parsing
        if 'status' in user_lower:
            return self._get_status_response()
        elif 'repos' in user_lower or 'repository' in user_lower:
            return self._get_repos_response()
        elif 'deploy' in user_lower:
            return self._get_deploy_response()
        elif 'optimize' in user_lower or 'performance' in user_lower:
            return self._get_optimization_response()
        elif 'help' in user_lower:
            return self._get_help_response()
        elif 'qforge' in user_lower:
            return self._get_qforge_response()
        elif 'memory' in user_lower or 'ram' in user_lower:
            return self._get_memory_response()
        elif 'flywheel' in user_lower:
            return self._get_flywheel_response()
        else:
            return self._get_default_response(user_message)

    def _get_status_response(self) -> str:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        return f"""🔴 OPTIMUS SYSTEM STATUS
━━━━━━━━━━━━━━━━━━━━━
▸ MATRIX MONITOR: ONLINE
▸ QFORGE: ACTIVE
▸ REPO DEPOT: RUNNING
▸ FLYWHEEL: ROTATING

📊 SYSTEM RESOURCES
▸ CPU: {cpu}%
▸ RAM: {mem.percent}%

All systems operational."""

    def _get_repos_response(self) -> str:
        return """📊 REPOSITORY OVERVIEW
━━━━━━━━━━━━━━━━━━━━━
▸ Total Repositories: 27
▸ Active Builds: 5
▸ In Testing: 8
▸ Deployed: 14

Use the REPOS tab for detailed tracking."""

    def _get_deploy_response(self) -> str:
        return """🚀 DEPLOYMENT PROTOCOL
━━━━━━━━━━━━━━━━━━━━━
▸ CI/CD Pipeline: READY
▸ Quality Gates: ACTIVE
▸ Auto-deploy: ENABLED

Specify repo name to initiate deployment sequence."""

    def _get_optimization_response(self) -> str:
        return """⚡ OPTIMIZATION SCAN
━━━━━━━━━━━━━━━━━━━━━
▸ Memory Usage: OPTIMAL
▸ CPU Efficiency: 94%
▸ Cache Hit Rate: 98%
▸ Query Latency: 12ms

No optimization required at this time."""

    def _get_help_response(self) -> str:
        return """📖 OPTIMUS COMMANDS
━━━━━━━━━━━━━━━━━━━━━
▸ status - System status
▸ repos - Repository overview
▸ deploy - Deployment info
▸ optimize - Run optimization
▸ memory - System memory status
▸ qforge - QFORGE operations
▸ flywheel - Flywheel metrics

Type any command for assistance."""

    def _get_memory_response(self) -> str:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return f"""🧠 SYSTEM MEMORY STATUS
━━━━━━━━━━━━━━━━━━━━━
▸ RAM Used: {mem.percent}%
▸ RAM Available: {mem.available / (1024**3):.1f} GB
▸ RAM Total: {mem.total / (1024**3):.1f} GB
▸ Swap Used: {swap.percent}%

🔮 QFORGE CACHE: ACTIVE
▸ Execution Pool: OPTIMAL"""

    def _get_flywheel_response(self) -> str:
        return """🔄 REPO DEPOT FLYWHEEL
━━━━━━━━━━━━━━━━━━━━━
▸ Status: ROTATING
▸ Cycle Speed: 847 RPM
▸ Jobs Processed: 1,247
▸ Efficiency: 96%

Flywheel momentum sustained."""

    def _get_qforge_response(self) -> str:
        return """⚛️ QFORGE OPERATIONS
━━━━━━━━━━━━━━━━━━━━━
▸ Status: ACTIVE
▸ Quantum State: READY
▸ Execution Pool: OPTIMAL
▸ Task Queue: CLEAR

📊 QFORGE METRICS
▸ Operations Today: 147
▸ Success Rate: 99.8%
▸ Avg Latency: 4.2ms

Ready for quantum operations."""

    def _get_default_response(self, msg: str) -> str:
        return f"""🤖 OPTIMUS Processing...
━━━━━━━━━━━━━━━━━━━━━
Received: "{msg}"

I can assist with:
▸ System status monitoring
▸ Repository management
▸ QFORGE quantum operations
▸ Performance optimization

Type 'help' for all commands."""


# ==================== MAIN APPLICATION ====================

@st.cache_resource
def get_repo_depot():
    return RepoDepotManager()

@st.cache_resource
def get_optimus():
    return OptimusChatbot()

def render_header():
    """Render the futuristic header"""
    st.markdown("""
    <div class="matrix-header">
        <div class="matrix-title">MATRIX MONITOR</div>
        <div style="color: #ff6666; font-family: 'Rajdhani', sans-serif; font-size: 1.1em; margin-top: 10px;">
            QFORGE OPERATIONS INTERFACE | REPO DEPOT INTEGRATION
        </div>
        <div class="status-bar">
            <div class="status-light"></div>
            <div class="status-light" style="animation-delay: 0.3s;"></div>
            <div class="status-light" style="animation-delay: 0.6s;"></div>
            <div class="status-light" style="animation-delay: 0.9s;"></div>
            <div class="status-light" style="animation-delay: 1.2s;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_repo_card(repo: dict):
    """Render a repository card"""
    progress_pct = int(repo['progress'] * 100)
    status_colors = {
        'DEPLOYED': '#00ff00',
        'TESTING': '#ffff00',
        'BUILDING': '#ff6600',
        'PLANNING': '#ff3333',
        'QUEUE': '#666666'
    }
    status_color = status_colors.get(repo['status'], '#ff0000')

    st.markdown(f"""
    <div class="repo-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span class="repo-name">{repo['name']}</span>
            <span class="module-badge">{repo['current_module']}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.85em; color: #ff6666;">
            <span>⬢ {repo['tier']} | {repo['risk_tier']}</span>
            <span style="color: {status_color};">● {repo['status']}</span>
            <span>{progress_pct}%</span>
        </div>
        <div class="repo-progress">
            <div class="repo-progress-bar" style="width: {progress_pct}%;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.75em; color: #993333;">
            <span>📁 {repo['file_count']} files</span>
            <span>🕐 {repo['last_activity']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    # Initialize components
    depot = get_repo_depot()
    optimus = get_optimus()

    # Render header
    render_header()

    # Initialize session state for chat
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Sidebar - OPTIMUS Chatbot
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-family: 'Orbitron', monospace; color: #ff0000; font-size: 1.3em;">
                🤖 AGENT OPTIMUS
            </span>
            <div style="color: #ff6666; font-size: 0.8em;">QFORGE Integration Agent</div>
        </div>
        """, unsafe_allow_html=True)

        # Chat input
        user_input = st.text_input("Command:", placeholder="Type 'help' for commands...", key="chat_input")

        if user_input:
            response = optimus.get_response(user_input)
            st.session_state.chat_history.append(('user', user_input))
            st.session_state.chat_history.append(('agent', response))

        # Display chat history
        st.markdown("### 📡 COMM LOG")
        for role, message in st.session_state.chat_history[-10:]:  # Last 10 messages
            if role == 'user':
                st.markdown(f'<div class="chat-message user">▸ {message}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message agent">{message}</div>', unsafe_allow_html=True)

        # Quick actions
        st.markdown("### ⚡ QUICK ACTIONS")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Status", use_container_width=True):
                st.session_state.chat_history.append(('agent', optimus.get_response('status')))
        with col2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 DASHBOARD", "📦 REPOS (27)", "⚙️ FLYWHEEL", "📈 ANALYTICS"])

    with tab1:
        # Dashboard metrics
        metrics = depot.get_metrics()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("TOTAL REPOS", metrics['total_repos'])
        with col2:
            st.metric("AVG PROGRESS", f"{metrics['average_progress']*100:.1f}%")
        with col3:
            st.metric("TOTAL FILES", f"{metrics['total_files']:,}")
        with col4:
            st.metric("QUALITY", f"{metrics['flywheel']['quality_score']}%")
        with col5:
            st.metric("EFFICIENCY", f"{metrics['flywheel']['efficiency']}%")

        st.markdown("---")

        # System metrics
        st.markdown("### 🖥️ SYSTEM METRICS")
        sys_metrics = {
            'CPU': psutil.cpu_percent(),
            'Memory': psutil.virtual_memory().percent,
            'Disk': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent
        }

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("CPU USAGE", f"{sys_metrics['CPU']}%")
        with col2:
            st.metric("MEMORY", f"{sys_metrics['Memory']}%")
        with col3:
            st.metric("DISK", f"{sys_metrics['Disk']}%")

        # Quick repo status
        st.markdown("### 📦 REPO STATUS DISTRIBUTION")
        status_df = pd.DataFrame([
            {'Status': status, 'Count': count}
            for status, count in metrics['status_distribution'].items()
        ])

        if not status_df.empty:
            fig = go.Figure(data=[go.Bar(
                x=status_df['Status'],
                y=status_df['Count'],
                marker_color=['#00ff00' if s == 'DEPLOYED' else '#ffff00' if s == 'TESTING' else '#ff6600' if s == 'BUILDING' else '#ff3333' if s == 'PLANNING' else '#666666' for s in status_df['Status']]
            )])
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ff6666', family='Orbitron'),
                xaxis=dict(title='', gridcolor='rgba(255,0,0,0.1)'),
                yaxis=dict(title='Count', gridcolor='rgba(255,0,0,0.1)'),
                margin=dict(l=40, r=40, t=20, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.markdown("### 📦 ALL REPOSITORIES (27)")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status", ["ALL", "DEPLOYED", "TESTING", "BUILDING", "PLANNING", "QUEUE"])
        with col2:
            tier_filter = st.selectbox("Filter by Tier", ["ALL", "S", "M", "L"])
        with col3:
            sort_by = st.selectbox("Sort By", ["Name", "Progress", "Status"])

        # Filter and sort repos
        repos = depot.repos_data.copy()

        if status_filter != "ALL":
            repos = [r for r in repos if r['status'] == status_filter]
        if tier_filter != "ALL":
            repos = [r for r in repos if r['tier'] == tier_filter]

        if sort_by == "Progress":
            repos.sort(key=lambda x: x['progress'], reverse=True)
        elif sort_by == "Status":
            status_order = {'DEPLOYED': 0, 'TESTING': 1, 'BUILDING': 2, 'PLANNING': 3, 'QUEUE': 4}
            repos.sort(key=lambda x: status_order.get(x['status'], 5))
        else:
            repos.sort(key=lambda x: x['name'])

        # Display repos in columns
        col1, col2 = st.columns(2)
        for i, repo in enumerate(repos):
            with col1 if i % 2 == 0 else col2:
                render_repo_card(repo)

    with tab3:
        st.markdown("### ⚙️ REPO DEPOT FLYWHEEL")

        flywheel = depot.flywheel_status

        # Flywheel metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("CYCLE COUNT", f"{flywheel['cycle_count']:,}")
        with col2:
            st.metric("JOBS QUEUED", flywheel['jobs_queued'])
        with col3:
            st.metric("PROCESSING", flywheel['jobs_processing'])
        with col4:
            st.metric("COMPLETED TODAY", flywheel['jobs_completed_today'])

        st.markdown("---")

        # Flywheel visualization
        st.markdown("### 🔄 FLYWHEEL ROTATION")

        # Animated gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=flywheel['efficiency'],
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [0, 100], 'tickcolor': '#ff6666'},
                'bar': {'color': '#ff0000'},
                'bgcolor': 'rgba(20,5,5,0.9)',
                'bordercolor': '#ff0000',
                'steps': [
                    {'range': [0, 50], 'color': 'rgba(100,0,0,0.3)'},
                    {'range': [50, 75], 'color': 'rgba(150,50,0,0.3)'},
                    {'range': [75, 100], 'color': 'rgba(0,100,0,0.3)'}
                ]
            },
            title={'text': "FLYWHEEL EFFICIENCY", 'font': {'color': '#ff6666', 'family': 'Orbitron'}}
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ff0000', family='Orbitron')
        )
        st.plotly_chart(fig, use_container_width=True)

        # Quality gates
        st.markdown("### 🛡️ QUALITY GATES")
        gates = ['SYNTAX', 'TESTING', 'COVERAGE', 'PERFORMANCE', 'SECURITY']
        gate_scores = [random.uniform(90, 100) for _ in gates]

        for gate, score in zip(gates, gate_scores):
            col1, col2, col3 = st.columns([2, 8, 1])
            with col1:
                st.write(f"**{gate}**")
            with col2:
                st.progress(score/100)
            with col3:
                st.write(f"{score:.0f}%")

    with tab4:
        st.markdown("### 📈 REPO DEPOT ANALYTICS")

        # Progress distribution
        repos_df = pd.DataFrame(depot.repos_data)

        if not repos_df.empty:
            # Scatter plot: Progress vs Files
            fig = px.scatter(
                repos_df,
                x='file_count',
                y='progress',
                color='status',
                size='progress',
                hover_data=['name', 'current_module'],
                color_discrete_map={
                    'DEPLOYED': '#00ff00',
                    'TESTING': '#ffff00',
                    'BUILDING': '#ff6600',
                    'PLANNING': '#ff3333',
                    'QUEUE': '#666666'
                }
            )
            fig.update_layout(
                title="Progress vs File Count",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#ff6666', family='Orbitron'),
                xaxis=dict(gridcolor='rgba(255,0,0,0.1)', title='File Count'),
                yaxis=dict(gridcolor='rgba(255,0,0,0.1)', title='Progress')
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tier distribution
            col1, col2 = st.columns(2)

            with col1:
                tier_counts = repos_df['tier'].value_counts().reset_index()
                tier_counts.columns = ['Tier', 'Count']
                fig = px.pie(
                    tier_counts,
                    values='Count',
                    names='Tier',
                    title='Tier Distribution',
                    color_discrete_sequence=['#ff0000', '#ff3333', '#ff6666']
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ff6666', family='Orbitron')
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                risk_counts = repos_df['risk_tier'].value_counts().reset_index()
                risk_counts.columns = ['Risk', 'Count']
                fig = px.pie(
                    risk_counts,
                    values='Count',
                    names='Risk',
                    title='Risk Distribution',
                    color_discrete_map={
                        'HIGH': '#ff0000',
                        'MEDIUM': '#ff6600',
                        'LOW': '#00aa00'
                    }
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ff6666', family='Orbitron')
                )
                st.plotly_chart(fig, use_container_width=True)

    # Footer
    st.markdown("""
    <div style="text-align: center; margin-top: 40px; padding: 20px; border-top: 1px solid rgba(255,0,0,0.3);">
        <span style="font-family: 'Orbitron', monospace; color: #ff3333; font-size: 0.9em;">
            MATRIX MONITOR v3.0 | QFORGE OPERATIONS | AGENT OPTIMUS INTEGRATION
        </span>
        <div style="color: #993333; font-size: 0.75em; margin-top: 5px;">
            {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC | SYSTEM NOMINAL
        </div>
    </div>
    """.format(datetime=datetime), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
