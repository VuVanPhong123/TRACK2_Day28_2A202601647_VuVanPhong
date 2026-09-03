"""Cross-platform HTTP load probe using only the Python standard library."""

from __future__ import annotations

import argparse
import http.client
import json
import math
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1)]


def request(url: str) -> tuple[float, int]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/ready", timeout=10) as response:
            status = response.status
    except HTTPError as error:
        # HTTP rejections are application responses, not transport failures.
        status = error.code
    except (URLError, TimeoutError, OSError, http.client.HTTPException):
        # Status 0 is reserved for a request that never received an HTTP
        # response (DNS/connect/timeout/protocol transport failure).
        status = 0
    return (time.perf_counter() - started) * 1000, status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda _: request(args.url), range(args.requests)))
    elapsed_ms = (time.perf_counter() - started) * 1000
    durations = [duration for duration, _ in results]
    statuses: dict[str, int] = {}
    for _, status in results:
        statuses[str(status)] = statuses.get(str(status), 0) + 1
    success = sum(200 <= status < 300 for _, status in results)
    rejected = sum(400 <= status < 500 for _, status in results)
    errors = len(results) - success - rejected
    print(
        json.dumps(
            {
                "requests": args.requests,
                "workers": args.workers,
                "status_counts": statuses,
                "success": success,
                "rejected": rejected,
                "errors": errors,
                "elapsed_ms": elapsed_ms,
                "throughput_requests_per_second": (
                    args.requests / (elapsed_ms / 1000) if elapsed_ms else 0.0
                ),
                "latency_ms": {
                    "p50": percentile(durations, 0.50),
                    "p95": percentile(durations, 0.95),
                    "p99": percentile(durations, 0.99),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
