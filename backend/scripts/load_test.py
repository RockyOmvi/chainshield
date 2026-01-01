"""
ChainShield Load Testing Script

Performance testing for the risk assessment API.
Uses asyncio for concurrent requests.

Usage:
    python scripts/load_test.py --concurrency 50 --requests 1000
"""

import argparse
import asyncio
import random
import statistics
import time
from dataclasses import dataclass
from typing import List
import sys


@dataclass
class RequestResult:
    """Result of a single request."""
    success: bool
    latency_ms: float
    status_code: int = 200
    error: str = None


@dataclass
class LoadTestResult:
    """Overall load test results."""
    total_requests: int
    successful: int
    failed: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    requests_per_second: float
    duration_seconds: float


def generate_test_wallet() -> dict:
    """Generate a random test wallet."""
    return {
        "address": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
        "balance": random.uniform(0, 100),
        "first_seen": "2024-01-01T00:00:00Z",
        "transactions": [
            {
                "from": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                "to": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                "value": random.uniform(0.1, 10),
                "timestamp": "2024-06-15T10:00:00Z",
                "gas_price": random.randint(10000000000, 100000000000),
            }
            for _ in range(random.randint(1, 10))
        ],
    }


async def make_request(session, url: str, wallet: dict) -> RequestResult:
    """Make a single request to the API."""
    start = time.perf_counter()
    
    try:
        async with session.post(
            url,
            json=wallet,
            headers={"X-API-Key": "test_key_123"}
        ) as response:
            latency = (time.perf_counter() - start) * 1000
            
            return RequestResult(
                success=response.status == 200 or response.status == 401,
                latency_ms=latency,
                status_code=response.status,
            )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return RequestResult(
            success=False,
            latency_ms=latency,
            error=str(e),
        )


async def run_load_test(
    url: str,
    concurrency: int,
    total_requests: int
) -> LoadTestResult:
    """
    Run the load test.
    
    Args:
        url: API endpoint URL
        concurrency: Number of concurrent requests
        total_requests: Total requests to make
    """
    try:
        import aiohttp
    except ImportError:
        print("ERROR: aiohttp required. Install with: pip install aiohttp")
        sys.exit(1)
    
    results: List[RequestResult] = []
    wallets = [generate_test_wallet() for _ in range(total_requests)]
    
    start_time = time.perf_counter()
    
    async with aiohttp.ClientSession() as session:
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_request(wallet):
            async with semaphore:
                return await make_request(session, url, wallet)
        
        # Run all requests
        tasks = [bounded_request(w) for w in wallets]
        results = await asyncio.gather(*tasks)
    
    duration = time.perf_counter() - start_time
    
    # Calculate statistics
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    latencies = [r.latency_ms for r in results]
    latencies.sort()
    
    def percentile(data, p):
        if not data:
            return 0
        idx = int(len(data) * p / 100)
        return data[min(idx, len(data) - 1)]
    
    return LoadTestResult(
        total_requests=len(results),
        successful=len(successful),
        failed=len(failed),
        avg_latency_ms=statistics.mean(latencies) if latencies else 0,
        p50_latency_ms=percentile(latencies, 50),
        p95_latency_ms=percentile(latencies, 95),
        p99_latency_ms=percentile(latencies, 99),
        max_latency_ms=max(latencies) if latencies else 0,
        requests_per_second=len(results) / duration,
        duration_seconds=duration,
    )


def print_results(result: LoadTestResult) -> None:
    """Print load test results."""
    print("\n" + "="*60)
    print("LOAD TEST RESULTS")
    print("="*60)
    
    print(f"\n📊 Summary:")
    print(f"   Total Requests:    {result.total_requests}")
    print(f"   Successful:        {result.successful} ({result.successful/result.total_requests*100:.1f}%)")
    print(f"   Failed:            {result.failed}")
    print(f"   Duration:          {result.duration_seconds:.2f}s")
    print(f"   Throughput:        {result.requests_per_second:.1f} req/s")
    
    print(f"\n⏱️ Latency:")
    print(f"   Average:           {result.avg_latency_ms:.2f} ms")
    print(f"   P50:               {result.p50_latency_ms:.2f} ms")
    print(f"   P95:               {result.p95_latency_ms:.2f} ms")
    print(f"   P99:               {result.p99_latency_ms:.2f} ms")
    print(f"   Max:               {result.max_latency_ms:.2f} ms")
    
    # Verdict
    print("\n" + "="*60)
    if result.failed / max(result.total_requests, 1) > 0.05:
        print("❌ FAILED: >5% error rate")
    elif result.p95_latency_ms > 1000:
        print("⚠️ WARNING: P95 latency >1s")
    elif result.requests_per_second < 10:
        print("⚠️ WARNING: Low throughput (<10 req/s)")
    else:
        print("✅ PASSED: All metrics within acceptable range")
    print("="*60)


async def main():
    parser = argparse.ArgumentParser(description="ChainShield Load Test")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/api/v1/risk/assess/wallet",
        help="API endpoint URL"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=10,
        help="Number of concurrent requests"
    )
    parser.add_argument(
        "--requests", "-n",
        type=int,
        default=100,
        help="Total number of requests"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("CHAINSHIELD LOAD TEST")
    print("="*60)
    print(f"\nTarget:       {args.url}")
    print(f"Concurrency:  {args.concurrency}")
    print(f"Requests:     {args.requests}")
    print("\nRunning...")
    
    result = await run_load_test(
        url=args.url,
        concurrency=args.concurrency,
        total_requests=args.requests
    )
    
    print_results(result)


if __name__ == "__main__":
    asyncio.run(main())
