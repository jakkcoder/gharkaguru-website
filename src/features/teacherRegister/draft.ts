import { readJson, writeJson } from '../../lib/storage'

export type TeacherDraft = {
  step: number
  phoneVerified: boolean
  phone?: string
  path?: 'wizard' | 'assist'
  values?: Record<string, unknown>
}

const KEY = 'tn_teacher_draft'

export function readTeacherDraft() {
  return readJson<TeacherDraft | null>(KEY, null)
}

export function writeTeacherDraft(draft: TeacherDraft) {
  writeJson(KEY, draft)
}

export function clearTeacherDraft() {
  localStorage.removeItem(KEY)
}

