import { Helmet } from 'react-helmet-async'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Textarea } from '../../components/ui/Textarea'
import { useToast } from '../../components/ui/toast/useToast'
import { useAppForm } from '../../lib/forms'

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
  message: z.string().min(1, 'Message is required').max(500, 'Max 500 characters'),
})

export function ContactPage() {
  const toast = useToast()
  const form = useAppForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', email: '', message: '' },
  })

  return (
    <>
      <Helmet>
        <title>Contact | GharKaGuru</title>
        <meta name="description" content="Contact GharKaGuru support." />
      </Helmet>

      <h1 className="text-2xl font-semibold">Contact</h1>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Send us a message</h2>
          <form
            className="mt-4 space-y-4"
            onSubmit={form.handleSubmit(async (values) => {
              void values
              toast.success('Message sent', 'We’ll get back to you soon. (Mock)')
              form.reset()
            })}
          >
            <div>
              <label className="text-sm font-medium">Name</label>
              <Input className="mt-1" {...form.register('name')} error={!!form.formState.errors.name} />
              {form.formState.errors.name ? (
                <p className="mt-1 text-sm text-tn-error">{form.formState.errors.name.message}</p>
              ) : null}
            </div>
            <div>
              <label className="text-sm font-medium">Email</label>
              <Input className="mt-1" {...form.register('email')} error={!!form.formState.errors.email} />
              {form.formState.errors.email ? (
                <p className="mt-1 text-sm text-tn-error">{form.formState.errors.email.message}</p>
              ) : null}
            </div>
            <div>
              <label className="text-sm font-medium">Message</label>
              <Textarea className="mt-1" rows={6} {...form.register('message')} error={!!form.formState.errors.message} />
              <div className="mt-1 text-right text-xs text-tn-muted">
                {(form.watch('message') ?? '').length}/500
              </div>
              {form.formState.errors.message ? (
                <p className="mt-1 text-sm text-tn-error">{form.formState.errors.message.message}</p>
              ) : null}
            </div>
            <Button type="submit">Submit</Button>
          </form>
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">Business info</h2>
            <div className="mt-3 text-sm text-tn-muted">
              <div>Phone: +9310941052</div>
              <div>Email: support@gharkaguru.com</div>
            </div>
          </div>
        </aside>
      </div>
    </>
  )
}

