import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Webhook Management Page
 */

interface Webhook {
    id: string;
    url: string;
    events: string[];
    active: boolean;
    createdAt: string;
    lastTriggered?: string;
}

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
    },
    main: {
        maxWidth: '1000px',
        margin: '0 auto',
        padding: '40px',
    },
    title: {
        fontSize: '28px',
        fontWeight: '600' as const,
        color: '#fff',
        marginBottom: '8px',
    },
    subtitle: {
        color: '#94a3b8',
        marginBottom: '32px',
    },
    card: {
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '16px',
        padding: '24px',
        border: '1px solid rgba(255,255,255,0.1)',
        marginBottom: '24px',
    },
    button: {
        padding: '12px 24px',
        fontSize: '14px',
        fontWeight: '600' as const,
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        border: 'none',
        borderRadius: '8px',
        color: '#fff',
        cursor: 'pointer',
    },
    secondaryButton: {
        padding: '8px 16px',
        fontSize: '14px',
        background: 'transparent',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: '6px',
        color: '#fff',
        cursor: 'pointer',
    },
    dangerButton: {
        background: 'transparent',
        border: '1px solid rgba(239, 68, 68, 0.5)',
        color: '#ef4444',
    },
    input: {
        width: '100%',
        padding: '12px 16px',
        fontSize: '14px',
        background: 'rgba(255,255,255,0.08)',
        border: '1px solid rgba(255,255,255,0.15)',
        borderRadius: '8px',
        color: '#fff',
        outline: 'none',
        boxSizing: 'border-box' as const,
    },
    label: {
        display: 'block',
        color: '#94a3b8',
        fontSize: '14px',
        marginBottom: '8px',
    },
    table: {
        width: '100%',
        borderCollapse: 'collapse' as const,
    },
    th: {
        textAlign: 'left' as const,
        padding: '12px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        color: '#94a3b8',
        fontSize: '12px',
        textTransform: 'uppercase' as const,
    },
    td: {
        padding: '16px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        color: '#fff',
    },
    statusActive: {
        display: 'inline-block',
        padding: '4px 12px',
        borderRadius: '100px',
        fontSize: '12px',
        fontWeight: '600' as const,
        background: 'rgba(34, 197, 94, 0.2)',
        color: '#22c55e',
    },
    statusInactive: {
        display: 'inline-block',
        padding: '4px 12px',
        borderRadius: '100px',
        fontSize: '12px',
        fontWeight: '600' as const,
        background: 'rgba(239, 68, 68, 0.2)',
        color: '#ef4444',
    },
    modal: {
        position: 'fixed' as const,
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
    },
    modalContent: {
        background: '#1e293b',
        borderRadius: '16px',
        padding: '32px',
        width: '100%',
        maxWidth: '500px',
        border: '1px solid rgba(255,255,255,0.1)',
    },
    checkbox: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '8px',
        color: '#fff',
    },
};

const EVENTS = [
    { id: 'high_risk', name: 'High Risk Detected', desc: 'When a wallet exceeds risk threshold' },
    { id: 'critical_risk', name: 'Critical Risk Alert', desc: 'When a blocked address is found' },
    { id: 'usage_limit', name: 'Usage Limit', desc: 'When approaching rate limits' },
    { id: 'new_assessment', name: 'New Assessment', desc: 'On every new assessment' },
];

const Webhooks: React.FC = () => {
    const navigate = useNavigate();
    const [webhooks, setWebhooks] = useState<Webhook[]>([
        {
            id: '1',
            url: 'https://api.example.com/webhook',
            events: ['high_risk', 'critical_risk'],
            active: true,
            createdAt: '2026-01-01',
            lastTriggered: '2026-01-04',
        },
    ]);
    const [showModal, setShowModal] = useState(false);
    const [newWebhook, setNewWebhook] = useState({ url: '', events: [] as string[] });

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    const handleAddWebhook = () => {
        if (!newWebhook.url || newWebhook.events.length === 0) return;

        const webhook: Webhook = {
            id: Date.now().toString(),
            url: newWebhook.url,
            events: newWebhook.events,
            active: true,
            createdAt: new Date().toISOString().split('T')[0],
        };

        setWebhooks([...webhooks, webhook]);
        setNewWebhook({ url: '', events: [] });
        setShowModal(false);
    };

    const toggleEvent = (eventId: string) => {
        setNewWebhook(prev => ({
            ...prev,
            events: prev.events.includes(eventId)
                ? prev.events.filter(e => e !== eventId)
                : [...prev.events, eventId],
        }));
    };

    const toggleWebhook = (id: string) => {
        setWebhooks(prev => prev.map(w =>
            w.id === id ? { ...w, active: !w.active } : w
        ));
    };

    const deleteWebhook = (id: string) => {
        setWebhooks(prev => prev.filter(w => w.id !== id));
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
                    <a href="/webhooks" style={{ ...styles.navLink, color: '#8b5cf6' }}>Webhooks</a>
                    <a href="/settings" style={styles.navLink}>Settings</a>
                    <button onClick={handleLogout} style={{ ...styles.navLink, background: 'none', border: 'none', cursor: 'pointer' }}>
                        Logout
                    </button>
                </nav>
            </header>

            <main style={styles.main}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                    <div>
                        <h1 style={styles.title}>Webhooks</h1>
                        <p style={styles.subtitle}>Receive real-time notifications for risk events</p>
                    </div>
                    <button style={styles.button} onClick={() => setShowModal(true)}>
                        + Add Webhook
                    </button>
                </div>

                <div style={styles.card}>
                    <table style={styles.table}>
                        <thead>
                            <tr>
                                <th style={styles.th}>Endpoint</th>
                                <th style={styles.th}>Events</th>
                                <th style={styles.th}>Status</th>
                                <th style={styles.th}>Last Triggered</th>
                                <th style={styles.th}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {webhooks.length === 0 ? (
                                <tr>
                                    <td colSpan={5} style={{ ...styles.td, textAlign: 'center', color: '#94a3b8' }}>
                                        No webhooks configured. Add one to get started.
                                    </td>
                                </tr>
                            ) : (
                                webhooks.map(webhook => (
                                    <tr key={webhook.id}>
                                        <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: '13px' }}>
                                            {webhook.url}
                                        </td>
                                        <td style={styles.td}>
                                            {webhook.events.join(', ')}
                                        </td>
                                        <td style={styles.td}>
                                            <span style={webhook.active ? styles.statusActive : styles.statusInactive}>
                                                {webhook.active ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                        <td style={styles.td}>
                                            {webhook.lastTriggered || 'Never'}
                                        </td>
                                        <td style={styles.td}>
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                <button
                                                    style={styles.secondaryButton}
                                                    onClick={() => toggleWebhook(webhook.id)}
                                                >
                                                    {webhook.active ? 'Disable' : 'Enable'}
                                                </button>
                                                <button
                                                    style={{ ...styles.secondaryButton, ...styles.dangerButton }}
                                                    onClick={() => deleteWebhook(webhook.id)}
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </main>

            {showModal && (
                <div style={styles.modal} onClick={() => setShowModal(false)}>
                    <div style={styles.modalContent} onClick={e => e.stopPropagation()}>
                        <h2 style={{ color: '#fff', marginBottom: '24px' }}>Add Webhook</h2>

                        <div style={{ marginBottom: '20px' }}>
                            <label style={styles.label}>Endpoint URL</label>
                            <input
                                style={styles.input}
                                type="url"
                                placeholder="https://your-server.com/webhook"
                                value={newWebhook.url}
                                onChange={e => setNewWebhook({ ...newWebhook, url: e.target.value })}
                            />
                        </div>

                        <div style={{ marginBottom: '24px' }}>
                            <label style={styles.label}>Events</label>
                            {EVENTS.map(event => (
                                <label key={event.id} style={styles.checkbox}>
                                    <input
                                        type="checkbox"
                                        checked={newWebhook.events.includes(event.id)}
                                        onChange={() => toggleEvent(event.id)}
                                    />
                                    <div>
                                        <div>{event.name}</div>
                                        <div style={{ fontSize: '12px', color: '#94a3b8' }}>{event.desc}</div>
                                    </div>
                                </label>
                            ))}
                        </div>

                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button style={styles.button} onClick={handleAddWebhook}>
                                Add Webhook
                            </button>
                            <button style={styles.secondaryButton} onClick={() => setShowModal(false)}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Webhooks;
