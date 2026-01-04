import React, { useState, useEffect } from 'react';

/**
 * ChainShield Dashboard
 * 
 * Main dashboard component for authenticated users.
 */

// API Base URL (Vite uses import.meta.env instead of process.env)
const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

// Types
interface RiskAssessment {
    address: string;
    chain: string;
    risk_score: number;
    risk_level: string;
    blocked: boolean;
    factors: string[];
    timestamp: string;
}

interface UsageStats {
    requests_today: number;
    requests_this_month: number;
    tier: string;
    limits: {
        per_minute: number;
        per_day: number;
        per_month: number;
    };
}

interface DashboardState {
    recentAssessments: RiskAssessment[];
    usage: UsageStats | null;
    isLoading: boolean;
    error: string | null;
}

// Styles
const styles = {
    dashboard: {
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        color: '#fff',
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
        fontWeight: '700',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
    },
    main: {
        padding: '40px',
        maxWidth: '1400px',
        margin: '0 auto',
    },
    grid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '24px',
        marginBottom: '40px',
    },
    card: {
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '16px',
        padding: '24px',
        border: '1px solid rgba(255,255,255,0.1)',
    },
    cardTitle: {
        fontSize: '14px',
        color: '#94a3b8',
        marginBottom: '8px',
        textTransform: 'uppercase' as const,
        letterSpacing: '1px',
    },
    cardValue: {
        fontSize: '36px',
        fontWeight: '700',
        margin: '0',
    },
    searchBox: {
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '12px',
        padding: '24px',
        marginBottom: '40px',
    },
    input: {
        width: '100%',
        padding: '16px 20px',
        fontSize: '16px',
        background: 'rgba(255,255,255,0.1)',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: '8px',
        color: '#fff',
        outline: 'none',
    },
    button: {
        padding: '16px 32px',
        fontSize: '16px',
        fontWeight: '600',
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
        border: 'none',
        borderRadius: '8px',
        color: '#fff',
        cursor: 'pointer',
        marginLeft: '12px',
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
    },
    badge: (level: string) => ({
        display: 'inline-block',
        padding: '4px 12px',
        borderRadius: '100px',
        fontSize: '12px',
        fontWeight: '600',
        background: level === 'CRITICAL' ? '#ef4444' :
            level === 'HIGH' ? '#f97316' :
                level === 'MEDIUM' ? '#eab308' : '#22c55e',
        color: '#fff',
    }),
};

// Dashboard Component
const Dashboard: React.FC = () => {
    const [state, setState] = useState<DashboardState>({
        recentAssessments: [],
        usage: null,
        isLoading: true,
        error: null,
    });

    const [searchAddress, setSearchAddress] = useState('');
    const [searchResult, setSearchResult] = useState<RiskAssessment | null>(null);
    const [isSearching, setIsSearching] = useState(false);

    // Fetch dashboard data
    useEffect(() => {
        const fetchData = async () => {
            try {
                const token = localStorage.getItem('token');
                const headers = { 'Authorization': `Bearer ${token}` };

                // Fetch usage stats
                const usageRes = await fetch(`${API_BASE}/account/usage`, { headers });
                const usage = await usageRes.json();

                setState(prev => ({
                    ...prev,
                    usage,
                    isLoading: false,
                }));
            } catch (error) {
                setState(prev => ({
                    ...prev,
                    error: 'Failed to load dashboard data',
                    isLoading: false,
                }));
            }
        };

        fetchData();
    }, []);

    // Analyze wallet
    const handleAnalyze = async () => {
        if (!searchAddress) return;

        setIsSearching(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`${API_BASE}/wallet/analyze`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ address: searchAddress }),
            });

            const result = await res.json();
            setSearchResult(result);

            // Add to recent assessments
            setState(prev => ({
                ...prev,
                recentAssessments: [result, ...prev.recentAssessments.slice(0, 9)],
            }));
        } catch (error) {
            console.error('Analysis failed:', error);
        }
        setIsSearching(false);
    };

    if (state.isLoading) {
        return (
            <div style={styles.dashboard}>
                <div style={{ textAlign: 'center', padding: '100px' }}>Loading...</div>
            </div>
        );
    }

    return (
        <div style={styles.dashboard}>
            {/* Header */}
            <header style={styles.header}>
                <div style={styles.logo}>
                    <span>🛡️</span>
                    <span>ChainShield</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                    <a href="/dashboard" style={{ color: '#8b5cf6', textDecoration: 'none', fontSize: '14px' }}>Dashboard</a>
                    <a href="/settings" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>Settings</a>
                    <a href="/profile" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '14px' }}>Profile</a>
                    <span style={{ color: '#94a3b8', fontSize: '14px' }}>
                        {state.usage?.tier.toUpperCase()} Plan
                    </span>
                    <button
                        style={{ ...styles.button, padding: '8px 16px', fontSize: '14px' }}
                        onClick={() => {
                            localStorage.removeItem('token');
                            localStorage.removeItem('refreshToken');
                            window.location.href = '/login';
                        }}
                    >
                        Logout
                    </button>
                </div>
            </header>

            <main style={styles.main}>
                {/* Stats Cards */}
                <div style={styles.grid}>
                    <div style={styles.card}>
                        <p style={styles.cardTitle}>Requests Today</p>
                        <p style={styles.cardValue}>{state.usage?.requests_today || 0}</p>
                    </div>
                    <div style={styles.card}>
                        <p style={styles.cardTitle}>This Month</p>
                        <p style={styles.cardValue}>{state.usage?.requests_this_month || 0}</p>
                    </div>
                    <div style={styles.card}>
                        <p style={styles.cardTitle}>Monthly Limit</p>
                        <p style={styles.cardValue}>{state.usage?.limits.per_month.toLocaleString() || 0}</p>
                    </div>
                    <div style={styles.card}>
                        <p style={styles.cardTitle}>Remaining</p>
                        <p style={styles.cardValue}>
                            {((state.usage?.limits.per_month || 0) - (state.usage?.requests_this_month || 0)).toLocaleString()}
                        </p>
                    </div>
                </div>

                {/* Search Box */}
                <div style={styles.searchBox}>
                    <h2 style={{ marginBottom: '16px' }}>Analyze Wallet</h2>
                    <div style={{ display: 'flex' }}>
                        <input
                            style={styles.input}
                            type="text"
                            placeholder="Enter wallet address (0x...)"
                            value={searchAddress}
                            onChange={(e) => setSearchAddress(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleAnalyze()}
                        />
                        <button
                            style={styles.button}
                            onClick={handleAnalyze}
                            disabled={isSearching}
                        >
                            {isSearching ? 'Analyzing...' : 'Analyze'}
                        </button>
                    </div>

                    {/* Search Result */}
                    {searchResult && (
                        <div style={{ marginTop: '24px', padding: '20px', background: 'rgba(0,0,0,0.3)', borderRadius: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <span style={{ fontFamily: 'monospace', fontSize: '14px' }}>{searchResult.address}</span>
                                <span style={styles.badge(searchResult.risk_level)}>{searchResult.risk_level}</span>
                            </div>
                            <div style={{ display: 'flex', gap: '40px' }}>
                                <div>
                                    <span style={{ color: '#94a3b8', fontSize: '12px' }}>Risk Score</span>
                                    <p style={{ fontSize: '24px', fontWeight: '700', margin: '4px 0' }}>
                                        {searchResult.risk_score.toFixed(1)}
                                    </p>
                                </div>
                                <div>
                                    <span style={{ color: '#94a3b8', fontSize: '12px' }}>Blocked</span>
                                    <p style={{ fontSize: '24px', fontWeight: '700', margin: '4px 0' }}>
                                        {searchResult.blocked ? '🚫 Yes' : '✅ No'}
                                    </p>
                                </div>
                                <div>
                                    <span style={{ color: '#94a3b8', fontSize: '12px' }}>Chain</span>
                                    <p style={{ fontSize: '24px', fontWeight: '700', margin: '4px 0' }}>
                                        {searchResult.chain.toUpperCase()}
                                    </p>
                                </div>
                            </div>
                            {searchResult.factors.length > 0 && (
                                <div style={{ marginTop: '16px' }}>
                                    <span style={{ color: '#94a3b8', fontSize: '12px' }}>Risk Factors</span>
                                    <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
                                        {searchResult.factors.map((factor, i) => (
                                            <li key={i} style={{ marginBottom: '4px' }}>{factor}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Recent Assessments */}
                <div style={styles.card}>
                    <h2 style={{ marginBottom: '24px' }}>Recent Assessments</h2>
                    <table style={styles.table}>
                        <thead>
                            <tr>
                                <th style={styles.th}>Address</th>
                                <th style={styles.th}>Chain</th>
                                <th style={styles.th}>Score</th>
                                <th style={styles.th}>Level</th>
                                <th style={styles.th}>Blocked</th>
                            </tr>
                        </thead>
                        <tbody>
                            {state.recentAssessments.length === 0 ? (
                                <tr>
                                    <td colSpan={5} style={{ ...styles.td, textAlign: 'center', color: '#94a3b8' }}>
                                        No assessments yet. Try analyzing a wallet above.
                                    </td>
                                </tr>
                            ) : (
                                state.recentAssessments.map((assessment, i) => (
                                    <tr key={i}>
                                        <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: '14px' }}>
                                            {assessment.address.slice(0, 10)}...{assessment.address.slice(-8)}
                                        </td>
                                        <td style={styles.td}>{assessment.chain}</td>
                                        <td style={styles.td}>{assessment.risk_score.toFixed(1)}</td>
                                        <td style={styles.td}>
                                            <span style={styles.badge(assessment.risk_level)}>
                                                {assessment.risk_level}
                                            </span>
                                        </td>
                                        <td style={styles.td}>
                                            {assessment.blocked ? '🚫' : '✅'}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </main>
        </div>
    );
};

export default Dashboard;
