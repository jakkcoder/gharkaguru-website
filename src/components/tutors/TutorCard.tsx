import { Heart } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { TutorSummary } from '../../domain/types'
import { cn } from '../../lib/cn'
import { trackEvent } from '../../lib/analytics'
import { Button } from '../ui/Button'
import { addToShortlist, removeFromShortlist } from '../../features/shortlist/shortlistStore'
import { useIsShortlisted } from '../../features/shortlist/useShortlist'
import { useToast } from '../ui/toast/useToast'

function modeLabel(mode: TutorSummary['mode']) {
  if (mode === 'online') return 'Online'
  if (mode === 'offline') return 'Home tuition'
  return 'Home and online'
}

export function TutorCard({ tutor, view = 'grid' }: { tutor: TutorSummary; view?: 'grid' | 'list' }) {
  const toast = useToast()
  const shortlisted = useIsShortlisted(tutor.id)
  const address = tutor.locality || tutor.city
  const to = `/tutor/${encodeURIComponent(tutor.id)}/${encodeURIComponent(tutor.slug)}`
  const classes = tutor.classes ?? []

  const onToggleShortlist = () => {
    if (shortlisted) {
      removeFromShortlist(tutor.id)
      toast.info('Removed from shortlist')
      trackEvent('shortlist_removed', { tutorId: tutor.id })
    } else {
      addToShortlist(tutor.id)
      toast.success('Saved to shortlist')
      trackEvent('shortlist_added', { tutorId: tutor.id })
    }
  }

  return (
    <div
      className={cn(
        'rounded-2xl border border-tn-border bg-white p-4 shadow-sm transition-shadow hover:shadow-soft',
        view === 'list' && 'flex items-start justify-between gap-4',
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <Link
            to={to}
            className="text-base font-semibold text-tn-text hover:text-tn-primary"
            onClick={() => trackEvent('tutor_profile_viewed', { tutorId: tutor.id })}
          >
            {tutor.name}
          </Link>
          <button
            type="button"
            onClick={onToggleShortlist}
            className="inline-flex h-9 w-9 flex-none items-center justify-center rounded-full border border-tn-border bg-white text-tn-text hover:bg-tn-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2"
            aria-label={shortlisted ? 'Remove from shortlist' : 'Add to shortlist'}
          >
            <Heart className={cn('h-4 w-4', shortlisted ? 'fill-tn-error text-tn-error' : '')} aria-hidden="true" />
          </button>
        </div>
        <p className="mt-1 text-sm text-tn-muted">{address}</p>
        <p className="mt-2 text-sm text-tn-text">{modeLabel(tutor.mode)}</p>
        {classes.length ? <p className="mt-1 text-sm text-tn-muted">Classes: {classes.join(', ')}</p> : null}
        <div className="mt-3 flex flex-wrap gap-2">
          {tutor.topSubjects.map((subject) => (
            <span key={subject} className="rounded-full bg-tn-bg px-3 py-1 text-xs text-tn-text">
              {subject}
            </span>
          ))}
        </div>
        <div className="mt-4">
          <Link to={to} className="inline-flex">
            <Button variant="secondary" type="button">
              View Profile
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
