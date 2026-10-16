import { useEffect, useRef } from 'react'
import { AlertCircle, Check, LoaderCircle, X } from 'lucide-react'

const buttonStyles = {
  primary: 'bg-orange-600 text-white hover:bg-orange-700 focus-visible:ring-orange-500',
  secondary: 'border border-line bg-white text-ink hover:bg-canvas focus-visible:ring-orange-500',
  quiet: 'text-muted hover:bg-canvas hover:text-ink focus-visible:ring-orange-500',
  danger: 'bg-red-700 text-white hover:bg-red-800 focus-visible:ring-red-500',
}

export function Button({ variant = 'primary', className = '', children, ...props }) {
  return (
    <button
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-55 ${buttonStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function TextField({ id, label, hint, error, className = '', ...props }) {
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ')
  return (
    <div className={`grid gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-sm font-semibold text-ink">{label}</label>
      <input
        id={id}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy || undefined}
        className="min-h-11 rounded-md border border-line bg-white px-3 text-sm text-ink outline-none transition focus:border-orange-500 focus:ring-2 focus:ring-orange-100 aria-[invalid=true]:border-red-600"
        {...props}
      />
      {hint && <p id={`${id}-hint`} className="text-xs text-muted">{hint}</p>}
      {error && <p id={`${id}-error`} className="text-xs font-medium text-red-700">{error}</p>}
    </div>
  )
}

export function StatusBadge({ status }) {
  const key = String(status || 'unknown').toLowerCase()
  const styles = {
    active: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    completed: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    issued: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
    draft: 'bg-amber-50 text-amber-800 ring-amber-200',
    planned: 'bg-amber-50 text-amber-800 ring-amber-200',
    in_progress: 'bg-sky-50 text-sky-800 ring-sky-200',
    inactive: 'bg-stone-100 text-stone-700 ring-stone-200',
    archived: 'bg-stone-100 text-stone-700 ring-stone-200',
    cancelled: 'bg-red-50 text-red-800 ring-red-200',
    withdrawn: 'bg-red-50 text-red-800 ring-red-200',
    revoked: 'bg-red-50 text-red-800 ring-red-200',
  }
  const label = key.replaceAll('_', ' ')
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset ${styles[key] || 'bg-slate-50 text-slate-700 ring-slate-200'}`}>
      {label}
    </span>
  )
}

export function LoadingState({ label = 'Loading' }) {
  return (
    <div role="status" className="flex min-h-40 items-center justify-center gap-3 text-sm text-muted">
      <LoaderCircle aria-hidden="true" className="h-5 w-5 animate-spin text-orange-600" />
      <span>{label}<span className="sr-only">, please wait</span></span>
    </div>
  )
}

export function EmptyState({ title, description, action }) {
  return (
    <div className="grid min-h-48 place-items-center rounded-lg border border-dashed border-line bg-white px-6 py-10 text-center">
      <div className="max-w-md">
        <div className="mx-auto mb-3 grid h-10 w-10 place-items-center rounded-full bg-orange-50 text-orange-700">
          <Check aria-hidden="true" className="h-5 w-5" />
        </div>
        <h2 className="font-semibold text-ink">{title}</h2>
        <p className="mt-1 text-sm leading-6 text-muted">{description}</p>
        {action && <div className="mt-4">{action}</div>}
      </div>
    </div>
  )
}

export function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
      <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="flex-1">
        <p className="font-semibold">{title}</p>
        {message && <p className="mt-1 text-red-800">{message}</p>}
        {onRetry && <button type="button" onClick={onRetry} className="mt-2 font-semibold underline underline-offset-2">Try again</button>}
      </div>
    </div>
  )
}

export function DataTable({ columns, rows, getRowKey, caption, emptyMessage = 'No records to display.' }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-white">
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-canvas text-xs uppercase text-muted">
          <tr>{columns.map((column) => <th key={column.key} scope="col" className="whitespace-nowrap px-4 py-3 font-semibold">{column.label}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.length ? rows.map((row) => (
            <tr key={getRowKey(row)} className="hover:bg-orange-50/40">
              {columns.map((column, index) => (
                <td key={column.key} className="whitespace-nowrap px-4 py-3 text-ink">
                  {index === 0 ? <span className="font-medium">{column.render ? column.render(row) : row[column.key]}</span> : column.render ? column.render(row) : row[column.key]}
                </td>
              ))}
            </tr>
          )) : (
            <tr><td colSpan={columns.length} className="px-4 py-10 text-center text-muted">{emptyMessage}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

export function Modal({ title, onClose, children }) {
  const dialogRef = useRef(null)
  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return undefined
    const previousFocus = document.activeElement
    dialog.showModal()
    return () => {
      dialog.close()
      previousFocus?.focus?.()
    }
  }, [])

  return (
    <dialog ref={dialogRef} aria-labelledby="modal-title" onCancel={onClose} className="w-[min(92vw,34rem)] rounded-lg p-0 text-ink shadow-soft backdrop:bg-ink/40">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <h2 id="modal-title" className="text-lg font-semibold">{title}</h2>
        <button type="button" onClick={onClose} aria-label="Close dialog" className="grid h-9 w-9 place-items-center rounded-md text-muted hover:bg-canvas focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500">
          <X aria-hidden="true" className="h-5 w-5" />
        </button>
      </div>
      <div className="p-5">{children}</div>
    </dialog>
  )
}