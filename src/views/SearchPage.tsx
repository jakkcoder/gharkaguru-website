import { useEffect, useMemo } from 'react'
import { Helmet } from 'react-helmet-async'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getTutors } from '../api/tutors'
import { subjects, boards as boardOptions } from '../mocks/data/tutors'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Pagination } from '../components/ui/Pagination'
import { Skeleton } from '../components/ui/Skeleton'
import { TutorCard } from '../components/tutors/TutorCard'
import { trackEvent } from '../lib/analytics'
import { cn } from '../lib/cn'

function num(sp: URLSearchParams, key: string, fallback: number) {
  const raw = sp.get(key)
  const n = raw === null ? NaN : Number(raw)
  return Number.isFinite(n) ? n : fallback
}

function str(sp: URLSearchParams, key: string, fallback = '') {
  return (sp.get(key) ?? fallback).trim()
}

function arr(sp: URLSearchParams, key: string) {
  const raw = (sp.get(key) ?? '').trim()
  if (!raw) return []
  return raw
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
}

export function SearchPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [sp, setSp] = useSearchParams()

  const params = useMemo(() => {
    const location = str(sp, 'location')
    const subject = str(sp, 'subject')
    const page = Math.max(1, num(sp, 'page', 1))
    const pageSize = 20

    return {
      location,
      subject,
      page,
      pageSize,
      radiusKm: num(sp, 'radiusKm', 10),
      subjects: arr(sp, 'subjects'),
      feeMin: num(sp, 'feeMin', 200),
      feeMax: num(sp, 'feeMax', 2000),
      expMin: num(sp, 'expMin', 0),
      expMax: num(sp, 'expMax', 20),
      ratingMin: num(sp, 'ratingMin', 0),
      gender: str(sp, 'gender', 'Any'),
      board: str(sp, 'board', 'Any'),
      mode: str(sp, 'mode', 'Any'),
      sort: str(sp, 'sort', 'relevance'),
      view: (str(sp, 'view', 'grid') as 'grid' | 'list') ?? 'grid',
    }
  }, [sp])

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['tutors', params],
    queryFn: () =>
      getTutors({
        location: params.location || undefined,
        subject: params.subject || undefined,
        page: params.page,
        pageSize: params.pageSize,
        radiusKm: params.radiusKm,
        subjects: params.subjects.length ? params.subjects : undefined,
        feeMin: params.feeMin,
        feeMax: params.feeMax,
        expMin: params.expMin,
        expMax: params.expMax,
        ratingMin: params.ratingMin,
        gender: params.gender !== 'Any' ? params.gender : undefined,
        board: params.board !== 'Any' ? params.board : undefined,
        mode:
          params.mode === 'Home'
            ? 'offline'
            : params.mode === 'Online'
              ? 'online'
              : params.mode === 'Both'
                ? 'both'
                : undefined,
        sort: params.sort,
      }),
  })

  useEffect(() => {
    const url = `${location.pathname}?${sp.toString()}`
    sessionStorage.setItem('tn_last_search_url', url)
  }, [location.pathname, sp])

  const title =
    params.subject && params.location
      ? `${params.subject} Tutors in ${params.location}`
      : 'Find Tutors'

  const onChange = (next: Record<string, string>) => {
    const n = new URLSearchParams(sp)
    Object.entries(next).forEach(([k, v]) => {
      if (!v) n.delete(k)
      else n.set(k, v)
    })
    n.delete('page') // reset to first page on filter changes
    setSp(n, { replace: true })
    trackEvent('filter_applied', next)
  }

  const onClearAll = () => {
    const n = new URLSearchParams()
    if (params.location) n.set('location', params.location)
    if (params.subject) n.set('subject', params.subject)
    setSp(n, { replace: true })
    trackEvent('filter_applied', { clearAll: true })
  }

  const total = data?.total ?? 0
  const page = data?.page ?? params.page
  const pageSize = data?.pageSize ?? params.pageSize
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)

  const chips = useMemo(() => {
    const out: Array<{ key: string; label: string; onRemove: () => void }> = []

    const removeKey = (k: string) => {
      const n = new URLSearchParams(sp)
      n.delete(k)
      n.delete('page')
      setSp(n, { replace: true })
    }

    if (params.radiusKm !== 10) out.push({ key: 'radiusKm', label: `Radius: ${params.radiusKm}km`, onRemove: () => removeKey('radiusKm') })
    if (params.subjects.length) out.push({ key: 'subjects', label: `Subjects: ${params.subjects.join(', ')}`, onRemove: () => removeKey('subjects') })
    if (params.feeMin !== 200 || params.feeMax !== 2000)
      out.push({ key: 'fee', label: `Fee: ₹${params.feeMin}–₹${params.feeMax}`, onRemove: () => { const n = new URLSearchParams(sp); n.delete('feeMin'); n.delete('feeMax'); n.delete('page'); setSp(n, { replace: true }) } })
    if (params.expMin !== 0 || params.expMax !== 20)
      out.push({ key: 'exp', label: `Exp: ${params.expMin}–${params.expMax} yrs`, onRemove: () => { const n = new URLSearchParams(sp); n.delete('expMin'); n.delete('expMax'); n.delete('page'); setSp(n, { replace: true }) } })
    if (params.ratingMin !== 0) out.push({ key: 'ratingMin', label: `Rating: ${params.ratingMin}+`, onRemove: () => removeKey('ratingMin') })
    if (params.gender !== 'Any') out.push({ key: 'gender', label: `Gender: ${params.gender}`, onRemove: () => removeKey('gender') })
    if (params.board !== 'Any') out.push({ key: 'board', label: `Board: ${params.board}`, onRemove: () => removeKey('board') })
    if (params.mode !== 'Any') out.push({ key: 'mode', label: `Mode: ${params.mode}`, onRemove: () => removeKey('mode') })

    return out
  }, [params.board, params.expMax, params.expMin, params.feeMax, params.feeMin, params.gender, params.mode, params.radiusKm, params.ratingMin, params.subjects, setSp, sp])

  return (
    <>
      <Helmet>
        <title>{params.subject && params.location ? `${title} | GharKaGuru` : 'Find Tutors | GharKaGuru'}</title>
        <meta name="description" content="Search tutors by subject and location, then filter by fee, experience, mode, and more." />
      </Helmet>

      <div className="flex flex-col gap-6 lg:flex-row">
        <aside className="w-full rounded-2xl border border-tn-border bg-white p-5 lg:w-[320px] lg:self-start">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">Filters</h2>
            <button type="button" className="text-sm text-tn-primary hover:underline" onClick={onClearAll}>
              Clear all
            </button>
          </div>

          <div className="mt-4 space-y-4">
            <div>
              <label className="text-sm font-medium">Location</label>
              <Input
                className="mt-1"
                value={params.location}
                placeholder="Enter city or area"
                onChange={(e) => onChange({ location: e.target.value })}
              />
            </div>

            <div>
              <label className="text-sm font-medium">Radius ({params.radiusKm} km)</label>
              <input
                className="mt-2 w-full"
                type="range"
                min={5}
                max={50}
                step={1}
                value={params.radiusKm}
                onChange={(e) => onChange({ radiusKm: e.target.value })}
                aria-label="Radius in km"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Subjects</label>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {subjects.slice(0, 8).map((s) => {
                  const checked = params.subjects.includes(s)
                  return (
                    <label key={s} className="flex items-center gap-2 text-sm text-tn-text">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          const next = e.target.checked
                            ? Array.from(new Set([...params.subjects, s]))
                            : params.subjects.filter((x) => x !== s)
                          onChange({ subjects: next.join(',') })
                        }}
                      />
                      <span>{s}</span>
                    </label>
                  )
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">Min fee</label>
                <Input
                  className="mt-1"
                  inputMode="numeric"
                  value={params.feeMin}
                  onChange={(e) => onChange({ feeMin: e.target.value.replace(/[^\d]/g, '') })}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Max fee</label>
                <Input
                  className="mt-1"
                  inputMode="numeric"
                  value={params.feeMax}
                  onChange={(e) => onChange({ feeMax: e.target.value.replace(/[^\d]/g, '') })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">Exp min</label>
                <Input
                  className="mt-1"
                  inputMode="numeric"
                  value={params.expMin}
                  onChange={(e) => onChange({ expMin: e.target.value.replace(/[^\d]/g, '') })}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Exp max</label>
                <Input
                  className="mt-1"
                  inputMode="numeric"
                  value={params.expMax}
                  onChange={(e) => onChange({ expMax: e.target.value.replace(/[^\d]/g, '') })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">Rating</label>
                <select
                  className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm"
                  value={params.ratingMin}
                  onChange={(e) => onChange({ ratingMin: e.target.value })}
                >
                  <option value={0}>Any</option>
                  <option value={3}>3+</option>
                  <option value={4}>4+</option>
                  <option value={4.5}>4.5+</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Board</label>
                <select
                  className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm"
                  value={params.board}
                  onChange={(e) => onChange({ board: e.target.value })}
                >
                  <option>Any</option>
                  {boardOptions.map((b) => (
                    <option key={b}>{b}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">Gender</label>
                <select
                  className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm"
                  value={params.gender}
                  onChange={(e) => onChange({ gender: e.target.value })}
                >
                  <option>Any</option>
                  <option>Male</option>
                  <option>Female</option>
                  <option>Other</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Mode</label>
                <select
                  className="mt-1 h-10 w-full rounded-md border border-tn-border bg-white px-3 text-sm"
                  value={params.mode}
                  onChange={(e) => onChange({ mode: e.target.value })}
                >
                  <option>Any</option>
                  <option>Home</option>
                  <option>Online</option>
                  <option>Both</option>
                </select>
              </div>
            </div>
          </div>
        </aside>

        <section className="min-w-0 flex-1">
          <div className="flex flex-col gap-3 rounded-2xl border border-tn-border bg-white p-5 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-xl font-semibold">{title}</h1>
              <div className="mt-1 text-sm text-tn-muted">
                {isLoading ? 'Loading tutors…' : `Showing ${from}–${to} of ${total} tutors`}
                {isFetching && !isLoading ? <span className="ml-2">(updating…)</span> : null}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                className="h-10 rounded-md border border-tn-border bg-white px-3 text-sm"
                value={params.sort}
                onChange={(e) => onChange({ sort: e.target.value })}
                aria-label="Sort results"
              >
                <option value="relevance">Relevance</option>
                <option value="rating">Rating (high → low)</option>
                <option value="fee">Fee (low → high)</option>
                <option value="experience">Experience (high → low)</option>
                <option value="distance">Distance (near → far)</option>
              </select>

              <div className="inline-flex rounded-md border border-tn-border bg-white p-1">
                <Button
                  variant={params.view === 'grid' ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => {
                    const n = new URLSearchParams(sp)
                    n.set('view', 'grid')
                    setSp(n, { replace: true })
                  }}
                >
                  Grid
                </Button>
                <Button
                  variant={params.view === 'list' ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => {
                    const n = new URLSearchParams(sp)
                    n.set('view', 'list')
                    setSp(n, { replace: true })
                  }}
                >
                  List
                </Button>
              </div>
            </div>
          </div>

          <div className="mt-4">
            {chips.length ? (
              <div className="mb-4 flex flex-wrap items-center gap-2">
                {chips.map((c) => (
                  <button
                    key={c.key}
                    type="button"
                    onClick={c.onRemove}
                    className={cn(
                      'inline-flex items-center gap-2 rounded-full border border-tn-border bg-white px-3 py-1 text-sm text-tn-text hover:bg-tn-bg',
                      'focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2',
                    )}
                    aria-label={`Remove filter ${c.label}`}
                  >
                    <span>{c.label}</span>
                    <span className="text-tn-muted">×</span>
                  </button>
                ))}
                <button
                  type="button"
                  className="ml-1 text-sm font-medium text-tn-primary hover:underline"
                  onClick={onClearAll}
                >
                  Reset filters
                </button>
              </div>
            ) : null}

            {isLoading ? (
              <div className="grid gap-4 md:grid-cols-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="rounded-2xl border border-tn-border bg-white p-4">
                    <Skeleton className="h-40 w-full rounded-xl" />
                    <Skeleton className="mt-3 h-4 w-1/2" />
                    <Skeleton className="mt-2 h-4 w-2/3" />
                    <Skeleton className="mt-4 h-10 w-44" />
                  </div>
                ))}
              </div>
            ) : data && data.items.length === 0 ? (
              <div className="rounded-2xl border border-tn-border bg-white p-10 text-center">
                <h2 className="text-lg font-semibold">No tutors found for your search.</h2>
                <p className="mt-2 text-tn-muted">
                  Try increasing radius, clearing filters, or searching another subject.
                </p>
                <div className="mt-6 flex justify-center gap-3">
                  <Button variant="secondary" onClick={onClearAll}>
                    Clear filters
                  </Button>
                  <Button onClick={() => navigate('/')}>Back to Home</Button>
                </div>
              </div>
            ) : (
              <>
                {isFetching ? (
                  <div className={params.view === 'grid' ? 'grid gap-4 md:grid-cols-2' : 'space-y-4'}>
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div key={i} className="rounded-2xl border border-tn-border bg-white p-4">
                        <Skeleton className={params.view === 'grid' ? 'h-40 w-full rounded-xl' : 'h-24 w-24 rounded-xl'} />
                        <Skeleton className="mt-3 h-4 w-1/2" />
                        <Skeleton className="mt-2 h-4 w-2/3" />
                        <Skeleton className="mt-4 h-10 w-44" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className={params.view === 'grid' ? 'grid gap-4 md:grid-cols-2' : 'space-y-4'}>
                    {data?.items.map((t) => (
                      <TutorCard key={t.id} tutor={t} view={params.view} />
                    ))}
                  </div>
                )}

                {data ? (
                  <Pagination
                    className="mt-6 justify-center"
                    page={data.page}
                    pageSize={data.pageSize}
                    total={data.total}
                    onPageChange={(p) => {
                      const n = new URLSearchParams(sp)
                      n.set('page', String(p))
                      setSp(n, { replace: true })
                      trackEvent('filter_applied', { page: p })
                    }}
                  />
                ) : null}
              </>
            )}
          </div>
        </section>
      </div>
    </>
  )
}

