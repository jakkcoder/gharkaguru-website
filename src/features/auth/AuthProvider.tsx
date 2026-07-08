import type { ReactNode } from 'react'
import { useCallback, useMemo, useState } from 'react'
import type { AuthRole } from './authStore'
import { clearAuth, getAuth, setAuth } from './authStore'
import { AuthContext, type AuthCtx } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const initial = getAuth()
  const [token, setToken] = useState<string | null>(initial.token)
  const [role, setRole] = useState<AuthRole | null>(initial.role)

  const login = useCallback((t: string, r: AuthRole) => {
    setAuth(t, r)
    setToken(t)
    setRole(r)
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setToken(null)
    setRole(null)
  }, [])

  const value = useMemo<AuthCtx>(() => ({ token, role, login, logout }), [token, role, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

