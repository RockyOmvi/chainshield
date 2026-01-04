import React, { Component, ErrorInfo, ReactNode } from 'react';

/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors anywhere in child component tree and displays fallback UI.
 */

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

const styles = {
    container: {
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: "'Inter', sans-serif",
        padding: '20px',
    },
    card: {
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '24px',
        padding: '48px',
        width: '100%',
        maxWidth: '500px',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        textAlign: 'center' as const,
    },
    icon: {
        fontSize: '64px',
        marginBottom: '16px',
    },
    title: {
        color: '#ef4444',
        fontSize: '24px',
        fontWeight: '600' as const,
        marginBottom: '12px',
    },
    message: {
        color: '#94a3b8',
        fontSize: '16px',
        marginBottom: '24px',
    },
    errorBox: {
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '24px',
        textAlign: 'left' as const,
    },
    errorText: {
        color: '#f87171',
        fontSize: '13px',
        fontFamily: 'monospace',
        whiteSpace: 'pre-wrap' as const,
        wordBreak: 'break-all' as const,
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
        marginRight: '12px',
    },
    secondaryButton: {
        padding: '14px 28px',
        fontSize: '16px',
        fontWeight: '600' as const,
        background: 'transparent',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: '10px',
        color: '#fff',
        cursor: 'pointer',
    },
};

class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    private handleReload = () => {
        window.location.reload();
    };

    private handleHome = () => {
        window.location.href = '/';
    };

    public render() {
        if (this.state.hasError) {
            return (
                <div style={styles.container}>
                    <div style={styles.card}>
                        <div style={styles.icon}>⚠️</div>
                        <h1 style={styles.title}>Something went wrong</h1>
                        <p style={styles.message}>
                            An unexpected error occurred. Please try reloading the page.
                        </p>

                        {this.state.error && (
                            <div style={styles.errorBox}>
                                <code style={styles.errorText}>
                                    {this.state.error.message}
                                </code>
                            </div>
                        )}

                        <div>
                            <button style={styles.button} onClick={this.handleReload}>
                                Reload Page
                            </button>
                            <button style={styles.secondaryButton} onClick={this.handleHome}>
                                Go Home
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
