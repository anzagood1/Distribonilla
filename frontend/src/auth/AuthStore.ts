import { createContext } from 'react'
import type { Session, User } from '@supabase/supabase-js'

export interface AuthContextValue {
  session: Session | null
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<{ error: string | null }>
  logout: () => Promise<{ error: string | null }>
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
