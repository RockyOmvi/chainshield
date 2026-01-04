import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

/**
 * Email Verification Page
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
        textAlign: 'center' as const,
    },
    icon: {
        fontSize: '64px',
        marginBottom: '24px',
    },
    title: {
        fontSize: '24px',
        fontWeight: '600' as const,
        color: '#fff',
        marginBottom: '12px',
    },
    message: {
        color: '#94a3b8',
        fontSize: '16px',
        marginBottom: '32px',
    },
    button: {
        padding: '14px 28px',
        fontSize: '16px',
        fontWeight: '600' as const,
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        border: 'none',
        borderRadius: '10px',
        color: '#fff',
        cursor: 'pointer',
        textDecoration: 'none',
        display: 'inline-block',
    },
    error: {
        background: 'rgba(239, 68, 68, 0.1)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        color: '#ef4444',
        padding: '12px 16px',
        borderRadius: '8px',
        fontSize: '14px',
        marginBottom: '24px',
    },
    success: {
        background: 'rgba(34, 197, 94, 0.1)',
        border: '1px solid rgba(34, 197, 94, 0.3)',
        color: '#22c55e',
        padding: '12px 16px',
        borderRadius: '8px',
        fontSize: '14px',
        marginBottom: '24px',
    },
    spinner: {
        width: '48px',
        height: '48px',
        border: '4px solid rgba(255,255,255,0.2)',
        borderTopColor: '#8b5cf6',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
        margin: '0 auto 24px',
    },
};

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

type Status = 'verifying' | 'success' | 'error' | 'resend';

const VerifyEmail: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token');

    const [status, setStatus] = useState<Status>(token ? 'verifying' : 'resend');
    const [error, setError] = useState<string | null>(null);
    const [email, setEmail] = useState('');
    const [resendSuccess, setResendSuccess] = useState(false);

    useEffect(() => {
        if (token) {
            verifyEmail();
        }
    }, [token]);

    const verifyEmail = async () => {
        try {
            const res = await fetch(`${API_BASE}/auth/verify-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token }),
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Verification failed');
            }

            setStatus('success');
            setTimeout(() => navigate('/login'), 3000);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Verification failed');
            setStatus('error');
        }
    };

    const handleResend = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const res = await fetch(`${API_BASE}/auth/resend-verification`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });

            if (res.ok) {
                setResendSuccess(true);
            }
        } catch (err) {
            setError('Failed to send verification email');
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                {status === 'verifying' && (
                    <>
                        <div style={styles.spinner} />
                        <h1 style={styles.title}>Verifying Email</h1>
                        <p style={styles.message}>Please wait while we verify your email...</p>
                    </>
                )}

                {status === 'success' && (
                    <>
                        <div style={styles.icon}>✅</div>
                        <h1 style={styles.title}>Email Verified!</h1>
                        <p style={styles.message}>Your email has been verified. Redirecting to login...</p>
                        <a href="/login" style={styles.button}>Go to Login</a>
                    </>
                )}

                {status === 'error' && (
                    <>
                        <div style={styles.icon}>❌</div>
                        <h1 style={styles.title}>Verification Failed</h1>
                        {error && <div style={styles.error}>{error}</div>}
                        <p style={styles.message}>The verification link may have expired.</p>
                        <button style={styles.button} onClick={() => setStatus('resend')}>
                            Resend Verification
                        </button>
                    </>
                )}

                {status === 'resend' && (
                    <>
                        <div style={styles.icon}>📧</div>
                        <h1 style={styles.title}>Verify Your Email</h1>
                        {resendSuccess ? (
                            <>
                                <div style={styles.success}>Verification email sent!</div>
                                <p style={styles.message}>Check your inbox for the verification link.</p>
                            </>
                        ) : (
                            <form onSubmit={handleResend}>
                                <p style={{ ...styles.message, marginBottom: '20px' }}>
                                    Enter your email to receive a new verification link.
                                </p>
                                <input
                                    type="email"
                                    placeholder="you@example.com"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    required
                                    style={{
                                        width: '100%',
                                        padding: '14px 16px',
                                        fontSize: '16px',
                                        background: 'rgba(255,255,255,0.08)',
                                        border: '1px solid rgba(255,255,255,0.15)',
                                        borderRadius: '10px',
                                        color: '#fff',
                                        marginBottom: '20px',
                                        boxSizing: 'border-box',
                                    }}
                                />
                                <button type="submit" style={styles.button}>
                                    Send Verification Email
                                </button>
                            </form>
                        )}
                    </>
                )}
            </div>
            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default VerifyEmail;
