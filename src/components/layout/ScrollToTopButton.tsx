import { useEffect, useState } from 'react'
import { ArrowUp } from 'lucide-react'
import { cn } from '../../lib/cn'

export function ScrollToTopButton() {
  const [show, setShow] = useState(false)

  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > 400)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  if (!show) return null

  return (
    <button
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      className={cn(
        'fixed bottom-5 right-5 z-40 inline-flex h-11 w-11 items-center justify-center rounded-full bg-tn-primary text-white shadow-soft',
        'hover:bg-tn-primaryDark focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2',
      )}
      aria-label="Scroll to top"
    >
      <ArrowUp className="h-5 w-5" aria-hidden="true" />
    </button>
  )
}

