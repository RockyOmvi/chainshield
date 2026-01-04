import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'

// Components
import ErrorBoundary from './components/ErrorBoundary'
import AuthGuard from './components/AuthGuard'
import { ToastProvider } from './components/Toast'
import Dashboard from './components/Dashboard'

// Pages
import Login from './pages/Login'
import Register from './pages/Register'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import NotFound from './pages/NotFound'

/**
 * ChainShield React App
 * 
 * Routes:
 * - /login - Login page
 * - /register - Registration page
 * - /dashboard - Main dashboard (auth required)
 * - /profile - User profile (auth required)
 * - /settings - User settings (auth required)
 * - /* - Not found
 */

const App: React.FC = () => {
    return (
        <ErrorBoundary>
            <ToastProvider>
                <BrowserRouter>
                    <Routes>
                        <Route path="/login" element={<Login />} />
                        <Route path="/register" element={<Register />} />
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
                        <Route path="*" element={<NotFound />} />
                    </Routes>
                </BrowserRouter>
            </ToastProvider>
        </ErrorBoundary>
    )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
