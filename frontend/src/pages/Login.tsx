import React, { useState } from 'react';

/**
 * Login Page Component
 */

interface LoginState {
    email: string;
    password: string;
    isLoading: boolean;
    error: string | null;
}

const styles = {
    container: {
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        fontFamily: "'Inter', sans-serif",
    },
    card: {
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '24px',
        padding: '48px',
        width: '100%',
        maxWidth: '420px',
        border: '1px solid rgba(255,255,255,0.1)',
    },
    logo: {
        fontSize: '28px',
        fontWeight: '700' as const,
        color: '#fff',
        textAlign: 'center' as const,
        marginBottom: '8px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '10px',
    },
    subtitle: {
        color: '#94a3b8',
        textAlign: 'center' as const,
        marginBottom: '32px',
        fontSize: '14px',
    },
    form: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '20px',
    },
    inputGroup: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '8px',
    },
    label: {
        color: '#94a3b8',
        fontSize: '14px',
        fontWeight: '500' as const,
    },
    input: {
        width: '100%',
        padding: '14px 16px',
        fontSize: '16px',
        background: 'rgba(255,255,255,0.08)',
        border: '1px solid rgba(255,255,255,0.15)',
        borderRadius: '10px',
        color: '#fff',
        outline: 'none',
        transition: 'border-color 0.2s',
        boxSizing: 'border-box' as const,
    },
    button: {
        width: '100%',
        padding: '16px',
        fontSize: '16px',
        fontWeight: '600' as const,
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        border: 'none',
        borderRadius: '10px',
        color: '#fff',
        cursor: 'pointer',
        marginTop: '8px',
        transition: 'transform 0.2s, opacity 0.2s',
    },
    error: {
        background: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        color: '#ef4444',
        padding: '12px 16px',
        borderRadius: '8px',
        fontSize: '14px',
    },
    footer: {
        textAlign: 'center' as const,
        marginTop: '24px',
        color: '#94a3b8',
        fontSize: '14px',
    },
    link: {
        color: '#8b5cf6',
        textDecoration: 'none',
        fontWeight: '500' as const,
        marginLeft: '4px',
    },
};

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

const Login: React.FC = () => {
    const [state, setState] = useState<LoginState>({
        email: '',
        password: '',
        isLoading: false,
        error: null,
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: state.email,
                    password: state.password,
                }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Login failed');
            }

            // Store token and redirect
            localStorage.setItem('token', data.access_token);
            window.location.href = '/dashboard';
        } catch (error) {
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: error instanceof Error ? error.message : 'Login failed',
            }));
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <div style={styles.logo}>
                    <span>🛡️</span>
                    <span>ChainShield</span>
                </div>
                <p style={styles.subtitle}>Sign in to your account</p>

                <form style={styles.form} onSubmit={handleSubmit}>
                    {state.error && (
                        <div style={styles.error}>{state.error}</div>
                    )}

                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Email</label>
                        <input
                            style={styles.input}
                            type="email"
                            placeholder="you@example.com"
                            value={state.email}
                            onChange={e => setState(prev => ({ ...prev, email: e.target.value }))}
                            required
                        />
                    </div>

                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Password</label>
                        <input
                            style={styles.input}
                            type="password"
                            placeholder="••••••••"
                            value={state.password}
                            onChange={e => setState(prev => ({ ...prev, password: e.target.value }))}
                            required
                        />
                    </div>

                    <button
                        style={{
                            ...styles.button,
                            opacity: state.isLoading ? 0.7 : 1,
                        }}
                        type="submit"
                        disabled={state.isLoading}
                    >
                        {state.isLoading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <p style={styles.footer}>
                    Don't have an account?
                    <a href="/register" style={styles.link}>Sign up</a>
                </p>
            </div>
        </div>
    );
};

export default Login;
