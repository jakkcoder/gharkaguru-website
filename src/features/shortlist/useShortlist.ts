import { useMemo, useSyncExternalStore } from 'react'
import type { ShortlistState } from './shortlistStore'
import { SHORTLIST_STORAGE_KEY, subscribeShortlist } from './shortlistStore'

const EVT = 'tn_shortlist_changed'
const EMPTY = JSON.stringify({ tutorIds: [] satisfies string[] })

function subscribe(callback: () => void) {
  const unsub = subscribeShortlist(callback)
  const onStorage = (e: StorageEvent) => {
    if (e.key === SHORTLIST_STORAGE_KEY) callback()
  }
  const onCustom = () => callback()
  window.addEventListener('storage', onStorage)
  window.addEventListener(EVT, onCustom)
  return () => {
    unsub()
    window.removeEventListener('storage', onStorage)
    window.removeEventListener(EVT, onCustom)
  }
}

function getSnapshot() {
  // IMPORTANT: Must be referentially stable when unchanged.
  return localStorage.getItem(SHORTLIST_STORAGE_KEY) ?? EMPTY
}

export function useShortlist() {
  const raw = useSyncExternalStore(subscribe, getSnapshot, () => EMPTY)
  return useMemo<ShortlistState>(() => {
    try {
      return JSON.parse(raw) as ShortlistState
    } catch {
      return { tutorIds: [] }
    }
  }, [raw])
}

export function useIsShortlisted(tutorId: string) {
  const s = useShortlist()
  return s.tutorIds.includes(tutorId)
}

