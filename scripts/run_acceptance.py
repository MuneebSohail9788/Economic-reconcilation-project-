"""Run the locked golden/adversarial acceptance suite."""

import subprocess
import sys

raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", "tests/test_acceptance.py"]))
