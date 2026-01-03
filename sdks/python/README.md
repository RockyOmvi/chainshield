# ChainShield Python SDK

Official Python SDK for the ChainShield Risk Assessment API.

## Installation

```bash
pip install chainshield
```

## Quick Start

```python
from chainshield import ChainShield

# Initialize client
client = ChainShield(api_key="cs_your_api_key")

# Analyze a wallet
result = client.analyze("0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb")

print(f"Risk Score: {result.risk_score}")
print(f"Risk Level: {result.risk_level}")
print(f"Blocked: {result.blocked}")
print(f"Factors: {result.factors}")
```

## Features

### Quick Risk Checks

```python
# Check if sanctioned
if client.is_sanctioned("0x123..."):
    print("Address is sanctioned!")

# Check if high risk
if client.is_high_risk("0x456...", threshold=70):
    print("High risk wallet!")
```

### Batch Analysis

```python
addresses = [
    "0x111...",
    "0x222...",
    "0x333..."
]

results = client.analyze_batch(addresses)
for r in results:
    print(f"{r.address}: {r.risk_level}")
```

### Multi-Chain Support

```python
from chainshield import Chain

# Analyze on different chains
eth_result = client.analyze("0x...", chain=Chain.ETHEREUM)
btc_result = client.analyze("bc1...", chain=Chain.BITCOIN)
sol_result = client.analyze("7xKX...", chain=Chain.SOLANA)
```

### Webhook Alerts

```python
# Register webhook for alerts
client.register_webhook(
    url="https://your-app.com/webhook",
    events=["HIGH_RISK", "BLOCKED"],
    secret="your_webhook_secret"
)
```

### Async Support

```python
from chainshield import AsyncChainShield

async def main():
    async with AsyncChainShield(api_key="cs_xxx") as client:
        result = await client.analyze("0x742d35Cc...")
        print(result.risk_score)
```

## Error Handling

```python
from chainshield import (
    ChainShieldError,
    AuthenticationError,
    RateLimitError
)

try:
    result = client.analyze("0x...")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except ChainShieldError as e:
    print(f"Error: {e.message}")
```

## License

MIT
