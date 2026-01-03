# ChainShield Go SDK

Official Go SDK for the ChainShield Risk Assessment API.

## Installation

```bash
go get github.com/chainshield/chainshield-go
```

## Quick Start

```go
package main

import (
    "context"
    "fmt"
    "log"

    "github.com/chainshield/chainshield-go"
)

func main() {
    client := chainshield.New("cs_your_api_key")
    
    ctx := context.Background()
    result, err := client.Analyze(ctx, "0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb")
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Risk Score: %.1f\n", result.RiskScore)
    fmt.Printf("Risk Level: %s\n", result.RiskLevel)
    fmt.Printf("Blocked: %v\n", result.Blocked)
}
```

## Features

### Quick Risk Checks

```go
// Check if sanctioned
sanctioned, _ := client.IsSanctioned(ctx, "0x123...")
if sanctioned {
    fmt.Println("Address is sanctioned!")
}

// Check if high risk
highRisk, _ := client.IsHighRisk(ctx, "0x456...", 70.0)
if highRisk {
    fmt.Println("High risk wallet!")
}
```

### Multi-Chain Support

```go
// Analyze on different chains
ethResult, _ := client.AnalyzeWithChain(ctx, "0x...", chainshield.ChainEthereum)
btcResult, _ := client.AnalyzeWithChain(ctx, "bc1...", chainshield.ChainBitcoin)
solResult, _ := client.AnalyzeWithChain(ctx, "7xKX...", chainshield.ChainSolana)
```

### Custom Configuration

```go
import "time"

client := chainshield.New("cs_xxx",
    chainshield.WithTimeout(60 * time.Second),
    chainshield.WithBaseURL("https://custom.api.com"),
)
```

## Error Handling

```go
result, err := client.Analyze(ctx, "0x...")
if err != nil {
    if apiErr, ok := err.(*chainshield.Error); ok {
        fmt.Printf("API Error: %s (status %d)\n", apiErr.Message, apiErr.StatusCode)
    } else {
        fmt.Printf("Error: %v\n", err)
    }
}
```

## License

MIT
