import React, { createContext, useContext, useState, useCallback } from 'react';

/**
 * Toast Notification System
 * 
 * Context-based toast notifications for success, error, warning, and info messages.
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
    id: string;
    type: ToastType;
    message: string;
    duration: number;
}

interface ToastContextType {
    toasts: Toast[];
    showToast: (message: string, type?: ToastType, duration?: number) => void;
    success: (message: string) => void;
    error: (message: string) => void;
    warning: (message: string) => void;
    info: (message: string) => void;
    removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};

const styles = {
    container: {
        position: 'fixed' as const,
        top: '20px',
        right: '20px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '12px',
        maxWidth: '400px',
    },
    toast: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '16px 20px',
        borderRadius: '12px',
        boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
        animation: 'slideIn 0.3s ease-out',
        minWidth: '300px',
    },
    success: {
        background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.95), rgba(21, 128, 61, 0.95))',
        border: '1px solid rgba(34, 197, 94, 0.5)',
    },
    error: {
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.95), rgba(185, 28, 28, 0.95))',
        border: '1px solid rgba(239, 68, 68, 0.5)',
    },
    warning: {
        background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.95), rgba(161, 98, 7, 0.95))',
        border: '1px solid rgba(234, 179, 8, 0.5)',
    },
    info: {
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.95), rgba(29, 78, 216, 0.95))',
        border: '1px solid rgba(59, 130, 246, 0.5)',
    },
    icon: {
        fontSize: '20px',
    },
    message: {
        flex: 1,
        color: '#fff',
        fontSize: '14px',
        fontWeight: '500' as const,
    },
    closeButton: {
        background: 'none',
        border: 'none',
        color: 'rgba(255,255,255,0.7)',
        cursor: 'pointer',
        fontSize: '18px',
        padding: '0',
        lineHeight: '1',
    },
};

const icons: Record<ToastType, string> = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
};

interface ToastProviderProps {
    children: React.ReactNode;
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const showToast = useCallback((
        message: string,
        type: ToastType = 'info',
        duration: number = 4000
    ) => {
        const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        setToasts(prev => [...prev, { id, type, message, duration }]);

        // Auto-remove after duration
        setTimeout(() => removeToast(id), duration);
    }, [removeToast]);

    const success = useCallback((message: string) => showToast(message, 'success'), [showToast]);
    const error = useCallback((message: string) => showToast(message, 'error', 6000), [showToast]);
    const warning = useCallback((message: string) => showToast(message, 'warning'), [showToast]);
    const info = useCallback((message: string) => showToast(message, 'info'), [showToast]);

    return (
        <ToastContext.Provider value={{ toasts, showToast, success, error, warning, info, removeToast }}>
            {children}
            <div style={styles.container}>
                {toasts.map(toast => (
                    <div
                        key={toast.id}
                        style={{
                            ...styles.toast,
                            ...styles[toast.type],
                        }}
                    >
                        <span style={styles.icon}>{icons[toast.type]}</span>
                        <span style={styles.message}>{toast.message}</span>
                        <button
                            style={styles.closeButton}
                            onClick={() => removeToast(toast.id)}
                        >
                            ×
                        </button>
                    </div>
                ))}
            </div>
            <style>{`
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            `}</style>
        </ToastContext.Provider>
    );
};

export default ToastProvider;
