import { http, HttpResponse, delay } from 'msw'
import type { Enquiry, Paginated, Tutor, TutorSummary } from '../domain/types'
import { tutors } from './data/tutors'

let enquirySeq = 123
let inquirySeq = 321
let teacherSeq = 456
const otpAttempts = new Map<string, number>()
const enquiries: Enquiry[] = []

export const handlers = [
  http.get('/api/health', async () => {
    await delay(250)
    return HttpResponse.json({ ok: true })
  }),

  http.get('/api/tutors', async ({ request }) => {
    await delay(450 + Math.floor(Math.random() * 450))
    const url = new URL(request.url)

    const location = (url.searchParams.get('location') ?? '').trim().toLowerCase()
    const subject = (url.searchParams.get('subject') ?? '').trim().toLowerCase()
    const page = Math.max(1, Number(url.searchParams.get('page') ?? 1))
    const pageSize = Math.max(1, Math.min(50, Number(url.searchParams.get('pageSize') ?? 20)))

    const radiusKm = Number(url.searchParams.get('radiusKm') ?? 10)
    const feeMin = Number(url.searchParams.get('feeMin') ?? 200)
    const feeMax = Number(url.searchParams.get('feeMax') ?? 2000)
    const expMin = Number(url.searchParams.get('expMin') ?? 0)
    const expMax = Number(url.searchParams.get('expMax') ?? 99)
    const ratingMin = Number(url.searchParams.get('ratingMin') ?? 0)
    const gender = (url.searchParams.get('gender') ?? '').toLowerCase()
    const board = (url.searchParams.get('board') ?? '').toLowerCase()
    const mode = (url.searchParams.get('mode') ?? '').toLowerCase()

    const subjectsParam = (url.searchParams.get('subjects') ?? '')
      .split(',')
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean)

    const sort = (url.searchParams.get('sort') ?? 'relevance').toLowerCase()
    const view = (url.searchParams.get('view') ?? 'grid').toLowerCase()
    void view // view is client-side, but accepted for URL completeness

    const idsParam = (url.searchParams.get('ids') ?? '')
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean)

    let list: Tutor[] = tutors

    if (idsParam.length) {
      const idSet = new Set(idsParam)
      list = list.filter((t) => idSet.has(t.id))
    } else {
      if (location) {
        list = list.filter(
          (t) =>
            t.city.toLowerCase().includes(location) || t.locality.toLowerCase().includes(location),
        )
      }
      if (subject) {
        list = list.filter((t) => t.subjects.some((s) => s.toLowerCase() === subject))
      }
      if (subjectsParam.length) {
        list = list.filter((t) =>
          subjectsParam.some((sub) => t.subjects.some((s) => s.toLowerCase() === sub)),
        )
      }

      list = list.filter((t) => t.distanceKm <= radiusKm)
      list = list.filter((t) => t.feeMax >= feeMin && t.feeMin <= feeMax)
      list = list.filter((t) => t.experienceYears >= expMin && t.experienceYears <= expMax)
      list = list.filter((t) => t.rating >= ratingMin)

      if (gender) list = list.filter((t) => t.gender.toLowerCase() === gender)
      if (board) list = list.filter((t) => t.boards.some((b) => b.toLowerCase() === board))
      if (mode) list = list.filter((t) => t.mode.toLowerCase() === mode)
    }

    if (sort === 'rating') list = [...list].sort((a, b) => b.rating - a.rating)
    else if (sort === 'fee') list = [...list].sort((a, b) => a.feeMin - b.feeMin)
    else if (sort === 'experience') list = [...list].sort((a, b) => b.experienceYears - a.experienceYears)
    else if (sort === 'distance') list = [...list].sort((a, b) => a.distanceKm - b.distanceKm)

    const total = list.length
    const start = (page - 1) * pageSize
    const end = start + pageSize

    const items: TutorSummary[] = list.slice(start, end).map((t) => ({
      id: t.id,
      name: t.name,
      slug: t.slug,
      photoUrl: t.photoUrl,
      isVerified: t.isVerified,
      rating: t.rating,
      reviewCount: t.reviewCount,
      subjects: t.subjects,
      topSubjects: t.topSubjects,
      experienceYears: t.experienceYears,
      feeMin: t.feeMin,
      feeMax: t.feeMax,
      city: t.city,
      locality: t.locality,
      distanceKm: t.distanceKm,
      responseTimeMins: t.responseTimeMins,
      boards: t.boards,
      mode: t.mode,
    }))

    const body: Paginated<TutorSummary> = {
      items,
      total,
      page,
      pageSize,
    }

    return HttpResponse.json(body)
  }),

  http.get('/api/tutor/:id', async ({ params }) => {
    await delay(350 + Math.floor(Math.random() * 450))
    const id = String(params.id)
    const tutor = tutors.find((t) => t.id === id)
    if (!tutor) return new HttpResponse(null, { status: 404 })
    return HttpResponse.json(tutor)
  }),

  http.post('/api/auth/otp/send', async ({ request }) => {
    await delay(450)
    const body = (await request.json().catch(() => ({}))) as { phone?: string; role?: 'student' | 'teacher' }
    const phone = body.phone ?? ''
    const count = (otpAttempts.get(phone) ?? 0) + 1
    otpAttempts.set(phone, count)
    return HttpResponse.json({ token: `tn_${crypto.randomUUID()}`, role: body.role ?? 'student' })
  }),

  http.post('/api/enquiry', async ({ request }) => {
    await delay(700)
    const payload = (await request.json().catch(() => ({}))) as {
      tutorId?: string
      student?: { name?: string }
      needs?: { subjects?: string[]; message?: string }
    }
    const tutor = tutors.find((t) => t.id === payload.tutorId)
    if (!tutor) return HttpResponse.json({ message: 'Tutor not found' }, { status: 404 })
    const enquiryId = `ENQ-2026-${String(enquirySeq++).padStart(6, '0')}`
    const item: Enquiry = {
      id: enquiryId,
      tutorId: tutor.id,
      tutorName: tutor.name,
      subject: (payload.needs?.subjects?.[0] ?? tutor.topSubjects[0] ?? 'Subject').toString(),
      createdAtISO: new Date().toISOString(),
      status: 'Pending',
      message: (payload.needs?.message ?? '').toString(),
    }
    enquiries.unshift(item)
    return HttpResponse.json({ enquiryId })
  }),

  http.post('/api/inquiry', async ({ request }) => {
    await delay(500)
    const payload = (await request.json().catch(() => ({}))) as { tutorId?: string; contactPhone?: string }
    if (!payload.tutorId || !payload.contactPhone) {
      return HttpResponse.json({ message: 'Validation error' }, { status: 400 })
    }
    const inquiryId = `INQ-2026-${String(inquirySeq++).padStart(6, '0')}`
    return HttpResponse.json({ inquiryId })
  }),

  http.post('/api/lead-inquiry', async ({ request }) => {
    await delay(500)
    const payload = (await request.json().catch(() => ({}))) as { contactPhone?: string; classLevel?: string; subject?: string }
    if (!payload.contactPhone || !payload.classLevel || !payload.subject) {
      return HttpResponse.json({ message: 'Validation error' }, { status: 400 })
    }
    const inquiryId = `INQ-2026-${String(inquirySeq++).padStart(6, '0')}`
    return HttpResponse.json({ inquiryId })
  }),

  http.get('/api/enquiries', async () => {
    await delay(400)
    return HttpResponse.json({ items: enquiries })
  }),

  http.post('/api/teacher/register', async () => {
    await delay(900)
    const referenceId = `TUT-APP-2026-${String(teacherSeq++).padStart(6, '0')}`
    return HttpResponse.json({ referenceId })
  }),

  http.get('/api/teacher/application', async () => {
    await delay(300)
    return HttpResponse.json({ referenceId: null, status: 'NotStarted', profileCompletionPercent: 0 })
  }),
]

