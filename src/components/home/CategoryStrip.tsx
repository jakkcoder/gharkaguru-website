import { Link } from 'react-router-dom'
import { categoryTiles } from '../../assets/stockImages'

export function CategoryStrip() {
  return (
    <section className="mt-8">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Explore popular categories</h2>
        <Link to="/search" className="text-sm font-medium text-tn-primary hover:underline">
          Browse all
        </Link>
      </div>

      <div className="mt-4 flex gap-4 overflow-x-auto pb-2">
        {categoryTiles.map((c) => {
          const qs = new URLSearchParams({ subject: c.subject, location: 'Delhi' })
          return (
            <Link
              key={c.title}
              to={`/search?${qs.toString()}`}
              className="group min-w-[240px] max-w-[240px] overflow-hidden rounded-2xl border border-tn-border bg-white shadow-sm transition-shadow hover:shadow-soft"
              aria-label={`Browse ${c.title}`}
            >
              <div className="relative h-32 w-full">
                <img
                  src={c.imageUrl}
                  alt={c.title}
                  className="h-32 w-full object-cover"
                  loading="lazy"
                  decoding="async"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/10 to-transparent" />
                <div className="absolute bottom-3 left-3 right-3">
                  <div className="text-sm font-semibold text-white">{c.title}</div>
                  <div className="mt-1 text-xs text-white/90">Tap to see tutors</div>
                </div>
              </div>
              <div className="p-4">
                <div className="text-sm text-tn-muted">Recommended tutors • fast response</div>
              </div>
            </Link>
          )
        })}
      </div>
    </section>
  )
}

