/**
 * ChainShield JavaScript/TypeScript SDK
 *
 * Official SDK for the ChainShield Risk Assessment API.
 *
 * @example
 * ```typescript
 * import { ChainShield } from 'chainshield';
 *
 * const client = new ChainShield('cs_your_api_key');
 * const result = await client.analyze('0x742d35Cc...');
 *
 * if (result.isHighRisk) {
 *   console.log('High risk wallet!');
 * }
 * ```
 */

// Types
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type Chain =
    | 'ethereum'
    | 'polygon'
    | 'arbitrum'
    | 'bsc'
    | 'optimism'
    | 'base'
    | 'avalanche'
    | 'fantom'
    | 'zksync'
    | 'bitcoin'
    | 'solana';

export type AlertType =
    | 'high_risk'
    | 'critical_risk'
    | 'blocked'
    | 'mixer_detected'
    | 'sanctions_hit';

export interface RiskAssessment {
    address: string;
    chain: Chain;
    riskScore: number;
    riskLevel: RiskLevel;
    blocked: boolean;
    factors: string[];
    entity?: {
        name: string;
        category: string;
    };
    timestamp?: string;
}

export interface UsageInfo {
    tier: string;
    requestsToday: number;
    requestsMonth: number;
    limitDay: number;
    limitMonth: number;
}

export interface WebhookConfig {
    id?: string;
    url: string;
    events: AlertType[];
    secret?: string;
    enabled?: boolean;
}

export interface ChainShieldOptions {
    baseUrl?: string;
    timeout?: number;
}

// Errors
export class ChainShieldError extends Error {
    constructor(
        message: string,
        public statusCode?: number,
        public details?: Record<string, unknown>
    ) {
        super(message);
        this.name = 'ChainShieldError';
    }
}

export class AuthenticationError extends ChainShieldError {
    constructor(message: string = 'Invalid API key') {
        super(message, 401);
        this.name = 'AuthenticationError';
    }
}

export class RateLimitError extends ChainShieldError {
    constructor(message: string = 'Rate limit exceeded', public retryAfter?: number) {
        super(message, 429);
        this.name = 'RateLimitError';
    }
}

export class ValidationError extends ChainShieldError {
    constructor(message: string) {
        super(message, 400);
        this.name = 'ValidationError';
    }
}

// Main Client
export class ChainShield {
    private apiKey: string;
    private baseUrl: string;
    private timeout: number;

    /**
     * Create a new ChainShield client.
     *
     * @param apiKey - Your ChainShield API key (starts with "cs_")
     * @param options - Optional configuration
     */
    constructor(apiKey: string, options: ChainShieldOptions = {}) {
        if (!apiKey) {
            throw new AuthenticationError('API key is required');
        }

        if (!apiKey.startsWith('cs_')) {
            throw new AuthenticationError('Invalid API key format. Keys start with "cs_"');
        }

        this.apiKey = apiKey;
        this.baseUrl = (options.baseUrl || 'https://api.chainshield.io').replace(/\/$/, '');
        this.timeout = options.timeout || 30000;
    }

    private async request<T>(
        method: 'GET' | 'POST' | 'DELETE',
        endpoint: string,
        body?: Record<string, unknown>
    ): Promise<T> {
        const url = `${this.baseUrl}/api/v1${endpoint}`;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(url, {
                method,
                headers: {
                    'X-API-Key': this.apiKey,
                    'Content-Type': 'application/json',
                    'User-Agent': 'ChainShield-JS-SDK/1.0.0',
                },
                body: body ? JSON.stringify(body) : undefined,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                await this.handleError(response);
            }

            return response.json();
        } catch (error) {
            clearTimeout(timeoutId);

            if (error instanceof ChainShieldError) {
                throw error;
            }

            throw new ChainShieldError(
                error instanceof Error ? error.message : 'Request failed'
            );
        }
    }

    private async handleError(response: Response): Promise<never> {
        let message: string;

        try {
            const data = await response.json();
            message = data.detail || JSON.stringify(data);
        } catch {
            message = response.statusText || `HTTP ${response.status}`;
        }

        switch (response.status) {
            case 401:
                throw new AuthenticationError(message);
            case 429:
                const retryAfter = response.headers.get('Retry-After');
                throw new RateLimitError(message, retryAfter ? parseInt(retryAfter) : undefined);
            case 400:
                throw new ValidationError(message);
            default:
                throw new ChainShieldError(message, response.status);
        }
    }

    /**
     * Analyze a wallet address for risk.
     *
     * @param address - Wallet address to analyze
     * @param chain - Blockchain network (default: ethereum)
     * @returns Risk assessment result
     *
     * @example
     * ```typescript
     * const result = await client.analyze('0x742d35Cc...');
     * console.log(result.riskScore, result.riskLevel);
     * ```
     */
    async analyze(address: string, chain: Chain = 'ethereum'): Promise<RiskAssessment> {
        const data = await this.request<any>('POST', '/wallet/analyze', {
            address,
            chain,
        });

        return {
            address: data.address,
            chain: data.chain,
            riskScore: data.risk_score,
            riskLevel: data.risk_level,
            blocked: data.blocked,
            factors: data.factors || data.risk_factors || [],
            entity: data.entity,
            timestamp: data.timestamp,
        };
    }

    /**
     * Analyze multiple wallet addresses.
     *
     * @param addresses - List of wallet addresses
     * @param chain - Blockchain network
     * @returns List of risk assessment results
     */
    async analyzeBatch(addresses: string[], chain: Chain = 'ethereum'): Promise<RiskAssessment[]> {
        const data = await this.request<{ results: any[] }>('POST', '/wallet/analyze/batch', {
            addresses,
            chain,
        });

        return data.results.map((r) => ({
            address: r.address,
            chain: r.chain,
            riskScore: r.risk_score,
            riskLevel: r.risk_level,
            blocked: r.blocked,
            factors: r.factors || r.risk_factors || [],
            entity: r.entity,
            timestamp: r.timestamp,
        }));
    }

    /**
     * Quick check if address is sanctioned/blocked.
     *
     * @param address - Wallet address to check
     * @returns True if address is sanctioned
     */
    async isSanctioned(address: string): Promise<boolean> {
        try {
            const result = await this.analyze(address);
            return result.blocked;
        } catch {
            return false;
        }
    }

    /**
     * Quick check if address is high risk.
     *
     * @param address - Wallet address to check
     * @param threshold - Risk score threshold (default: 70)
     * @returns True if risk score exceeds threshold
     */
    async isHighRisk(address: string, threshold: number = 70): Promise<boolean> {
        const result = await this.analyze(address);
        return result.riskScore >= threshold;
    }

    /**
     * Get current API usage statistics.
     */
    async getUsage(): Promise<UsageInfo> {
        const data = await this.request<any>('GET', '/account/usage');
        return {
            tier: data.tier,
            requestsToday: data.requests_today,
            requestsMonth: data.requests_this_month,
            limitDay: data.limits.per_day,
            limitMonth: data.limits.per_month,
        };
    }

    /**
     * Register a webhook for real-time alerts.
     */
    async registerWebhook(config: WebhookConfig): Promise<{ id: string }> {
        return this.request('POST', '/webhooks', {
            url: config.url,
            events: config.events,
            secret: config.secret,
        });
    }

    /**
     * List all registered webhooks.
     */
    async listWebhooks(): Promise<WebhookConfig[]> {
        return this.request('GET', '/webhooks');
    }

    /**
     * Delete a webhook by ID.
     */
    async deleteWebhook(webhookId: string): Promise<boolean> {
        try {
            await this.request('DELETE', `/webhooks/${webhookId}`);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Check API health status.
     */
    async health(): Promise<{ status: string }> {
        return this.request('GET', '/health');
    }

    /**
     * Quick connectivity check.
     */
    async ping(): Promise<boolean> {
        try {
            await this.health();
            return true;
        } catch {
            return false;
        }
    }
}

// Default export
export default ChainShield;
