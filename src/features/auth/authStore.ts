import { readJson, writeJson } from '../../lib/storage'

export type AuthRole = 'student' | 'teacher'

export type AuthState = {
  token: string | null
  role: AuthRole | null
}

const TOKEN_KEY = 'tn_token'
const ROLE_KEY = 'tn_role'

export function getAuth(): AuthState {
  const token = readJson<string | null>(TOKEN_KEY, null)
  const role = readJson<AuthRole | null>(ROLE_KEY, null)
  return { token, role }
}

export function setAuth(token: string, role: AuthRole) {
  writeJson(TOKEN_KEY, token)
  writeJson(ROLE_KEY, role)
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
}

