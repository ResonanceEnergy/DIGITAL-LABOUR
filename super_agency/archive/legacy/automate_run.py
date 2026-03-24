#!/usr/bin/env python3
"""
Automation helper for launching the DIGITAL LABOUR from Python.
Performs dependency installation, optional AAC UI sanity check, sample
training of the decision optimizer, registration of test intelligence nodes
and then starts the full runtime.
"""

import subprocess
import sys
import os
import time
from decision_optimizer import DecisionOptimizer
from global_intelligence_network import global_network


def install_dependencies():
    """install_dependencies handler."""
    print("[install] Installing Python dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"] )



def check_aac_ui():
    """check_aac_ui handler."""
    path = os.path.join("apps","monitor","matrix_monitor","monitoring","aac_matrix_monitor_enhanced.py")
    if os.path.isfile(path):
        print(f"[aac] AAC UI module found at {path}")
    else:
        """train_optimizer handler."""
        print(f"[aac] No AAC UI module present, fallback monitor will be used")


def train_optimizer(dataset=None,label_key='label'):
    print("[opt] Training decision optimizer...")
    opt = DecisionOptimizer()
    if dataset is None:
        # create a trivial dummy dataset so that the model is "trained"
        dataset = [
            {'repo_size':120,'open_prs':5,'critical_bugs':2,'label':1},
            {'repo_size':40,'open_prs':0,'critical_bugs':0,'label':0},
        ]
    opt.train(dataset,label_key=label_key)
    return opt


def register_sample_nodes():
    print("[gin] Registering example intelligence nodes...")
    try:
        global_network.register_node(name="europe_news", endpoint="https://news.example.com/api", api_key=os.getenv("GIN_API_KEY", ""))
        print("[gin] node europe_news registered")
    except Exception as e:
        print(f"[gin] error registering node: {e}")


def launch():
    """main handler."""
    print("[launch] Starting DIGITAL LABOUR runtime")
    # call main from run_bit_rage_labour to keep in-process
    try:
        import run_bit_rage_labour
        run_bit_rage_labour.main()
    except Exception as e:
        print(f"[launch] runtime error: {e}")


def main():
    install_dependencies()
    check_aac_ui()
    # optional training, users can supply real data
    train_optimizer()
    register_sample_nodes()
    launch()


if __name__ == '__main__':
    main()
