import { useMemo, useState } from 'react'
import { Helmet } from 'react-helmet-async'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Star } from 'lucide-react'
import { getTutor } from '../api/tutors'
import { Button } from '../components/ui/Button'
import { Lightbox } from '../components/ui/Lightbox'
import { Skeleton } from '../components/ui/Skeleton'
import { addToShortlist, removeFromShortlist } from '../features/shortlist/shortlistStore'
import { useIsShortlisted } from '../features/shortlist/useShortlist'
import { useToast } from '../components/ui/toast/useToast'
import { trackEvent } from '../lib/analytics'
import { EnquiryModal } from '../features/enquiry/EnquiryModal'
import { getTutorPhotoUrl, normalizePhotoUrl } from '../lib/photo'

export function TutorProfilePage() {
  const { tutorId } = useParams()
  const toast = useToast()
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null)
  const [enquiryOpen, setEnquiryOpen] = useState(false)
  const [bioExpanded, setBioExpanded] = useState(false)

  const q = useQuery({
    queryKey: ['tutor', tutorId],
    queryFn: () => getTutor(String(tutorId)),
    enabled: !!tutorId,
  })

  const tutor = q.data
  const shortlisted = useIsShortlisted(tutor?.id ?? '')

  const backToResults = useMemo(() => {
    return sessionStorage.getItem('tn_last_search_url') || '/search'
  }, [])

  if (q.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  }

  if (!tutor) {
    return (
      <div className="rounded-2xl border border-tn-border bg-white p-8 text-center">
        <h1 className="text-xl font-semibold">Tutor not found</h1>
        <p className="mt-2 text-tn-muted">This tutor profile does not exist.</p>
        <div className="mt-6">
          <a className="text-tn-primary hover:underline" href={backToResults}>
            ← Back to results
          </a>
        </div>
      </div>
    )
  }

  const photoUrl = normalizePhotoUrl(tutor.photoUrl) || getTutorPhotoUrl(tutor.id)

  return (
    <>
      <Helmet>
        <title>
          {tutor.name} - {tutor.topSubjects[0] ?? 'Tutor'} Tutor in {tutor.city} | GharKaGuru
        </title>
        <meta
          name="description"
          content={`${tutor.name} is a ${tutor.topSubjects[0] ?? 'home'} tutor in ${tutor.city}. View qualifications, availability, and reviews on GharKaGuru.`}
        />
        <meta property="og:title" content={`${tutor.name} | GharKaGuru`} />
        <meta
          property="og:description"
          content={`Top subjects: ${tutor.topSubjects.join(', ')}. Rating ${tutor.rating.toFixed(1)}/5.`}
        />
        <meta property="og:image" content={photoUrl} />
        <meta property="og:type" content="profile" />
        <link rel="canonical" href={`/tutor/${encodeURIComponent(tutor.id)}/${encodeURIComponent(tutor.slug)}`} />
      </Helmet>

      <a className="text-sm font-medium text-tn-primary hover:underline" href={backToResults}>
        ← Back to results
      </a>

      <section className="mt-4 rounded-2xl border border-tn-border bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex gap-4">
            <img
              src={photoUrl}
              alt={`${tutor.name} photo`}
              className="h-24 w-24 rounded-full object-cover md:h-[150px] md:w-[150px]"
            />
            <div>
              {tutor.isVerified ? (
                <span className="inline-flex rounded-full bg-tn-success px-2 py-1 text-xs font-medium text-white">
                  Verified
                </span>
              ) : null}
              <h1 className="mt-2 text-2xl font-semibold">{tutor.name}</h1>
              <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-tn-muted">
                <span className="inline-flex items-center gap-1">
                  <Star className="h-4 w-4 fill-tn-warning text-tn-warning" aria-hidden="true" />
                  <span className="font-medium text-tn-text">{tutor.rating.toFixed(1)}/5</span>
                  <span>({tutor.reviewCount} reviews)</span>
                </span>
                <span>•</span>
                <span>
                  ₹{tutor.feeMin}–₹{tutor.feeMax}/hr
                </span>
                <span>•</span>
                <span>
                  Usually responds in{' '}
                  {tutor.responseTimeMins < 60
                    ? '< 1 hour'
                    : `${Math.round(tutor.responseTimeMins / 60)} hours`}
                </span>
              </div>
              <div className="mt-2 text-sm text-tn-muted">
                {tutor.city}, {tutor.locality} • {tutor.distanceKm.toFixed(1)} km
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              onClick={() => {
                trackEvent('contact_clicked', { tutorId: tutor.id })
                setEnquiryOpen(true)
              }}
            >
              Contact Now
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                if (shortlisted) {
                  removeFromShortlist(tutor.id)
                  toast.info('Removed from shortlist')
                  trackEvent('shortlist_removed', { tutorId: tutor.id })
                } else {
                  addToShortlist(tutor.id)
                  toast.success('Saved to shortlist', 'Login to sync later.')
                  trackEvent('shortlist_added', { tutorId: tutor.id })
                }
              }}
            >
              {shortlisted ? 'Shortlisted' : 'Shortlist'}
            </Button>
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">About</h2>
            <p className="mt-2 text-tn-muted">
              {bioExpanded ? tutor.bio : tutor.bio.split(/\s+/).slice(0, 200).join(' ')}
              {tutor.bio.split(/\s+/).length > 200 ? (bioExpanded ? '' : '…') : ''}
            </p>
            {tutor.bio.split(/\s+/).length > 200 ? (
              <button
                type="button"
                className="mt-2 text-sm font-medium text-tn-primary hover:underline"
                onClick={() => setBioExpanded((v) => !v)}
              >
                {bioExpanded ? 'Read less' : 'Read more'}
              </button>
            ) : null}
            <div className="mt-4">
              <div className="text-sm font-medium">Teaching style</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-tn-muted">
                {tutor.teachingStyle.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
            <div className="mt-4">
              <div className="text-sm font-medium">Achievements</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-tn-muted">
                {tutor.achievements.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">Qualifications</h2>
            <div className="mt-3 grid gap-3 text-sm text-tn-muted sm:grid-cols-2">
              <div>10th: {tutor.qualifications.tenthPercent}%</div>
              <div>12th: {tutor.qualifications.twelfthPercent}%</div>
            </div>
            <div className="mt-4">
              <div className="text-sm font-medium">Degrees</div>
              <ul className="mt-2 space-y-1 text-sm text-tn-muted">
                {tutor.qualifications.degrees.map((d) => (
                  <li key={`${d.name}-${d.year}`}>
                    {d.name} • {d.college} • {d.year} • {d.grade}
                  </li>
                ))}
              </ul>
            </div>
            <div className="mt-4">
              <div className="text-sm font-medium">Certifications</div>
              <ul className="mt-2 space-y-1 text-sm text-tn-muted">
                {tutor.qualifications.certifications.map((c) => (
                  <li key={`${c.name}-${c.year}`}>
                    {c.name} • {c.issuer} • {c.year}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">Availability</h2>
            <p className="mt-1 text-sm text-tn-muted">Select a slot to contact this tutor.</p>
            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {tutor.availability.map((s) => (
                <button
                  key={`${s.day}-${s.start}-${s.end}`}
                  type="button"
                  className="rounded-md border border-tn-border bg-white px-3 py-2 text-left text-sm hover:bg-tn-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2"
                  onClick={() => setEnquiryOpen(true)}
                  aria-label={`Select slot ${s.day} ${s.start} to ${s.end}`}
                >
                  <div className="font-medium">{s.day}</div>
                  <div className="text-tn-muted">
                    {s.start}–{s.end}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">Reviews</h2>
            <div className="mt-4 space-y-4">
              {tutor.reviews.slice(0, 8).map((r) => (
                <div key={r.id} className="rounded-xl border border-tn-border bg-white p-4">
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <div className="font-medium">{r.studentName}</div>
                    <div className="text-tn-muted">
                      {new Date(r.dateISO).toLocaleDateString()} • {r.city}
                    </div>
                  </div>
                  <div className="mt-1 text-sm text-tn-muted">Rating: {r.rating.toFixed(1)}/5</div>
                  <p className="mt-2 text-sm text-tn-text">{r.comment}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">Gallery</h2>
            <div className="mt-4 grid grid-cols-3 gap-2">
              {tutor.gallery.slice(0, 6).map((img) => (
                <button
                  key={img}
                  type="button"
                  className="overflow-hidden rounded-xl border border-tn-border bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2"
                  onClick={() => setLightboxIdx(tutor.gallery.indexOf(img))}
                  aria-label="Open image"
                >
                  <img src={img} alt="Tutor gallery image" className="h-24 w-full object-cover" loading="lazy" />
                </button>
              ))}
            </div>
          </div>

          <div className="hidden rounded-2xl border border-tn-border bg-white p-6 lg:block">
            <div className="text-sm text-tn-muted">Sticky CTA (desktop)</div>
            <div className="mt-3 flex gap-2">
              <Button
                className="flex-1"
                onClick={() => {
                  setEnquiryOpen(true)
                }}
              >
                Contact
              </Button>
              <Button
                className="flex-1"
                variant="secondary"
                onClick={() => {
                  if (shortlisted) removeFromShortlist(tutor.id)
                  else addToShortlist(tutor.id)
                  toast.info(shortlisted ? 'Removed from shortlist' : 'Saved to shortlist')
                }}
              >
                {shortlisted ? 'Saved' : 'Shortlist'}
              </Button>
            </div>
          </div>
        </aside>
      </section>

      <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-tn-border bg-white p-3 lg:hidden">
        <div className="mx-auto flex max-w-[1200px] gap-2 px-4">
          <Button
            className="flex-1"
            onClick={() => {
              setEnquiryOpen(true)
            }}
          >
            Contact
          </Button>
          <Button
            className="flex-1"
            variant="secondary"
            onClick={() => {
              if (shortlisted) removeFromShortlist(tutor.id)
              else addToShortlist(tutor.id)
              toast.info(shortlisted ? 'Removed from shortlist' : 'Saved to shortlist')
            }}
          >
            {shortlisted ? 'Saved' : 'Shortlist'}
          </Button>
        </div>
      </div>

      <Lightbox
        open={lightboxIdx !== null}
        onOpenChange={(open) => {
          if (!open) setLightboxIdx(null)
        }}
        images={tutor.gallery}
        index={Math.max(0, lightboxIdx ?? 0)}
        onIndexChange={(idx) => setLightboxIdx(idx)}
      />

      <EnquiryModal
        open={enquiryOpen}
        onOpenChange={setEnquiryOpen}
        tutorId={tutor.id}
        tutorName={tutor.name}
      />
    </>
  )
}

