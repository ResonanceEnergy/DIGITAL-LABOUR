#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT/'agents'
steps = [
    ('autodiscover',
     [sys.executable, str(AGENTS / 'portfolio_autodiscover.py')]),
    ('autotier', [sys.executable, str(AGENTS / 'portfolio_autotier.py')]),
    ('selfheal', [sys.executable, str(AGENTS / 'portfolio_selfheal.py')])]
for name, cmd in steps:
    print(f'[RUN] {name} ...')
    cp = subprocess.run(cmd)
    if cp.returncode!=0:
        print(f'[WARN] {name} returned non-zero: {cp.returncode}')
print('[OK] Portfolio maintenance run complete.')
