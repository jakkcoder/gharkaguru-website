import { Helmet } from 'react-helmet-async'
import { useQuery } from '@tanstack/react-query'
import { listParentEnquiries } from '../../api/parentEnquiries'
import { EnquiryCard } from '../../features/parentEnquiries/EnquiryCard'

export function ParentEnquiriesPage() {
  const query = useQuery({ queryKey: ['parent-enquiries'], queryFn: listParentEnquiries })
  const items = query.data?.items ?? []

  return (
    <>
      <Helmet>
        <title>Running parent enquiries | GharKaGuru</title>
        <meta name="description" content="Open parent tuition enquiries for registered GharKaGuru tutors." />
      </Helmet>
      <h1 className="text-2xl font-semibold">Running parent enquiries</h1>
      <p className="mt-2 text-sm text-tn-muted">
        These parents are looking for a tutor. The parent phone number stays hidden until the access fee is confirmed.
      </p>
      {query.isLoading ? <p className="mt-6 text-sm text-tn-muted">Loading enquiries…</p> : null}
      {query.isError ? <p className="mt-6 text-sm text-tn-error">Could not load parent enquiries.</p> : null}
      {!query.isLoading && !items.length ? <p className="mt-6 text-sm text-tn-muted">No open parent enquiries right now.</p> : null}
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {items.map((enquiry) => (
          <EnquiryCard key={enquiry.id} enquiry={enquiry} />
        ))}
      </div>
    </>
  )
}
