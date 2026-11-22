import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { LoaderCircle } from 'lucide-react'
import { useAuth } from './useAuth'

export function ProtectedRoute() {
  const { session, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <output className="auth-loading"><LoaderCircle className="spin" size={28} /><span>Comprobando sesión...</span></output>
  }

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}

export function PublicOnlyRoute() {
  const { session, loading } = useAuth()

  if (loading) {
    return <output className="auth-loading"><LoaderCircle className="spin" size={28} /><span>Comprobando sesión...</span></output>
  }

  return session ? <Navigate to="/home" replace /> : <Outlet />
}
