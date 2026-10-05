import { readJson, writeJson } from '../../lib/storage'

export type AuthRole = 'student' | 'teacher'

export type AuthState = {
  token: string | null
  role: AuthRole | null
  phone: string | null
}

const TOKEN_KEY = 'tn_token'
const ROLE_KEY = 'tn_role'
const PHONE_KEY = 'tn_phone'

export function getAuth(): AuthState {
  const token = readJson<string | null>(TOKEN_KEY, null)
  const role = readJson<AuthRole | null>(ROLE_KEY, null)
  const phone = readJson<string | null>(PHONE_KEY, null)
  return { token, role, phone }
}

export function setAuth(token: string, role: AuthRole, phone?: string) {
  writeJson(TOKEN_KEY, token)
  writeJson(ROLE_KEY, role)
  if (phone) writeJson(PHONE_KEY, phone)
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
  localStorage.removeItem(PHONE_KEY)
}

