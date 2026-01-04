import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

/**
 * Auth Guard Component
 * 
 * Protects routes that require authentication.
 * Redirects to login if no token is found.
 */

interface AuthGuardProps {
    children: React.ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
    const location = useLocation();
    const token = localStorage.getItem('token');

    // Check if token exists
    if (!token) {
        // Redirect to login, preserving the intended destination
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Check if token is expired (basic check)
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const exp = payload.exp * 1000; // Convert to milliseconds

        if (Date.now() > exp) {
            // Token expired, clear and redirect
            localStorage.removeItem('token');
            return <Navigate to="/login" state={{ from: location, expired: true }} replace />;
        }
    } catch (e) {
        // Invalid token format, clear and redirect
        localStorage.removeItem('token');
        return <Navigate to="/login" replace />;
    }

    return <>{children}</>;
};

export default AuthGuard;
