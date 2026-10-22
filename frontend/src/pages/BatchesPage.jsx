import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, SquarePen, Trash2, UsersRound } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import LifecycleDeleteDialog from '../components/LifecycleDeleteDialog.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, Modal, StatusBadge, TextField } from '../components/ui.jsx'
import { apiRequest } from '../lib/api.js'
import { getAllPages } from '../lib/adminData.js'

const PAGE_SIZE = 20

function BatchForm({ batch, programs, token, onClose, onSaved }) {
  const savingRef = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState(null)
  const [values, setValues] = useState({
    program_id: String(batch?.program_id || programs.find((program) => program.status === 'active')?.program_id || ''),
    name: batch?.name || '',
    starts_on: batch?.starts_on || '',
    ends_on: batch?.ends_on || '',
    capacity: batch?.capacity == null ? '' : String(batch.capacity),
    status: batch?.status || 'planned',
  })

  function change(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function save(payload) {
    if (savingRef.current) return
    savingRef.current = true
    setSaving(true)
    setError('')
    try {
      const result = await apiRequest(batch ? `batches/${batch.batch_id}` : 'batches', {
        token,
        method: batch ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
      })
      onSaved(result)
    } catch (cause) {
      setError(cause.message || 'The batch could not be saved. Existing enrollments may constrain dates or capacity.')
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  function submit(event) {
    event.preventDefault()
    if (savingRef.current) return
    const capacity = values.capacity === '' ? null : Number(values.capacity)
    if ((!batch && !values.program_id) || !values.name.trim() || !values.starts_on || !values.ends_on) {
      setError('Complete all required fields.')
      return
    }
    if (values.ends_on < values.starts_on) {
      setError('The end date must not precede the start date.')
      return
    }
    if (capacity !== null && (!Number.isInteger(capacity) || capacity < 1 || capacity > 100000)) {
      setError('Capacity must be a whole number between 1 and 100,000.')
      return
    }
    const payload = batch
      ? { name: values.name.trim(), starts_on: values.starts_on, ends_on: values.ends_on, capacity, status: values.status }
      : { program_id: Number(values.program_id), name: values.name.trim(), starts_on: values.starts_on, ends_on: values.ends_on, capacity, status: values.status }
    setError('')
    if (batch && batch.status !== values.status) setConfirmation(payload)
    else save(payload)
  }

  return (
    <Modal title={batch ? 'Edit batch' : 'Create batch'} onClose={saving ? () => {} : onClose}>
      <form onSubmit={submit} noValidate className="grid gap-4">
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
        {!batch && <div className="grid gap-1.5"><label htmlFor="batch-program" className="text-sm font-semibold text-ink">Active program</label><select id="batch-program" name="program_id" value={values.program_id} onChange={change} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm"><option value="">Select a program</option>{programs.filter((program) => program.status === 'active').map((program) => <option key={program.program_id} value={program.program_id}>{program.program_code} · {program.name}</option>)}</select></div>}
        {batch && <p className="rounded-md bg-orange-50 px-3 py-2 text-sm text-orange-950">Batch code: <strong>{batch.batch_code}</strong></p>}
        {!batch && <p className="rounded-md bg-orange-50 px-3 py-2 text-sm text-orange-950">A unique batch code will be generated after saving.</p>}
        <TextField id="batch-name" name="name" label="Batch name" maxLength={200} required value={values.name} onChange={change} />
        <div className="grid gap-4 sm:grid-cols-2"><TextField id="batch-start" name="starts_on" label="Starts on" type="date" required value={values.starts_on} onChange={change} /><TextField id="batch-end" name="ends_on" label="Ends on" type="date" required value={values.ends_on} onChange={change} /></div>
        <TextField id="batch-capacity" name="capacity" label="Capacity" type="number" min="1" max="100000" step="1" hint="Leave blank for unlimited capacity." value={values.capacity} onChange={change} />
        <div className="grid gap-1.5"><label htmlFor="batch-status" className="text-sm font-semibold text-ink">Status</label><select id="batch-status" name="status" value={values.status} onChange={change} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm">{(batch ? ['planned', 'active', 'completed', 'cancelled'] : ['planned', 'active']).map((status) => <option key={status} value={status}>{status.replaceAll('_', ' ')}</option>)}</select></div>
        <div className="flex justify-end gap-2 border-t border-line pt-4"><Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button><Button type="submit" disabled={saving || (!batch && !programs.some((program) => program.status === 'active'))}>{saving ? 'Saving…' : batch ? 'Save changes' : 'Create batch'}</Button></div>
      </form>
      {confirmation && <ConfirmDialog title="Change batch status?" message={`Change ${batch.name} from ${batch.status} to ${confirmation.status}? The server will validate capacity and enrollment date constraints.`} confirmLabel="Save status change" reasonRequired={confirmation.status === 'cancelled'} reasonLabel="Reason for cancellation" busy={saving} onCancel={() => setConfirmation(null)} onConfirm={(reason) => { const payload = { ...confirmation, ...(confirmation.status === 'cancelled' ? { reason } : {}) }; setConfirmation(null); save(payload) }} />}
    </Modal>
  )
}

function BatchRoster({ batch, token, onClose }) {
  const [roster, setRoster] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    apiRequest(`batches/${batch.batch_id}/roster`, { token })
      .then((result) => { if (active) setRoster(result) })
      .catch((cause) => { if (active) setError(cause.message || 'The batch roster could not be loaded.') })
    return () => { active = false }
  }, [batch.batch_id, token])
  const columns = [
    { key: 'student_number', label: 'Student number' },
    { key: 'full_name', label: 'Student' },
    { key: 'enrollment_number', label: 'Enrollment' },
    { key: 'enrollment_status', label: 'Status', render: (row) => <StatusBadge status={row.enrollment_status} /> },
    { key: 'email', label: 'Email', render: (row) => row.email || '—' },
  ]
  return (
    <Modal title={`${batch.name} roster`} onClose={onClose}>
      {error ? <ErrorState title="Roster unavailable" message={error} /> : !roster ? <LoadingState label="Loading roster" /> : (
        <><p className="mb-3 text-sm text-muted">{roster.active_enrollment_count} active enrollments{roster.capacity ? ` · capacity ${roster.capacity}` : ' · unlimited capacity'}</p><DataTable columns={columns} rows={roster.students} getRowKey={(row) => row.enrollment_id} caption="Batch roster" emptyMessage="No enrollments in this batch." /></>
      )}
      <div className="mt-4 flex justify-end"><Button variant="secondary" onClick={onClose}>Close</Button></div>
    </Modal>
  )
}

export default function BatchesPage() {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [programs, setPrograms] = useState([])
  const [programId, setProgramId] = useState('all')
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formBatch, setFormBatch] = useState(undefined)
  const [rosterBatch, setRosterBatch] = useState(null)
  const [deleteBatch, setDeleteBatch] = useState(null)
  const [success, setSuccess] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), status })
    if (programId !== 'all') params.set('program_id', programId)
    Promise.all([
      apiRequest(`batches?${params}`, { token }),
      getAllPages('programs', { status: 'all' }, token),
    ])
      .then(([batchPage, programPage]) => {
        if (active) { setData(batchPage); setPrograms(programPage.items) }
      })
      .catch((cause) => { if (active) setError(cause.message || 'Batches could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, page, programId, status, reloadKey])

  function saved(batch) {
    setFormBatch(undefined)
    setSuccess(`${batch.batch_code} saved successfully.`)
    setReloadKey((key) => key + 1)
  }

  const columns = [
    { key: 'batch_code', label: 'Batch', render: (row) => <Link to={`/batches/${row.batch_id}`} className="font-semibold text-ink hover:text-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500">{row.batch_code}</Link> },
    { key: 'name', label: 'Name' },
    { key: 'program', label: 'Program', render: (row) => `${row.program_code} · ${row.program_name}` },
    { key: 'schedule', label: 'Schedule', render: (row) => `${row.starts_on} to ${row.ends_on}` },
    { key: 'capacity', label: 'Capacity', render: (row) => row.capacity ?? 'Unlimited' },
    { key: 'active_enrollment_count', label: 'Active enrollments', render: (row) => <span>{row.active_enrollment_count}<span className="mt-0.5 block text-xs text-muted">{row.unique_active_student_count} unique students · {row.enrollment_count} total enrollments</span></span> },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'actions', label: 'Actions', render: (row) => <div className="flex gap-1"><Button variant="quiet" className="min-h-9 px-2" aria-label={`View ${row.name} roster`} onClick={() => setRosterBatch(row)}><UsersRound aria-hidden="true" className="h-4 w-4" /></Button><Button variant="quiet" className="min-h-9 px-2" aria-label={`Edit ${row.name}`} onClick={() => setFormBatch(row)}><SquarePen aria-hidden="true" className="h-4 w-4" /></Button><Button variant="quiet" className="min-h-9 px-2 text-red-700" aria-label={`Delete ${row.name}`} onClick={() => setDeleteBatch(row)}><Trash2 aria-hidden="true" className="h-4 w-4" /></Button></div> },
  ]

  return (
    <div className="animate-enter">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Scheduling</p><h1 className="mt-2 font-display text-4xl text-ink">Batches</h1><p className="mt-2 text-sm text-muted">Manage cohort dates, capacity, and rosters.</p></div><Button onClick={() => setFormBatch(null)} disabled={!programs.some((program) => program.status === 'active')}><Plus aria-hidden="true" className="h-4 w-4" /> Add batch</Button></div>
      {success && <p role="status" aria-live="polite" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">{success}</p>}
      <section className="mb-4 flex flex-wrap gap-3 rounded-lg border border-line bg-white p-4">
        <div className="grid min-w-48 gap-1.5"><label htmlFor="batch-program-filter" className="text-xs font-semibold text-muted">Program</label><select id="batch-program-filter" value={programId} onChange={(event) => { setProgramId(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm"><option value="all">All programs</option>{programs.map((program) => <option key={program.program_id} value={program.program_id}>{program.program_code} · {program.name}</option>)}</select></div>
        <div className="grid min-w-40 gap-1.5"><label htmlFor="batch-status-filter" className="text-xs font-semibold text-muted">Status</label><select id="batch-status-filter" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">{['all', 'planned', 'active', 'completed', 'cancelled'].map((value) => <option key={value} value={value}>{value === 'all' ? 'All statuses' : value}</option>)}</select></div>
      </section>
      {loading ? <LoadingState label="Loading batches" /> : error ? <ErrorState title="Batches could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} /> : data.total === 0 ? <EmptyState title="No batches found" description="Adjust the filters or create a batch under an active program." action={<Button onClick={() => setFormBatch(null)} disabled={!programs.some((program) => program.status === 'active')}><Plus aria-hidden="true" className="h-4 w-4" /> Add batch</Button>} /> : (
        <><div className="mb-3 flex justify-between text-sm text-muted"><span>{data.total.toLocaleString('en-IN')} batches</span><span>Page {data.page} of {data.pages}</span></div><DataTable columns={columns} rows={data.items} getRowKey={(row) => row.batch_id} caption="Internship batches" /><div className="mt-4 flex justify-between"><Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>Previous</Button><Button variant="secondary" disabled={page >= data.pages || loading} onClick={() => setPage((value) => value + 1)}>Next</Button></div></>
      )}
      {formBatch !== undefined && <BatchForm batch={formBatch || undefined} programs={programs} token={token} onClose={() => setFormBatch(undefined)} onSaved={saved} />}
      {rosterBatch && <BatchRoster batch={rosterBatch} token={token} onClose={() => setRosterBatch(null)} />}
      {deleteBatch && <LifecycleDeleteDialog resourcePath={`batches/${deleteBatch.batch_id}`} resourceLabel="batch" identifier={deleteBatch.batch_code} token={token} onCancel={() => setDeleteBatch(null)} onDeleted={() => { setSuccess(`${deleteBatch.batch_code} deleted.`); setDeleteBatch(null); setReloadKey((key) => key + 1) }} />}
    </div>
  )
}