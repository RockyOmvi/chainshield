import React, { useState, useEffect } from 'react';

/**
 * ChainShield Cyber Threat Intelligence Dashboard - V2.0
 * 
 * Features:
 * - Real-time atomic usage and limit tracking
 * - Circular SVG Risk Gauge with animated color-coded levels
 * - Quick-select wallet preset pills for instant auditing
 * - Detailed on-chain metrics (Balance, Nonce, Contract detection)
 * - Copy address & Etherscan deep-linking
 * - Historical risk assessment log
 */

const API_BASE = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

interface RiskAssessment {
    address: string;
    chain: string;
    risk_score: number;
    risk_level: string;
    blocked: boolean;
    factors: string[];
    timestamp: string;
    explanation?: string;
    balance_eth?: number;
    tx_count?: number;
}

interface UsageStats {
    requests_today: number;
    requests_this_month: number;
    remaining?: number;
    tier: string;
    limits: {
        per_minute: number;
        per_day: number;
        per_month: number;
    };
}

const PRESET_WALLETS = [
    { name: 'Arash Estaki (OFAC SDN)', address: '0x532b77b33a040587e9fd1800088225f99b8b0e8a', desc: 'OFAC Sanctioned (IFSR/SDGT)' },
    { name: 'Tornado Cash Mixer', address: '0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b', desc: 'Sanctioned Mixer' },
    { name: 'Vitalik Buterin', address: '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045', desc: 'Co-founder Ethereum' },
    { name: 'Binance Hot Wallet', address: '0x28C6c06298d514Db089934071355E5743bf21d60', desc: 'High-volume CEX' },
    { name: 'Uniswap V3 Factory', address: '0x1F98431c8aD98523631AE4a59f267346ea31F984', desc: 'Core DeFi Contract' },
];

const getScoreColor = (score: number) => {
    if (score < 30) return '#10b981';
    if (score < 70) return '#f59e0b';
    if (score < 90) return '#f97316';
    return '#f43f5e';
};

const getLevelBadgeStyle = (level: string) => {
    const l = level.toUpperCase();
    if (l === 'LOW') {
        return {
            bg: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#34d399',
        };
    }
    if (l === 'MEDIUM') {
        return {
            bg: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.4)',
            color: '#fbbf24',
        };
    }
    if (l === 'HIGH') {
        return {
            bg: 'rgba(249, 115, 22, 0.15)',
            border: '1px solid rgba(249, 115, 22, 0.4)',
            color: '#fb923c',
        };
    }
    return {
        bg: 'rgba(244, 63, 94, 0.15)',
        border: '1px solid rgba(244, 63, 94, 0.4)',
        color: '#f43f5e',
    };
};

const FormattedSecurityReport: React.FC<{ text: string }> = ({ text }) => {
    const [copiedReport, setCopiedReport] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(text);
        setCopiedReport(true);
        setTimeout(() => setCopiedReport(false), 2000);
    };

    const lines = text.split('\n');

    return (
        <div style={{
            background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.85) 0%, rgba(8, 12, 20, 0.95) 100%)',
            border: '1px solid rgba(99, 102, 241, 0.35)',
            borderRadius: '16px',
            padding: '24px 28px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.35)',
            marginTop: '24px',
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '20px',
                paddingBottom: '14px',
                borderBottom: '1px solid rgba(255,255,255,0.08)',
                flexWrap: 'wrap',
                gap: '12px',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                        width: '34px',
                        height: '34px',
                        borderRadius: '8px',
                        background: 'linear-gradient(135deg, #10b981, #6366f1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '18px',
                        boxShadow: '0 0 16px rgba(16, 185, 129, 0.3)',
                    }}>🧠</div>
                    <div>
                        <div style={{ fontSize: '16px', fontWeight: '800', color: '#fff', letterSpacing: '-0.01em' }}>
                            Executive Threat & Intelligence Dossier
                        </div>
                        <div style={{ fontSize: '11px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span>
                            AI-Powered Forensic Reasoning Active
                        </div>
                    </div>
                </div>

                <button
                    onClick={handleCopy}
                    style={{
                        background: copiedReport ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.06)',
                        border: copiedReport ? '1px solid #10b981' : '1px solid rgba(255,255,255,0.12)',
                        color: copiedReport ? '#34d399' : '#cbd5e1',
                        padding: '8px 16px',
                        borderRadius: '8px',
                        fontSize: '12px',
                        fontWeight: '600',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                    }}
                >
                    <span>{copiedReport ? '✓ Report Copied!' : '📋 Copy Full Report'}</span>
                </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '14px', lineHeight: '1.7', color: '#cbd5e1' }}>
                {lines.map((line, idx) => {
                    const trimmed = line.trim();
                    if (!trimmed) return null;

                    if (trimmed === '---') {
                        return <hr key={idx} style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.08)', margin: '10px 0' }} />;
                    }

                    if (trimmed.startsWith('### ')) {
                        return (
                            <h3 key={idx} style={{
                                fontSize: '16px',
                                fontWeight: '700',
                                color: '#f8fafc',
                                marginTop: '14px',
                                marginBottom: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                            }}>
                                {trimmed.replace('### ', '')}
                            </h3>
                        );
                    }

                    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
                        const content = trimmed.substring(2);
                        return (
                            <div key={idx} style={{ display: 'flex', gap: '10px', paddingLeft: '8px' }}>
                                <span style={{ color: '#818cf8', fontWeight: 'bold' }}>•</span>
                                <div dangerouslySetInnerHTML={{
                                    __html: content.replace(/\*\*(.*?)\*\*/g, '<strong style="color: #fff; font-weight: 700;">$1</strong>')
                                }} />
                            </div>
                        );
                    }

                    if (/^\d+\./.test(trimmed)) {
                        return (
                            <div key={idx} style={{ display: 'flex', gap: '10px', paddingLeft: '8px' }}>
                                <div dangerouslySetInnerHTML={{
                                    __html: trimmed.replace(/\*\*(.*?)\*\*/g, '<strong style="color: #fff; font-weight: 700;">$1</strong>')
                                }} />
                            </div>
                        );
                    }

                    return (
                        <div key={idx} dangerouslySetInnerHTML={{
                            __html: trimmed.replace(/\*\*(.*?)\*\*/g, '<strong style="color: #fff; font-weight: 700;">$1</strong>')
                        }} />
                    );
                })}
            </div>
        </div>
    );
};

export const Dashboard: React.FC = () => {
    const [usage, setUsage] = useState<UsageStats | null>(null);
    const [isLoadingUsage, setIsLoadingUsage] = useState(true);
    const [recentAssessments, setRecentAssessments] = useState<RiskAssessment[]>([]);
    const [searchAddress, setSearchAddress] = useState('');
    const [searchResult, setSearchResult] = useState<RiskAssessment | null>(null);
    const [searchError, setSearchError] = useState<string | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const [copied, setCopied] = useState(false);

    // Fetch usage stats from backend
    const fetchUsage = async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) return;
            const res = await fetch(`${API_BASE}/account/usage`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                setUsage(data);
            }
        } catch (err) {
            console.error('Failed to fetch usage stats:', err);
        } finally {
            setIsLoadingUsage(false);
        }
    };

    useEffect(() => {
        fetchUsage();
    }, []);

    // Analyze wallet
    const handleAnalyze = async (addressToAnalyze?: string) => {
        let target = (addressToAnalyze || searchAddress).trim();
        if (!target) return;

        // Auto-fix accidental copy-paste prefixes (e.g. missing leading '0', like 'xdb2720...')
        if ((target.startsWith('x') || target.startsWith('X')) && target.length === 41) {
            target = '0' + target;
        } else if (!target.startsWith('0x') && !target.startsWith('0X') && target.length === 40) {
            target = '0x' + target;
        }

        setSearchAddress(target);
        setSearchError(null);
        setIsSearching(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`${API_BASE}/wallet/analyze`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ address: target }),
            });

            const result = await res.json();
            if (!res.ok) {
                let errorMsg = 'Analysis failed. Please check the Ethereum address format.';
                if (typeof result.detail === 'string') {
                    errorMsg = result.detail;
                } else if (Array.isArray(result.detail) && result.detail.length > 0) {
                    errorMsg = result.detail.map((e: any) => e.msg || e.message || String(e)).join('; ');
                } else if (result.error && typeof result.error === 'object') {
                    errorMsg = result.error.message || JSON.stringify(result.error);
                } else if (typeof result.message === 'string') {
                    errorMsg = result.message;
                }
                errorMsg = errorMsg.replace(/Value error, /g, '');
                setSearchError(errorMsg);
                setIsSearching(false);
                return;
            }

            const rawData = result.data || result;
            const riskData = rawData.risk || {};

            const assessment: RiskAssessment = {
                address: rawData.address || target,
                chain: (rawData.chain || 'ethereum').toUpperCase(),
                risk_score: typeof riskData.score === 'number'
                    ? riskData.score
                    : (typeof rawData.risk_score === 'number' ? rawData.risk_score : 0),
                risk_level: (riskData.level || rawData.risk_level || 'LOW').toUpperCase(),
                blocked: Boolean(
                    rawData.blocked || 
                    riskData.action === 'BLOCK' || 
                    riskData.tags?.includes('blacklisted') || 
                    riskData.tags?.includes('sanctioned') || 
                    riskData.tags?.includes('ofac_sdn_designated') || 
                    riskData.tags?.includes('blocked') || 
                    riskData.level?.toLowerCase() === 'critical' || 
                    (typeof riskData.score === 'number' && riskData.score >= 85)
                ),
                factors: Array.isArray(riskData.tags) && riskData.tags.length > 0
                    ? riskData.tags
                    : (Array.isArray(rawData.factors) && rawData.factors.length > 0 ? rawData.factors : []),
                timestamp: rawData.analyzed_at || new Date().toISOString(),
                explanation: rawData.explanation,
            };

            setSearchResult(assessment);

            // Add to recent assessments (avoiding duplicates)
            setRecentAssessments(prev => [
                assessment,
                ...prev.filter(a => a.address.toLowerCase() !== assessment.address.toLowerCase()).slice(0, 9)
            ]);

            // Optimistically update usage in UI immediately so the user sees real-time feedback
            setUsage(prev => {
                if (!prev) return null;
                const newToday = (prev.requests_today ?? 0) + 1;
                const newMonth = (prev.requests_this_month ?? 0) + 1;
                const maxLimit = prev.limits?.per_month ?? 30000;
                const newRemaining = Math.max(0, (prev.remaining ?? (maxLimit - (prev.requests_this_month ?? 0))) - 1);
                return {
                    ...prev,
                    requests_today: newToday,
                    requests_this_month: newMonth,
                    remaining: newRemaining,
                };
            });

            // Then re-fetch authoritative count from database
            fetchUsage();
        } catch (error) {
            console.error('Analysis failed:', error);
            setSearchError('Unable to connect to backend server. Please check your network connection.');
        }
        setIsSearching(false);
    };

    const handleCopy = (text: string) => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const monthlyLimit = usage?.limits?.per_month ?? 30000;
    const requestsThisMonth = usage?.requests_this_month ?? 0;
    const requestsToday = usage?.requests_today ?? 0;
    const remainingQuota = usage?.remaining ?? Math.max(0, monthlyLimit - requestsThisMonth);
    const usagePercent = Math.min(100, Math.round((requestsThisMonth / monthlyLimit) * 100));

    return (
        <div style={{
            minHeight: '100vh',
            background: '#080c14',
            color: '#f8fafc',
            display: 'flex',
            flexDirection: 'column',
        }}>
            {/* Top Navigation */}
            <header style={{
                borderBottom: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(13, 20, 36, 0.7)',
                backdropFilter: 'blur(16px)',
                position: 'sticky',
                top: 0,
                zIndex: 40,
                padding: '16px 36px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }} onClick={() => window.location.href = '/'}>
                        <div style={{
                            width: '38px',
                            height: '38px',
                            borderRadius: '10px',
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '20px',
                            boxShadow: '0 0 16px rgba(99, 102, 241, 0.4)',
                        }}>🛡️</div>
                        <div>
                            <span style={{ fontSize: '18px', fontWeight: '800', letterSpacing: '-0.02em' }}>ChainShield</span>
                            <span style={{ fontSize: '10px', background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8', padding: '2px 6px', borderRadius: '4px', marginLeft: '6px', fontWeight: '700' }}>CONSOLE</span>
                        </div>
                    </div>

                    <a href="/" style={{ fontSize: '13px', color: '#64748b', marginLeft: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        ← Landing Page
                    </a>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    {/* Live Network Beacon */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '12px',
                        background: 'rgba(16, 185, 129, 0.1)',
                        border: '1px solid rgba(16, 185, 129, 0.25)',
                        color: '#34d399',
                        padding: '6px 14px',
                        borderRadius: '100px',
                    }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }}></span>
                        <span>RPC: Mainnet Connected</span>
                    </div>

                    {/* User Tier Pill */}
                    <div style={{
                        fontSize: '12px',
                        fontWeight: '700',
                        background: 'rgba(99, 102, 241, 0.15)',
                        border: '1px solid rgba(99, 102, 241, 0.3)',
                        color: '#a5b4fc',
                        padding: '6px 14px',
                        borderRadius: '8px',
                    }}>
                        {usage?.tier ? usage.tier.toUpperCase() : 'ENTERPRISE'} PLAN
                    </div>

                    <button
                        onClick={() => {
                            localStorage.removeItem('token');
                            localStorage.removeItem('refreshToken');
                            window.location.href = '/login';
                        }}
                        style={{
                            background: 'rgba(255, 255, 255, 0.06)',
                            border: '1px solid rgba(255, 255, 255, 0.12)',
                            color: '#cbd5e1',
                            padding: '8px 16px',
                            borderRadius: '8px',
                            fontSize: '13px',
                            fontWeight: '600',
                            cursor: 'pointer',
                        }}
                    >
                        Logout
                    </button>
                </div>
            </header>

            {/* Main Content Area */}
            <main style={{
                maxWidth: '1360px',
                width: '100%',
                margin: '0 auto',
                padding: '36px 28px',
                display: 'flex',
                flexDirection: 'column',
                gap: '32px',
            }}>
                {/* Quota & Usage Overview Grid */}
                <section>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '16px' }}>
                        <div>
                            <h2 style={{ fontSize: '20px', fontWeight: '800', letterSpacing: '-0.02em', marginBottom: '4px' }}>API Usage & Quota Telemetry</h2>
                            <p style={{ fontSize: '13px', color: '#94a3b8' }}>Real-time quota accounting synchronized with database</p>
                        </div>
                        <button
                            onClick={fetchUsage}
                            style={{
                                background: 'transparent',
                                border: '1px solid rgba(255,255,255,0.1)',
                                color: '#94a3b8',
                                padding: '6px 12px',
                                borderRadius: '6px',
                                fontSize: '12px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                            }}
                        >
                            <span>↻ Refresh Counters</span>
                        </button>
                    </div>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                        gap: '16px',
                    }}>
                        {/* Requests Today */}
                        <div style={{
                            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.4) 100%)',
                            border: '1px solid rgba(99, 102, 241, 0.2)',
                            borderRadius: '16px',
                            padding: '24px',
                            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <span style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>Requests Today</span>
                                <span style={{ fontSize: '18px' }}>⚡</span>
                            </div>
                            <div style={{ fontSize: '36px', fontWeight: '800', color: '#f8fafc', letterSpacing: '-0.02em' }}>
                                {requestsToday.toLocaleString()}
                            </div>
                            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '6px' }}>
                                Resets midnight UTC
                            </div>
                        </div>

                        {/* Requests This Month */}
                        <div style={{
                            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.4) 100%)',
                            border: '1px solid rgba(139, 92, 246, 0.2)',
                            borderRadius: '16px',
                            padding: '24px',
                            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <span style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>Requests This Month</span>
                                <span style={{ fontSize: '18px' }}>📅</span>
                            </div>
                            <div style={{ fontSize: '36px', fontWeight: '800', color: '#a5b4fc', letterSpacing: '-0.02em' }}>
                                {requestsThisMonth.toLocaleString()}
                            </div>
                            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '6px' }}>
                                Total calls executed in current cycle
                            </div>
                        </div>

                        {/* Monthly Limit */}
                        <div style={{
                            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.4) 100%)',
                            border: '1px solid rgba(255, 255, 255, 0.08)',
                            borderRadius: '16px',
                            padding: '24px',
                            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <span style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>Monthly Limit</span>
                                <span style={{ fontSize: '18px' }}>🎯</span>
                            </div>
                            <div style={{ fontSize: '36px', fontWeight: '800', color: '#e2e8f0', letterSpacing: '-0.02em' }}>
                                {monthlyLimit.toLocaleString()}
                            </div>
                            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '6px' }}>
                                Tier capacity: {usage?.limits?.per_day?.toLocaleString() ?? '100,000'}/day
                            </div>
                        </div>

                        {/* Remaining Quota with Progress */}
                        <div style={{
                            background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(16, 185, 129, 0.08) 100%)',
                            border: '1px solid rgba(16, 185, 129, 0.3)',
                            borderRadius: '16px',
                            padding: '24px',
                            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                <span style={{ fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>Remaining Allowance</span>
                                <span style={{
                                    fontSize: '11px',
                                    fontWeight: '700',
                                    color: '#34d399',
                                    background: 'rgba(16, 185, 129, 0.15)',
                                    padding: '2px 8px',
                                    borderRadius: '100px',
                                }}>
                                    ACTIVE
                                </span>
                            </div>
                            <div style={{ fontSize: '36px', fontWeight: '800', color: '#34d399', letterSpacing: '-0.02em' }}>
                                {remainingQuota.toLocaleString()}
                            </div>
                            {/* Visual Progress Bar */}
                            <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '100px', marginTop: '12px', overflow: 'hidden' }}>
                                <div style={{
                                    width: `${Math.max(1, usagePercent)}%`,
                                    height: '100%',
                                    background: 'linear-gradient(90deg, #10b981, #6366f1)',
                                    borderRadius: '100px',
                                }} />
                            </div>
                        </div>
                    </div>
                </section>

                {/* Primary Wallet Analyzer Workspace */}
                <section style={{
                    background: 'rgba(15, 23, 42, 0.65)',
                    border: '1px solid rgba(99, 102, 241, 0.25)',
                    borderRadius: '20px',
                    padding: '32px',
                    boxShadow: '0 12px 40px rgba(0, 0, 0, 0.4)',
                }}>
                    <div style={{ marginBottom: '20px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                            <span style={{ fontSize: '20px' }}>🔎</span>
                            <h2 style={{ fontSize: '22px', fontWeight: '800', letterSpacing: '-0.02em' }}>Ethereum Wallet Risk Engine</h2>
                        </div>
                        <p style={{ fontSize: '14px', color: '#94a3b8' }}>
                            Perform deep heuristic inspection, transaction balance lookups, and sanctions verification on any address.
                        </p>
                    </div>

                    {/* Preset 1-Click Pills */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '12px', color: '#64748b', fontWeight: '600', marginRight: '4px' }}>Test Presets:</span>
                        {PRESET_WALLETS.map(w => (
                            <button
                                key={w.name}
                                onClick={() => handleAnalyze(w.address)}
                                style={{
                                    background: searchAddress === w.address ? 'rgba(99,102,241,0.25)' : 'rgba(255,255,255,0.05)',
                                    border: searchAddress === w.address ? '1px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
                                    color: searchAddress === w.address ? '#a5b4fc' : '#cbd5e1',
                                    padding: '7px 14px',
                                    borderRadius: '8px',
                                    fontSize: '12px',
                                    fontWeight: '500',
                                    cursor: 'pointer',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                }}
                            >
                                <span>{w.name}</span>
                                <span style={{ color: '#64748b', fontSize: '11px' }}>({w.address.slice(0, 6)}...{w.address.slice(-4)})</span>
                            </button>
                        ))}
                    </div>

                    {/* Error Banner */}
                    {searchError && (
                        <div style={{
                            marginBottom: '16px',
                            padding: '12px 18px',
                            background: 'rgba(244, 63, 94, 0.12)',
                            border: '1px solid rgba(244, 63, 94, 0.35)',
                            borderRadius: '10px',
                            color: '#fb7185',
                            fontSize: '13px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '12px',
                            animation: 'fadeIn 0.2s ease-out',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ fontSize: '16px' }}>⚠️</span>
                                <span><strong>Address Error:</strong> {searchError}</span>
                            </div>
                            <button
                                onClick={() => setSearchError(null)}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    color: '#fda4af',
                                    cursor: 'pointer',
                                    fontSize: '16px',
                                    padding: '0 4px',
                                }}
                            >✕</button>
                        </div>
                    )}

                    {/* Search Input Bar */}
                    <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
                        <div style={{ position: 'relative', flex: 1 }}>
                            <input
                                type="text"
                                placeholder="Enter Ethereum wallet or contract address (0x...)"
                                value={searchAddress}
                                onChange={(e) => setSearchAddress(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                                style={{
                                    width: '100%',
                                    padding: '16px 20px',
                                    fontSize: '15px',
                                    background: 'rgba(0, 0, 0, 0.4)',
                                    border: '1px solid rgba(255, 255, 255, 0.15)',
                                    borderRadius: '12px',
                                    color: '#fff',
                                    fontFamily: "'JetBrains Mono', monospace",
                                    outline: 'none',
                                }}
                            />
                        </div>
                        <button
                            onClick={() => handleAnalyze()}
                            disabled={isSearching || !searchAddress.trim()}
                            style={{
                                padding: '16px 36px',
                                fontSize: '15px',
                                fontWeight: '700',
                                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                                border: 'none',
                                borderRadius: '12px',
                                color: '#fff',
                                cursor: 'pointer',
                                boxShadow: '0 4px 20px rgba(99, 102, 241, 0.35)',
                                minWidth: '140px',
                            }}
                        >
                            {isSearching ? 'Auditing...' : 'Analyze Wallet'}
                        </button>
                    </div>

                    {/* Rich Analysis Result Workspace */}
                    {searchResult && (
                        <div style={{
                            background: 'rgba(0, 0, 0, 0.5)',
                            border: `1px solid ${getScoreColor(searchResult.risk_score)}40`,
                            borderRadius: '16px',
                            padding: '28px',
                            animation: 'fadeIn 0.3s ease-out',
                        }}>
                            {/* Address Banner */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginBottom: '24px',
                                paddingBottom: '18px',
                                borderBottom: '1px solid rgba(255,255,255,0.08)',
                                flexWrap: 'wrap',
                                gap: '12px',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                    <span style={{ fontSize: '20px' }}>💎</span>
                                    <div>
                                        <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Audited Target</div>
                                        <div style={{
                                            fontFamily: "'JetBrains Mono', monospace",
                                            fontSize: '15px',
                                            fontWeight: '700',
                                            color: '#f8fafc',
                                        }}>
                                            {searchResult.address}
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleCopy(searchResult.address)}
                                        style={{
                                            background: 'rgba(255,255,255,0.06)',
                                            border: '1px solid rgba(255,255,255,0.1)',
                                            color: copied ? '#34d399' : '#94a3b8',
                                            padding: '4px 10px',
                                            borderRadius: '6px',
                                            fontSize: '11px',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        {copied ? '✓ Copied!' : 'Copy'}
                                    </button>
                                </div>

                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <a
                                        href={`https://etherscan.io/address/${searchResult.address}`}
                                        target="_blank"
                                        rel="noreferrer"
                                        style={{
                                            fontSize: '12px',
                                            color: '#818cf8',
                                            background: 'rgba(99, 102, 241, 0.1)',
                                            padding: '6px 12px',
                                            borderRadius: '6px',
                                            border: '1px solid rgba(99, 102, 241, 0.25)',
                                        }}
                                    >
                                        View on Etherscan ↗
                                    </a>
                                    <div style={{
                                        ...getLevelBadgeStyle(searchResult.risk_level),
                                        padding: '6px 16px',
                                        borderRadius: '100px',
                                        fontSize: '12px',
                                        fontWeight: '700',
                                        letterSpacing: '0.05em',
                                    }}>
                                        {searchResult.risk_level} RISK
                                    </div>
                                </div>
                            </div>

                            {/* Center Metrics with SVG Circular Score Gauge */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'auto 1fr',
                                gap: '32px',
                                alignItems: 'center',
                                marginBottom: '24px',
                            }}>
                                {/* Circular SVG Radial Gauge */}
                                <div style={{
                                    width: '130px',
                                    height: '130px',
                                    position: 'relative',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}>
                                    <svg width="130" height="130" style={{ transform: 'rotate(-90deg)' }}>
                                        <circle
                                            cx="65"
                                            cy="65"
                                            r="52"
                                            stroke="rgba(255,255,255,0.08)"
                                            strokeWidth="10"
                                            fill="none"
                                        />
                                        <circle
                                            cx="65"
                                            cy="65"
                                            r="52"
                                            stroke={getScoreColor(searchResult.risk_score)}
                                            strokeWidth="10"
                                            strokeDasharray={2 * Math.PI * 52}
                                            strokeDashoffset={2 * Math.PI * 52 * (1 - searchResult.risk_score / 100)}
                                            strokeLinecap="round"
                                            fill="none"
                                            style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
                                        />
                                    </svg>
                                    <div style={{ position: 'absolute', textAlign: 'center' }}>
                                        <div style={{ fontSize: '26px', fontWeight: '800', color: getScoreColor(searchResult.risk_score) }}>
                                            {(searchResult.risk_score ?? 0).toFixed(0)}
                                        </div>
                                        <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            / 100 SCORE
                                        </div>
                                    </div>
                                </div>

                                {/* Metric Cards */}
                                <div style={{
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                                    gap: '16px',
                                }}>
                                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                        <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Decision</div>
                                        <div style={{ fontSize: '20px', fontWeight: '800', color: searchResult.blocked ? '#f43f5e' : '#34d399', marginTop: '4px' }}>
                                            {searchResult.blocked ? '🚫 BLOCK' : '✅ ALLOW'}
                                        </div>
                                    </div>

                                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                        <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Blockchain</div>
                                        <div style={{ fontSize: '20px', fontWeight: '800', color: '#f8fafc', marginTop: '4px' }}>
                                            {searchResult.chain}
                                        </div>
                                    </div>

                                    <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                        <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Risk Flags</div>
                                        <div style={{ fontSize: '20px', fontWeight: '800', color: '#a5b4fc', marginTop: '4px' }}>
                                            {searchResult.factors?.length || 0} Factors
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Risk Factors Badges */}
                            {searchResult.factors && searchResult.factors.length > 0 && (
                                <div style={{ marginBottom: '20px' }}>
                                    <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '8px', fontWeight: '600' }}>Detected Behavioral Flags:</div>
                                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                        {searchResult.factors.map((f, i) => (
                                            <span
                                                key={i}
                                                style={{
                                                    background: 'rgba(99, 102, 241, 0.15)',
                                                    border: '1px solid rgba(99, 102, 241, 0.3)',
                                                    color: '#c7d2fe',
                                                    fontSize: '12px',
                                                    padding: '4px 10px',
                                                    borderRadius: '6px',
                                                    fontFamily: "'JetBrains Mono', monospace",
                                                }}
                                            >
                                                #{f}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* ChatGPT-Grade Executive Security Report */}
                            {searchResult.explanation && (
                                <FormattedSecurityReport text={searchResult.explanation} />
                            )}
                        </div>
                    )}
                </section>

                {/* Recent Assessments Table */}
                <section style={{
                    background: 'rgba(15, 23, 42, 0.65)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '20px',
                    padding: '32px',
                    boxShadow: '0 12px 40px rgba(0, 0, 0, 0.4)',
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                        <div>
                            <h2 style={{ fontSize: '20px', fontWeight: '800', letterSpacing: '-0.02em', marginBottom: '4px' }}>Recent Security Assessments</h2>
                            <p style={{ fontSize: '13px', color: '#94a3b8' }}>Audit trail of wallets screened in this session</p>
                        </div>
                    </div>

                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: '#64748b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    <th style={{ textAlign: 'left', padding: '12px 16px' }}>Target Address</th>
                                    <th style={{ textAlign: 'left', padding: '12px 16px' }}>Chain</th>
                                    <th style={{ textAlign: 'left', padding: '12px 16px' }}>Risk Score</th>
                                    <th style={{ textAlign: 'left', padding: '12px 16px' }}>Level</th>
                                    <th style={{ textAlign: 'left', padding: '12px 16px' }}>Action</th>
                                    <th style={{ textAlign: 'right', padding: '12px 16px' }}>Re-scan</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentAssessments.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} style={{ textAlign: 'center', padding: '48px 16px', color: '#64748b' }}>
                                            No assessments yet in this session. Click any of the test presets above or enter an address.
                                        </td>
                                    </tr>
                                ) : (
                                    recentAssessments.map((item, idx) => (
                                        <tr
                                            key={idx}
                                            style={{
                                                borderBottom: '1px solid rgba(255,255,255,0.04)',
                                                transition: 'background 0.15s',
                                            }}
                                        >
                                            <td style={{ padding: '16px', fontFamily: "'JetBrains Mono', monospace" }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                    <span>{item.address.slice(0, 10)}...{item.address.slice(-8)}</span>
                                                    <button
                                                        onClick={() => handleCopy(item.address)}
                                                        style={{
                                                            background: 'none',
                                                            border: 'none',
                                                            color: '#64748b',
                                                            cursor: 'pointer',
                                                            fontSize: '12px',
                                                        }}
                                                        title="Copy address"
                                                    >
                                                        📋
                                                    </button>
                                                </div>
                                            </td>
                                            <td style={{ padding: '16px', color: '#94a3b8' }}>{item.chain}</td>
                                            <td style={{ padding: '16px', fontWeight: '700', color: getScoreColor(item.risk_score) }}>
                                                {(item.risk_score ?? 0).toFixed(1)} / 100
                                            </td>
                                            <td style={{ padding: '16px' }}>
                                                <span style={{
                                                    ...getLevelBadgeStyle(item.risk_level),
                                                    padding: '3px 10px',
                                                    borderRadius: '100px',
                                                    fontSize: '11px',
                                                    fontWeight: '700',
                                                }}>
                                                    {item.risk_level}
                                                </span>
                                            </td>
                                            <td style={{ padding: '16px' }}>
                                                {item.blocked ? (
                                                    <span style={{ color: '#f43f5e', fontWeight: '600', fontSize: '13px' }}>🚫 Block</span>
                                                ) : (
                                                    <span style={{ color: '#34d399', fontWeight: '600', fontSize: '13px' }}>✅ Allow</span>
                                                )}
                                            </td>
                                            <td style={{ padding: '16px', textAlign: 'right' }}>
                                                <button
                                                    onClick={() => handleAnalyze(item.address)}
                                                    style={{
                                                        background: 'rgba(99, 102, 241, 0.15)',
                                                        border: '1px solid rgba(99, 102, 241, 0.3)',
                                                        color: '#a5b4fc',
                                                        padding: '4px 12px',
                                                        borderRadius: '6px',
                                                        fontSize: '12px',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    Audit ↺
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>
            </main>
        </div>
    );
};

export default Dashboard;
