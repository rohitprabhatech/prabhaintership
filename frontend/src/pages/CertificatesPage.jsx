import { useEffect, useRef, useState } from 'react'
import { History, Plus, RefreshCw } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import ConfirmDialog from '../components/ConfirmDialog.jsx'
import { Button, DataTable, EmptyState, ErrorState, LoadingState, Modal, StatusBadge, TextField } from '../components/ui.jsx'
import { apiRequest } from '../lib/api.js'
import { getAllPages } from '../lib/adminData.js'

const PAGE_SIZE = 20

function localToIso(value) {
  return value ? new Date(value).toISOString() : null
}

function CertificateForm({ action, token, onClose, onSaved }) {
  const submittingRef = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [enrollments, setEnrollments] = useState([])
  const [loadingEnrollments, setLoadingEnrollments] = useState(action.type === 'issue')
  const [confirmation, setConfirmation] = useState(null)
  const [values, setValues] = useState({ enrollment_id: '', certificate_type: '', issued_at: '', document_uri: '', reason: '' })
  const current = action.certificate
  const title = action.type === 'issue' ? 'Issue certificate' : action.type === 'replace' ? 'Replace certificate' : action.type === 'revoke' ? 'Revoke certificate' : 'Record correction'

  useEffect(() => {
    if (action.type !== 'issue') return undefined
    let active = true
    getAllPages('enrollments', { status: 'all' }, token)
      .then((page) => { if (active) setEnrollments(page.items) })
      .catch((cause) => { if (active) setError(cause.message || 'Enrollments could not be loaded.') })
      .finally(() => { if (active) setLoadingEnrollments(false) })
    return () => { active = false }
  }, [action.type, token])

  function update(event) {
    setValues((currentValues) => ({ ...currentValues, [event.target.name]: event.target.value }))
  }

  function submit(event) {
    event.preventDefault()
    if (submittingRef.current) return
    const needsReason = ['replace', 'revoke', 'correction'].includes(action.type)
    if (action.type === 'issue' && (!values.enrollment_id || !values.certificate_type.trim())) {
      setError('Select an enrollment and enter a certificate type.')
      return
    }
    if (needsReason && !values.reason.trim()) {
      setError('Enter a reason of 1 to 500 characters.')
      return
    }
    if (values.reason.length > 500 || values.certificate_type.length > 128 || values.document_uri.length > 2048) {
      setError('One or more fields exceed the API length limit.')
      return
    }
    const payload = action.type === 'issue'
      ? { enrollment_id: Number(values.enrollment_id), certificate_type: values.certificate_type.trim(), issued_at: localToIso(values.issued_at), document_uri: values.document_uri.trim() || null }
      : action.type === 'replace'
        ? { issued_at: localToIso(values.issued_at), document_uri: values.document_uri.trim() || null, reason: values.reason.trim() }
        : { reason: values.reason.trim() }
    setError('')
    setConfirmation(payload)
  }

  async function confirm() {
    if (!confirmation || submittingRef.current) return
    submittingRef.current = true
    setSaving(true)
    setError('')
    const endpoint = action.type === 'issue'
      ? 'certificates'
      : action.type === 'replace'
        ? `certificates/${current.certificate_id}/replacement`
        : `certificates/${current.certificate_id}/${action.type === 'revoke' ? 'revocation' : 'corrections'}`
    try {
      const result = await apiRequest(endpoint, { token, method: 'POST', body: JSON.stringify(confirmation) })
      onSaved(result, action.type)
    } catch (cause) {
      setConfirmation(null)
      const message = cause.code === 'certificate_conflict'
        ? 'That certificate number already exists or conflicts with existing history.'
        : cause.message || 'The certificate action failed. No success is recorded.'
      setError(message)
    } finally {
      submittingRef.current = false
      setSaving(false)
    }
  }

  const confirmMessage = action.type === 'issue'
    ? 'Issue a certificate for the selected enrollment? A unique certificate number will be generated, and the issuance record will be immutable.'
    : action.type === 'replace'
      ? `Replace ${current.certificate_number} with a new automatically numbered certificate? The original will remain in history and be marked replaced.`
      : action.type === 'revoke'
        ? `Revoke certificate ${current.certificate_number}? This creates a permanent revocation event.`
        : `Record a correction event for ${current.certificate_number}? The original certificate details will not be rewritten.`

  return (
    <Modal title={title} onClose={saving ? () => {} : onClose}>
      <form onSubmit={submit} noValidate className="grid gap-4">
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}
        {action.type === 'issue' && (loadingEnrollments ? <LoadingState label="Loading enrollments" /> : <div className="grid gap-1.5"><label htmlFor="certificate-enrollment" className="text-sm font-semibold text-ink">Enrollment</label><select id="certificate-enrollment" name="enrollment_id" value={values.enrollment_id} onChange={update} className="min-h-11 rounded-md border border-line bg-white px-3 text-sm"><option value="">Select an enrollment</option>{enrollments.map((enrollment) => <option key={enrollment.enrollment_id} value={enrollment.enrollment_id}>{enrollment.enrollment_number} · {enrollment.status}</option>)}</select></div>)}
        {(action.type === 'issue' || action.type === 'replace') && <p className="rounded-md bg-orange-50 px-3 py-2 text-sm text-orange-950">A unique certificate number will be generated after confirmation.</p>}
        {action.type === 'issue' && <TextField id="certificate-type" name="certificate_type" label="Certificate type" maxLength={128} required value={values.certificate_type} onChange={update} />}
        {(action.type === 'issue' || action.type === 'replace') && <>
          <TextField id="certificate-issued-at" name="issued_at" label="Issued at (optional)" type="datetime-local" value={values.issued_at} onChange={update} />
          <TextField id="certificate-document" name="document_uri" label="Private document URI (optional)" maxLength={2048} value={values.document_uri} onChange={update} />
        </>}
        {action.type !== 'issue' && <div className="grid gap-1.5"><label htmlFor="certificate-reason" className="text-sm font-semibold text-ink">Reason</label><textarea id="certificate-reason" name="reason" required maxLength={500} rows={3} value={values.reason} onChange={update} className="rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-100" /></div>}
        <div className="flex justify-end gap-2 border-t border-line pt-4"><Button type="button" variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button><Button type="submit" disabled={saving || loadingEnrollments}>{saving ? 'Submitting…' : 'Review action'}</Button></div>
      </form>
      {confirmation && <ConfirmDialog title={`Confirm ${title.toLowerCase()}?`} message={confirmMessage} confirmLabel={title} busy={saving} onCancel={() => setConfirmation(null)} onConfirm={confirm} />}
    </Modal>
  )
}

function CertificateHistory({ certificate, token, onClose }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest(`certificates/${certificate.certificate_id}`, { token }),
      apiRequest(`certificates/${certificate.certificate_id}/events`, { token }),
    ])
      .then(([details, events]) => { if (active) setData({ details, events }) })
      .catch((cause) => { if (active) setError(cause.message || 'Certificate history could not be loaded.') })
    return () => { active = false }
  }, [certificate.certificate_id, token])
  const columns = [
    { key: 'occurred_at', label: 'Occurred', render: (row) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(row.occurred_at)) },
    { key: 'event_type', label: 'Event', render: (row) => <StatusBadge status={row.event_type} /> },
    { key: 'reason', label: 'Reason' },
    { key: 'related_certificate_id', label: 'Related certificate', render: (row) => row.related_certificate_id || '—' },
  ]
  return (
    <Modal title="Certificate history" onClose={onClose}>
      {error ? <ErrorState title="Certificate history unavailable" message={error} /> : !data ? <LoadingState label="Loading certificate record and events" /> : <div className="grid gap-4">
        <dl className="grid gap-3 sm:grid-cols-2">{[
          ['Certificate number', data.details.certificate_number], ['Type', data.details.certificate_type], ['Enrollment', data.details.enrollment_number || data.details.enrollment_id], ['Student', data.details.full_name || data.details.student_number || '—'], ['Program', data.details.program_code || '—'], ['Issued', new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(data.details.issued_at))], ['Status', <StatusBadge status={data.details.derived_status} />],
        ].map(([label, value]) => <div key={label}><dt className="text-xs font-semibold uppercase text-muted">{label}</dt><dd className="mt-1 text-sm text-ink">{value}</dd></div>)}</dl>
        <div><h3 className="mb-2 text-sm font-semibold text-ink">Traceable events</h3><DataTable columns={columns} rows={data.events} getRowKey={(row) => row.certificate_event_id} caption="Certificate event history" emptyMessage="No certificate events." /></div>
      </div>}
      <div className="mt-4 flex justify-end"><Button variant="secondary" onClick={onClose}>Close</Button></div>
    </Modal>
  )
}

export default function CertificatesPage() {
  const { token } = useAuth()
  const [data, setData] = useState(null)
  const [queryDraft, setQueryDraft] = useState('')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [action, setAction] = useState(null)
  const [history, setHistory] = useState(null)
  const [success, setSuccess] = useState('')
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), status })
    if (query) params.set('q', query)
    apiRequest(`certificates?${params}`, { token })
      .then((result) => { if (active) setData(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Certificates could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, page, query, status, reloadKey])

  const columns = [
    { key: 'certificate_number', label: 'Certificate' },
    { key: 'full_name', label: 'Student', render: (row) => <span>{row.full_name || row.student_number || '—'}<span className="mt-0.5 block text-xs text-muted">{row.enrollment_number || `Enrollment ${row.enrollment_id}`}</span></span> },
    { key: 'program_code', label: 'Program', render: (row) => row.program_code || '—' },
    { key: 'certificate_type', label: 'Type' },
    { key: 'issued_at', label: 'Issued', render: (row) => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(row.issued_at)) },
    { key: 'derived_status', label: 'Status', render: (row) => <StatusBadge status={row.derived_status} /> },
    { key: 'actions', label: 'Actions', render: (row) => <div className="flex flex-wrap gap-1"><Button variant="quiet" className="min-h-8 px-2" aria-label={`History for ${row.certificate_number}`} onClick={() => setHistory(row)}><History aria-hidden="true" className="h-4 w-4" /></Button>{row.derived_status === 'issued' && <><Button variant="secondary" className="min-h-8 px-2 text-xs" onClick={() => setAction({ type: 'replace', certificate: row })}>Replace</Button><Button variant="quiet" className="min-h-8 px-2 text-xs text-red-700" onClick={() => setAction({ type: 'revoke', certificate: row })}>Revoke</Button><Button variant="quiet" className="min-h-8 px-2 text-xs" onClick={() => setAction({ type: 'correction', certificate: row })}>Correction</Button></>}</div> },
  ]

  function saved(result, type) {
    setAction(null)
    const identifier = result.certificate_number || result.certificate_id || result.certificate_event_id
    setSuccess(`${type === 'issue' ? 'Certificate issued' : type === 'replace' ? 'Certificate replaced' : type === 'revoke' ? 'Certificate revoked' : 'Correction recorded'} successfully by the API${identifier ? ` · ${identifier}` : ''}.`)
    setReloadKey((key) => key + 1)
  }

  return (
    <div className="animate-enter">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase text-orange-700">Prabha Technology / Records</p><h1 className="mt-2 font-display text-4xl text-ink">Certificates</h1><p className="mt-2 text-sm text-muted">Issue immutable records and trace replacements, revocations, and corrections.</p></div><Button onClick={() => setAction({ type: 'issue' })}><Plus aria-hidden="true" className="h-4 w-4" /> Issue certificate</Button></div>
      {success && <p role="status" aria-live="polite" className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">{success}</p>}
      <div className="mb-4 flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"><RefreshCw aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" /><p>Issued certificates cannot be edited or deleted. Replace, revoke, and correction actions preserve the original issuance and append traceable events.</p></div>
      <form onSubmit={(event) => { event.preventDefault(); setPage(1); setQuery(queryDraft.trim()) }} className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-white p-4">
        <TextField id="certificate-search" label="Search certificates" type="search" maxLength={128} value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} placeholder="Number, student, enrollment" className="min-w-[min(100%,18rem)] flex-1" />
        <div className="grid min-w-40 gap-1.5"><label htmlFor="certificate-status" className="text-xs font-semibold text-muted">Status</label><select id="certificate-status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }} className="min-h-10 rounded-md border border-line bg-white px-3 text-sm">{['all', 'issued', 'replaced', 'revoked'].map((value) => <option key={value} value={value}>{value}</option>)}</select></div>
        <Button type="submit" variant="secondary">Search</Button>
      </form>
      {loading ? <LoadingState label="Loading certificates" /> : error ? <ErrorState title="Certificates could not be loaded" message={error} onRetry={() => setReloadKey((key) => key + 1)} /> : data.total === 0 ? <EmptyState title="No certificates found" description="Adjust the search or status filter, or issue a certificate for an enrollment." action={<Button onClick={() => setAction({ type: 'issue' })}><Plus aria-hidden="true" className="h-4 w-4" /> Issue certificate</Button>} /> : (
        <><div className="mb-3 flex justify-between text-sm text-muted"><span>{data.total.toLocaleString('en-IN')} certificates</span><span>Page {data.page} of {data.pages}</span></div><DataTable columns={columns} rows={data.items} getRowKey={(row) => row.certificate_id} caption="Certificate report" /><div className="mt-4 flex justify-between"><Button variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><Button variant="secondary" disabled={page >= data.pages} onClick={() => setPage((value) => value + 1)}>Next</Button></div></>
      )}
      {action && <CertificateForm action={action} token={token} onClose={() => setAction(null)} onSaved={saved} />}
      {history && <CertificateHistory certificate={history} token={token} onClose={() => setHistory(null)} />}
    </div>
  )
}