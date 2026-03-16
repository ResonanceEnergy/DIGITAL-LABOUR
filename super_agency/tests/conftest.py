import os
import sys
from pathlib import Path

# ensure repository root is on sys.path for all tests
root = Path(__file__).parent.parent.resolve()

# remove any stray inner_council path which would introduce a conflicting
# top-level `agents` package (inner_council/agents) before the real one
sys.path = [p for p in sys.path if "inner_council" not in Path(p).parts]

# prepend project root so the real `agents` package is importable
sys.path.insert(0, str(root))
