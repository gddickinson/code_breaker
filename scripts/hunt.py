"""Run the leads hunt for a time budget: python scripts/hunt.py --minutes 5"""
import argparse
import json

from codebreaker.mysteries.catalog import seed
from codebreaker.mysteries.hunter import hunt

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--workers", type=int, default=9)
    ap.add_argument("--seed-only", action="store_true")
    a = ap.parse_args()
    print(seed(), flush=True)
    if not a.seed_only:
        print(json.dumps(hunt(a.minutes, a.workers), indent=1), flush=True)
