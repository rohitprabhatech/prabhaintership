import { useEffect, useRef, useState } from 'react'
import { Plus, SquarePen } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, Modal, StatusBadge, TextField } from '../components/ui.jsx'
import { apiRequest } from '../lib/api.js'

const PAGE_SIZE = 20

function ProgramForm({ program, token, onClose, onSaved }) {
  const savingRef = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState(null)
  const [values, setValues] = useState({
    program_code: program?.program_code || '',
    name: program?.name || '',
    description: program?.description || '',
    status: program?.status || 'draft',
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
      const result = await apiRequest(program ? `programs/${program.program_id}` : 'programs', {
        token,
        method: program ? 'PATCH' : 'POST',
        body: JSON.stringify(payload),
      })
      onSaved(result)
    } catch (cause) {
      setError(cause.message || 'The program could not be saved.')
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  function submit(event) {
    event.preventDefault()
    if (savingRef.current) return
    if (!values.name.trim() || (!program && !values.program_code.trim())) {
      setError('Enter a program code and name.')
      return
    }
    const payload = {
      name: values.name.trim(),
      description: values.description.trim() || null,
      status: values.status,
    }
    if (!program) payload.program_code = values.program_code.trim().toUpperCase()
    if (program && program.status !== values.status) setConfirmation(payload)
    else save(payload)
  }

  return (
    <Modal title={program ? 'Edit program' : 'Create program'} onClose={saving ? () => {} : onClose}>
      <form onSubmit={submit} noValidate className="grid gap-4">
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
        {!program && <TextField id="program-code" name="program_code" label="Program code" maxLength={64} required value={values.program_code} onChange={change} />}
        <TextField id="program-name" name="name" label="Program name" maxLength={200} required value={values.name} onChange={change} />
        <div className="grid gap-1.5">
          <label htmlFor="program-description" className="text-sm font-semibold text-ink">Description</label>
          <textarea id="program-description" name="description" maxLength={4000} rows={4} value={values.description} onChange={change} className="rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100" />
        </div>
        <div className="grid gap-1.5">
          <label htmlFor="program-status" className="text-sm font-semibold text-ink">Status</label>
          <select id="program-status" name="status" value={values.status} onChange={change} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100">
            {(program ? ['draft', 'active', 'inactive'] : ['draft', 'active']).map((status) => <option key={status} value={status}>{status[0].toUpperCase() + status.slice(1)}</option>)}
          </select>
        </div>
        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button type="submit" disabled={saving}>{saving ? 'Saving…' : program ? 'Save changes' : 'Create program'}</Button>
        </div>
      </form>
      {confirmation && <ConfirmDialog title="Change program status?" message={`Change ${program.name} from ${program.status} to ${confirmation.status}? This can affect which programs are available for new batches and enrollments.`} confirmLabel="Save status change" busy={saving} onCancel={() => setConfirmation(null)} onConfirm={() => save(confirmation)} />}
    </Modal>
  )
}

export default function ProgramsPage() {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [queryDraft, setQueryDraft] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formProgram, setFormProgram] = useState(undefined)
  const [success, setSuccess] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), status })
    if (query) params.set('q', query)
    apiRequest(`programs?${params}`, { token })
      .then((result) => { if (active) setData(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Programs could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, page, query, status, reloadKey])

  function saved(program) {
    setFormProgram(undefined)
    setSuccess(`${program.program_code} saved successfully.`)
    setReloadKey((key) => key + 1)
  }

  const columns = [
    { key: 'program_code', label: 'Code' },
    { key: 'name', label: 'Program' },
    { key: 'description', label: 'Description', render: (row) => row.description || '—' },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'updated_at', label: 'Updated', render: (row) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(row.updated_at)) },
    { key: 'actions', label: 'Actions', render: (row) => <Button variant="quiet" className="min-h-9 px-2" aria-label={`Edit ${row.name}`} onClick={() => setFormProgram(row)}><SquarePen aria-hidden="true" className="h-4 w-4" /></Button> },
  ]

  return (
    <div className="animate-enter">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Catalog</p><h1 className="mt-2 font-display text-4xl text-ink">Programs</h1><p className="mt-2 text-sm text-muted">Manage program definitions and lifecycle status.</p></div>
        <Button onClick={() => setFormProgram(null)}><Plus aria-hidden="true" className="h-4 w-4" /> Add program</Button>
      </div>
      {success && <p role="status" aria-live="polite" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">{success}</p>}
      <form onSubmit={(event) => { event.preventDefault(); setPage(1); setQuery(queryDraft.trim()) }} className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-white p-4">
        <TextField id="program-search" label="Search programs" type="search" maxLength={100} value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} placeholder="Code or name" className="min-w-[min(100%,18rem)] flex-1" />
        <div className="grid min-w-36 gap-1.5"><label htmlFor="program-filter" className="text-xs font-semibold text-muted">Status</label><select id="program-filter" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm"><option value="all">All statuses</option><option value="draft">Draft</option><option value="active">Active</option><option value="inactive">Inactive</option></select></div>
        <Button type="submit" variant="secondary">Search</Button>
      </form>
      {loading ? <LoadingState label="Loading programs" /> : error ? <ErrorState title="Programs could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} /> : data.total === 0 ? (
        <EmptyState title="No programs found" description="Adjust the search or status filter, or create a program." action={<Button onClick={() => setFormProgram(null)}><Plus aria-hidden="true" className="h-4 w-4" /> Add program</Button>} />
      ) : (
        <><div className="mb-3 flex justify-between text-sm text-muted"><span>{data.total.toLocaleString('en-IN')} programs</span><span>Page {data.page} of {data.pages}</span></div><DataTable columns={columns} rows={data.items} getRowKey={(row) => row.program_id} caption="Internship programs" /><div className="mt-4 flex justify-between"><Button variant="secondary" disabled={page <= 1 || loading} onClick={() => setPage((value) => value - 1)}>Previous</Button><Button variant="secondary" disabled={page >= data.pages || loading} onClick={() => setPage((value) => value + 1)}>Next</Button></div></>
      )}
      {formProgram !== undefined && <ProgramForm program={formProgram || undefined} token={token} onClose={() => setFormProgram(undefined)} onSaved={saved} />}
    </div>
  )
}