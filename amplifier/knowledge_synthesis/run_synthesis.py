#!/usr/bin/env python3
"""
Run knowledge synthesis - simple runner for Makefile.
"""

import sys

from .synthesis_engine import SynthesisEngine


def main():
    """Run synthesis and print summary."""
    # Initialize synthesis engine
    engine = SynthesisEngine()

    # Run synthesis
    results = engine.run_synthesis()

    # Print summary
    engine.print_summary(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
