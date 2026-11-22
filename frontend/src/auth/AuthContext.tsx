import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { isAxiosError } from 'axios'
import { supabase } from '../utils/supabase'
import { loginWithBackend, type LoginResponse } from '../services/auth'
import { classifyLoginError, getLoginErrorMessage } from '../utils/loginErrors'
import { AuthContext } from './AuthStore'

export function AuthProvider({ children }: { readonly children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    let hasAuthEvent = false

    const { data } = supabase.auth.onAuthStateChange((event, nextSession) => {
      // A late startup snapshot cannot replace an auth event we already handled.
      if (!mounted || (event === 'INITIAL_SESSION' && hasAuthEvent)) return
      hasAuthEvent = true
      setSession(nextSession)
      setLoading(false)
    })

    supabase.auth.getSession().then(({ data, error }) => {
      if (!mounted || hasAuthEvent) return
      setSession(error ? null : data.session)
      setLoading(false)
    }).catch(() => {
      if (mounted && !hasAuthEvent) setLoading(false)
    })

    return () => {
      mounted = false
      data.subscription.unsubscribe()
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const fallback = getLoginErrorMessage('unexpected', 'es')
    let result: LoginResponse

    try {
      result = await loginWithBackend(email, password)
    } catch (error) {
      const category = isAxiosError(error)
        ? classifyLoginError(error.response?.status, error.code)
        : 'unexpected'
      return { error: getLoginErrorMessage(category, 'es') }
    }

    if (
      typeof result?.access_token !== 'string' || !result.access_token ||
      typeof result?.refresh_token !== 'string' || !result.refresh_token
    ) {
      return { error: fallback }
    }

    try {
      const { error } = await supabase.auth.setSession({
        access_token: result.access_token,
        refresh_token: result.refresh_token,
      })
      return { error: error ? fallback : null }
    } catch {
      return { error: fallback }
    }
  }, [])

  const logout = useCallback(async () => {
    const { error } = await supabase.auth.signOut()
    if (!error) setSession(null)
    return { error: error?.message ?? null }
  }, [])

  const contextValue = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      loading,
      login,
      logout,
    }),
    [session, loading, login, logout],
  )

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  )
}
