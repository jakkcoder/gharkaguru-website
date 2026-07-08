import { Helmet } from 'react-helmet-async'
import { useQuery } from '@tanstack/react-query'
import { getEnquiries } from '../../api/auth'
import type { Enquiry } from '../../domain/types'

export function StudentDashboardPage() {
  const q = useQuery({
    queryKey: ['enquiries'],
    queryFn: async () => {
      const res = await getEnquiries()
      return (res.items ?? []) as Enquiry[]
    },
  })

  return (
    <>
      <Helmet>
        <title>Student Dashboard | GharKaGuru</title>
        <meta name="description" content="Track your enquiries and shortlisted tutors." />
      </Helmet>

      <h1 className="text-2xl font-semibold">Student Dashboard</h1>
      <div className="mt-3 rounded-2xl border border-tn-border bg-white p-5 text-sm text-tn-muted">
        Dashboard is in beta; full features coming soon.
      </div>

      <section className="mt-6 rounded-2xl border border-tn-border bg-white p-6">
        <h2 className="text-lg font-semibold">My Enquiries</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-tn-muted">
              <tr>
                <th className="py-2">Enquiry ID</th>
                <th className="py-2">Tutor</th>
                <th className="py-2">Subject</th>
                <th className="py-2">Date</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {q.isLoading ? (
                <tr>
                  <td className="py-3 text-tn-muted" colSpan={5}>
                    Loading…
                  </td>
                </tr>
              ) : (q.data ?? []).length === 0 ? (
                <tr>
                  <td className="py-3 text-tn-muted" colSpan={5}>
                    No enquiries yet.
                  </td>
                </tr>
              ) : (
                (q.data ?? []).map((e) => (
                  <tr key={e.id} className="border-t border-tn-border">
                    <td className="py-3 font-medium">{e.id}</td>
                    <td className="py-3">{e.tutorName}</td>
                    <td className="py-3">{e.subject}</td>
                    <td className="py-3 text-tn-muted">{new Date(e.createdAtISO).toLocaleDateString()}</td>
                    <td className="py-3">
                      <span className="rounded-full bg-tn-bg px-2 py-1 text-xs">{e.status}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

