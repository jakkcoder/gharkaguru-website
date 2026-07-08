import { publicUrl } from './publicUrl'

function normalizeBase(base: string) {
  const trimmed = base.trim()
  if (!trimmed) return ''
  const noSlash = trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed
  if (noSlash.endsWith('/v1')) return noSlash.slice(0, -3)
  return noSlash
}

// Important: never default to localhost in production.
// When VITE_API_BASE_URL is '/v1' (recommended behind a reverse proxy), normalizeBase() returns ''.
// In that case we intentionally return a same-origin relative URL like '/photo/<id>'.
const defaultBase = ''

export function getTutorPhotoUrl(tutorId: string) {
  const configured = import.meta.env.VITE_API_BASE_URL ?? ''
  const normalized = normalizeBase(configured) || defaultBase
  return `${normalized}/photo/${encodeURIComponent(tutorId)}`
}

function isAbsoluteUrl(raw: string) {
  return /^[a-z][a-z0-9+.-]*:/.test(raw) || raw.startsWith('//')
}

export function normalizePhotoUrl(raw?: string) {
  if (!raw) return ''
  if (raw.startsWith('images/')) return publicUrl(`/${raw}`)
  return raw
}

export function resolveTutorCardPhotoUrl(raw?: string) {
  const normalized = normalizePhotoUrl(raw)
  if (!normalized) return ''

  try {
    const url = new URL(normalized, window.location.origin)
    const path = url.pathname
    if (path.startsWith('/images/teachers/') && !path.startsWith('/images/teachers/thumbs/')) {
      const file = path.split('/').pop()
      if (!file) return normalized
      const thumbPath = publicUrl(`/images/teachers/thumbs/${file}`)
      if (!isAbsoluteUrl(normalized)) return thumbPath
      return `${url.origin}${thumbPath}`
    }
  } catch {
    // If URL parsing fails, keep the original path.
  }

  return normalized
}
