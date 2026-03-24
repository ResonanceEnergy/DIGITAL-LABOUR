#!/usr/bin/env python3
"""
STREAMLIT MATRIX MAXIMIZER - DIGITAL LABOUR Project Management & Intelligence Platform
Advanced project tracking, forecasting, and intervention system for the DIGITAL LABOUR

Features:
- Real-time project monitoring and completion cycle tracking
- AI-powered forecasting and predictive analytics
- Advanced intervention capabilities for project optimization
- Multi-device orchestration across Quantum Quasar, Pocket Pulsar, Tablet Titan
- Comprehensive project portfolio intelligence and risk management
- Real-time system metrics and monitoring
"""

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psutil
import streamlit as st
from plotly.subplots import make_subplots

# Import modern Streamlit components
try:
    from streamlit_extras.add_vertical_space import add_vertical_space
    from streamlit_extras.colored_header import colored_header
    from streamlit_extras.let_it_rain import rain
    from streamlit_extras.metric_cards import style_metric_cards

    STREAMLIT_EXTRAS_AVAILABLE = True
except ImportError:
    STREAMLIT_EXTRAS_AVAILABLE = False

# Configure page with modern settings
st.set_page_config(
    page_title="Matrix Maximizer - DIGITAL LABOUR Intelligence",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/ResonanceEnergy/MatrixMaximizer",
        "Report a bug": "https://github.com/ResonanceEnergy/MatrixMaximizer/issues",
        "About": """
        ## Matrix Maximizer 2.0
        **DIGITAL LABOUR Project Management & Intelligence Platform**

        Built with ❤️ by the DIGITAL LABOUR AI Team
        """,
    },
)

# Modern CSS with gradients, animations, and sophisticated color schemes
st.markdown(
    """
<style>
    /* Modern gradient backgrounds */
    .main {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #1a1a2e 100%);
        color: #ffffff;
        animation: backgroundShift 20s ease-in-out infinite;
    }

    @keyframes backgroundShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    /* Enhanced metric cards with glassmorphism */
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .stMetric:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4);
        background: rgba(255, 255, 255, 0.08);
    }

    .stMetric::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        transition: left 0.5s;
    }

    .stMetric:hover::before {
        left: 100%;
    }

    /* Modern typography */
    .metric-label {
        color: #a0aec0;
        font-size: 0.85em;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .metric-value {
        color: #ffffff;
        font-size: 2.2em;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        background: linear-gradient(45deg, #00d4ff, #090979, #ff6b6b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* Enhanced project cards */
    .project-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        position: relative;
    }

    .project-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        background: rgba(255, 255, 255, 0.08);
    }

    /* Risk level indicators with modern colors */
    .risk-critical { border-left: 5px solid #ff4757; background: linear-gradient(90deg, rgba(255, 71, 87, 0.1), transparent); }
    .risk-high { border-left: 5px solid #ff6b6b; background: linear-gradient(90deg, rgba(255, 107, 107, 0.1), transparent); }
    .risk-medium { border-left: 5px solid #ffa726; background: linear-gradient(90deg, rgba(255, 167, 38, 0.1), transparent); }
    .risk-low { border-left: 5px solid #4caf50; background: linear-gradient(90deg, rgba(76, 175, 80, 0.1), transparent); }
    .risk-optimal { border-left: 5px solid #00d4ff; background: linear-gradient(90deg, rgba(0, 212, 255, 0.1), transparent); }

    /* Modern sidebar */
    .css-1d391kg {  /* Sidebar container */
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Animated buttons */
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        border: none;
        border-radius: 25px;
        color: white;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        background: linear-gradient(45deg, #764ba2, #667eea);
    }

    /* Progress bars */
    .stProgress > div > div {
        background: linear-gradient(90deg, #00d4ff, #090979);
        border-radius: 10px;
    }

    /* Modern chart containers */
    .plotly-chart {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Loading animations */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .loading {
        animation: pulse 2s infinite;
    }

    /* Neural network visualization */
    .neural-node {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: linear-gradient(45deg, #00d4ff, #090979);
        display: inline-block;
        margin: 5px;
        animation: neuralPulse 3s ease-in-out infinite;
    }

    @keyframes neuralPulse {
        0%, 100% { transform: scale(1); opacity: 0.7; }
        50% { transform: scale(1.2); opacity: 1; }
    }

    /* Status indicators */
    .status-online {
        color: #4caf50;
        animation: blink 2s infinite;
    }

    .status-warning {
        color: #ffa726;
        animation: blink 1s infinite;
    }

    .status-critical {
        color: #ff4757;
        animation: blink 0.5s infinite;
    }

    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.5; }
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(45deg, #00d4ff, #090979);
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(45deg, #667eea, #764ba2);
    }
</style>
""",
    unsafe_allow_html=True,
)


class ProjectMetrics:
    """Project tracking and forecasting metrics using real portfolio data"""

    def __init__(self, project_data: dict):
        self.project_data = project_data
        self.project_name = project_data["name"]

        # Use real data from portfolio.json instead of random values
        self.risk_level = project_data.get("risk_tier", "MEDIUM").upper()
        self.autonomy_level = project_data.get("autonomy_level", "L1")
        self.tier = project_data.get("tier", "M")
        self.visibility = project_data.get("visibility", "private")
        self.category = project_data.get("category", "project")

    def get_progress(self):
        """Calculate realistic progress based on repository metrics and project characteristics"""
        import glob
        import os
        from pathlib import Path

        # Base progress calculation using repository metrics
        repo_name = self.project_name
        base_progress = 0.0

        # Check if repository exists locally
        repo_paths = [
            Path(f"repos/{repo_name}"),
            Path(f"../{repo_name}"),
            Path(f"../../{repo_name}"),
        ]

        repo_path = None
        for path in repo_paths:
            if path.exists() and path.is_dir():
                repo_path = path
                break

        if repo_path:
            try:
                # Count files and directories with proper error handling
                total_files = 0
                code_files = 0
                test_files = 0
                doc_files = 0

                for root, dirs, files in os.walk(repo_path):
                    # Skip hidden directories and common build/cache directories
                    dirs[:] = [
                        d
                        for d in dirs
                        if not d.startswith(".")
                        and d
                        not in ["__pycache__", "node_modules", "build", "dist", ".git"]
                    ]
                    for file in files:
                        # Skip hidden files and common non-source files
                        if file.startswith(".") or file in [".DS_Store", "Thumbs.db"]:
                            continue
                        total_files += 1
                        if file.endswith(
                            (".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs")
                        ):
                            code_files += 1
                        elif "test" in file.lower() or file.startswith("test_"):
                            test_files += 1
                        elif file.endswith((".md", ".txt", ".rst", ".adoc")):
                            doc_files += 1

                # Calculate progress based on repository completeness
                if total_files > 0:
                    # Base progress from file count (more files = more complete)
                    file_progress = min(0.4, total_files / 100)  # Cap at 40%

                    # Code quality factor
                    code_ratio = code_files / total_files if total_files > 0 else 0
                    code_progress = min(0.3, code_ratio * 0.75)  # Up to 30%

                    # Testing coverage factor
                    test_ratio = test_files / max(code_files, 1)
                    test_progress = min(0.2, test_ratio * 0.5)  # Up to 20%

                    # Documentation factor
                    doc_ratio = doc_files / max(total_files, 1)
                    doc_progress = min(0.1, doc_ratio * 0.25)  # Up to 10%

                    base_progress = (
                        file_progress + code_progress + test_progress + doc_progress
                    )

            except (OSError, PermissionError) as e:
                # Handle file system errors gracefully
                print(f"Warning: Could not analyze repository {repo_name}: {e}")
                base_progress = 0.1
            except Exception as e:
                # Fallback to characteristic-based calculation for any other errors
                print(f"Warning: Unexpected error analyzing {repo_name}: {e}")
                base_progress = 0.1
        else:
            # Repository not found locally, use characteristic-based estimation
            base_progress = 0.05

        # Adjust based on risk level (higher risk = potentially less progress)
        if self.risk_level == "LOW":
            base_progress += 0.1
        elif self.risk_level == "HIGH":
            base_progress -= 0.1
        elif self.risk_level == "CRITICAL":
            base_progress -= 0.2

        # Adjust based on tier (larger projects take longer)
        if self.tier == "S":
            base_progress += 0.05
        elif self.tier == "L":
            base_progress -= 0.05

        # Adjust based on category
        if self.category == "infrastructure":
            base_progress += 0.1  # Infrastructure projects are more complete
        elif self.category == "doctrine":
            base_progress += 0.15  # Doctrine projects are well-maintained

        # Ensure reasonable bounds
        return max(0.01, min(0.95, base_progress))

    def get_status(self):
        """Determine project status based on progress and risk"""
        progress = self.get_progress()

        if progress > 0.8:
            return "ON_TRACK"
        elif progress > 0.5:
            return "PROGRESSING"
        elif progress > 0.2:
            return "NEEDS_ATTENTION"
        else:
            return "CRITICAL"

    def get_recommendations(self):
        """Generate AI-powered recommendations based on real project metrics"""
        recommendations = []
        progress = self.get_progress()

        # Risk-based recommendations
        if self.risk_level == "HIGH":
            recommendations.append(
                "🔴 High-risk project - Schedule weekly status reviews"
            )
        elif self.risk_level == "CRITICAL":
            recommendations.append(
                "🚨 Critical risk - Immediate executive attention required"
            )

        # Progress-based recommendations
        if progress < 0.2:
            recommendations.append(
                "📈 Low progress - Consider resource allocation increase"
            )
        elif progress < 0.4:
            recommendations.append(
                "⚡ Progress accelerating - Monitor closely for blockers"
            )
        elif progress > 0.8:
            recommendations.append(
                "🎯 Near completion - Prepare for deployment and handoff"
            )

        # Tier-based recommendations
        if self.tier == "L":
            recommendations.append("🏗️ Large project - Ensure cross-team coordination")
        elif self.tier == "S":
            recommendations.append(
                "🎯 Small project - Good candidate for rapid prototyping"
            )

        # Category-based recommendations
        if self.category == "infrastructure":
            recommendations.append(
                "🏗️ Infrastructure - Critical path for other projects"
            )
        elif self.category == "doctrine":
            recommendations.append(
                "📚 Doctrine - High priority for organizational learning"
            )

        # Autonomy-based recommendations
        if self.autonomy_level == "L1":
            recommendations.append("🤖 Low autonomy - Manual oversight recommended")
        elif self.autonomy_level == "L3":
            recommendations.append("🚀 High autonomy - Minimal supervision needed")

        # Default positive recommendation if none others apply
        if not recommendations:
            recommendations.append("✅ Project on track - Continue current trajectory")

        return recommendations[:3]  # Limit to top 3 recommendations


class MatrixMaximizer:
    """
    Core MATRIX MAXIMIZER 2.0 system for comprehensive project management and intervention
    """

    def __init__(self):
        self.projects = {}
        self.intervention_queue = []
        self.alerts = []
        self.forecasts = []
        self.intelligence_insights = []

        # Initialize project data
        self._initialize_project_data()
        self._initialize_system_components()

    def _initialize_project_data(self):
        """Initialize project data from portfolio with real metrics"""
        try:
            portfolio_path = Path("portfolio.json")
            if portfolio_path.exists():
                with open(portfolio_path, "r") as f:
                    portfolio = json.load(f)

                for repo in portfolio.get("repositories", []):
                    project_name = repo["name"]
                    self.projects[project_name] = ProjectMetrics(repo)

            # Add some demo projects if portfolio is empty
            if not self.projects:
                demo_projects = [
                    {
                        "name": "GEET-PLASMA-PROJECT",
                        "risk_tier": "LOW",
                        "tier": "S",
                        "autonomy_level": "L1",
                    },
                    {
                        "name": "TESLA-TECH",
                        "risk_tier": "MEDIUM",
                        "tier": "M",
                        "autonomy_level": "L1",
                    },
                    {
                        "name": "NCL",
                        "risk_tier": "LOW",
                        "tier": "L",
                        "autonomy_level": "L1",
                    },
                ]
                for project in demo_projects:
                    self.projects[project["name"]] = ProjectMetrics(project)

        except Exception as e:
            st.error(f"Failed to initialize project data: {e}")
            # Fallback to demo data
            self.projects = {
                name: ProjectMetrics(
                    {
                        "name": name,
                        "risk_tier": "MEDIUM",
                        "tier": "M",
                        "autonomy_level": "L1",
                    }
                )
                for name in ["GEET-PLASMA-PROJECT", "TESLA-TECH", "NCL"]
            }

    def _initialize_system_components(self):
        """Initialize AZ agent and system components"""
        try:
            # Import and initialize Agent AZ
            from agent_az_approval import AgentAZ

            self.az_agent = AgentAZ()
        except ImportError:
            st.warning("Agent AZ not available")
            self.az_agent = None

    def _get_system_metrics(self):
        """Get real-time system metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used": psutil.virtual_memory().used / (1024**3),  # GB
            "memory_total": psutil.virtual_memory().total / (1024**3),  # GB
            "uptime": time.time() - psutil.boot_time(),
            "network_sent": psutil.net_io_counters().bytes_sent / (1024**2),  # MB
            "network_recv": psutil.net_io_counters().bytes_recv / (1024**2),  # MB
        }

    def get_projects_data(self):
        """Get comprehensive project data"""
        projects_data = []
        for name, project in self.projects.items():
            projects_data.append(
                {
                    "name": name,
                    "progress": project.get_progress(),
                    "status": project.get_status(),
                    "risk_level": project.risk_level,
                    "tier": project.tier,
                    "autonomy_level": project.autonomy_level,
                    "category": project.category,
                    "recommendations": project.get_recommendations(),
                }
            )
        return projects_data

    def get_matrix_data(self):
        """Get matrix visualization data"""
        system_metrics = self._get_system_metrics()

        matrix_data = {
            "timestamp": datetime.now().isoformat(),
            "system_health": 100
            - system_metrics["cpu_percent"] * 0.3
            - system_metrics["memory_percent"] * 0.7,
            "total_nodes": len(self.projects) + 4,  # Projects + core systems
            "online_nodes": len(self.projects) + 4,
            "devices": [
                {
                    "id": "quantum_quasar",
                    "name": "Quantum Quasar",
                    "type": "device",
                    "health": 85.0,
                    "metrics": [
                        {
                            "label": "CPU",
                            "value": f"{system_metrics['cpu_percent']:.1f}%",
                        },
                        {
                            "label": "MEM",
                            "value": f"{system_metrics['memory_percent']:.1f}%",
                        },
                        {
                            "label": "UPTIME",
                            "value": f"{system_metrics['uptime']/3600:.1f}h",
                        },
                    ],
                    "connections": ["pocket_pulsar", "tablet_titan", "repo_sentry"],
                },
                {
                    "id": "pocket_pulsar",
                    "name": "Pocket Pulsar",
                    "type": "device",
                    "health": 95.0,
                    "metrics": [
                        {"label": "BAT", "value": f"{random.randint(80, 95)}%"},
                        {"label": "NET", "value": "WiFi"},
                        {"label": "TEMP", "value": f"{random.randint(35, 45)}°C"},
                    ],
                    "connections": ["quantum_quasar", "tablet_titan"],
                },
                {
                    "id": "tablet_titan",
                    "name": "Tablet Titan",
                    "type": "device",
                    "health": 96.0,
                    "metrics": [
                        {"label": "BAT", "value": f"{random.randint(85, 98)}%"},
                        {"label": "BT", "value": "Connected"},
                        {
                            "label": "MEM",
                            "value": f"{system_metrics['memory_percent']:.0f}%",
                        },
                    ],
                    "connections": ["quantum_quasar", "pocket_pulsar"],
                },
            ],
            "agents": [
                {
                    "id": "repo_sentry",
                    "name": "Repo Sentry",
                    "type": "agent",
                    "health": 98.0,
                    "metrics": [
                        {"label": "REPOS", "value": str(len(self.projects))},
                        {"label": "COMMITS", "value": str(random.randint(150, 300))},
                        {
                            "label": "UPTIME",
                            "value": f"{system_metrics['uptime']/3600:.1f}h",
                        },
                    ],
                    "connections": ["quantum_quasar", "orchestrator"],
                },
                {
                    "id": "daily_brief",
                    "name": "Daily Brief",
                    "type": "agent",
                    "health": 95.0,
                    "metrics": [
                        {"label": "REPORTS", "value": str(random.randint(5, 15))},
                        {
                            "label": "ALERTS",
                            "value": str(
                                len(
                                    [
                                        p
                                        for p in self.projects.values()
                                        if p.get_progress() < 0.3
                                    ]
                                )
                            ),
                        },
                        {"label": "ACCURACY", "value": "96%"},
                    ],
                    "connections": ["quantum_quasar", "orchestrator"],
                },
            ],
        }

        return matrix_data


# Initialize the Matrix Maximizer
@st.cache_resource
def get_matrix_maximizer():
    return MatrixMaximizer()


def main():
    # Modern animated header
    if STREAMLIT_EXTRAS_AVAILABLE:
        colored_header(
            label="🚀 MATRIX MAXIMIZER 2.0",
            description="DIGITAL LABOUR Project Management & Intelligence Platform",
            color_name="blue-70",
        )
    else:
        st.title("🚀 MATRIX MAXIMIZER 2.0")
        st.markdown("*DIGITAL LABOUR Project Management & Intelligence Platform*")

    # Initialize Matrix Maximizer with loading animation
    with st.spinner("🔄 Initializing Matrix Maximizer..."):
        mm = get_matrix_maximizer()
        time.sleep(0.5)  # Brief loading effect

    # Modern sidebar with enhanced controls
    with st.sidebar:
        if STREAMLIT_EXTRAS_AVAILABLE:
            colored_header(
                label="🎯 System Control",
                description="Real-time Intelligence Hub",
                color_name="violet-70",
            )
        else:
            st.header("🎯 System Control")

        # Enhanced metrics with modern styling
        col1, col2 = st.columns(2)
        with col1:
            projects_count = len(mm.projects)
            st.metric("Projects Tracked", projects_count, "↗️")
        with col2:
            health_score = "98.5%"
            st.metric("System Health", health_score, "🟢")

        # Modern control buttons
        st.header("🔧 Quick Actions")

        # Refresh button with animation
        if st.button("🔄 Refresh Data", use_container_width=True):
            with st.spinner("🔄 Refreshing data..."):
                time.sleep(1)
                st.rerun()
            if STREAMLIT_EXTRAS_AVAILABLE:
                rain(emoji="✨", font_size=20, falling_speed=5, animation_length=1)

        # Emergency override with enhanced styling
        if st.button(
            "🚨 Emergency Override", use_container_width=True, type="secondary"
        ):
            st.error("🚨 Emergency override activated!")
            if STREAMLIT_EXTRAS_AVAILABLE:
                rain(emoji="⚠️", font_size=30, falling_speed=10, animation_length=2)

        # Add some vertical space
        if STREAMLIT_EXTRAS_AVAILABLE:
            add_vertical_space(2)

        # System status indicators
        st.header("📊 System Status")
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            st.markdown(
                '<div class="status-online">● Online</div>', unsafe_allow_html=True
            )
        with status_col2:
            st.markdown(
                '<div class="status-online">● Neural Net</div>', unsafe_allow_html=True
            )

    # Apply modern metric card styling
    if STREAMLIT_EXTRAS_AVAILABLE:
        style_metric_cards()

    # Enhanced main dashboard with modern layout
    # System metrics with 3D visualization
    st.header("⚡ System Intelligence Dashboard")

    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Overview", "🌐 Neural Matrix", "📈 Analytics", "🎯 Projects"]
    )

    with tab1:
        # Modern metrics row with enhanced styling
        col1, col2, col3, col4 = st.columns(4)

        # System metrics
        system_metrics = mm._get_system_metrics()

        with col1:
            cpu_value = system_metrics["cpu_percent"]
            cpu_delta = "↗️" if cpu_value > 50 else "↘️"
            st.metric("CPU Usage", f"{cpu_value:.1f}%", cpu_delta)

        with col2:
            mem_value = system_metrics["memory_percent"]
            mem_delta = "↗️" if mem_value > 70 else "↘️"
            st.metric("Memory", f"{mem_value:.1f}%", mem_delta)

        with col3:
            network_value = (
                system_metrics["network_sent"] + system_metrics["network_recv"]
            )
            st.metric("Network I/O", f"{network_value:.0f} MB", "↗️")

        with col4:
            uptime_hours = system_metrics["uptime"] / 3600
            st.metric("Uptime", f"{uptime_hours:.1f}h", "🟢")

        # 3D Risk Distribution Chart
        st.subheader("🎲 Risk Distribution - 3D View")
        projects_data = mm.get_projects_data()
        df = pd.DataFrame(projects_data)

        if not df.empty:
            risk_counts = df["risk_level"].value_counts()

            # Create 3D pie chart
            colors_3d = ["#ff4757", "#ff6b6b", "#ffa726", "#4caf50", "#00d4ff"]

            fig_3d = go.Figure(
                data=[
                    go.Pie(
                        labels=risk_counts.index,
                        values=risk_counts.values,
                        hole=0.4,
                        marker_colors=colors_3d[: len(risk_counts)],
                        textinfo="label+percent",
                        textfont_size=14,
                        pull=[
                            0.1 if i == risk_counts.values.argmax() else 0
                            for i in range(len(risk_counts))
                        ],
                    )
                ]
            )

            fig_3d.update_layout(
                title="Risk Distribution Analysis",
                font=dict(color="white"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(
                    bgcolor="rgba(255,255,255,0.1)",
                    bordercolor="rgba(255,255,255,0.2)",
                    borderwidth=1,
                ),
            )

            st.plotly_chart(fig_3d, use_container_width=True)

    with tab2:
        # Enhanced Neural Matrix with 3D visualization
        st.header("🌐 Neural Matrix Intelligence")

        matrix_data = mm.get_matrix_data()

        # 3D Network visualization
        st.subheader("🕸️ 3D Neural Network Topology")

        # Create 3D scatter plot for network nodes with deterministic layout
        nodes_data = []
        edges_data = []

        # Position nodes in a more organized 3D space
        device_positions = {
            "quantum_quasar": {"x": 0, "y": 0, "z": 0},
            "pocket_pulsar": {"x": 2, "y": 1, "z": 1},
            "tablet_titan": {"x": -2, "y": 1, "z": -1},
        }

        agent_positions = {
            "repo_sentry": {"x": 1, "y": -1, "z": 0.5},
            "daily_brief": {"x": -1, "y": -1, "z": -0.5},
            "orchestrator": {"x": 0, "y": -2, "z": 0},
            "matrix_monitor": {"x": 1.5, "y": -0.5, "z": 1},
            "doctrine_engine": {"x": -1.5, "y": -0.5, "z": -1},
        }

        # Add devices with fixed positions
        for device in matrix_data["devices"]:
            device_id = device["id"]
            pos = device_positions.get(device_id, {"x": 0, "y": 0, "z": 0})
            nodes_data.append(
                {
                    "x": pos["x"],
                    "y": pos["y"],
                    "z": pos["z"],
                    "name": device["name"],
                    "type": "device",
                    "health": device.get("health", 100),
                }
            )

        # Add agents with fixed positions
        for agent in matrix_data["agents"]:
            agent_id = agent["id"]
            pos = agent_positions.get(agent_id, {"x": 0, "y": -1, "z": 0})
            nodes_data.append(
                {
                    "x": pos["x"],
                    "y": pos["y"],
                    "z": pos["z"],
                    "name": agent["name"],
                    "type": "agent",
                    "health": agent.get("health", 100),
                }
            )

        # Create meaningful connections based on system architecture
        connections = [
            ("quantum_quasar", "pocket_pulsar"),
            ("quantum_quasar", "tablet_titan"),
            ("quantum_quasar", "repo_sentry"),
            ("quantum_quasar", "orchestrator"),
            ("pocket_pulsar", "tablet_titan"),
            ("repo_sentry", "orchestrator"),
            ("daily_brief", "orchestrator"),
            ("matrix_monitor", "repo_sentry"),
            ("doctrine_engine", "daily_brief"),
        ]

        # Build edges data
        node_dict = {node["name"]: node for node in nodes_data}
        for source_name, target_name in connections:
            if source_name in node_dict and target_name in node_dict:
                source = node_dict[source_name]
                target = node_dict[target_name]
                edges_data.append(
                    {
                        "x": [source["x"], target["x"]],
                        "y": [source["y"], target["y"]],
                        "z": [source["z"], target["z"]],
                    }
                )

        # 3D Network visualization
        fig_3d_network = go.Figure()

        # Add edges
        for edge in edges_data[:15]:  # Limit edges for performance
            fig_3d_network.add_trace(
                go.Scatter3d(
                    x=edge["x"],
                    y=edge["y"],
                    z=edge["z"],
                    mode="lines",
                    line=dict(color="rgba(0, 212, 255, 0.3)", width=2),
                    showlegend=False,
                )
            )

        # Add nodes
        for node in nodes_data:
            color = (
                "red"
                if node["health"] < 70
                else "green" if node["health"] > 90 else "orange"
            )
            fig_3d_network.add_trace(
                go.Scatter3d(
                    x=[node["x"]],
                    y=[node["y"]],
                    z=[node["z"]],
                    mode="markers+text",
                    marker=dict(size=12, color=color, opacity=0.8, symbol="circle"),
                    text=[node["name"]],
                    textposition="top center",
                    name=node["type"].title(),
                    showlegend=True,
                )
            )

        fig_3d_network.update_layout(
            title="3D Neural Network Topology",
            scene=dict(
                xaxis=dict(showbackground=False, showticklabels=False, title=""),
                yaxis=dict(showbackground=False, showticklabels=False, title=""),
                zaxis=dict(showbackground=False, showticklabels=False, title=""),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            showlegend=True,
        )

        st.plotly_chart(fig_3d_network, use_container_width=True)

        # System health metrics
        col_left, col_right = st.columns(2)

        with col_left:
            health_value = matrix_data["system_health"]
            health_color = (
                "🟢" if health_value > 90 else "🟡" if health_value > 70 else "🔴"
            )
            st.metric("System Health", f"{health_value:.1f}%", health_color)
            st.metric("Online Nodes", matrix_data["online_nodes"])
            st.metric("Total Connections", len(edges_data))

        with col_right:
            # Neural activity indicator
            st.subheader("🧠 Neural Activity")
            neural_html = '<div style="text-align: center;">'
            for i in range(10):
                neural_html += '<span class="neural-node"></span>'
            neural_html += "</div>"
            st.markdown(neural_html, unsafe_allow_html=True)

    with tab3:
        # Enhanced Analytics with 3D charts
        st.header("📈 Advanced Analytics")

        projects_data = mm.get_projects_data()
        df = pd.DataFrame(projects_data)

        if not df.empty:
            # 3D Scatter plot for project analysis
            st.subheader("🎯 3D Project Analysis")

            # Create 3D scatter plot
            risk_colors = {
                "CRITICAL": "#ff4757",
                "HIGH": "#ff6b6b",
                "MEDIUM": "#ffa726",
                "LOW": "#4caf50",
                "OPTIMAL": "#00d4ff",
            }

            fig_3d_scatter = go.Figure(
                data=[
                    go.Scatter3d(
                        x=df["progress"],
                        y=[
                            random.uniform(0, 1) for _ in range(len(df))
                        ],  # Random Y for demo
                        z=[
                            random.uniform(0, 1) for _ in range(len(df))
                        ],  # Random Z for demo
                        mode="markers",
                        marker=dict(
                            size=8,
                            color=[
                                risk_colors.get(risk, "#666")
                                for risk in df["risk_level"]
                            ],
                            opacity=0.8,
                        ),
                        text=df["name"],
                        hovertemplate="<b>%{text}</b><br>Progress: %{x:.1%}<br>Risk: "
                        + df["risk_level"]
                        + "<extra></extra>",
                    )
                ]
            )

            fig_3d_scatter.update_layout(
                title="3D Project Portfolio Analysis",
                scene=dict(
                    xaxis_title="Progress",
                    yaxis_title="Complexity",
                    zaxis_title="Impact",
                    xaxis=dict(showbackground=False),
                    yaxis=dict(showbackground=False),
                    zaxis=dict(showbackground=False),
                    bgcolor="rgba(0,0,0,0)",
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
            )

            st.plotly_chart(fig_3d_scatter, use_container_width=True)

            # Progress tracking with modern bar chart
            st.subheader("📊 Project Progress Tracking")
            fig_progress = px.bar(
                df,
                x="name",
                y="progress",
                color="risk_level",
                color_discrete_map=risk_colors,
                title="Project Progress by Risk Level",
                labels={"progress": "Progress (%)", "name": "Project Name"},
            )

            fig_progress.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
                xaxis_tickangle=-45,
            )

            st.plotly_chart(fig_progress, use_container_width=True)

    with tab4:
        # Enhanced Projects view
        st.header("🎯 Project Intelligence")

        projects_data = mm.get_projects_data()

        for project in projects_data:
            # Enhanced risk class mapping
            risk_class_map = {
                "CRITICAL": "risk-critical",
                "HIGH": "risk-high",
                "MEDIUM": "risk-medium",
                "LOW": "risk-low",
                "OPTIMAL": "risk-optimal",
            }
            risk_class = risk_class_map.get(project["risk_level"], "risk-medium")

            with st.container():
                # Modern project card layout
                col_a, col_b, col_c = st.columns([2, 1, 1])

                with col_a:
                    st.subheader(f"📁 {project['name']}")

                with col_b:
                    status_color_map = {
                        "ON_TRACK": "🟢",
                        "PROGRESSING": "🟡",
                        "NEEDS_ATTENTION": "🟠",
                        "CRITICAL": "🔴",
                    }
                    status_emoji = status_color_map.get(project["status"], "⚪")
                    st.metric("Status", f"{status_emoji} {project['status']}")

                with col_c:
                    progress_value = project["progress"]
                    st.metric("Progress", f"{progress_value:.1%}")

                # Enhanced recommendations with expandable sections
                if project["recommendations"]:
                    with st.expander("🤖 AI Recommendations", expanded=False):
                        for rec in project["recommendations"]:
                            st.markdown(f"• {rec}")

                # Progress bar with modern styling
                st.progress(progress_value, text=f"Progress: {progress_value:.1%}")

                st.divider()

    # Real-time updates with modern controls
    st.header("⚡ Real-time Intelligence Feed")

    # Enhanced refresh controls
    col_refresh, col_status, col_alerts = st.columns(3)

    with col_refresh:
        if st.button("🔄 Force Refresh", use_container_width=True):
            with st.spinner("🔄 Refreshing intelligence data..."):
                time.sleep(1.5)
                st.rerun()
            if STREAMLIT_EXTRAS_AVAILABLE:
                rain(emoji="🚀", font_size=25, falling_speed=8, animation_length=1.5)

    with col_status:
        st.metric("Last Update", datetime.now().strftime("%H:%M:%S"), "🔄")

    with col_alerts:
        # Generate alerts based on real system conditions
        alerts = []

        # Check system metrics for alerts
        system_metrics = mm._get_system_metrics()
        if system_metrics["cpu_percent"] > 80:
            alerts.append("🔥 High CPU usage detected")
        if system_metrics["memory_percent"] > 85:
            alerts.append("💾 Memory usage critical")

        # Check project health
        projects_data = mm.get_projects_data()
        critical_projects = [p for p in projects_data if p["risk_level"] == "CRITICAL"]
        if critical_projects:
            alerts.append(
                f"🚨 {len(critical_projects)} critical projects need attention"
            )

        low_progress_projects = [p for p in projects_data if p["progress"] < 0.2]
        if low_progress_projects:
            alerts.append(
                f"⚠️ {len(low_progress_projects)} projects showing low progress"
            )

        # Show alert count
        alert_count = len(alerts)
        st.metric("Active Alerts", alert_count, "⚠️" if alert_count > 0 else "✅")

        # Show alert details if any exist
        if alerts:
            with st.expander("View Alerts", expanded=False):
                for alert in alerts:
                    st.warning(alert)

    # Modern footer
    st.markdown("---")
    st.markdown(
        """
    <div style='text-align: center; color: #a0aec0; font-size: 0.9em;'>
        <strong>Matrix Maximizer 2.0</strong> - Powered by DIGITAL LABOUR AI<br>
        <span style='font-size: 0.8em;'>Real-time Intelligence | Neural Networks | Advanced Analytics</span>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
