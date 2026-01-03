/**
 * ChainShield Risk Dashboard Component
 * 
 * Real-time monitoring dashboard showing:
 * - Current SLA status
 * - Risk assessment metrics
 * - Recent alerts
 * - System health
 */

import React, { useState, useEffect } from 'react';

// Styles
const styles = {
  dashboard: {
    padding: '24px',
    backgroundColor: '#0f172a',
    minHeight: '100vh',
    color: '#e2e8f0',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '32px',
  },
  title: {
    fontSize: '28px',
    fontWeight: '700',
    background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    borderRadius: '24px',
    fontSize: '14px',
    fontWeight: '500',
  },
  statusOk: {
    backgroundColor: 'rgba(34, 197, 94, 0.15)',
    color: '#22c55e',
  },
  statusWarning: {
    backgroundColor: 'rgba(234, 179, 8, 0.15)',
    color: '#eab308',
  },
  statusCritical: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    color: '#ef4444',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '24px',
    marginBottom: '32px',
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: '16px',
    padding: '24px',
    border: '1px solid #334155',
  },
  cardTitle: {
    fontSize: '14px',
    color: '#94a3b8',
    marginBottom: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  cardValue: {
    fontSize: '36px',
    fontWeight: '700',
    color: '#f1f5f9',
  },
  cardSubtext: {
    fontSize: '14px',
    color: '#64748b',
    marginTop: '4px',
  },
  slaItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 0',
    borderBottom: '1px solid #334155',
  },
  slaName: {
    fontSize: '14px',
    color: '#cbd5e1',
  },
  slaValue: {
    fontSize: '14px',
    fontWeight: '600',
  },
  alertItem: {
    padding: '12px 16px',
    borderRadius: '8px',
    marginBottom: '8px',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
  },
  alertHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '4px',
  },
  alertType: {
    fontSize: '12px',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  alertTime: {
    fontSize: '12px',
    color: '#64748b',
  },
  alertAddress: {
    fontSize: '14px',
    color: '#94a3b8',
    fontFamily: 'monospace',
  },
  walletInput: {
    width: '100%',
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #334155',
    backgroundColor: '#1e293b',
    color: '#e2e8f0',
    fontSize: '14px',
    marginBottom: '16px',
  },
  button: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: 'none',
    background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
    color: 'white',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
  },
};

// Mock data for demonstration
const mockSLAData = [
  { name: 'Uptime', value: 99.95, target: 99.9, unit: '%', status: 'ok' },
  { name: 'Response Time (P95)', value: 245, target: 500, unit: 'ms', status: 'ok' },
  { name: 'Error Rate', value: 0.05, target: 0.1, unit: '%', status: 'ok' },
];

const mockAlerts = [
  { type: 'HIGH_RISK', severity: 'warning', address: '0x8589...FDA16', time: '2 min ago', score: 78 },
  { type: 'BLOCKED', severity: 'critical', address: '0x098B...2f96', time: '5 min ago', score: 100 },
  { type: 'UNUSUAL_PATTERN', severity: 'warning', address: '0xfa42...1847', time: '12 min ago', score: 65 },
];

export default function RiskDashboard() {
  const [systemStatus, setSystemStatus] = useState('ok');
  const [metrics, setMetrics] = useState({
    totalAssessments: 12847,
    blockedAddresses: 37,
    averageScore: 42.3,
    activeChains: 9,
  });
  const [slaData, setSlaData] = useState(mockSLAData);
  const [alerts, setAlerts] = useState(mockAlerts);
  const [walletAddress, setWalletAddress] = useState('');
  const [loading, setLoading] = useState(false);

  // Simulated real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prev => ({
        ...prev,
        totalAssessments: prev.totalAssessments + Math.floor(Math.random() * 5),
      }));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const getStatusStyle = (status) => {
    switch (status) {
      case 'ok': return styles.statusOk;
      case 'warning': return styles.statusWarning;
      case 'critical': return styles.statusCritical;
      default: return styles.statusOk;
    }
  };

  const handleAnalyze = async () => {
    if (!walletAddress) return;
    setLoading(true);
    // API call would go here
    setTimeout(() => setLoading(false), 1500);
  };

  return (
    <div style={styles.dashboard}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>ChainShield Dashboard</h1>
        <div style={{ ...styles.status, ...getStatusStyle(systemStatus) }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: 'currentColor',
          }} />
          {systemStatus === 'ok' ? 'All Systems Operational' : 'Issues Detected'}
        </div>
      </div>

      {/* Metrics Grid */}
      <div style={styles.grid}>
        <div style={styles.card}>
          <div style={styles.cardTitle}>Total Assessments</div>
          <div style={styles.cardValue}>{metrics.totalAssessments.toLocaleString()}</div>
          <div style={styles.cardSubtext}>+127 today</div>
        </div>
        <div style={styles.card}>
          <div style={styles.cardTitle}>Blocked Addresses</div>
          <div style={{ ...styles.cardValue, color: '#ef4444' }}>{metrics.blockedAddresses}</div>
          <div style={styles.cardSubtext}>OFAC Sanctions</div>
        </div>
        <div style={styles.card}>
          <div style={styles.cardTitle}>Average Risk Score</div>
          <div style={{ ...styles.cardValue, color: '#22c55e' }}>{metrics.averageScore}</div>
          <div style={styles.cardSubtext}>Out of 100</div>
        </div>
        <div style={styles.card}>
          <div style={styles.cardTitle}>Active Chains</div>
          <div style={{ ...styles.cardValue, color: '#3b82f6' }}>{metrics.activeChains}</div>
          <div style={styles.cardSubtext}>ETH, BTC, SOL +6</div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* SLA Status */}
        <div style={styles.card}>
          <h2 style={{ fontSize: '18px', marginBottom: '16px' }}>SLA Status</h2>
          {slaData.map((sla, i) => (
            <div key={i} style={styles.slaItem}>
              <span style={styles.slaName}>{sla.name}</span>
              <span style={{
                ...styles.slaValue,
                color: sla.status === 'ok' ? '#22c55e' : '#eab308',
              }}>
                {sla.value}{sla.unit} / {sla.target}{sla.unit}
              </span>
            </div>
          ))}
        </div>

        {/* Recent Alerts */}
        <div style={styles.card}>
          <h2 style={{ fontSize: '18px', marginBottom: '16px' }}>Recent Alerts</h2>
          {alerts.map((alert, i) => (
            <div key={i} style={styles.alertItem}>
              <div style={styles.alertHeader}>
                <span style={{
                  ...styles.alertType,
                  color: alert.severity === 'critical' ? '#ef4444' : '#eab308',
                }}>
                  {alert.type}
                </span>
                <span style={styles.alertTime}>{alert.time}</span>
              </div>
              <div style={styles.alertAddress}>{alert.address} - Score: {alert.score}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Wallet Lookup */}
      <div style={{ ...styles.card, marginTop: '24px' }}>
        <h2 style={{ fontSize: '18px', marginBottom: '16px' }}>Quick Wallet Lookup</h2>
        <div style={{ display: 'flex', gap: '12px' }}>
          <input
            type="text"
            placeholder="Enter wallet address (0x... or bc1...)"
            value={walletAddress}
            onChange={(e) => setWalletAddress(e.target.value)}
            style={{ ...styles.walletInput, flex: 1, marginBottom: 0 }}
          />
          <button
            onClick={handleAnalyze}
            style={styles.button}
            disabled={loading}
          >
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>
      </div>
    </div>
  );
}
