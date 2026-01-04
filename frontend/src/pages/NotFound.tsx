import React from 'react';

/**
 * 404 Not Found Page
 */

const styles = {
    container: {
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column' as const,
        fontFamily: "'Inter', sans-serif",
        color: '#fff',
        textAlign: 'center' as const,
        padding: '20px',
    },
    code: {
        fontSize: '120px',
        fontWeight: '700' as const,
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        marginBottom: '16px',
        lineHeight: '1',
    },
    title: {
        fontSize: '32px',
        fontWeight: '600' as const,
        marginBottom: '12px',
    },
    subtitle: {
        fontSize: '16px',
        color: '#94a3b8',
        marginBottom: '32px',
        maxWidth: '400px',
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
    links: {
        display: 'flex',
        gap: '24px',
        marginTop: '24px',
    },
    link: {
        color: '#94a3b8',
        textDecoration: 'none',
        fontSize: '14px',
        transition: 'color 0.2s',
    },
};

const NotFound: React.FC = () => {
    return (
        <div style={styles.container}>
            <div style={styles.code}>404</div>
            <h1 style={styles.title}>Page Not Found</h1>
            <p style={styles.subtitle}>
                The page you're looking for doesn't exist or has been moved.
            </p>
            <a href="/" style={styles.button}>
                Back to Home
            </a>
            <div style={styles.links}>
                <a href="/login" style={styles.link}>Login</a>
                <a href="/dashboard" style={styles.link}>Dashboard</a>
                <a href="https://docs.chainshield.io" style={styles.link}>API Docs</a>
            </div>
        </div>
    );
};

export default NotFound;
