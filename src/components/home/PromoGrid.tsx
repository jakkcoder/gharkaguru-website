import { Link } from 'react-router-dom'
import { publicUrl } from '../../lib/publicUrl'

const promos = [
  {
    title: 'Verified tutors near you',
    subtitle: 'Trusted profiles with badges',
    imageUrl: publicUrl('/assets/stock/promo-1.jpg'),
    to: '/search',
  },
  {
    title: 'Online or home tuition',
    subtitle: 'Choose what works for you',
    imageUrl: publicUrl('/assets/stock/promo-2.jpg'),
    to: '/search?mode=Online',
  },
  {
    title: 'Book a demo faster',
    subtitle: 'Send enquiry in minutes',
    imageUrl: publicUrl('/assets/stock/promo-3.jpg'),
    to: '/search',
  },
  {
    title: 'Become a tutor',
    subtitle: 'Apply with OTP + documents',
    imageUrl: publicUrl('/assets/stock/promo-4.jpg'),
    to: '/teacher/register',
  },
]

export function PromoGrid() {
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold">Featured</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {promos.map((p) => (
          <Link
            key={p.title}
            to={p.to}
            className="group relative overflow-hidden rounded-2xl border border-tn-border bg-white shadow-sm transition-shadow hover:shadow-soft"
          >
            <div className="relative h-44 w-full">
              <img
                src={p.imageUrl}
                alt={p.title}
                className="h-44 w-full object-cover"
                loading="lazy"
                decoding="async"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-black/65 via-black/25 to-transparent" />
              <div className="absolute left-5 top-5 max-w-[80%]">
                <div className="text-lg font-semibold text-white">{p.title}</div>
                <div className="mt-1 text-sm text-white/90">{p.subtitle}</div>
                <div className="mt-4 inline-flex rounded-md bg-white/90 px-3 py-2 text-sm font-medium text-tn-text group-hover:bg-white">
                  Explore →
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}

