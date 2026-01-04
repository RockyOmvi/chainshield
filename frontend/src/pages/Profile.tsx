import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Profile Page Component
 */

const styles = {
    container: {
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        fontFamily: "'Inter', sans-serif",
    },
    header: {
        padding: '20px 40px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    logo: {
        fontSize: '24px',
        fontWeight: '700' as const,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        textDecoration: 'none',
    },
    nav: {
        display: 'flex',
        gap: '24px',
    },
    navLink: {
        color: '#94a3b8',
        textDecoration: 'none',
        fontSize: '14px',
        transition: 'color 0.2s',
    },
    main: {
        maxWidth: '800px',
        margin: '0 auto',
        padding: '40px',
    },
    title: {
        fontSize: '28px',
        fontWeight: '600' as const,
        color: '#fff',
        marginBottom: '32px',
    },
    card: {
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '16px',
        padding: '32px',
        border: '1px solid rgba(255,255,255,0.1)',
        marginBottom: '24px',
    },
    cardTitle: {
        fontSize: '18px',
        fontWeight: '600' as const,
        color: '#fff',
        marginBottom: '24px',
    },
    field: {
        marginBottom: '20px',
    },
    label: {
        display: 'block',
        color: '#94a3b8',
        fontSize: '14px',
        marginBottom: '8px',
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
    inputDisabled: {
        opacity: 0.6,
        cursor: 'not-allowed',
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
    },
    dangerButton: {
        background: 'transparent',
        border: '1px solid rgba(239, 68, 68, 0.5)',
        color: '#ef4444',
    },
    tier: {
        display: 'inline-block',
        padding: '6px 16px',
        borderRadius: '100px',
        fontSize: '14px',
        fontWeight: '600' as const,
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        color: '#fff',
    },
};

const Profile: React.FC = () => {
    const navigate = useNavigate();
    const [profile, setProfile] = useState({
        name: 'John Doe',
        email: 'john@example.com',
        tier: 'PRO',
        createdAt: '2025-01-15',
    });
    const [isEditing, setIsEditing] = useState(false);

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        navigate('/login');
    };

    return (
        <div style={styles.container}>
            <header style={styles.header}>
                <a href="/dashboard" style={styles.logo}>
                    <span>🛡️</span>
                    <span>ChainShield</span>
                </a>
                <nav style={styles.nav}>
                    <a href="/dashboard" style={styles.navLink}>Dashboard</a>
                    <a href="/settings" style={styles.navLink}>Settings</a>
                    <a href="/profile" style={{ ...styles.navLink, color: '#8b5cf6' }}>Profile</a>
                    <button
                        onClick={handleLogout}
                        style={{ ...styles.navLink, background: 'none', border: 'none', cursor: 'pointer' }}
                    >
                        Logout
                    </button>
                </nav>
            </header>

            <main style={styles.main}>
                <h1 style={styles.title}>Profile</h1>

                <div style={styles.card}>
                    <h2 style={styles.cardTitle}>Account Information</h2>

                    <div style={styles.field}>
                        <label style={styles.label}>Name</label>
                        <input
                            style={{ ...styles.input, ...(isEditing ? {} : styles.inputDisabled) }}
                            value={profile.name}
                            onChange={e => setProfile(p => ({ ...p, name: e.target.value }))}
                            disabled={!isEditing}
                        />
                    </div>

                    <div style={styles.field}>
                        <label style={styles.label}>Email</label>
                        <input
                            style={{ ...styles.input, ...styles.inputDisabled }}
                            value={profile.email}
                            disabled
                        />
                    </div>

                    <div style={styles.field}>
                        <label style={styles.label}>Subscription</label>
                        <span style={styles.tier}>{profile.tier}</span>
                    </div>

                    <div style={styles.field}>
                        <label style={styles.label}>Member Since</label>
                        <p style={{ color: '#fff', margin: 0 }}>{profile.createdAt}</p>
                    </div>

                    {isEditing ? (
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button style={styles.button} onClick={() => setIsEditing(false)}>
                                Save Changes
                            </button>
                            <button
                                style={{ ...styles.button, ...styles.dangerButton }}
                                onClick={() => setIsEditing(false)}
                            >
                                Cancel
                            </button>
                        </div>
                    ) : (
                        <button style={styles.button} onClick={() => setIsEditing(true)}>
                            Edit Profile
                        </button>
                    )}
                </div>

                <div style={styles.card}>
                    <h2 style={styles.cardTitle}>API Keys</h2>
                    <p style={{ color: '#94a3b8', marginBottom: '20px' }}>
                        Manage your API keys for programmatic access.
                    </p>
                    <button style={styles.button}>Generate New Key</button>
                </div>

                <div style={styles.card}>
                    <h2 style={{ ...styles.cardTitle, color: '#ef4444' }}>Danger Zone</h2>
                    <p style={{ color: '#94a3b8', marginBottom: '20px' }}>
                        Once you delete your account, there is no going back.
                    </p>
                    <button style={{ ...styles.button, ...styles.dangerButton }}>
                        Delete Account
                    </button>
                </div>
            </main>
        </div>
    );
};

export default Profile;
