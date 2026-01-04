import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

/**
 * Reset Password Page (with token from email)
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
    },
    footer: {
        textAlign: 'center' as const,
        marginTop: '24px',
        color: '#94a3b8',
        fontSize: '14px',
    },
};

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

const ResetPassword: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token');

    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        if (!token) {
            setError('Invalid or missing reset token');
        }
    }, [token]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/auth/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, password }),
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Failed to reset password');
            }

            setSuccess(true);
            setTimeout(() => navigate('/login'), 3000);
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
                <p style={styles.subtitle}>Create a new password</p>

                {success ? (
                    <div>
                        <div style={styles.success}>
                            ✓ Password reset successful! Redirecting to login...
                        </div>
                    </div>
                ) : (
                    <form style={styles.form} onSubmit={handleSubmit}>
                        {error && <div style={styles.error}>{error}</div>}

                        <div>
                            <label style={styles.label}>New Password</label>
                            <input
                                style={styles.input}
                                type="password"
                                placeholder="Min. 8 characters"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                required
                                disabled={!token}
                            />
                        </div>

                        <div>
                            <label style={styles.label}>Confirm Password</label>
                            <input
                                style={styles.input}
                                type="password"
                                placeholder="••••••••"
                                value={confirmPassword}
                                onChange={e => setConfirmPassword(e.target.value)}
                                required
                                disabled={!token}
                            />
                        </div>

                        <button
                            style={{ ...styles.button, opacity: isLoading || !token ? 0.7 : 1 }}
                            type="submit"
                            disabled={isLoading || !token}
                        >
                            {isLoading ? 'Resetting...' : 'Reset Password'}
                        </button>

                        <p style={styles.footer}>
                            <a href="/login" style={styles.link}>Back to Login</a>
                        </p>
                    </form>
                )}
            </div>
        </div>
    );
};

export default ResetPassword;
