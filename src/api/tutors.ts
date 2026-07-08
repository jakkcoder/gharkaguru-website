import type { Paginated, Tutor, TutorSummary } from '../domain/types'
import { apiGet } from './http'

export type TutorSearchParams = {
  location?: string
  subject?: string
  page?: number
  pageSize?: number
  radiusKm?: number
  subjects?: string[]
  feeMin?: number
  feeMax?: number
  expMin?: number
  expMax?: number
  ratingMin?: number
  gender?: string
  board?: string
  mode?: string
  sort?: string
  ids?: string[]
}

function qs(params: Record<string, string | number | undefined>) {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined) continue
    sp.set(k, String(v))
  }
  const q = sp.toString()
  return q ? `?${q}` : ''
}

export function getTutors(params: TutorSearchParams) {
  return apiGet<Paginated<TutorSummary>>(
    `/api/tutors${qs({
      location: params.location,
      subject: params.subject,
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 20,
      radiusKm: params.radiusKm,
      subjects: params.subjects?.join(','),
      feeMin: params.feeMin,
      feeMax: params.feeMax,
      expMin: params.expMin,
      expMax: params.expMax,
      ratingMin: params.ratingMin,
      gender: params.gender,
      board: params.board,
      mode: params.mode,
      sort: params.sort,
      ids: params.ids?.join(','),
    })}`,
  )
}

export function getTutor(id: string) {
  return apiGet<Tutor>(`/api/tutor/${encodeURIComponent(id)}`)
}

