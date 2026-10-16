import { useEffect, useState } from 'react'
import {
  BadgeIndianRupee, BookOpen, CalendarDays, FileBadge, GraduationCap,
  RefreshCw, Users,
} from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/ui.jsx'
import { formatInrMinorUnits, loadDashboard } from '../lib/adminData.js'

const metrics = [
  { key: 'students', label: 'Total students', icon: Users, format: (value) => value.toLocaleString('en-IN'), tone: 'orange' },
  { key: 'programs', label: 'Active programs', icon: BookOpen, format: (value) => value.toLocaleString('en-IN'), tone: 'green' },
  { key: 'batches', label: 'Active batches', icon: CalendarDays, format: (value) => value.toLocaleString('en-IN'), tone: 'blue' },
  { key: 'collected', label: 'Collected fees', icon: BadgeIndianRupee, format: formatInrMinorUnits, tone: 'green' },
  { key: 'outstanding', label: 'Outstanding fees', icon: BadgeIndianRupee, format: formatInrMinorUnits, tone: 'amber' },
  { key: 'completed', label: 'Completed internships', icon: GraduationCap, format: (value) => value.toLocaleString('en-IN'), tone: 'blue' },
  { key: 'certificates', label: 'Issued certificates', icon: FileBadge, format: (value) => value.toLocaleString('en-IN'), tone: 'orange' },
]

const toneClasses = {
  orange: 'bg-orange-50 text-orange-700',
  green: 'bg-emerald-50 text-emerald-700',
  blue: 'bg-sky-50 text-sky-700',
  amber: 'bg-amber-50 text-amber-800',
}

function displayDate(value) {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(value))
}

export default function DashboardPage() {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    loadDashboard(token)
      .then((result) => { if (active) setData(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Dashboard data could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, reloadKey])

  const columns = [
    { key: 'enrollment_number', label: 'Enrollment' },
    { key: 'student', label: 'Student', render: (row) => <span>{row.student.full_name}<span className="ml-2 text-xs text-muted">{row.student.student_number}</span></span> },
    { key: 'program', label: 'Program', render: (row) => row.program.name },
    { key: 'batch', label: 'Batch', render: (row) => row.batch?.name || 'Not assigned' },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'created_at', label: 'Created', render: (row) => displayDate(row.created_at) },
  ]

  return (
    <div className="animate-enter">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Workspace</p>
          <h1 className="mt-2 font-display text-4xl text-ink">Overview</h1>
          <p className="mt-2 text-sm text-muted">Current operational and fee-summary data.</p>
        </div>
        <Button variant="secondary" onClick={() => setReloadKey((key) => key + 1)} disabled={loading}>
          <RefreshCw aria-hidden="true" className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {loading ? <LoadingState label="Loading dashboard data" /> : error ? (
        <ErrorState title="Dashboard data could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} />
      ) : (
        <>
          <section aria-label="Operational metrics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map(({ key, label, icon: Icon, format, tone }) => (
              <article key={key} className="rounded-lg border border-line bg-white p-4 sm:p-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-muted">{label}</p>
                  <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-md ${toneClasses[tone]}`}><Icon aria-hidden="true" className="h-[18px] w-[18px]" /></span>
                </div>
                <p className="mt-4 text-2xl font-bold tabular-nums text-ink">{format(data.counts[key])}</p>
              </article>
            ))}
          </section>

          <div className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(16rem,0.65fr)]">
            <section aria-labelledby="recent-enrollments-heading" className="min-w-0">
              <div className="mb-3 flex items-end justify-between gap-3">
                <div><h2 id="recent-enrollments-heading" className="text-base font-semibold text-ink">Recent enrollments</h2><p className="mt-1 text-xs text-muted">Newest records returned by the enrollment API</p></div>
              </div>
              <DataTable
                columns={columns}
                rows={data.recentEnrollments}
                getRowKey={(row) => row.enrollment_id}
                caption="Six most recent enrollments"
                emptyMessage="No enrollments have been recorded."
              />
            </section>

            <aside className="rounded-lg border border-line bg-white p-5" aria-labelledby="recent-payments-heading">
              <h2 id="recent-payments-heading" className="text-base font-semibold text-ink">Recent payments</h2>
              <p className="mt-1 text-sm leading-6 text-muted">Payment history is available per enrollment. The approved API does not expose a global recent-payments list, so no cross-enrollment payment feed is inferred here.</p>
              <EmptyState title="Open a student profile" description="Payment and refund history is shown in the relevant enrollment history." />
            </aside>
          </div>
          <p className="mt-5 text-xs text-muted">Fee totals sum each enrollment's current API-provided fee summary. Balances are not recalculated in the browser.</p>
        </>
      )}
    </div>
  )
}