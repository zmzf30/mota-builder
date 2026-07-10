#!/usr/bin/env python3
"""Export the selected local mota examples into the repository corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mota_few_shot import (
    DEFAULT_BUNDLED_CORPUS,
    DEFAULT_REFERENCE_ROOT,
    build_bundled_reference_corpus,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the bundled mota few-shot corpus.")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_REFERENCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_BUNDLED_CORPUS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    corpus = build_bundled_reference_corpus(args.source_root)
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {corpus['project_count']} projects and {corpus['floor_count']} floors "
        f"to {output} ({corpus['fingerprint']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
