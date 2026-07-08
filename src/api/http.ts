import { getAuth } from '../features/auth/authStore'

export class ApiError extends Error {
  status: number
  code?: string
  details?: Record<string, unknown>

  constructor(message: string, status: number, code?: string, details?: Record<string, unknown>) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

function parseErrorEnvelope(text: string, status: number) {
  if (!text) return { message: `Request failed: ${status}` }
  try {
    const json = JSON.parse(text) as { error?: { code?: string; message?: string; details?: Record<string, unknown> } }
    const code = json?.error?.code
    const message = json?.error?.message ?? (code ? `${code}` : undefined)
    const details = json?.error?.details
    return { message: message ?? text, code, details }
  } catch {
    return { message: text }
  }
}

function apiUrl(path: string) {
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').toString().trim()
  if (!base) return path
  const baseNoSlash = base.endsWith('/') ? base.slice(0, -1) : base
  return `${baseNoSlash}${path}`
}

function withAuthHeader(headersInit?: HeadersInit) {
  const headers = new Headers(headersInit)
  if (!headers.has('Authorization')) {
    const token = getAuth().token
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }
  return headers
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...Object.fromEntries(withAuthHeader(init?.headers).entries()),
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const err = parseErrorEnvelope(text, res.status)
    throw new ApiError(err.message, res.status, err.code, err.details)
  }
  return (await res.json()) as T
}

export async function apiPost<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...Object.fromEntries(withAuthHeader(init?.headers).entries()),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const err = parseErrorEnvelope(text, res.status)
    throw new ApiError(err.message, res.status, err.code, err.details)
  }
  return (await res.json()) as T
}

export async function apiPostForm<T>(path: string, form: FormData, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    ...init,
    // Important: don't set Content-Type for multipart; browser will add boundary.
    headers: Object.fromEntries(withAuthHeader(init?.headers).entries()),
    body: form,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const err = parseErrorEnvelope(text, res.status)
    throw new ApiError(err.message, res.status, err.code, err.details)
  }
  return (await res.json()) as T
}

