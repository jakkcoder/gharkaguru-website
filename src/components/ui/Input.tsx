import type { InputHTMLAttributes } from 'react'
import { forwardRef } from 'react'
import { cn } from '../../lib/cn'

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  error?: boolean
}

export const Input = forwardRef<HTMLInputElement, InputProps>(({ className, error, ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        'h-10 w-full rounded-md border bg-white px-3 text-sm text-tn-text placeholder:text-tn-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2 disabled:bg-tn-bg disabled:opacity-60',
        error ? 'border-tn-error' : 'border-tn-border',
        className,
      )}
      {...props}
    />
  )
})

Input.displayName = 'Input'

