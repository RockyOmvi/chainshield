/**
 * Test JavaScript/TypeScript SDK
 */

// Since we're testing the raw TS file, we'll use a simple Node.js test
// In production, this would be compiled first

const fs = require('fs');
const path = require('path');

console.log('==================================================');
console.log('  JAVASCRIPT SDK TEST');
console.log('==================================================');

let passed = 0;
let failed = 0;

function test(name, fn) {
    try {
        fn();
        console.log(`  [PASS] ${name}`);
        passed++;
    } catch (e) {
        console.log(`  [FAIL] ${name}: ${e.message}`);
        failed++;
    }
}

// Read and parse the TypeScript file to verify structure
const sdkPath = path.join(__dirname, 'src', 'index.ts');
const sdkContent = fs.readFileSync(sdkPath, 'utf-8');

console.log('\nTesting TypeScript SDK structure...\n');

// Test exports exist
test('RiskLevel type exported', () => {
    if (!sdkContent.includes("export type RiskLevel")) throw new Error('Missing');
});

test('Chain type exported', () => {
    if (!sdkContent.includes("export type Chain")) throw new Error('Missing');
});

test('AlertType type exported', () => {
    if (!sdkContent.includes("export type AlertType")) throw new Error('Missing');
});

test('RiskAssessment interface exported', () => {
    if (!sdkContent.includes("export interface RiskAssessment")) throw new Error('Missing');
});

test('ChainShield class exported', () => {
    if (!sdkContent.includes("export class ChainShield")) throw new Error('Missing');
});

test('ChainShieldError class exported', () => {
    if (!sdkContent.includes("export class ChainShieldError")) throw new Error('Missing');
});

test('AuthenticationError class exported', () => {
    if (!sdkContent.includes("export class AuthenticationError")) throw new Error('Missing');
});

test('RateLimitError class exported', () => {
    if (!sdkContent.includes("export class RateLimitError")) throw new Error('Missing');
});

// Test methods exist
console.log('\nTesting SDK methods...\n');

test('analyze method exists', () => {
    if (!sdkContent.includes("async analyze(")) throw new Error('Missing');
});

test('analyzeBatch method exists', () => {
    if (!sdkContent.includes("async analyzeBatch(")) throw new Error('Missing');
});

test('isSanctioned method exists', () => {
    if (!sdkContent.includes("async isSanctioned(")) throw new Error('Missing');
});

test('isHighRisk method exists', () => {
    if (!sdkContent.includes("async isHighRisk(")) throw new Error('Missing');
});

test('registerWebhook method exists', () => {
    if (!sdkContent.includes("async registerWebhook(")) throw new Error('Missing');
});

test('health method exists', () => {
    if (!sdkContent.includes("async health(")) throw new Error('Missing');
});

// Test chains
console.log('\nTesting chain support...\n');

const chains = ['ethereum', 'polygon', 'arbitrum', 'bsc', 'optimism', 'base', 'avalanche', 'fantom', 'zksync', 'bitcoin', 'solana'];
chains.forEach(chain => {
    test(`Chain ${chain} supported`, () => {
        if (!sdkContent.includes(`'${chain}'`)) throw new Error('Missing');
    });
});

// Summary
console.log('\n==================================================');
console.log(`  RESULT: ${passed}/${passed + failed} tests passed`);
console.log('==================================================');

process.exit(failed > 0 ? 1 : 0);
