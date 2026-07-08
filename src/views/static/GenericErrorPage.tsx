import { Helmet } from 'react-helmet-async'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'

export function GenericErrorPage() {
  return (
    <>
      <Helmet>
        <title>Something went wrong | GharKaGuru</title>
        <meta name="description" content="An unexpected error occurred." />
      </Helmet>

      <div className="mx-auto max-w-xl rounded-2xl border border-tn-border bg-white p-8 text-center shadow-soft">
        <div className="text-sm font-medium text-tn-muted">500</div>
        <h1 className="mt-2 text-2xl font-semibold">Something went wrong</h1>
        <p className="mt-2 text-tn-muted">
          This is a simulated error page. Please try again or return to the home page.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link to="/">
            <Button>Go Home</Button>
          </Link>
          <Link to="/search">
            <Button variant="secondary">Search Tutors</Button>
          </Link>
        </div>
      </div>
    </>
  )
}

