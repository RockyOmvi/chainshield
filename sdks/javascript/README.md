# ChainShield JavaScript/TypeScript SDK

Official JavaScript/TypeScript SDK for the ChainShield Risk Assessment API.

## Installation

```bash
npm install chainshield
# or
yarn add chainshield
# or
pnpm add chainshield
```

## Quick Start

```typescript
import { ChainShield } from 'chainshield';

const client = new ChainShield('cs_your_api_key');

// Analyze a wallet
const result = await client.analyze('0x742d35Cc6634C0532925a3b844Bc9e7595f2B5Fb');

console.log(`Risk Score: ${result.riskScore}`);
console.log(`Risk Level: ${result.riskLevel}`);
console.log(`Blocked: ${result.blocked}`);
```

## Features

### Quick Risk Checks

```typescript
// Check if sanctioned
if (await client.isSanctioned('0x123...')) {
  console.log('Address is sanctioned!');
}

// Check if high risk
if (await client.isHighRisk('0x456...', 70)) {
  console.log('High risk wallet!');
}
```

### Batch Analysis

```typescript
const addresses = ['0x111...', '0x222...', '0x333...'];
const results = await client.analyzeBatch(addresses);

for (const result of results) {
  console.log(`${result.address}: ${result.riskLevel}`);
}
```

### Multi-Chain Support

```typescript
// Analyze on different chains
const ethResult = await client.analyze('0x...', 'ethereum');
const btcResult = await client.analyze('bc1...', 'bitcoin');
const solResult = await client.analyze('7xKX...', 'solana');
```

### Webhooks

```typescript
// Register webhook
await client.registerWebhook({
  url: 'https://your-app.com/webhook',
  events: ['high_risk', 'blocked'],
  secret: 'your_secret',
});

// List webhooks
const webhooks = await client.listWebhooks();
```

## Error Handling

```typescript
import {
  ChainShield,
  ChainShieldError,
  AuthenticationError,
  RateLimitError,
} from 'chainshield';

try {
  const result = await client.analyze('0x...');
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.log('Invalid API key');
  } else if (error instanceof RateLimitError) {
    console.log(`Rate limited. Retry after ${error.retryAfter}s`);
  } else if (error instanceof ChainShieldError) {
    console.log(`Error: ${error.message}`);
  }
}
```

## TypeScript Types

Full TypeScript support with exported types:

```typescript
import type {
  RiskAssessment,
  RiskLevel,
  Chain,
  AlertType,
  UsageInfo,
  WebhookConfig,
} from 'chainshield';
```

## License

MIT
