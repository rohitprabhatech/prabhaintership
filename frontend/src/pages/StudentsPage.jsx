import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, SquarePen, Trash2 } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import StudentForm from '../components/StudentForm.jsx'
import LifecycleDeleteDialog from '../components/LifecycleDeleteDialog.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/ui.jsx'
import { loadStudentList } from '../lib/studentData.js'

const PAGE_SIZE = 20

function displayDate(value) {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(value))
}

export default function StudentsPage() {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [queryDraft, setQueryDraft] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('active')
  const [programId, setProgramId] = useState('all')
  const [batchId, setBatchId] = useState('all')
  const [enrollmentStatus, setEnrollmentStatus] = useState('all')
  const [feeStatus, setFeeStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formStudent, setFormStudent] = useState(undefined)
  const [deleteStudent, setDeleteStudent] = useState(null)
  const [success, setSuccess] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    loadStudentList({
      token,
      page,
      pageSize: PAGE_SIZE,
      query,
      status,
      programId,
      batchId,
      enrollmentStatus,
      feeStatus,
    })
      .then((result) => { if (active) setData(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Student records could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, page, query, status, programId, batchId, enrollmentStatus, feeStatus, reloadKey])

  function saveStudent(student) {
    setFormStudent(undefined)
    setSuccess(`${student.student_number} · ${student.full_name} ${student.status === 'archived' ? 'updated' : 'saved'} successfully.`)
    setReloadKey((key) => key + 1)
  }

  function submitSearch(event) {
    event.preventDefault()
    setPage(1)
    setQuery(queryDraft.trim())
  }

  const columns = [
    {
      key: 'full_name', label: 'Student', render: (row) => (
        <Link to={`/students/${row.student_id}`} className="font-semibold text-ink hover:text-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500">
          {row.full_name}<span className="mt-0.5 block text-xs font-normal text-muted">{row.student_number}</span>
        </Link>
      ),
    },
    { key: 'email', label: 'Contact', render: (row) => <span>{row.email || '—'}<span className="mt-0.5 block text-xs text-muted">{row.phone || 'No phone'}</span></span> },
    { key: 'education', label: 'Education / program', render: (row) => [row.course, row.internship_domain, row.program?.name].filter(Boolean).join(' · ') || '—' },
    { key: 'batch', label: 'Batch', render: (row) => row.batch?.name || '—' },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'updated_at', label: 'Updated', render: (row) => displayDate(row.updated_at) },
    {
      key: 'actions', label: 'Actions', render: (row) => (
        <div className="flex gap-1">
          <Button variant="quiet" className="min-h-9 px-2" aria-label={`Edit ${row.full_name}`} onClick={() => setFormStudent(row)}>
            <SquarePen aria-hidden="true" className="h-4 w-4" />
          </Button>
          <Button variant="quiet" className="min-h-9 px-2 text-red-700" aria-label={`Delete ${row.student_number}`} onClick={() => setDeleteStudent(row)}>
            <Trash2 aria-hidden="true" className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="animate-enter">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Records</p>
          <h1 className="mt-2 font-display text-4xl text-ink">Students</h1>
          <p className="mt-2 text-sm text-muted">Search and maintain student profiles and their enrollment context.</p>
        </div>
        <Button onClick={() => setFormStudent(null)}><Plus aria-hidden="true" className="h-4 w-4" /> Add student</Button>
      </div>

      {success && <p role="status" aria-live="polite" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">{success}</p>}

      <section className="mb-4 flex flex-wrap items-end justify-between gap-3 rounded-lg border border-line bg-white p-4">
        <form onSubmit={submitSearch} className="flex min-w-[min(100%,20rem)] flex-1 items-end gap-2">
          <div className="grid flex-1 gap-1.5">
            <label htmlFor="student-search" className="text-xs font-semibold text-muted">Search students</label>
            <input id="student-search" type="search" maxLength={100} value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} placeholder="Name, number, email, or phone" className="min-h-10 w-full rounded-md border border-line px-3 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100" />
          </div>
          <Button type="submit" variant="secondary" aria-label="Apply student search"><Search aria-hidden="true" className="h-4 w-4" /> Search</Button>
        </form>
        <div className="grid min-w-40 gap-1.5">
          <label htmlFor="student-filter" className="text-xs font-semibold text-muted">Status</label>
          <select id="student-filter" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100">
            <option value="active">Active</option><option value="archived">Archived</option><option value="all">All students</option>
          </select>
        </div>
        <div className="grid min-w-48 gap-1.5">
          <label htmlFor="student-program-filter" className="text-xs font-semibold text-muted">Program</label>
          <select id="student-program-filter" value={programId} onChange={(event) => { setProgramId(event.target.value); setBatchId('all'); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">
            <option value="all">All programs</option>
            {(data?.programs || []).map((program) => <option key={program.program_id} value={program.program_id}>{program.program_code} · {program.name}</option>)}
          </select>
        </div>
        <div className="grid min-w-48 gap-1.5">
          <label htmlFor="student-batch-filter" className="text-xs font-semibold text-muted">Batch</label>
          <select id="student-batch-filter" value={batchId} onChange={(event) => { setBatchId(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">
            <option value="all">All batches</option>
            {(data?.batches || []).filter((batch) => programId === 'all' || String(batch.program_id) === programId).map((batch) => <option key={batch.batch_id} value={batch.batch_id}>{batch.batch_code} · {batch.name}</option>)}
          </select>
        </div>
        <div className="grid min-w-40 gap-1.5">
          <label htmlFor="student-enrollment-filter" className="text-xs font-semibold text-muted">Enrollment status</label>
          <select id="student-enrollment-filter" value={enrollmentStatus} onChange={(event) => { setEnrollmentStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">
            <option value="all">All enrollments</option>
            {['active', 'completed', 'withdrawn', 'cancelled'].map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>
        <div className="grid min-w-40 gap-1.5">
          <label htmlFor="student-fee-filter" className="text-xs font-semibold text-muted">Fee status</label>
          <select id="student-fee-filter" value={feeStatus} onChange={(event) => { setFeeStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">
            <option value="all">All fee statuses</option><option value="outstanding">Outstanding</option><option value="paid">Paid</option>
          </select>
        </div>
      </section>

      {loading ? <LoadingState label="Loading students" /> : error ? (
        <ErrorState title="Student records could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} />
      ) : data.total === 0 ? (
        <EmptyState title={query ? 'No matching students' : 'No students in this view'} description={query ? 'Try a different search or status filter.' : 'Add a student profile to begin maintaining records.'} action={!query && <Button onClick={() => setFormStudent(null)}><Plus aria-hidden="true" className="h-4 w-4" /> Add student</Button>} />
      ) : (
        <>
          <div className="mb-3 flex items-center justify-between gap-3 text-sm text-muted">
            <p>{data.total.toLocaleString('en-IN')} {data.total === 1 ? 'student' : 'students'}</p>
            <p>Page {data.page} of {data.pages}</p>
          </div>
          <DataTable columns={columns} rows={data.items} getRowKey={(row) => row.student_id} caption="Student records" />
          <div className="mt-4 flex items-center justify-between">
            <Button variant="secondary" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1 || loading}>Previous</Button>
            <p aria-live="polite" className="text-sm text-muted">{data.total.toLocaleString('en-IN')} total</p>
            <Button variant="secondary" onClick={() => setPage((current) => Math.min(data.pages, current + 1))} disabled={page >= data.pages || loading}>Next</Button>
          </div>
        </>
      )}

      {formStudent !== undefined && <StudentForm student={formStudent || undefined} token={token} onClose={() => setFormStudent(undefined)} onSaved={saveStudent} />}
      {deleteStudent && <LifecycleDeleteDialog resourcePath={`students/${deleteStudent.student_id}`} resourceLabel="student" identifier={deleteStudent.student_number} token={token} onCancel={() => setDeleteStudent(null)} onDeleted={() => { setSuccess(`${deleteStudent.student_number} deleted.`); setDeleteStudent(null); setReloadKey((key) => key + 1) }} />}
    </div>
  )
}