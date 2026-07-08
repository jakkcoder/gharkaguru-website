import { Heart, Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useState } from 'react'
import type { TutorSummary } from '../../domain/types'
import { cn } from '../../lib/cn'
import { trackEvent } from '../../lib/analytics'
import { Button } from '../ui/Button'
import { addToShortlist, removeFromShortlist } from '../../features/shortlist/shortlistStore'
import { useIsShortlisted } from '../../features/shortlist/useShortlist'
import { useToast } from '../ui/toast/useToast'
import { EnquiryModal } from '../../features/enquiry/EnquiryModal'
import { getTutorPhotoUrl, resolveTutorCardPhotoUrl } from '../../lib/photo'

export function TutorCard({ tutor, view = 'grid' }: { tutor: TutorSummary; view?: 'grid' | 'list' }) {
  const toast = useToast()
  const [enquiryOpen, setEnquiryOpen] = useState(false)
  const shortlisted = useIsShortlisted(tutor.id)

  const resolvedPhotoUrl = (() => {
    const raw = tutor.photoUrl
    if (!raw) return getTutorPhotoUrl(tutor.id)
    const resolved = resolveTutorCardPhotoUrl(raw)
    return resolved || raw
  })()

  const onToggleShortlist = () => {
    if (shortlisted) {
      removeFromShortlist(tutor.id)
      toast.info('Removed from shortlist')
      trackEvent('shortlist_removed', { tutorId: tutor.id })
    } else {
      addToShortlist(tutor.id)
      toast.success('Saved to shortlist', 'Login to sync later.')
      trackEvent('shortlist_added', { tutorId: tutor.id })
    }
  }

  const to = `/tutor/${encodeURIComponent(tutor.id)}/${encodeURIComponent(tutor.slug)}`

  return (
    <div
      className={cn(
        'group rounded-2xl border border-tn-border bg-white p-3 shadow-sm transition-shadow hover:shadow-soft',
        view === 'list' && 'flex gap-4',
      )}
    >
      <div
        className={cn(
          'relative overflow-hidden rounded-xl bg-white',
          view === 'list' ? 'h-24 w-24 flex-none' : 'h-32 w-full',
        )}
      >
        <img
          src={resolvedPhotoUrl}
          alt={`${tutor.name} photo`}
          className={cn(
            // After preprocessing, thumbnails are card-shaped: fill nicely.
            'h-full w-full object-cover object-[50%_20%]',
            view === 'list' ? 'aspect-square' : '',
          )}
          loading="lazy"
        />
        {tutor.isVerified ? (
          <span className="absolute left-2 top-2 rounded-full bg-tn-success px-2 py-1 text-xs font-medium text-white">
            Verified
          </span>
        ) : null}
        <button
          type="button"
          onClick={onToggleShortlist}
          className="absolute right-2 top-2 inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-tn-text shadow-sm hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2"
          aria-label={shortlisted ? 'Remove from shortlist' : 'Add to shortlist'}
        >
          <Heart className={cn('h-4 w-4', shortlisted ? 'fill-tn-error text-tn-error' : '')} aria-hidden="true" />
        </button>
      </div>

      <div className={cn('mt-2', view === 'list' && 'mt-0 flex-1')}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <Link
              to={to}
              className="text-base font-semibold text-tn-text hover:text-tn-primary"
              onClick={() => trackEvent('tutor_profile_viewed', { tutorId: tutor.id })}
            >
              {tutor.name}
            </Link>
            <div className="mt-1 flex items-center gap-2 text-sm text-tn-muted">
              <span className="inline-flex items-center gap-1">
                <Star className="h-4 w-4 fill-tn-warning text-tn-warning" aria-hidden="true" />
                <span className="font-medium text-tn-text">{tutor.rating.toFixed(1)}</span>
                <span>({tutor.reviewCount})</span>
              </span>
              <span>•</span>
              <span>{tutor.experienceYears} yrs exp</span>
              <span>•</span>
              <span>
                ₹{tutor.feeMin}–₹{tutor.feeMax}/hr
              </span>
            </div>
          </div>
          <div className="text-right text-sm text-tn-muted">
            <div>
              {tutor.city}, {tutor.locality}
            </div>
            <div>{tutor.distanceKm.toFixed(1)} km</div>
          </div>
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          {tutor.topSubjects.map((s) => (
            <span key={s} className="rounded-full bg-tn-bg px-3 py-1 text-xs text-tn-text">
              {s}
            </span>
          ))}
        </div>

        <div className="mt-3 flex gap-2">
          <Button
            type="button"
            onClick={() => {
              trackEvent('contact_clicked', { tutorId: tutor.id })
              setEnquiryOpen(true)
            }}
          >
            Contact Now
          </Button>
          <Link to={to} className="inline-flex">
            <Button variant="secondary" type="button">
              View Profile
            </Button>
          </Link>
        </div>
      </div>

      <EnquiryModal
        open={enquiryOpen}
        onOpenChange={setEnquiryOpen}
        tutorId={tutor.id}
        tutorName={tutor.name}
      />
    </div>
  )
}

