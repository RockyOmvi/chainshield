import React, { useState } from 'react';

/**
 * Register Page Component
 */

interface RegisterState {
    name: string;
    email: string;
    password: string;
    confirmPassword: string;
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
        gap: '16px',
    },
    inputGroup: {
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '6px',
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
    },
    error: {
        background: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        color: '#ef4444',
        padding: '12px 16px',
        borderRadius: '8px',
        fontSize: '14px',
    },
    success: {
        background: 'rgba(34, 197, 94, 0.1)',
        border: '1px solid rgba(34, 197, 94, 0.3)',
        color: '#22c55e',
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
    features: {
        display: 'flex',
        gap: '8px',
        flexWrap: 'wrap' as const,
        marginTop: '8px',
    },
    featureBadge: {
        background: 'rgba(139, 92, 246, 0.2)',
        color: '#a78bfa',
        padding: '4px 10px',
        borderRadius: '100px',
        fontSize: '12px',
    },
};

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

const Register: React.FC = () => {
    const [state, setState] = useState<RegisterState>({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        isLoading: false,
        error: null,
    });
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (state.password !== state.confirmPassword) {
            setState(prev => ({ ...prev, error: 'Passwords do not match' }));
            return;
        }

        if (state.password.length < 8) {
            setState(prev => ({ ...prev, error: 'Password must be at least 8 characters' }));
            return;
        }

        setState(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const res = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: state.name,
                    email: state.email,
                    password: state.password,
                }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Registration failed');
            }

            setSuccess(true);
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } catch (error) {
            setState(prev => ({
                ...prev,
                isLoading: false,
                error: error instanceof Error ? error.message : 'Registration failed',
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
                <p style={styles.subtitle}>Create your account</p>

                {success ? (
                    <div style={styles.success}>
                        ✓ Account created! Redirecting to login...
                    </div>
                ) : (
                    <form style={styles.form} onSubmit={handleSubmit}>
                        {state.error && (
                            <div style={styles.error}>{state.error}</div>
                        )}

                        <div style={styles.inputGroup}>
                            <label style={styles.label}>Name</label>
                            <input
                                style={styles.input}
                                type="text"
                                placeholder="John Doe"
                                value={state.name}
                                onChange={e => setState(prev => ({ ...prev, name: e.target.value }))}
                                required
                            />
                        </div>

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
                                placeholder="Min. 8 characters"
                                value={state.password}
                                onChange={e => setState(prev => ({ ...prev, password: e.target.value }))}
                                required
                            />
                        </div>

                        <div style={styles.inputGroup}>
                            <label style={styles.label}>Confirm Password</label>
                            <input
                                style={styles.input}
                                type="password"
                                placeholder="••••••••"
                                value={state.confirmPassword}
                                onChange={e => setState(prev => ({ ...prev, confirmPassword: e.target.value }))}
                                required
                            />
                        </div>

                        <div style={styles.features}>
                            <span style={styles.featureBadge}>1,000 free requests</span>
                            <span style={styles.featureBadge}>Multi-chain</span>
                            <span style={styles.featureBadge}>API access</span>
                        </div>

                        <button
                            style={{
                                ...styles.button,
                                opacity: state.isLoading ? 0.7 : 1,
                            }}
                            type="submit"
                            disabled={state.isLoading}
                        >
                            {state.isLoading ? 'Creating account...' : 'Create Account'}
                        </button>
                    </form>
                )}

                <p style={styles.footer}>
                    Already have an account?
                    <a href="/login" style={styles.link}>Sign in</a>
                </p>
            </div>
        </div>
    );
};

export default Register;
