import { useEffect, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../utils/supabase'
import { loginWithBackend } from '../services/auth'
import { AuthContext } from './AuthStore'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    supabase.auth.getSession().then(({ data, error }) => {
      if (!mounted) return
      setSession(error ? null : data.session)
      setLoading(false)
    })

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!mounted) return
      setSession(nextSession)
      setLoading(false)
    })

    return () => {
      mounted = false
      data.subscription.unsubscribe()
    }
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const result = await loginWithBackend(email, password)
      const { error } = await supabase.auth.setSession({
        access_token: result.access_token,
        refresh_token: result.refresh_token,
      })
      return { error: error?.message ?? null }
    } catch (error) {
      if (typeof error === 'object' && error !== null && 'response' in error) {
        return { error: 'Credenciales inválidas o servicio no disponible.' }
      }
      return { error: 'No fue posible iniciar sesión.' }
    }
  }

  const logout = async () => {
    const { error } = await supabase.auth.signOut()
    if (!error) setSession(null)
    return { error: error?.message ?? null }
  }

  return (
    <AuthContext.Provider
      value={{ session, user: session?.user ?? null, loading, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}
