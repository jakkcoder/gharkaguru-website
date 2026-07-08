import { Helmet } from 'react-helmet-async'
import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'

export function NotFoundPage() {
  const [q, setQ] = useState('')
  const navigate = useNavigate()

  return (
    <>
      <Helmet>
        <title>404 | GharKaGuru</title>
        <meta name="description" content="Page not found." />
      </Helmet>

      <div className="mx-auto max-w-lg rounded-2xl border border-tn-border bg-white p-8 text-center shadow-soft">
        <div className="text-sm font-medium text-tn-muted">404</div>
        <h1 className="mt-2 text-2xl font-semibold">Page not found</h1>
        <p className="mt-2 text-tn-muted">
          The page you’re looking for doesn’t exist. Try going back to the home page.
        </p>
        <div className="mt-6">
          <div className="text-left text-sm font-medium text-tn-text">Search tutors</div>
          <div className="mt-2 flex gap-2">
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Enter subject or location"
              aria-label="Search tutors"
            />
            <Button
              type="button"
              onClick={() => navigate(q.trim() ? `/search?location=${encodeURIComponent(q.trim())}` : '/search')}
            >
              Search
            </Button>
          </div>
        </div>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            to="/"
          >
            <Button>Go Home</Button>
          </Link>
          <Link
            to="/search"
          >
            <Button variant="secondary">Search Tutors</Button>
          </Link>
        </div>
      </div>
    </>
  )
}

