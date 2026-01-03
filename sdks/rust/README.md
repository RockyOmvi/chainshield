# ChainShield Rust SDK

Official Rust SDK for the ChainShield Risk Assessment API.

## Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
chainshield = "1.0"
tokio = { version = "1.0", features = ["full"] }
```

## Quick Start

```rust
use chainshield::ChainShield;

#[tokio::main]
async fn main() -> Result<(), chainshield::Error> {
    let client = ChainShield::new("cs_your_api_key");
    
    let result = client.analyze("0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb").await?;

    println!("Risk Score: {}", result.risk_score);
    println!("Risk Level: {:?}", result.risk_level);
    println!("Blocked: {}", result.blocked);
    
    Ok(())
}
```

## Features

### Quick Risk Checks

```rust
// Check if sanctioned
if client.is_sanctioned("0x123...").await? {
    println!("Address is sanctioned!");
}

// Check if high risk
if client.is_high_risk("0x456...", 70.0).await? {
    println!("High risk wallet!");
}
```

### Multi-Chain Support

```rust
use chainshield::Chain;

let eth_result = client.analyze_with_chain("0x...", Chain::Ethereum).await?;
let btc_result = client.analyze_with_chain("bc1...", Chain::Bitcoin).await?;
let sol_result = client.analyze_with_chain("7xKX...", Chain::Solana).await?;
```

### Result Methods

```rust
let result = client.analyze("0x...").await?;

if result.is_high_risk() {
    // Handle high risk
}

if result.is_sanctioned() {
    // Block transaction
}

if result.is_safe() {
    // Proceed
}
```

## Error Handling

```rust
use chainshield::Error;

match client.analyze("0x...").await {
    Ok(result) => println!("Score: {}", result.risk_score),
    Err(Error::Authentication(msg)) => eprintln!("Auth failed: {}", msg),
    Err(Error::RateLimit { retry_after }) => {
        eprintln!("Rate limited, retry after {:?}s", retry_after);
    }
    Err(e) => eprintln!("Error: {}", e),
}
```

## License

MIT
