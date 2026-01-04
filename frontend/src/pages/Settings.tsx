import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Settings Page Component
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
        marginBottom: '8px',
    },
    cardDesc: {
        color: '#94a3b8',
        fontSize: '14px',
        marginBottom: '24px',
    },
    settingRow: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 0',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
    },
    settingLabel: {
        color: '#fff',
        fontSize: '15px',
    },
    settingDesc: {
        color: '#94a3b8',
        fontSize: '13px',
        marginTop: '4px',
    },
    toggle: {
        width: '48px',
        height: '26px',
        borderRadius: '13px',
        background: 'rgba(255,255,255,0.2)',
        position: 'relative' as const,
        cursor: 'pointer',
        transition: 'background 0.2s',
    },
    toggleActive: {
        background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    },
    toggleKnob: {
        width: '22px',
        height: '22px',
        borderRadius: '11px',
        background: '#fff',
        position: 'absolute' as const,
        top: '2px',
        left: '2px',
        transition: 'left 0.2s',
    },
    toggleKnobActive: {
        left: '24px',
    },
    select: {
        padding: '10px 16px',
        fontSize: '14px',
        background: 'rgba(255,255,255,0.1)',
        border: '1px solid rgba(255,255,255,0.2)',
        borderRadius: '8px',
        color: '#fff',
        outline: 'none',
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
};

interface Settings {
    emailNotifications: boolean;
    highRiskAlerts: boolean;
    weeklyReport: boolean;
    theme: string;
    language: string;
    timezone: string;
}

const Settings: React.FC = () => {
    const navigate = useNavigate();
    const [settings, setSettings] = useState<Settings>({
        emailNotifications: true,
        highRiskAlerts: true,
        weeklyReport: false,
        theme: 'dark',
        language: 'en',
        timezone: 'UTC',
    });

    const toggleSetting = (key: keyof Settings) => {
        setSettings(prev => ({
            ...prev,
            [key]: !prev[key],
        }));
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        navigate('/login');
    };

    const Toggle: React.FC<{ active: boolean; onClick: () => void }> = ({ active, onClick }) => (
        <div
            style={{ ...styles.toggle, ...(active ? styles.toggleActive : {}) }}
            onClick={onClick}
        >
            <div style={{ ...styles.toggleKnob, ...(active ? styles.toggleKnobActive : {}) }} />
        </div>
    );

    return (
        <div style={styles.container}>
            <header style={styles.header}>
                <a href="/dashboard" style={styles.logo}>
                    <span>🛡️</span>
                    <span>ChainShield</span>
                </a>
                <nav style={styles.nav}>
                    <a href="/dashboard" style={styles.navLink}>Dashboard</a>
                    <a href="/settings" style={{ ...styles.navLink, color: '#8b5cf6' }}>Settings</a>
                    <a href="/profile" style={styles.navLink}>Profile</a>
                    <button
                        onClick={handleLogout}
                        style={{ ...styles.navLink, background: 'none', border: 'none', cursor: 'pointer' }}
                    >
                        Logout
                    </button>
                </nav>
            </header>

            <main style={styles.main}>
                <h1 style={styles.title}>Settings</h1>

                <div style={styles.card}>
                    <h2 style={styles.cardTitle}>Notifications</h2>
                    <p style={styles.cardDesc}>Configure how you want to be notified.</p>

                    <div style={styles.settingRow}>
                        <div>
                            <div style={styles.settingLabel}>Email Notifications</div>
                            <div style={styles.settingDesc}>Receive important updates via email</div>
                        </div>
                        <Toggle
                            active={settings.emailNotifications}
                            onClick={() => toggleSetting('emailNotifications')}
                        />
                    </div>

                    <div style={styles.settingRow}>
                        <div>
                            <div style={styles.settingLabel}>High Risk Alerts</div>
                            <div style={styles.settingDesc}>Get notified when high risk addresses are detected</div>
                        </div>
                        <Toggle
                            active={settings.highRiskAlerts}
                            onClick={() => toggleSetting('highRiskAlerts')}
                        />
                    </div>

                    <div style={{ ...styles.settingRow, borderBottom: 'none' }}>
                        <div>
                            <div style={styles.settingLabel}>Weekly Report</div>
                            <div style={styles.settingDesc}>Receive a weekly summary of your activity</div>
                        </div>
                        <Toggle
                            active={settings.weeklyReport}
                            onClick={() => toggleSetting('weeklyReport')}
                        />
                    </div>
                </div>

                <div style={styles.card}>
                    <h2 style={styles.cardTitle}>Preferences</h2>
                    <p style={styles.cardDesc}>Customize your experience.</p>

                    <div style={styles.settingRow}>
                        <div>
                            <div style={styles.settingLabel}>Theme</div>
                            <div style={styles.settingDesc}>Choose your preferred color scheme</div>
                        </div>
                        <select
                            style={styles.select}
                            value={settings.theme}
                            onChange={e => setSettings(s => ({ ...s, theme: e.target.value }))}
                        >
                            <option value="dark">Dark</option>
                            <option value="light">Light</option>
                            <option value="system">System</option>
                        </select>
                    </div>

                    <div style={styles.settingRow}>
                        <div>
                            <div style={styles.settingLabel}>Language</div>
                            <div style={styles.settingDesc}>Select your preferred language</div>
                        </div>
                        <select
                            style={styles.select}
                            value={settings.language}
                            onChange={e => setSettings(s => ({ ...s, language: e.target.value }))}
                        >
                            <option value="en">English</option>
                            <option value="es">Español</option>
                            <option value="fr">Français</option>
                            <option value="de">Deutsch</option>
                        </select>
                    </div>

                    <div style={{ ...styles.settingRow, borderBottom: 'none' }}>
                        <div>
                            <div style={styles.settingLabel}>Timezone</div>
                            <div style={styles.settingDesc}>Set your local timezone</div>
                        </div>
                        <select
                            style={styles.select}
                            value={settings.timezone}
                            onChange={e => setSettings(s => ({ ...s, timezone: e.target.value }))}
                        >
                            <option value="UTC">UTC</option>
                            <option value="America/New_York">Eastern Time</option>
                            <option value="America/Los_Angeles">Pacific Time</option>
                            <option value="Europe/London">London</option>
                            <option value="Asia/Tokyo">Tokyo</option>
                        </select>
                    </div>
                </div>

                <button style={styles.button}>Save Settings</button>
            </main>
        </div>
    );
};

export default Settings;
