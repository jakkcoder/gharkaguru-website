import type { TextareaHTMLAttributes } from 'react'
import { forwardRef } from 'react'
import { cn } from '../../lib/cn'

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  error?: boolean
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, error, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={cn(
        'w-full rounded-md border bg-white px-3 py-2 text-sm text-tn-text placeholder:text-tn-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2 disabled:bg-tn-bg disabled:opacity-60',
        error ? 'border-tn-error' : 'border-tn-border',
        className,
      )}
      {...props}
    />
  )
})

Textarea.displayName = 'Textarea'

