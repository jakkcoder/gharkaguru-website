import { createContext, useContext } from 'react'
import type { AuthRole } from './authStore'

export type AuthCtx = {
  token: string | null
  role: AuthRole | null
  login: (token: string, role: AuthRole) => void
  logout: () => void
}

export const AuthContext = createContext<AuthCtx | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}

