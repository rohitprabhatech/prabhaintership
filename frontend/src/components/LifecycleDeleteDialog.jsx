import { useEffect, useState } from 'react'
import ConfirmDialog from './ConfirmDialog.jsx'
import { apiRequest } from '../lib/api.js'

function dependencyMessage(summary) {
  if (!summary) return 'Checking linked records before allowing deletion.'
  const linked = Object.entries(summary.dependencies)
    .filter(([, count]) => count > 0)
    .map(([name, count]) => `${count} ${name.replaceAll('_', ' ')}`)
  if (linked.length) {
    return `${summary.identifier} has linked history: ${linked.join(', ')}. Permanently deleting it is blocked; use its archive or cancellation workflow instead.`
  }
  return `No linked business records reference ${summary.identifier}. This permanently removes the record; the audit event will remain.`
}

export default function LifecycleDeleteDialog({
  resourcePath,
  resourceLabel,
  identifier,
  token,
  onCancel,
  onDeleted,
}) {
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    apiRequest(`${resourcePath}/dependencies`, { token })
      .then((result) => { if (active) setSummary(result) })
      .catch((cause) => { if (active) setError(cause.message || 'Linked record counts could not be verified.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [resourcePath, token])

  async function remove(reason) {
    if (!summary?.can_delete || saving) return
    setSaving(true)
    setError('')
    try {
      await apiRequest(resourcePath, {
        token,
        method: 'DELETE',
        body: JSON.stringify({ reason }),
      })
      onDeleted()
    } catch (cause) {
      setError(cause.message || 'The record could not be deleted.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <ConfirmDialog
      title={`Permanently delete ${resourceLabel} ${identifier}?`}
      message={[loading ? 'Checking linked records…' : dependencyMessage(summary), error].filter(Boolean).join(' ')}
      confirmLabel={summary?.can_delete ? 'Delete permanently' : 'Deletion blocked'}
      busy={saving}
      confirmDisabled={loading || !summary?.can_delete}
      reasonRequired={Boolean(summary?.can_delete)}
      reasonLabel="Reason for permanent deletion"
      onCancel={onCancel}
      onConfirm={remove}
    />
  )
}
