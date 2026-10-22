import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Search } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/ui.jsx'
import { apiRequest } from '../lib/api.js'
import { decimalToMinorUnits, formatInrMinorUnits } from '../lib/adminData.js'

const PAGE_SIZE = 20

function money(value) {
  return value == null ? '—' : formatInrMinorUnits(decimalToMinorUnits(value))
}

export default function BatchDetailsPage() {
  const { batchId } = useParams()
  const { token } = useAuth()
  const [batch, setBatch] = useState(null)
  const [program, setProgram] = useState(null)
  const [roster, setRoster] = useState(null)
  const [queryDraft, setQueryDraft] = useState('')
  const [query, setQuery] = useState('')
  const [enrollmentStatus, setEnrollmentStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
      status: enrollmentStatus,
    })
    if (query) params.set('q', query)
    Promise.all([
      apiRequest(`batches/${batchId}`, { token }),
      apiRequest(`batches/${batchId}/students?${params}`, { token }),
    ])
      .then(async ([batchResult, rosterResult]) => {
        const programResult = await apiRequest(`programs/${batchResult.program_id}`, { token })
        if (active) {
          setBatch(batchResult)
          setRoster(rosterResult)
          setProgram(programResult)
        }
      })
      .catch((cause) => {
        if (active) setError(cause.message || 'Batch details could not be loaded.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [batchId, token, page, query, enrollmentStatus, reloadKey])

  function search(event) {
    event.preventDefault()
    setPage(1)
    setQuery(queryDraft.trim())
  }

  const columns = [
    {
      key: 'full_name',
      label: 'Student',
      render: (row) => (
        <Link to={`/students/${row.student_id}`} className="font-semibold text-ink hover:text-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500">
          {row.full_name}<span className="mt-0.5 block text-xs font-normal text-muted">{row.student_number}</span>
        </Link>
      ),
    },
    { key: 'contact', label: 'Contact', render: (row) => <span>{row.email || '—'}<span className="mt-0.5 block text-xs text-muted">{row.phone || 'No phone'}</span></span> },
    { key: 'enrollment_number', label: 'Enrollment', render: (row) => <span>{row.enrollment_number}<span className="mt-0.5 block text-xs text-muted">Started {row.enrollment_starts_on}</span></span> },
    { key: 'enrollment_status', label: 'Status', render: (row) => <StatusBadge status={row.enrollment_status} /> },
    { key: 'fee_summary', label: 'Fee summary', render: (row) => row.fee_summary ? <span>{money(row.fee_summary.pending_balance)} pending<span className="mt-0.5 block text-xs text-muted">{money(row.fee_summary.net_paid)} paid of {money(row.fee_summary.effective_fee)}</span></span> : 'Fee not recorded' },
  ]

  return (
    <div className="animate-enter">
      <Link to="/batches" className="mb-5 inline-flex min-h-9 items-center gap-2 text-sm font-semibold text-muted hover:text-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500">
        <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Batches
      </Link>
      {loading ? <LoadingState label="Loading batch and student details" /> : error ? (
        <ErrorState title="Batch details could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} />
      ) : (
        <>
          <header className="mb-6 rounded-lg border border-line bg-white p-5 sm:p-7">
            <p className="text-xs font-bold uppercase text-orange-700">Batch details</p>
            <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h1 className="font-display text-3xl text-ink sm:text-4xl">{batch.name}</h1>
                <p className="mt-1 font-medium text-muted">{batch.batch_code}</p>
                <p className="mt-3 text-sm text-muted">{program.program_code} · {program.name}</p>
                <p className="mt-1 text-sm text-muted">{batch.starts_on} to {batch.ends_on} · Capacity {batch.capacity ?? 'unlimited'}</p>
              </div>
              <StatusBadge status={batch.status} />
            </div>
            <dl className="mt-5 grid gap-3 border-t border-line pt-4 sm:grid-cols-3">
              <div><dt className="text-xs font-semibold uppercase text-muted">Active enrollments</dt><dd className="mt-1 text-lg font-semibold text-ink">{roster.active_enrollment_count}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-muted">Unique active students</dt><dd className="mt-1 text-lg font-semibold text-ink">{roster.unique_active_student_count}</dd></div>
              <div><dt className="text-xs font-semibold uppercase text-muted">All enrollments</dt><dd className="mt-1 text-lg font-semibold text-ink">{roster.enrollment_count}</dd></div>
            </dl>
          </header>

          <section className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-white p-4">
            <form onSubmit={search} className="flex min-w-[min(100%,20rem)] flex-1 items-end gap-2">
              <div className="grid flex-1 gap-1.5">
                <label htmlFor="batch-student-search" className="text-xs font-semibold text-muted">Search students</label>
                <input id="batch-student-search" type="search" maxLength={100} value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} placeholder="Name, student number, email, phone, or enrollment" className="min-h-10 w-full rounded-md border border-line px-3 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100" />
              </div>
              <Button type="submit" variant="secondary"><Search aria-hidden="true" className="h-4 w-4" /> Search</Button>
            </form>
            <div className="grid min-w-44 gap-1.5">
              <label htmlFor="batch-enrollment-status" className="text-xs font-semibold text-muted">Enrollment status</label>
              <select id="batch-enrollment-status" value={enrollmentStatus} onChange={(event) => { setEnrollmentStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">
                <option value="all">All statuses</option>
                {['active', 'completed', 'withdrawn', 'cancelled'].map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
            </div>
          </section>

          {roster.total === 0 ? (
            <EmptyState
              title={query || enrollmentStatus !== 'all' ? 'No matching enrollments' : 'No students enrolled'}
              description={query || enrollmentStatus !== 'all' ? 'Try changing the search or enrollment-status filter.' : 'Students enrolled in this batch will appear here.'}
            />
          ) : (
            <>
              <div className="mb-3 flex items-center justify-between gap-3 text-sm text-muted">
                <p>{roster.total.toLocaleString('en-IN')} matching {roster.total === 1 ? 'enrollment' : 'enrollments'}</p>
                <p>Page {roster.page} of {roster.pages}</p>
              </div>
              <DataTable columns={columns} rows={roster.students} getRowKey={(row) => row.enrollment_id} caption={`Students enrolled in ${batch.name}`} />
              <div className="mt-4 flex items-center justify-between">
                <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</Button>
                <Button variant="secondary" disabled={page >= roster.pages} onClick={() => setPage((current) => Math.min(roster.pages, current + 1))}>Next</Button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
