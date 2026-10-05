import { useMemo } from 'react'
import { Helmet } from 'react-helmet-async'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getTutor } from '../api/tutors'
import { Button } from '../components/ui/Button'
import { Skeleton } from '../components/ui/Skeleton'
import { addToShortlist, removeFromShortlist } from '../features/shortlist/shortlistStore'
import { useIsShortlisted } from '../features/shortlist/useShortlist'
import { useToast } from '../components/ui/toast/useToast'
import { trackEvent } from '../lib/analytics'

function modeLabel(mode: string) {
  if (mode === 'online') return 'Online'
  if (mode === 'offline') return 'Home tuition'
  return 'Home and online'
}

export function TutorProfilePage() {
  const { tutorId } = useParams()
  const toast = useToast()

  const q = useQuery({
    queryKey: ['tutor', tutorId],
    queryFn: () => getTutor(String(tutorId)),
    enabled: !!tutorId,
  })

  const tutor = q.data
  const shortlisted = useIsShortlisted(tutor?.id ?? '')
  const backToResults = useMemo(() => sessionStorage.getItem('tn_last_search_url') || '/search', [])

  if (q.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-28 w-full rounded-2xl" />
        <Skeleton className="h-40 w-full rounded-2xl" />
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

  const address = tutor.locality || tutor.city

  return (
    <>
      <Helmet>
        <title>
          {tutor.name} - Tutor in {tutor.city} | GharKaGuru
        </title>
        <meta
          name="description"
          content={`${tutor.name} teaches ${tutor.topSubjects.join(', ') || 'home tuition'} in ${address}.`}
        />
        <meta property="og:title" content={`${tutor.name} | GharKaGuru`} />
        <meta property="og:description" content={`${tutor.name}, ${address}`} />
        <meta property="og:type" content="profile" />
        <link rel="canonical" href={`/tutor/${encodeURIComponent(tutor.id)}/${encodeURIComponent(tutor.slug)}`} />
      </Helmet>

      <a className="text-sm font-medium text-tn-primary hover:underline" href={backToResults}>
        ← Back to results
      </a>

      <section className="mt-4 rounded-2xl border border-tn-border bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{tutor.name}</h1>
            <p className="mt-2 text-sm text-tn-muted">{address}</p>
            <p className="mt-2 text-sm text-tn-text">{modeLabel(tutor.mode)}</p>
          </div>
          <Button
            variant="secondary"
            onClick={() => {
              if (shortlisted) {
                removeFromShortlist(tutor.id)
                toast.info('Removed from shortlist')
                trackEvent('shortlist_removed', { tutorId: tutor.id })
              } else {
                addToShortlist(tutor.id)
                toast.success('Saved to shortlist')
                trackEvent('shortlist_added', { tutorId: tutor.id })
              }
            }}
          >
            {shortlisted ? 'Shortlisted' : 'Shortlist'}
          </Button>
        </div>
      </section>

      <section className="mt-6 space-y-6">
        <div className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Profile</h2>
          {tutor.subjects.length ? (
            <p className="mt-3 text-sm text-tn-text">
              <span className="font-medium">Subjects: </span>
              {tutor.subjects.join(', ')}
            </p>
          ) : null}
          {tutor.classes.length ? (
            <p className="mt-2 text-sm text-tn-text">
              <span className="font-medium">Classes: </span>
              {tutor.classes.join(', ')}
            </p>
          ) : null}
          {tutor.bio ? <p className="mt-3 whitespace-pre-line text-sm text-tn-muted">{tutor.bio}</p> : null}
        </div>
      </section>
    </>
  )
}
