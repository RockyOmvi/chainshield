import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'

// Components
import ErrorBoundary from './components/ErrorBoundary'
import AuthGuard from './components/AuthGuard'
import { ToastProvider } from './components/Toast'
import { ThemeProvider } from './components/ThemeProvider'
import Dashboard from './components/Dashboard'

// Pages
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import VerifyEmail from './pages/VerifyEmail'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import Webhooks from './pages/Webhooks'
import AdminDashboard from './pages/AdminDashboard'
import NotFound from './pages/NotFound'

/**
 * ChainShield React App - V2.0
 * 
 * Public Routes:
 * - /login, /register, /forgot-password, /reset-password, /verify-email
 * 
 * Protected Routes:
 * - /dashboard, /profile, /settings, /webhooks, /admin
 */

const App: React.FC = () => {
    return (
        <ErrorBoundary>
            <ThemeProvider>
                <ToastProvider>
                    <BrowserRouter>
                        <Routes>
                            {/* Public Routes */}
                            <Route path="/login" element={<Login />} />
                            <Route path="/register" element={<Register />} />
                            <Route path="/forgot-password" element={<ForgotPassword />} />
                            <Route path="/reset-password" element={<ResetPassword />} />
                            <Route path="/verify-email" element={<VerifyEmail />} />

                            {/* Protected Routes */}
                            <Route path="/" element={
                                <AuthGuard>
                                    <Dashboard />
                                </AuthGuard>
                            } />
                            <Route path="/dashboard" element={
                                <AuthGuard>
                                    <Dashboard />
                                </AuthGuard>
                            } />
                            <Route path="/profile" element={
                                <AuthGuard>
                                    <Profile />
                                </AuthGuard>
                            } />
                            <Route path="/settings" element={
                                <AuthGuard>
                                    <Settings />
                                </AuthGuard>
                            } />
                            <Route path="/webhooks" element={
                                <AuthGuard>
                                    <Webhooks />
                                </AuthGuard>
                            } />
                            <Route path="/admin" element={
                                <AuthGuard>
                                    <AdminDashboard />
                                </AuthGuard>
                            } />

                            {/* 404 */}
                            <Route path="*" element={<NotFound />} />
                        </Routes>
                    </BrowserRouter>
                </ToastProvider>
            </ThemeProvider>
        </ErrorBoundary>
    )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)

