#!/usr/bin/env python3
"""Demonstrate selective prioritization with fictional data in a disposable directory."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/li-read/scripts'))
from read_layer import ingest
from intelligence import brief


def main():
    now = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
    payload = json.loads((ROOT / 'skills/li-read/assets/sample-read.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='linkedin-safe-demo-') as directory:
        ingest(directory, payload, now=now)
        result = brief(directory, now)
        print(json.dumps({'fictional_demo': True, **result}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
