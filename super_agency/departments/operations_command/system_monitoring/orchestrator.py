#!/usr/bin/env python3
import subprocess, sys
from .common import ROOT, Log

SENTRY = ROOT/"agents"/"repo_sentry.py"
DAILY = ROOT/"agents"/"daily_brief.py"

def main():
    Log.info("Running Repo Sentry across portfolio…")
    cp = subprocess.run([sys.executable, str(SENTRY)])
    if cp.returncode != 0:
        Log.warn("Repo Sentry exited with non-zero code")
    Log.info("Compiling Daily Ops Brief…")
    cp = subprocess.run([sys.executable, str(DAILY)])
    if cp.returncode != 0:
        Log.warn("Daily Brief exited with non-zero code")
    Log.info("Done.")

if __name__ == '__main__':
    main()