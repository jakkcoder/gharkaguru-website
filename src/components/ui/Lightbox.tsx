import { useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Modal } from './Modal'
import { Button } from './Button'

export function Lightbox({
  open,
  onOpenChange,
  images,
  index,
  onIndexChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  images: string[]
  index: number
  onIndexChange: (index: number) => void
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') onIndexChange((index - 1 + images.length) % images.length)
      if (e.key === 'ArrowRight') onIndexChange((index + 1) % images.length)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, index, images.length, onIndexChange])

  const src = images[index]

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Gallery" description="Use arrows to navigate.">
      <div className="flex items-center justify-between gap-2">
        <Button
          type="button"
          variant="secondary"
          onClick={() => onIndexChange((index - 1 + images.length) % images.length)}
          aria-label="Previous image"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          Prev
        </Button>
        <div className="text-sm text-tn-muted">
          {index + 1}/{images.length}
        </div>
        <Button
          type="button"
          variant="secondary"
          onClick={() => onIndexChange((index + 1) % images.length)}
          aria-label="Next image"
        >
          Next
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
      {src ? <img src={src} alt="Tutor gallery image" className="mt-4 w-full rounded-xl" /> : null}
    </Modal>
  )
}

