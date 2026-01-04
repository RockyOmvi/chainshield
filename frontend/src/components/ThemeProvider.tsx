import React, { createContext, useContext, useState, useEffect } from 'react';

/**
 * Theme Context
 * 
 * Provides dark/light theme switching across the app.
 */

type Theme = 'dark' | 'light' | 'system';

interface ThemeContextType {
    theme: Theme;
    actualTheme: 'dark' | 'light';
    setTheme: (theme: Theme) => void;
    toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
};

// Theme CSS variables
const themes = {
    dark: {
        '--bg-primary': '#0f172a',
        '--bg-secondary': '#1e293b',
        '--bg-card': 'rgba(255,255,255,0.05)',
        '--text-primary': '#ffffff',
        '--text-secondary': '#94a3b8',
        '--border': 'rgba(255,255,255,0.1)',
        '--accent': '#8b5cf6',
        '--accent-gradient': 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    },
    light: {
        '--bg-primary': '#f8fafc',
        '--bg-secondary': '#ffffff',
        '--bg-card': 'rgba(0,0,0,0.02)',
        '--text-primary': '#0f172a',
        '--text-secondary': '#64748b',
        '--border': 'rgba(0,0,0,0.1)',
        '--accent': '#6366f1',
        '--accent-gradient': 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    },
};

interface ThemeProviderProps {
    children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
    const [theme, setThemeState] = useState<Theme>(() => {
        const saved = localStorage.getItem('theme');
        return (saved as Theme) || 'dark';
    });

    const [actualTheme, setActualTheme] = useState<'dark' | 'light'>('dark');

    // Determine actual theme based on system preference
    useEffect(() => {
        const updateActualTheme = () => {
            if (theme === 'system') {
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                setActualTheme(prefersDark ? 'dark' : 'light');
            } else {
                setActualTheme(theme);
            }
        };

        updateActualTheme();

        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', updateActualTheme);

        return () => mediaQuery.removeEventListener('change', updateActualTheme);
    }, [theme]);

    // Apply theme variables to document
    useEffect(() => {
        const root = document.documentElement;
        const themeVars = themes[actualTheme];

        Object.entries(themeVars).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });

        // Update body class for CSS selectors
        document.body.classList.remove('theme-dark', 'theme-light');
        document.body.classList.add(`theme-${actualTheme}`);
    }, [actualTheme]);

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme);
        localStorage.setItem('theme', newTheme);
    };

    const toggleTheme = () => {
        setTheme(actualTheme === 'dark' ? 'light' : 'dark');
    };

    return (
        <ThemeContext.Provider value={{ theme, actualTheme, setTheme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
};

// Theme Toggle Button Component
export const ThemeToggle: React.FC<{ style?: React.CSSProperties }> = ({ style }) => {
    const { actualTheme, toggleTheme } = useTheme();

    return (
        <button
            onClick={toggleTheme}
            style={{
                background: 'none',
                border: 'none',
                fontSize: '20px',
                cursor: 'pointer',
                padding: '8px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                ...style,
            }}
            title={`Switch to ${actualTheme === 'dark' ? 'light' : 'dark'} mode`}
        >
            {actualTheme === 'dark' ? '☀️' : '🌙'}
        </button>
    );
};

export default ThemeProvider;
