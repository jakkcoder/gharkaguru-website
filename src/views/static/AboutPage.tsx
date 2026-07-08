import { Helmet } from 'react-helmet-async'

export function AboutPage() {
  return (
    <>
      <Helmet>
        <title>About | GharKaGuru</title>
        <meta name="description" content="Learn about GharKaGuru, our mission, and safety standards." />
      </Helmet>

      <h1 className="text-2xl font-semibold">About GharKaGuru</h1>

      <div className="mt-6 space-y-6">
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Mission</h2>
          <p className="mt-2 text-tn-muted">
            GharKaGuru connects students with trusted home and online tutors using transparent profiles, verified signals,
            and fast enquiry workflows.
          </p>
        </section>

        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Why GharKaGuru</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-tn-muted">
            <li>Search by location, subjects, and preferences.</li>
            <li>Shortlist tutors and compare easily.</li>
            <li>Send enquiries with preferred timing in minutes.</li>
          </ul>
        </section>

        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Safety & verification</h2>
          <p className="mt-2 text-tn-muted">
            Verification badges and document checks help improve trust. (Mocked in this frontend; full workflow will be
            added with the backend.)
          </p>
        </section>

        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">How it works</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
              <div className="text-sm font-medium">1) Search tutors</div>
              <div className="mt-1 text-sm text-tn-muted">Use location + subject filters to find a match.</div>
            </div>
            <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
              <div className="text-sm font-medium">2) Contact & share needs</div>
              <div className="mt-1 text-sm text-tn-muted">Send enquiry with preferred timings and details.</div>
            </div>
            <div className="rounded-xl border border-tn-border bg-tn-bg p-4">
              <div className="text-sm font-medium">3) Start learning</div>
              <div className="mt-1 text-sm text-tn-muted">Schedule a demo and begin classes.</div>
            </div>
          </div>
        </section>
      </div>
    </>
  )
}

