import { Helmet } from 'react-helmet-async'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getTutors } from '../api/tutors'
import { useShortlist } from '../features/shortlist/useShortlist'
import { TutorCard } from '../components/tutors/TutorCard'
import { Button } from '../components/ui/Button'
import { Skeleton } from '../components/ui/Skeleton'

export function ShortlistPage() {
  const ids = useShortlist().tutorIds

  const q = useQuery({
    queryKey: ['shortlist', ids],
    queryFn: () => getTutors({ ids, page: 1, pageSize: 50 }),
    enabled: ids.length > 0,
  })

  return (
    <>
      <Helmet>
        <title>Shortlist | GharKaGuru</title>
        <meta name="description" content="Your shortlisted tutors." />
      </Helmet>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Shortlisted Tutors</h1>
        <Link to="/search" className="text-sm font-medium text-tn-primary hover:underline">
          Find more tutors
        </Link>
      </div>

      <div className="mt-4 rounded-2xl border border-tn-border bg-white p-5">
        <div className="text-sm text-tn-muted">Synced (coming soon)</div>
      </div>

      <div className="mt-6">
        {ids.length === 0 ? (
          <div className="rounded-2xl border border-tn-border bg-white p-10 text-center">
            <h2 className="text-lg font-semibold">No shortlisted tutors yet.</h2>
            <p className="mt-2 text-tn-muted">
              Save tutors from the search results to compare and contact them later.
            </p>
            <div className="mt-6 flex justify-center">
              <Link to="/search">
                <Button>Find tutors</Button>
              </Link>
            </div>
          </div>
        ) : q.isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="rounded-2xl border border-tn-border bg-white p-4">
                <Skeleton className="h-24 w-24 rounded-xl" />
                <Skeleton className="mt-3 h-4 w-1/2" />
                <Skeleton className="mt-2 h-4 w-2/3" />
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {q.data?.items.map((t) => (
              <TutorCard key={t.id} tutor={t} view="list" />
            ))}
          </div>
        )}
      </div>
    </>
  )
}

