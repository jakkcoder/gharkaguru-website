import { Helmet } from 'react-helmet-async'

const faqs = [
  {
    category: 'For Students',
    items: [
      { q: 'How do I find tutors near me?', a: 'Use the search page with location and subject, then refine filters.' },
      { q: 'Are tutors verified?', a: 'Some tutors show a Verified badge. Verification workflow is mocked for now.' },
      { q: 'How do I contact a tutor?', a: 'Open a tutor profile and click “Contact Now” to submit an enquiry.' },
      { q: 'Can I shortlist tutors?', a: 'Yes. Click the heart icon to save tutors to your shortlist.' },
    ],
  },
  {
    category: 'For Tutors',
    items: [
      { q: 'How do I register as a tutor?', a: 'Go to “For Teachers” → complete the registration wizard.' },
      { q: 'What documents are required?', a: 'Aadhaar / PAN / Driving License (mocked uploads in frontend).' },
      { q: 'How do I set my availability?', a: 'Add weekly time slots in the Availability step.' },
    ],
  },
  {
    category: 'General',
    items: [
      { q: 'Is there a mobile app?', a: 'Not yet. This is a mobile-first web experience.' },
      { q: 'How is my data used?', a: 'We use your data to match you with tutors, manage enquiries, and provide support. See the Privacy Policy for details.' },
      { q: 'Where can I report an issue?', a: 'Use the Contact page to send a message.' },
    ],
  },
]

export function FaqPage() {
  return (
    <>
      <Helmet>
        <title>FAQs | GharKaGuru</title>
        <meta name="description" content="Frequently asked questions about GharKaGuru." />
      </Helmet>

      <h1 className="text-2xl font-semibold">FAQs</h1>

      <div className="mt-6 space-y-6">
        {faqs.map((group) => (
          <section key={group.category} className="rounded-2xl border border-tn-border bg-white p-6">
            <h2 className="text-lg font-semibold">{group.category}</h2>
            <div className="mt-4 space-y-3">
              {group.items.map((item) => (
                <details key={item.q} className="rounded-xl border border-tn-border bg-white p-4">
                  <summary className="cursor-pointer text-sm font-medium">{item.q}</summary>
                  <div className="mt-2 text-sm text-tn-muted">{item.a}</div>
                </details>
              ))}
            </div>
          </section>
        ))}
      </div>
    </>
  )
}

