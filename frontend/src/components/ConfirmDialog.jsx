import { useEffect, useRef } from 'react'
import { Button } from './ui.jsx'

export default function ConfirmDialog({ title, message, confirmLabel = 'Confirm', busy = false, onCancel, onConfirm }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    const previousFocus = document.activeElement
    dialogRef.current?.focus()
    function handleKeyDown(event) {
      if (event.key === 'Escape' && !busy) onCancel()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      previousFocus?.focus?.()
    }
  }, [busy, onCancel])

  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-ink/40 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onCancel() }}>
      <section ref={dialogRef} role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message" tabIndex={-1} className="w-full max-w-md rounded-lg border border-line bg-white p-5 shadow-soft outline-none">
        <h2 id="confirm-title" className="text-lg font-semibold text-ink">{title}</h2>
        <p id="confirm-message" className="mt-2 text-sm leading-6 text-muted">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onCancel} disabled={busy}>Cancel</Button>
          <Button type="button" variant="danger" onClick={onConfirm} disabled={busy}>{busy ? 'Saving…' : confirmLabel}</Button>
        </div>
      </section>
    </div>
  )
}