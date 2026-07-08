import { Helmet } from 'react-helmet-async'

export function TermsPage() {
  return (
    <>
      <Helmet>
        <title>Terms & Conditions | GharKaGuru</title>
        <meta
          name="description"
          content="Read the GharKaGuru terms for using our home tutoring platform and services."
        />
      </Helmet>

      <h1 className="text-2xl font-semibold">Terms & Conditions</h1>

      <div className="mt-6 space-y-6">
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Service overview</h2>
          <p className="mt-2 text-tn-muted">
            GharKaGuru provides home tutoring services by matching students and families with qualified tutors.
            We facilitate discovery, enquiries, and communication to help you find the right tutor and learning plan.
            Service availability, tutor selection, and session scheduling may vary by location and tutor capacity.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Eligibility and accounts</h2>
          <p className="mt-2 text-tn-muted">
            You must provide accurate and complete information when registering or submitting enquiries.
            You are responsible for maintaining the confidentiality of any account credentials and for activities
            that occur under your account.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Bookings and payments</h2>
          <p className="mt-2 text-tn-muted">
            Pricing, session duration, and payment methods are shared during the booking process.
            Any applicable fees, cancellations, or rescheduling policies will be communicated before a session
            is confirmed.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Tutor quality and availability</h2>
          <p className="mt-2 text-tn-muted">
            We aim to connect learners with qualified tutors. However, we do not guarantee the availability
            of specific tutors, subjects, or time slots. Final selection is based on mutual availability and fit.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Acceptable use</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-tn-muted">
            <li>Use the platform lawfully and respectfully.</li>
            <li>Do not share false, misleading, or harmful information.</li>
            <li>Do not attempt to disrupt, misuse, or access data beyond your authorization.</li>
          </ul>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Content and intellectual property</h2>
          <p className="mt-2 text-tn-muted">
            The GharKaGuru name, brand, and platform content are owned by GharKaGuru or its licensors.
            You may not copy, distribute, or create derivative works without permission.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Disclaimer and limitation of liability</h2>
          <p className="mt-2 text-tn-muted">
            The platform is provided on an “as is” basis. We do not guarantee uninterrupted service or specific
            learning outcomes. To the extent permitted by law, GharKaGuru is not liable for indirect or incidental
            damages related to the use of the platform or tutoring services.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Changes to these terms</h2>
          <p className="mt-2 text-tn-muted">
            We may update these terms from time to time. Continued use of the platform after changes means you
            accept the updated terms.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Contact</h2>
          <p className="mt-2 text-tn-muted">Email: legal@gharkaguru.com</p>
        </section>
      </div>
    </>
  )
}

