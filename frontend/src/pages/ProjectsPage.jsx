import { useEffect, useRef, useState } from 'react'
import { Plus } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, Modal, StatusBadge, TextField } from '../components/ui.jsx'
import { apiRequest } from '../lib/api.js'
import { getAllPages } from '../lib/adminData.js'

const PAGE_SIZE = 20

function ProjectForm({ token, onClose, onSaved }) {
  const savingRef = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [values, setValues] = useState({ project_code: '', name: '', description: '' })
  async function submit(event) {
    event.preventDefault()
    if (savingRef.current) return
    if (!values.project_code.trim() || !values.name.trim()) { setError('Enter a project code and name.'); return }
    savingRef.current = true
    setSaving(true)
    setError('')
    try {
      const project = await apiRequest('projects', { token, method: 'POST', body: JSON.stringify({
        project_code: values.project_code.trim().toUpperCase(),
        name: values.name.trim(),
        description: values.description.trim() || null,
      }) })
      onSaved(project)
    } catch (cause) {
      setError(cause.message || 'Project creation failed. No success is recorded.')
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }
  return (
    <Modal title="Create project" onClose={saving ? () => {} : onClose}>
      <form onSubmit={submit} noValidate className="grid gap-4">
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
        <TextField id="project-code" label="Project code" maxLength={64} required value={values.project_code} onChange={(event) => setValues((current) => ({ ...current, project_code: event.target.value }))} />
        <TextField id="project-name" label="Project name" maxLength={200} required value={values.name} onChange={(event) => setValues((current) => ({ ...current, name: event.target.value }))} />
        <div className="grid gap-1.5"><label htmlFor="project-description" className="text-sm font-semibold text-ink">Description</label><textarea id="project-description" maxLength={4000} rows={4} value={values.description} onChange={(event) => setValues((current) => ({ ...current, description: event.target.value }))} className="rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100" /></div>
        <p className="text-xs text-muted">Project definitions are create-only in the approved API; they cannot be edited or deleted here.</p>
        <div className="flex justify-end gap-2 border-t border-line pt-4"><Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button><Button type="submit" disabled={saving}>{saving ? 'Creating…' : 'Create project'}</Button></div>
      </form>
    </Modal>
  )
}

function ProjectCatalog({ token }) {
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [success, setSuccess] = useState('')
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    apiRequest(`projects?${new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), status })}`, { token })
      .then((result) => { if (active) setData(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Projects could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, status, page, reloadKey])
  const columns = [
    { key: 'project_code', label: 'Code' },
    { key: 'name', label: 'Project' },
    { key: 'description', label: 'Description', render: (row) => row.description || '—' },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
  ]
  return (
    <section aria-labelledby="project-catalog-heading" className="rounded-lg border border-line bg-white p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><h2 id="project-catalog-heading" className="text-base font-semibold text-ink">Project catalog</h2><p className="mt-1 text-xs text-muted">Project definitions are immutable after creation.</p></div><Button onClick={() => setShowForm(true)}><Plus aria-hidden="true" className="h-4 w-4" /> Create project</Button></div>
      {success && <p role="status" className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 p-2.5 text-sm text-emerald-900">{success}</p>}
      <div className="mb-3 flex justify-end"><select aria-label="Project status filter" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">{['all', 'active', 'archived'].map((value) => <option key={value} value={value}>{value === 'all' ? 'All statuses' : value}</option>)}</select></div>
      {loading ? <LoadingState label="Loading projects" /> : error ? <ErrorState title="Projects could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} /> : data.total === 0 ? <EmptyState title="No projects found" description="Create a project definition before assigning projects to enrollments." /> : <><DataTable columns={columns} rows={data.items} getRowKey={(row) => row.project_id} caption="Project catalog" /><div className="mt-3 flex justify-between text-sm"><Button variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span className="self-center text-muted">Page {data.page} of {data.pages}</span><Button variant="secondary" disabled={page >= data.pages} onClick={() => setPage((value) => value + 1)}>Next</Button></div></>}
      {showForm && <ProjectForm token={token} onClose={() => setShowForm(false)} onSaved={(project) => { setShowForm(false); setSuccess(`${project.project_code} created successfully.`); setReloadKey((key) => key + 1) }} />}
    </section>
  )
}

function AssignmentForm({ token, projects, enrollments, onClose, onSaved }) {
  const submittingRef = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [enrollmentId, setEnrollmentId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [confirmation, setConfirmation] = useState(false)
  async function confirm() {
    if (submittingRef.current || !enrollmentId || !projectId) return
    submittingRef.current = true
    setSaving(true)
    setError('')
    try {
      const assignment = await apiRequest(`enrollments/${enrollmentId}/projects`, { token, method: 'POST', body: JSON.stringify({ project_id: Number(projectId) }) })
      onSaved(assignment)
    } catch (cause) {
      setError(cause.message || 'The assignment was not created.')
      setConfirmation(false)
    } finally {
      submittingRef.current = false
      setSaving(false)
    }
  }
  return (
    <Modal title="Assign project" onClose={saving ? () => {} : onClose}>
      <div className="grid gap-4">
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
        <div className="grid gap-1.5"><label htmlFor="assignment-enrollment" className="text-sm font-semibold text-ink">Active enrollment</label><select id="assignment-enrollment" value={enrollmentId} onChange={(event) => setEnrollmentId(event.target.value)} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm"><option value="">Select an enrollment</option>{enrollments.filter((item) => item.status === 'active').map((item) => <option key={item.enrollment_id} value={item.enrollment_id}>{item.enrollment_number}</option>)}</select></div>
        <div className="grid gap-1.5"><label htmlFor="assignment-project" className="text-sm font-semibold text-ink">Active project</label><select id="assignment-project" value={projectId} onChange={(event) => setProjectId(event.target.value)} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm"><option value="">Select a project</option>{projects.filter((item) => item.status === 'active').map((item) => <option key={item.project_id} value={item.project_id}>{item.project_code} · {item.name}</option>)}</select></div>
        <div className="flex justify-end gap-2 border-t border-line pt-4"><Button variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button><Button onClick={() => { if (!enrollmentId || !projectId) setError('Select an active enrollment and project.'); else setConfirmation(true) }} disabled={saving || !enrollments.some((item) => item.status === 'active') || !projects.some((item) => item.status === 'active')}>Review assignment</Button></div>
      </div>
      {confirmation && <ConfirmDialog title="Assign this project?" message="This adds a project assignment to the selected active enrollment. The assignment cannot be deleted; its progress is tracked through status events." confirmLabel="Assign project" busy={saving} onCancel={() => setConfirmation(false)} onConfirm={confirm} />}
    </Modal>
  )
}

function AssignmentPanel({ token }) {
  const [data, setData] = useState(null)
  const [projects, setProjects] = useState([])
  const [enrollments, setEnrollments] = useState([])
  const [status, setStatus] = useState('all')
  const [projectId, setProjectId] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [pending, setPending] = useState(null)
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState('')
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), status })
    if (projectId !== 'all') params.set('project_id', projectId)
    Promise.all([
      apiRequest(`project-assignments?${params}`, { token }),
      getAllPages('projects', { status: 'all' }, token),
      getAllPages('enrollments', { status: 'all' }, token),
    ])
      .then(([assignments, projectPage, enrollmentPage]) => { if (active) { setData(assignments); setProjects(projectPage.items); setEnrollments(enrollmentPage.items) } })
      .catch((cause) => { if (active) setError(cause.message || 'Project assignments could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, page, status, projectId, reloadKey])

  async function transition() {
    if (!pending || busy) return
    setBusy(true)
    try {
      const result = await apiRequest(`project-assignments/${pending.project_assignment_id}/status`, { token, method: 'PATCH', body: JSON.stringify({ status: pending.next }) })
      setSuccess(`${result.project_name || result.project_code || 'Project'} marked ${result.status}.`)
      setPending(null)
      setReloadKey((key) => key + 1)
    } catch (cause) {
      setError(cause.message || 'Project progress was not updated.')
      setPending(null)
    } finally {
      setBusy(false)
    }
  }

  const enrollmentById = new Map(enrollments.map((enrollment) => [enrollment.enrollment_id, enrollment]))
  const actions = { assigned: ['in_progress', 'cancelled'], in_progress: ['completed', 'cancelled'] }
  const columns = [
    { key: 'project_name', label: 'Project', render: (row) => row.project_name || row.project_code || `Project ${row.project_id}` },
    { key: 'enrollment_number', label: 'Enrollment', render: (row) => enrollmentById.get(row.enrollment_id)?.enrollment_number || `Enrollment ${row.enrollment_id}` },
    { key: 'status', label: 'Progress', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'assigned_at', label: 'Assigned', render: (row) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(row.assigned_at)) },
    { key: 'completed_at', label: 'Completed', render: (row) => row.completed_at ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(row.completed_at)) : '—' },
    { key: 'actions', label: 'Actions', render: (row) => <div className="flex flex-wrap gap-1">{(actions[row.status] || []).map((next) => <Button key={next} variant={next === 'cancelled' ? 'quiet' : 'secondary'} className="min-h-8 px-2 text-xs capitalize" onClick={() => setPending({ ...row, next })}>{next.replaceAll('_', ' ')}</Button>)}</div> },
  ]
  return (
    <section aria-labelledby="project-assignment-heading" className="rounded-lg border border-line bg-white p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><h2 id="project-assignment-heading" className="text-base font-semibold text-ink">Assignments and progress</h2><p className="mt-1 text-xs text-muted">Transitions are server-validated and completion is audited.</p></div><Button onClick={() => setShowForm(true)}><Plus aria-hidden="true" className="h-4 w-4" /> Assign project</Button></div>
      {success && <p role="status" className="mb-3 rounded-md border border-emerald-200 bg-emerald-50 p-2.5 text-sm text-emerald-900">{success}</p>}
      {error && !loading && <div className="mb-3"><ErrorState title="Project assignments" message={error} onRetry={() => setReloadKey((key) => key + 1)} /></div>}
      <div className="mb-3 flex flex-wrap justify-end gap-2"><select aria-label="Assignment status filter" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">{['all', 'assigned', 'in_progress', 'completed', 'cancelled'].map((value) => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}</select><select aria-label="Assignment project filter" value={projectId} onChange={(event) => { setProjectId(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm"><option value="all">All projects</option>{projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.project_name || project.name}</option>)}</select></div>
      {loading ? <LoadingState label="Loading project assignments" /> : error ? null : data.total === 0 ? <EmptyState title="No assignments found" description="Adjust the filters or assign a project to an active enrollment." /> : <><DataTable columns={columns} rows={data.items} getRowKey={(row) => row.project_assignment_id} caption="Project assignment progress" /><div className="mt-3 flex justify-between text-sm"><Button variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span className="self-center text-muted">Page {data.page} of {data.pages}</span><Button variant="secondary" disabled={page >= data.pages} onClick={() => setPage((value) => value + 1)}>Next</Button></div></>}
      {showForm && <AssignmentForm token={token} projects={projects} enrollments={enrollments} onClose={() => setShowForm(false)} onSaved={(assignment) => { setShowForm(false); setSuccess(`Project assignment ${assignment.project_assignment_id} created.`); setReloadKey((key) => key + 1) }} />}
      {pending && <ConfirmDialog title={`Mark assignment ${pending.next.replaceAll('_', ' ')}?`} message={`This records a ${pending.next.replaceAll('_', ' ')} transition for ${pending.project_name || 'the project assignment'}. Completion or cancellation is retained in history.`} confirmLabel={`Set ${pending.next.replaceAll('_', ' ')}`} busy={busy} onCancel={() => setPending(null)} onConfirm={transition} />}
    </section>
  )
}

export default function ProjectsPage() {
  const { token } = useAuth()
  return (
    <div className="animate-enter">
      <div className="mb-6"><p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Delivery</p><h1 className="mt-2 font-display text-4xl text-ink">Projects</h1><p className="mt-2 text-sm text-muted">Create project definitions and track enrollment assignment progress.</p></div>
      <div className="grid gap-5"><ProjectCatalog token={token} /><AssignmentPanel token={token} /></div>
    </div>
  )
}