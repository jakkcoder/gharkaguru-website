import { readJson, writeJson } from '../../lib/storage'

export const SHORTLIST_STORAGE_KEY = 'tn_shortlist'
const EVT = 'tn_shortlist_changed'

export type ShortlistState = {
  tutorIds: string[]
}

type Listener = () => void
const listeners = new Set<Listener>()

function emit() {
  for (const l of listeners) l()
  // Also broadcast across tabs
  window.dispatchEvent(new Event(EVT))
}

export function getShortlist(): ShortlistState {
  return readJson<ShortlistState>(SHORTLIST_STORAGE_KEY, { tutorIds: [] })
}

export function isShortlisted(tutorId: string): boolean {
  return getShortlist().tutorIds.includes(tutorId)
}

export function subscribeShortlist(listener: Listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function addToShortlist(tutorId: string) {
  const cur = getShortlist()
  if (cur.tutorIds.includes(tutorId)) return
  const next = { tutorIds: [tutorId, ...cur.tutorIds] }
  writeJson(SHORTLIST_STORAGE_KEY, next)
  emit()
}

export function removeFromShortlist(tutorId: string) {
  const cur = getShortlist()
  const next = { tutorIds: cur.tutorIds.filter((id) => id !== tutorId) }
  writeJson(SHORTLIST_STORAGE_KEY, next)
  emit()
}

