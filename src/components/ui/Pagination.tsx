import { cn } from '../../lib/cn'
import { Button } from './Button'

function range(start: number, end: number) {
  const out: number[] = []
  for (let i = start; i <= end; i++) out.push(i)
  return out
}

function getPages(current: number, totalPages: number) {
  if (totalPages <= 7) return range(1, totalPages)
  const pages = new Set<number>([1, 2, totalPages - 1, totalPages, current - 1, current, current + 1])
  return Array.from(pages)
    .filter((p) => p >= 1 && p <= totalPages)
    .sort((a, b) => a - b)
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  className,
}: {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  className?: string
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const pages = getPages(page, totalPages)

  return (
    <nav className={cn('flex items-center gap-2', className)} aria-label="Pagination">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => onPageChange(Math.max(1, page - 1))}
        disabled={page <= 1}
      >
        Prev
      </Button>

      <div className="flex items-center gap-1">
        {pages.map((p, idx) => {
          const prev = pages[idx - 1]
          const showDots = prev !== undefined && p - prev > 1
          return (
            <span key={p} className="flex items-center gap-1">
              {showDots ? <span className="px-1 text-tn-muted">…</span> : null}
              <button
                type="button"
                onClick={() => onPageChange(p)}
                className={cn(
                  'h-9 min-w-9 rounded-md border px-3 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2',
                  p === page ? 'border-tn-primary bg-tn-bg text-tn-text' : 'border-tn-border bg-white hover:bg-tn-bg',
                )}
                aria-current={p === page ? 'page' : undefined}
              >
                {p}
              </button>
            </span>
          )
        })}
      </div>

      <Button
        variant="secondary"
        size="sm"
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        disabled={page >= totalPages}
      >
        Next
      </Button>
    </nav>
  )
}

