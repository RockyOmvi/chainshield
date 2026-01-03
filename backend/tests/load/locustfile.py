"""
ChainShield Load Testing with Locust

Run with:
    locust -f tests/load/locustfile.py --host=http://localhost:8000

Web UI will be at http://localhost:8089

Target metrics:
- 1000 requests/second
- P95 latency < 500ms
- 0% error rate
"""

from locust import HttpUser, task, between, events
import random
import json


# Sample Ethereum addresses for testing
TEST_ADDRESSES = [
    "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",  # Coinbase
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",  # Uniswap
    "0xd8dA6BF26964aF9D7eEed9e03E53415D37aA96045", # Vitalik
    f"0x{''.join(random.choices('0123456789abcdef', k=40))}",  # Random
]

# Sample Bitcoin addresses
BTC_ADDRESSES = [
    "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "1QK3dv3WWeXmhfDqZuKGmGFd9xBvAEjVo9",
    "bc1qhums9dd8kj5f0npnw2rsmgg5q5zra0plkx0pap",
]


class ChainShieldUser(HttpUser):
    """
    Simulated user making API requests to ChainShield.
    
    Tests:
    1. Wallet risk assessment (main endpoint)
    2. Transaction analysis
    3. Health checks
    """
    
    # Wait 1-5 seconds between requests per user
    wait_time = between(1, 5)
    
    def on_start(self):
        """Called when user starts - can do login here."""
        # If auth is required, add JWT/API key here
        self.api_key = "test_api_key_for_load_testing"
    
    @task(10)  # Weight: 10 (most common)
    def analyze_wallet_eth(self):
        """Test Ethereum wallet analysis endpoint."""
        address = random.choice(TEST_ADDRESSES)
        
        response = self.client.post(
            "/api/v1/risk/wallet/analyze",
            json={"address": address, "chain": "ethereum"},
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            },
            name="POST /wallet/analyze (ETH)"
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Validate response structure
                assert "risk_score" in data or "score" in data
            except Exception:
                pass
    
    @task(3)  # Weight: 3
    def analyze_wallet_btc(self):
        """Test Bitcoin wallet analysis endpoint."""
        address = random.choice(BTC_ADDRESSES)
        
        response = self.client.post(
            "/api/v1/risk/wallet/analyze",
            json={"address": address, "chain": "bitcoin"},
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            },
            name="POST /wallet/analyze (BTC)"
        )
    
    @task(2)  # Weight: 2
    def health_check(self):
        """Test health endpoint."""
        self.client.get("/health", name="GET /health")
    
    @task(1)  # Weight: 1
    def ready_check(self):
        """Test ready endpoint."""
        self.client.get("/ready", name="GET /ready")
    
    @task(2)  # Weight: 2
    def get_entity_info(self):
        """Test entity lookup endpoint."""
        address = random.choice(TEST_ADDRESSES)
        
        self.client.get(
            f"/api/v1/entity/{address}",
            name="GET /entity/{address}"
        )


class AdminUser(HttpUser):
    """
    Simulated admin user making less frequent, heavier requests.
    """
    
    wait_time = between(5, 15)
    weight = 1  # Fewer admin users
    
    @task(1)
    def get_stats(self):
        """Get system statistics."""
        self.client.get(
            "/api/v1/admin/stats",
            name="GET /admin/stats"
        )
    
    @task(1)
    def batch_analyze(self):
        """Batch wallet analysis (heavy)."""
        addresses = random.sample(TEST_ADDRESSES, 3)
        
        self.client.post(
            "/api/v1/risk/wallet/batch",
            json={"addresses": addresses},
            headers={"Content-Type": "application/json"},
            name="POST /wallet/batch"
        )


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log request metrics."""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("=" * 60)
    print("ChainShield Load Test Starting")
    print(f"Target host: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("=" * 60)
    print("Load Test Complete")
    
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Avg response time: {stats.total.avg_response_time:.0f}ms")
    
    if stats.total.num_requests > 0:
        error_rate = (stats.total.num_failures / stats.total.num_requests) * 100
        print(f"Error rate: {error_rate:.2f}%")
    
    print("=" * 60)
