import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'

// Components
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './components/Dashboard'

// Pages
import Login from './pages/Login'
import Register from './pages/Register'
import NotFound from './pages/NotFound'

/**
 * ChainShield React App
 * 
 * Routes:
 * - /login - Login page
 * - /register - Registration page
 * - /dashboard - Main dashboard (auth required)
 * - /404 - Not found
 */

const App: React.FC = () => {
    return (
        <ErrorBoundary>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="*" element={<NotFound />} />
                </Routes>
            </BrowserRouter>
        </ErrorBoundary>
    )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
