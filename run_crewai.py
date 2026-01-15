#!/usr/bin/env python
"""
Convenience runner script for Tour Charge Automation with CrewAI.
This script runs the multi-agent automation from the project root.

Usage:
    python run_crewai.py --start 303 --limit 1
    python run_crewai.py --csv ยอดเบิกอุปกรณ์.csv --start 0 --limit 5
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tour_charge_automation.main import main

if __name__ == "__main__":
    main()
