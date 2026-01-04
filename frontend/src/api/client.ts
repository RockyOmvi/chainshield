/**
 * ChainShield API Client
 * 
 * Handles all API calls with automatic token refresh and error handling.
 */

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
}

class ApiClient {
    private static instance: ApiClient;
    private refreshPromise: Promise<boolean> | null = null;

    static getInstance(): ApiClient {
        if (!ApiClient.instance) {
            ApiClient.instance = new ApiClient();
        }
        return ApiClient.instance;
    }

    private getToken(): string | null {
        return localStorage.getItem('token');
    }

    private getRefreshToken(): string | null {
        return localStorage.getItem('refreshToken');
    }

    private setTokens(access: string, refresh?: string): void {
        localStorage.setItem('token', access);
        if (refresh) {
            localStorage.setItem('refreshToken', refresh);
        }
    }

    private clearTokens(): void {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
    }

    private async refreshAccessToken(): Promise<boolean> {
        // Prevent multiple simultaneous refresh attempts
        if (this.refreshPromise) {
            return this.refreshPromise;
        }

        this.refreshPromise = (async () => {
            const refreshToken = this.getRefreshToken();
            if (!refreshToken) {
                return false;
            }

            try {
                const res = await fetch(`${API_BASE}/auth/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken }),
                });

                if (res.ok) {
                    const data = await res.json();
                    this.setTokens(data.access_token, data.refresh_token);
                    return true;
                }
                return false;
            } catch {
                return false;
            } finally {
                this.refreshPromise = null;
            }
        })();

        return this.refreshPromise;
    }

    async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<ApiResponse<T>> {
        const token = this.getToken();

        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (token) {
            (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
        }

        try {
            let res = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers,
            });

            // If unauthorized, try to refresh token
            if (res.status === 401 && token) {
                const refreshed = await this.refreshAccessToken();
                if (refreshed) {
                    // Retry with new token
                    const newToken = this.getToken();
                    (headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`;
                    res = await fetch(`${API_BASE}${endpoint}`, {
                        ...options,
                        headers,
                    });
                } else {
                    // Refresh failed, clear tokens
                    this.clearTokens();
                    window.location.href = '/login';
                    return { success: false, error: 'Session expired' };
                }
            }

            const data = await res.json();

            if (!res.ok) {
                return {
                    success: false,
                    error: data.detail || data.message || 'Request failed',
                };
            }

            return { success: true, data };
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Network error',
            };
        }
    }

    // Auth endpoints
    async login(email: string, password: string) {
        const res = await this.request<{ access_token: string; refresh_token: string }>(
            '/auth/login',
            {
                method: 'POST',
                body: JSON.stringify({ email, password }),
            }
        );

        if (res.success && res.data) {
            this.setTokens(res.data.access_token, res.data.refresh_token);
        }

        return res;
    }

    async register(name: string, email: string, password: string) {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ name, email, password }),
        });
    }

    async logout() {
        this.clearTokens();
        window.location.href = '/login';
    }

    // Wallet endpoints
    async analyzeWallet(address: string, chain: string = 'ethereum') {
        return this.request('/wallet/analyze', {
            method: 'POST',
            body: JSON.stringify({ address, chain }),
        });
    }

    // Account endpoints
    async getUsage() {
        return this.request('/account/usage');
    }

    async getProfile() {
        return this.request('/account/profile');
    }
}

export const api = ApiClient.getInstance();
export default api;
