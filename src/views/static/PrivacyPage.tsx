import { Helmet } from 'react-helmet-async'

export function PrivacyPage() {
  return (
    <>
      <Helmet>
        <title>Privacy Policy | GharKaGuru</title>
        <meta
          name="description"
          content="Learn how GharKaGuru collects, uses, and protects your data."
        />
      </Helmet>

      <h1 className="text-2xl font-semibold">Privacy Policy</h1>

      <div className="mt-6 space-y-6">
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Data collection</h2>
          <p className="mt-2 text-tn-muted">
            We collect information you provide such as name, phone number, email, location, and learning preferences to
            help match students with tutors and to communicate about enquiries, sessions, and support.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">How we use your data</h2>
          <p className="mt-2 text-tn-muted">
            We use your information to facilitate tutor discovery, manage bookings, provide customer support, and improve
            our services. We do not sell your personal data to third parties.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Sharing</h2>
          <p className="mt-2 text-tn-muted">
            We may share limited details with tutors or service partners only to deliver the requested tutoring service.
            We may also share data if required by law or to protect the safety of users and the platform.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Cookies notice</h2>
          <p className="mt-2 text-tn-muted">
            We may use cookies/local storage for session tokens and saved drafts. You can clear this data anytime from
            your browser.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Data security</h2>
          <p className="mt-2 text-tn-muted">
            We implement reasonable safeguards to protect your information. No method of transmission or storage is
            completely secure, so we cannot guarantee absolute security.
          </p>
        </section>
        <section className="rounded-2xl border border-tn-border bg-white p-6">
          <h2 className="text-lg font-semibold">Contact</h2>
          <p className="mt-2 text-tn-muted">Email: privacy@gharkaguru.com</p>
        </section>
      </div>
    </>
  )
}

