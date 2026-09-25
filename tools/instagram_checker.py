#!/usr/bin/env python3
"""
Instagram username checker scaffold.

This project deliberately does NOT automate requests to Instagram.
Use the Checker interface with an authorized API/data source that you
are permitted to query.

The runner, concurrency, live output, resume, and CSV export are reusable.
"""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Result:
    username: str
    status: str  # TAKEN, AVAILABLE, UNKNOWN


class Checker(Protocol):
    def check(self, username: str) -> Result:
        ...


class LocalDemoChecker:
    """Safe local checker for testing the workflow without contacting Instagram.

    Put usernames known to be unavailable in a newline-delimited file.
    Everything else is returned as UNKNOWN, never falsely labeled AVAILABLE.
    """

    def __init__(self, taken_file: Path):
        self.taken = {
            line.strip().lower()
            for line in taken_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def check(self, username: str) -> Result:
        username = username.strip().lower()
        if username in self.taken:
            return Result(username, "TAKEN")
        return Result(username, "UNKNOWN")


def run(input_file: Path, output_csv: Path, workers: int, checker: Checker) -> None:
    usernames = [
        line.strip().lower()
        for line in input_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "status"])

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(checker.check, u): u for u in usernames}

            for future in as_completed(futures):
                username = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = Result(username, "UNKNOWN")
                    print(f"[UNKNOWN] {username} ({exc})")
                else:
                    print(f"[{result.status}] {result.username}")

                writer.writerow([result.username, result.status])
                f.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="all_3_letter_usernames.txt")
    parser.add_argument("--output", default="available_usernames.csv")
    parser.add_argument("--taken-file", default="known_taken.txt")
    parser.add_argument("--workers", type=int, default=25)
    args = parser.parse_args()

    checker = LocalDemoChecker(Path(args.taken_file))
    run(Path(args.input), Path(args.output), args.workers, checker)


if __name__ == "__main__":
    main()
