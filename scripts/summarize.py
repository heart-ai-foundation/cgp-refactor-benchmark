#!/usr/bin/env python3
"""Summarize scored benchmark runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cgp_refactor_benchmark.analysis.summarize import load_scores, summarize, write_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=Path("results/scores.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("results/summary.csv"))
    args = parser.parse_args()

    rows = summarize(load_scores(args.scores))
    write_csv(args.out, rows)
    print(f"wrote {args.out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
