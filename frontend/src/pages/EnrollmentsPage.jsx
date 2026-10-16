import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, UserRound } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, Modal, StatusBadge, TextField } from '../components/ui.jsx'
import { apiRequest } from '../lib/api.js'
import { getAllPages } from '../lib/adminData.js'

const PAGE_SIZE = 20
const terminalStatuses = ['completed', 'withdrawn', 'cancelled']

function validAmount(value) {
  return /^(?=.*[1-9])\d{1,12}(?:\.\d{1,2})?$/.test(value)
}

function EnrollmentForm({ students, programs, batches, token, onClose, onSaved }) {
  const submittingRef = useRef(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState(null)
  const [values, setValues] = useState({ enrollment_number: '', student_id: '', program_id: '', batch_id: '', starts_on: '', ends_on: '', agreed_fee_amount: '', fee_reason: 'Initial agreed fee' })

  function change(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  function submit(event) {
    event.preventDefault()
    if (submittingRef.current) return
    if (!values.enrollment_number.trim() || !values.student_id || !values.program_id || !values.starts_on || !validAmount(values.agreed_fee_amount)) {
      setError('Complete the required fields. The agreed fee must be positive and use at most two decimal places.')
      return
    }
    if (values.ends_on && values.ends_on < values.starts_on) {
      setError('The enrollment end date must not precede its start date.')
      return
    }
    if (values.fee_reason.trim().length > 500) {
      setError('The fee reason must be 500 characters or fewer.')
      return
    }
    setError('')
    setConfirmation({
      enrollment_number: values.enrollment_number.trim(),
      payload: {
        enrollment_number: values.enrollment_number.trim(),
        student_id: Number(values.student_id),
        program_id: Number(values.program_id),
        batch_id: values.batch_id ? Number(values.batch_id) : null,
        starts_on: values.starts_on,
        ends_on: values.ends_on || null,
        agreed_fee_amount: values.agreed_fee_amount,
        fee_reason: values.fee_reason.trim() || 'Initial agreed fee',
      },
    })
  }

  async function confirmCreate() {
    if (submittingRef.current || !confirmation) return
    submittingRef.current = true
    setSubmitting(true)
    setError('')
    try {
      const result = await apiRequest('enrollments', { token, method: 'POST', body: JSON.stringify(confirmation.payload) })
      onSaved(result)
    } catch (cause) {
      setError(cause.message || 'The enrollment was not created.')
      setConfirmation(null)
    } finally {
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  return (
    <Modal title="Create enrollment" onClose={submitting ? () => {} : onClose}>
      <form onSubmit={submit} noValidate className="grid gap-4">
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
        <TextField id="enrollment-number" name="enrollment_number" label="Enrollment number" maxLength={64} required value={values.enrollment_number} onChange={change} />
        <div className="grid gap-1.5"><label htmlFor="enrollment-student" className="text-sm font-semibold text-ink">Active student</label><select id="enrollment-student" name="student_id" required value={values.student_id} onChange={change} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm"><option value="">Select a student</option>{students.map((student) => <option key={student.student_id} value={student.student_id}>{student.student_number} · {student.full_name}</option>)}</select></div>
        <div className="grid gap-1.5"><label htmlFor="enrollment-program" className="text-sm font-semibold text-ink">Active program</label><select id="enrollment-program" name="program_id" required value={values.program_id} onChange={(event) => { change(event); setValues((current) => ({ ...current, batch_id: '' })) }} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm"><option value="">Select a program</option>{programs.map((program) => <option key={program.program_id} value={program.program_id}>{program.program_code} · {program.name}</option>)}</select></div>
        <div className="grid gap-1.5"><label htmlFor="enrollment-batch" className="text-sm font-semibold text-ink">Eligible active batch <span className="font-normal text-muted">(optional)</span></label><select id="enrollment-batch" name="batch_id" value={values.batch_id} onChange={change} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm"><option value="">No batch</option>{batches.filter((batch) => !values.program_id || String(batch.program_id) === values.program_id).map((batch) => <option key={batch.batch_id} value={batch.batch_id}>{batch.batch_code} · {batch.name}</option>)}</select></div>
        <div className="grid gap-4 sm:grid-cols-2"><TextField id="enrollment-start" name="starts_on" label="Starts on" type="date" required value={values.starts_on} onChange={change} /><TextField id="enrollment-end" name="ends_on" label="Ends on" type="date" value={values.ends_on} onChange={change} /></div>
        <TextField id="enrollment-fee" name="agreed_fee_amount" label="Initial agreed fee (INR)" inputMode="decimal" placeholder="25000.00" hint="Use a decimal string with up to two decimal places." value={values.agreed_fee_amount} onChange={change} required />
        <TextField id="fee-reason" name="fee_reason" label="Initial fee reason" maxLength={500} value={values.fee_reason} onChange={change} />
        <p className="text-xs leading-5 text-muted">Creating an enrollment also records its initial fee term atomically.</p>
        <div className="flex justify-end gap-2 border-t border-line pt-4"><Button type="button" variant="secondary" onClick={onClose} disabled={submitting}>Cancel</Button><Button type="submit" disabled={submitting || !students.length || !programs.length}>{submitting ? 'Creating…' : 'Review enrollment'}</Button></div>
      </form>
      {confirmation && <ConfirmDialog title="Create this enrollment?" message={`This will create ${confirmation.enrollment_number} and record its initial agreed fee. The enrollment's student, program, and dates cannot be edited later.`} confirmLabel="Create enrollment" busy={submitting} onCancel={() => setConfirmation(null)} onConfirm={confirmCreate} />}
    </Modal>
  )
}

export default function EnrollmentsPage() {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [students, setStudents] = useState([])
  const [programs, setPrograms] = useState([])
  const [batches, setBatches] = useState([])
  const [queryDraft, setQueryDraft] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [programId, setProgramId] = useState('all')
  const [batchId, setBatchId] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [pendingTransition, setPendingTransition] = useState(null)
  const [transitionBusy, setTransitionBusy] = useState(false)
  const [success, setSuccess] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), status })
    if (query) params.set('q', query)
    if (programId !== 'all') params.set('program_id', programId)
    if (batchId !== 'all') params.set('batch_id', batchId)
    Promise.all([
      apiRequest(`enrollments?${params}`, { token }),
      getAllPages('students', { status: 'active' }, token),
      getAllPages('programs', { status: 'all' }, token),
      getAllPages('batches', { status: 'all' }, token),
    ])
      .then(([enrollments, studentPage, programPage, batchPage]) => {
        if (active) { setData(enrollments); setStudents(studentPage.items); setPrograms(programPage.items); setBatches(batchPage.items) }
      })
      .catch((cause) => { if (active) setError(cause.message || 'Enrollments could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, page, query, status, programId, batchId, reloadKey])

  const studentById = new Map(students.map((student) => [student.student_id, student]))
  const programById = new Map(programs.map((program) => [program.program_id, program]))
  const batchById = new Map(batches.map((batch) => [batch.batch_id, batch]))

  async function transition() {
    if (!pendingTransition || transitionBusy) return
    setTransitionBusy(true)
    try {
      const result = await apiRequest(`enrollments/${pendingTransition.enrollment_id}/status`, { token, method: 'PATCH', body: JSON.stringify({ status: pendingTransition.status }) })
      setSuccess(`${result.enrollment_number} marked ${result.status}.`)
      setPendingTransition(null)
      setReloadKey((key) => key + 1)
    } catch (cause) {
      setError(cause.message || 'The enrollment status was not changed.')
      setPendingTransition(null)
    } finally {
      setTransitionBusy(false)
    }
  }

  function created(enrollment) {
    setShowForm(false)
    setSuccess(`${enrollment.enrollment_number} created successfully.`)
    setPage(1)
    setReloadKey((key) => key + 1)
  }

  const columns = [
    { key: 'enrollment_number', label: 'Enrollment' },
    { key: 'student', label: 'Student', render: (row) => { const student = studentById.get(row.student_id); return student ? <Link className="font-semibold text-ink hover:text-orange-700" to={`/students/${student.student_id}`}>{student.full_name}<span className="mt-0.5 block text-xs font-normal text-muted">{student.student_number}</span></Link> : `Student ${row.student_id}` } },
    { key: 'program', label: 'Program', render: (row) => programById.get(row.program_id)?.name || `Program ${row.program_id}` },
    { key: 'batch', label: 'Batch', render: (row) => row.batch_id ? batchById.get(row.batch_id)?.name || `Batch ${row.batch_id}` : '—' },
    { key: 'schedule', label: 'Dates', render: (row) => `${row.starts_on}${row.ends_on ? ` to ${row.ends_on}` : ''}` },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'actions', label: 'Actions', render: (row) => row.status === 'active' ? <div className="flex flex-wrap gap-1">{terminalStatuses.map((nextStatus) => <Button key={nextStatus} variant="quiet" className="min-h-8 px-2 text-xs capitalize" onClick={() => setPendingTransition({ ...row, status: nextStatus })}>{nextStatus}</Button>)}</div> : '—' },
  ]

  return (
    <div className="animate-enter">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Lifecycle</p><h1 className="mt-2 font-display text-4xl text-ink">Enrollments</h1><p className="mt-2 text-sm text-muted">Create enrollment records and apply supported terminal status transitions.</p></div><Button onClick={() => setShowForm(true)}><Plus aria-hidden="true" className="h-4 w-4" /> New enrollment</Button></div>
      {success && <p role="status" aria-live="polite" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">{success}</p>}
      <form onSubmit={(event) => { event.preventDefault(); setPage(1); setQuery(queryDraft.trim()) }} className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-white p-4">
        <TextField id="enrollment-search" label="Search" type="search" maxLength={100} placeholder="Enrollment or student" value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} className="min-w-[min(100%,16rem)] flex-1" />
        <div className="grid min-w-36 gap-1.5"><label htmlFor="enrollment-status" className="text-xs font-semibold text-muted">Status</label><select id="enrollment-status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">{['all', 'active', 'completed', 'withdrawn', 'cancelled'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select></div>
        <div className="grid min-w-44 gap-1.5"><label htmlFor="enrollment-program-filter" className="text-xs font-semibold text-muted">Program</label><select id="enrollment-program-filter" value={programId} onChange={(event) => { setProgramId(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm"><option value="all">All programs</option>{programs.map((program) => <option key={program.program_id} value={program.program_id}>{program.name}</option>)}</select></div>
        <div className="grid min-w-40 gap-1.5"><label htmlFor="enrollment-batch-filter" className="text-xs font-semibold text-muted">Batch</label><select id="enrollment-batch-filter" value={batchId} onChange={(event) => { setBatchId(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm"><option value="all">All batches</option>{batches.map((batch) => <option key={batch.batch_id} value={batch.batch_id}>{batch.name}</option>)}</select></div>
        <Button type="submit" variant="secondary">Search</Button>
      </form>
      {loading ? <LoadingState label="Loading enrollments" /> : error ? <ErrorState title="Enrollments could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} /> : data.total === 0 ? <EmptyState title="No enrollments found" description="Adjust the search or filters, or create an enrollment." action={<Button onClick={() => setShowForm(true)}><Plus aria-hidden="true" className="h-4 w-4" /> New enrollment</Button>} /> : (
        <><div className="mb-3 flex justify-between text-sm text-muted"><span>{data.total.toLocaleString('en-IN')} enrollments</span><span>Page {data.page} of {data.pages}</span></div><DataTable columns={columns} rows={data.items} getRowKey={(row) => row.enrollment_id} caption="Enrollment records" /><div className="mt-4 flex justify-between"><Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>Previous</Button><Button variant="secondary" disabled={page >= data.pages || loading} onClick={() => setPage((value) => value + 1)}>Next</Button></div></>
      )}
      {showForm && <EnrollmentForm students={students} programs={programs.filter((program) => program.status === 'active')} batches={batches.filter((batch) => batch.status === 'active')} token={token} onClose={() => setShowForm(false)} onSaved={created} />}
      {pendingTransition && <ConfirmDialog title={`Mark ${pendingTransition.enrollment_number} ${pendingTransition.status}?`} message={`This changes the enrollment to ${pendingTransition.status}. Terminal enrollment states cannot be reactivated.`} confirmLabel={`Mark ${pendingTransition.status}`} busy={transitionBusy} onCancel={() => setPendingTransition(null)} onConfirm={transition} />}
    </div>
  )
}