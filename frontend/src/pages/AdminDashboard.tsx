import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Admin Dashboard Page
 */

interface User {
    id: string;
    email: string;
    name: string;
    tier: string;
    status: 'active' | 'suspended' | 'pending';
    createdAt: string;
    requestsTotal: number;
}

interface SystemStats {
    totalUsers: number;
    activeUsers: number;
    totalRequests: number;
    requestsToday: number;
    avgResponseTime: number;
    errorRate: number;
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
    },
    adminBadge: {
        fontSize: '12px',
        background: '#ef4444',
        padding: '2px 8px',
        borderRadius: '4px',
        marginLeft: '8px',
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
        padding: '40px',
    },
    title: {
        fontSize: '28px',
        fontWeight: '600' as const,
        color: '#fff',
        marginBottom: '32px',
    },
    statsGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(6, 1fr)',
        gap: '16px',
        marginBottom: '32px',
    },
    statCard: {
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '12px',
        padding: '20px',
        border: '1px solid rgba(255,255,255,0.1)',
    },
    statLabel: {
        color: '#94a3b8',
        fontSize: '12px',
        textTransform: 'uppercase' as const,
        marginBottom: '8px',
    },
    statValue: {
        color: '#fff',
        fontSize: '24px',
        fontWeight: '600' as const,
    },
    card: {
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '16px',
        padding: '24px',
        border: '1px solid rgba(255,255,255,0.1)',
        marginBottom: '24px',
    },
    cardTitle: {
        color: '#fff',
        fontSize: '18px',
        fontWeight: '600' as const,
        marginBottom: '20px',
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
    button: {
        padding: '8px 16px',
        fontSize: '13px',
        fontWeight: '500' as const,
        background: 'transparent',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: '6px',
        color: '#fff',
        cursor: 'pointer',
    },
    dangerButton: {
        border: '1px solid rgba(239, 68, 68, 0.5)',
        color: '#ef4444',
    },
    successButton: {
        border: '1px solid rgba(34, 197, 94, 0.5)',
        color: '#22c55e',
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
    statusSuspended: {
        display: 'inline-block',
        padding: '4px 12px',
        borderRadius: '100px',
        fontSize: '12px',
        fontWeight: '600' as const,
        background: 'rgba(239, 68, 68, 0.2)',
        color: '#ef4444',
    },
    statusPending: {
        display: 'inline-block',
        padding: '4px 12px',
        borderRadius: '100px',
        fontSize: '12px',
        fontWeight: '600' as const,
        background: 'rgba(234, 179, 8, 0.2)',
        color: '#eab308',
    },
    tabs: {
        display: 'flex',
        gap: '4px',
        marginBottom: '24px',
        background: 'rgba(255,255,255,0.05)',
        padding: '4px',
        borderRadius: '8px',
        width: 'fit-content',
    },
    tab: {
        padding: '10px 20px',
        fontSize: '14px',
        background: 'transparent',
        border: 'none',
        borderRadius: '6px',
        color: '#94a3b8',
        cursor: 'pointer',
    },
    tabActive: {
        background: 'rgba(139, 92, 246, 0.3)',
        color: '#fff',
    },
    searchInput: {
        width: '300px',
        padding: '10px 16px',
        fontSize: '14px',
        background: 'rgba(255,255,255,0.08)',
        border: '1px solid rgba(255,255,255,0.15)',
        borderRadius: '8px',
        color: '#fff',
        outline: 'none',
    },
};

const AdminDashboard: React.FC = () => {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState<'users' | 'system' | 'logs'>('users');
    const [searchQuery, setSearchQuery] = useState('');

    const [stats] = useState<SystemStats>({
        totalUsers: 1247,
        activeUsers: 892,
        totalRequests: 2847293,
        requestsToday: 15420,
        avgResponseTime: 142,
        errorRate: 0.12,
    });

    const [users] = useState<User[]>([
        { id: '1', email: 'john@example.com', name: 'John Doe', tier: 'pro', status: 'active', createdAt: '2026-01-01', requestsTotal: 15420 },
        { id: '2', email: 'jane@company.com', name: 'Jane Smith', tier: 'enterprise', status: 'active', createdAt: '2025-12-15', requestsTotal: 89230 },
        { id: '3', email: 'bob@startup.io', name: 'Bob Wilson', tier: 'free', status: 'suspended', createdAt: '2025-11-20', requestsTotal: 245 },
        { id: '4', email: 'alice@dev.co', name: 'Alice Brown', tier: 'pro', status: 'pending', createdAt: '2026-01-03', requestsTotal: 0 },
    ]);

    const [logs] = useState([
        { time: '2026-01-04 18:30:15', level: 'INFO', message: 'User john@example.com logged in', source: 'auth' },
        { time: '2026-01-04 18:29:45', level: 'WARN', message: 'Rate limit exceeded for API key cs_xxx', source: 'rate_limiter' },
        { time: '2026-01-04 18:28:30', level: 'ERROR', message: 'Blockchain RPC timeout after 30s', source: 'blockchain' },
        { time: '2026-01-04 18:27:12', level: 'INFO', message: 'New user registered: alice@dev.co', source: 'auth' },
        { time: '2026-01-04 18:25:00', level: 'INFO', message: 'Risk assessment completed: 0x742d...3f21 → HIGH', source: 'risk_engine' },
    ]);

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    const getStatusStyle = (status: string) => {
        switch (status) {
            case 'active': return styles.statusActive;
            case 'suspended': return styles.statusSuspended;
            case 'pending': return styles.statusPending;
            default: return {};
        }
    };

    const getLevelColor = (level: string) => {
        switch (level) {
            case 'ERROR': return '#ef4444';
            case 'WARN': return '#eab308';
            case 'INFO': return '#22c55e';
            default: return '#94a3b8';
        }
    };

    const filteredUsers = users.filter(u =>
        u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div style={styles.container}>
            <header style={styles.header}>
                <div style={styles.logo}>
                    <span>🛡️</span>
                    <span>ChainShield</span>
                    <span style={styles.adminBadge}>ADMIN</span>
                </div>
                <nav style={styles.nav}>
                    <a href="/dashboard" style={styles.navLink}>User Dashboard</a>
                    <a href="/admin" style={{ ...styles.navLink, color: '#8b5cf6' }}>Admin</a>
                    <button onClick={handleLogout} style={{ ...styles.navLink, background: 'none', border: 'none', cursor: 'pointer' }}>
                        Logout
                    </button>
                </nav>
            </header>

            <main style={styles.main}>
                <h1 style={styles.title}>Admin Dashboard</h1>

                {/* Stats Grid */}
                <div style={styles.statsGrid}>
                    <div style={styles.statCard}>
                        <p style={styles.statLabel}>Total Users</p>
                        <p style={styles.statValue}>{stats.totalUsers.toLocaleString()}</p>
                    </div>
                    <div style={styles.statCard}>
                        <p style={styles.statLabel}>Active Users</p>
                        <p style={styles.statValue}>{stats.activeUsers.toLocaleString()}</p>
                    </div>
                    <div style={styles.statCard}>
                        <p style={styles.statLabel}>Total Requests</p>
                        <p style={styles.statValue}>{(stats.totalRequests / 1000000).toFixed(2)}M</p>
                    </div>
                    <div style={styles.statCard}>
                        <p style={styles.statLabel}>Today</p>
                        <p style={styles.statValue}>{stats.requestsToday.toLocaleString()}</p>
                    </div>
                    <div style={styles.statCard}>
                        <p style={styles.statLabel}>Avg Response</p>
                        <p style={styles.statValue}>{stats.avgResponseTime}ms</p>
                    </div>
                    <div style={styles.statCard}>
                        <p style={styles.statLabel}>Error Rate</p>
                        <p style={styles.statValue}>{stats.errorRate}%</p>
                    </div>
                </div>

                {/* Tabs */}
                <div style={styles.tabs}>
                    <button
                        style={{ ...styles.tab, ...(activeTab === 'users' ? styles.tabActive : {}) }}
                        onClick={() => setActiveTab('users')}
                    >
                        Users
                    </button>
                    <button
                        style={{ ...styles.tab, ...(activeTab === 'system' ? styles.tabActive : {}) }}
                        onClick={() => setActiveTab('system')}
                    >
                        System
                    </button>
                    <button
                        style={{ ...styles.tab, ...(activeTab === 'logs' ? styles.tabActive : {}) }}
                        onClick={() => setActiveTab('logs')}
                    >
                        Logs
                    </button>
                </div>

                {activeTab === 'users' && (
                    <div style={styles.card}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                            <h2 style={styles.cardTitle}>User Management</h2>
                            <input
                                style={styles.searchInput}
                                type="text"
                                placeholder="Search users..."
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                            />
                        </div>
                        <table style={styles.table}>
                            <thead>
                                <tr>
                                    <th style={styles.th}>User</th>
                                    <th style={styles.th}>Tier</th>
                                    <th style={styles.th}>Status</th>
                                    <th style={styles.th}>Requests</th>
                                    <th style={styles.th}>Joined</th>
                                    <th style={styles.th}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredUsers.map(user => (
                                    <tr key={user.id}>
                                        <td style={styles.td}>
                                            <div style={{ fontWeight: '500' }}>{user.name}</div>
                                            <div style={{ fontSize: '13px', color: '#94a3b8' }}>{user.email}</div>
                                        </td>
                                        <td style={{ ...styles.td, textTransform: 'uppercase', fontSize: '12px' }}>
                                            {user.tier}
                                        </td>
                                        <td style={styles.td}>
                                            <span style={getStatusStyle(user.status)}>
                                                {user.status}
                                            </span>
                                        </td>
                                        <td style={styles.td}>{user.requestsTotal.toLocaleString()}</td>
                                        <td style={styles.td}>{user.createdAt}</td>
                                        <td style={styles.td}>
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                                <button style={styles.button}>View</button>
                                                {user.status === 'active' ? (
                                                    <button style={{ ...styles.button, ...styles.dangerButton }}>Suspend</button>
                                                ) : (
                                                    <button style={{ ...styles.button, ...styles.successButton }}>Activate</button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {activeTab === 'system' && (
                    <div style={styles.card}>
                        <h2 style={styles.cardTitle}>System Status</h2>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                            {[
                                { name: 'API Server', status: 'Healthy', uptime: '99.99%' },
                                { name: 'PostgreSQL', status: 'Healthy', uptime: '99.98%' },
                                { name: 'Redis Cache', status: 'Healthy', uptime: '99.99%' },
                                { name: 'Risk Engine', status: 'Healthy', uptime: '99.97%' },
                            ].map((service, i) => (
                                <div key={i} style={{ padding: '16px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <span style={{ color: '#fff', fontWeight: '500' }}>{service.name}</span>
                                        <span style={styles.statusActive}>{service.status}</span>
                                    </div>
                                    <div style={{ marginTop: '8px', color: '#94a3b8', fontSize: '13px' }}>
                                        Uptime: {service.uptime}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {activeTab === 'logs' && (
                    <div style={styles.card}>
                        <h2 style={styles.cardTitle}>System Logs</h2>
                        <table style={styles.table}>
                            <thead>
                                <tr>
                                    <th style={styles.th}>Time</th>
                                    <th style={styles.th}>Level</th>
                                    <th style={styles.th}>Source</th>
                                    <th style={styles.th}>Message</th>
                                </tr>
                            </thead>
                            <tbody>
                                {logs.map((log, i) => (
                                    <tr key={i}>
                                        <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: '13px' }}>{log.time}</td>
                                        <td style={styles.td}>
                                            <span style={{ color: getLevelColor(log.level), fontWeight: '600' }}>{log.level}</span>
                                        </td>
                                        <td style={{ ...styles.td, color: '#94a3b8' }}>{log.source}</td>
                                        <td style={styles.td}>{log.message}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </main>
        </div>
    );
};

export default AdminDashboard;
