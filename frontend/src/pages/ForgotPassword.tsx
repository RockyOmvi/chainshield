import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Password Reset Request Page
 */

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
    label: {
        color: '#94a3b8',
        fontSize: '14px',
        fontWeight: '500' as const,
        marginBottom: '8px',
        display: 'block',
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
    link: {
        color: '#8b5cf6',
        textDecoration: 'none',
        fontWeight: '500' as const,
    },
    footer: {
        textAlign: 'center' as const,
        marginTop: '24px',
        color: '#94a3b8',
        fontSize: '14px',
    },
};

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

const ForgotPassword: React.FC = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Failed to send reset email');
            }

            setSuccess(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Something went wrong');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <div style={styles.logo}>
                    <span>🛡️</span>
                    <span>ChainShield</span>
                </div>
                <p style={styles.subtitle}>Reset your password</p>

                {success ? (
                    <div>
                        <div style={styles.success}>
                            ✓ Password reset link sent! Check your email.
                        </div>
                        <p style={{ ...styles.footer, marginTop: '24px' }}>
                            <a href="/login" style={styles.link}>Back to Login</a>
                        </p>
                    </div>
                ) : (
                    <form style={styles.form} onSubmit={handleSubmit}>
                        {error && <div style={styles.error}>{error}</div>}

                        <div>
                            <label style={styles.label}>Email Address</label>
                            <input
                                style={styles.input}
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                required
                            />
                        </div>

                        <button
                            style={{ ...styles.button, opacity: isLoading ? 0.7 : 1 }}
                            type="submit"
                            disabled={isLoading}
                        >
                            {isLoading ? 'Sending...' : 'Send Reset Link'}
                        </button>

                        <p style={styles.footer}>
                            Remember your password?{' '}
                            <a href="/login" style={styles.link}>Sign in</a>
                        </p>
                    </form>
                )}
            </div>
        </div>
    );
};

export default ForgotPassword;
