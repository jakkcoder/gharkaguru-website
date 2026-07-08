function fnv1a32(str: string) {
  let hash = 0x811c9dc5
  for (let i = 0; i < str.length; i += 1) {
    hash ^= str.charCodeAt(i)
    hash = (hash * 0x01000193) >>> 0
  }
  return hash >>> 0
}

export function stableTutorIdFromKey(key: string) {
  const h = fnv1a32(`bot:${key}`).toString(16).padStart(8, '0')
  return `${h}${h}`.slice(0, 8) + '-0000-4000-8000-' + `${h}${h}${h}`.slice(0, 12)
}

export const LEAD_INQUIRY_TUTOR_ID = stableTutorIdFromKey('lead_inquiry')
