import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  BadgeIndianRupee, BookOpen, Boxes, BriefcaseBusiness, Building2, ChevronRight, FileText,
  ClipboardList, FileBadge, GraduationCap, KeyRound, LayoutDashboard, LogOut, Menu, X,
} from 'lucide-react'
import { useAuth } from '../auth/AuthProvider.jsx'
import { Button } from '../components/ui.jsx'

const navigation = [
  { label: 'Overview', to: '/', icon: LayoutDashboard },
  { label: 'Students', to: '/students', icon: GraduationCap },
  { label: 'Programs', to: '/programs', icon: BookOpen },
  { label: 'Batches', to: '/batches', icon: Boxes },
  { label: 'Enrollments', to: '/enrollments', icon: ClipboardList },
  { label: 'Finance', to: '/finance', icon: BadgeIndianRupee },
  { label: 'Projects', to: '/projects', icon: BriefcaseBusiness },
  { label: 'Certificates', to: '/certificates', icon: FileBadge },
  { label: 'Reports', to: '/reports', icon: FileText },
  { label: 'Change password', to: '/change-password', icon: KeyRound },
]

function Brand() {
  return (
    <div className="flex items-center gap-3 px-5 py-5">
      <div className="grid h-10 w-10 place-items-center rounded-md bg-orange-600 text-white">
        <Building2 aria-hidden="true" className="h-5 w-5" />
      </div>
      <div>
        <p className="text-sm font-bold leading-5 text-ink">Prabha Technology</p>
        <p className="text-xs text-muted">Administration</p>
      </div>
    </div>
  )
}

function Sidebar({ close }) {
  return (
    <>
      <Brand />
      <div className="px-5 pb-2 pt-3 text-[11px] font-bold uppercase text-muted">Workspace</div>
      <nav aria-label="Main navigation" className="grid gap-1 px-3">
        {navigation.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            onClick={close}
            className={({ isActive }) => `group flex min-h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors ${isActive ? 'bg-orange-50 text-orange-700' : 'text-muted hover:bg-canvas hover:text-ink'}`}
          >
            {({ isActive }) => <><Icon aria-hidden="true" className="h-[18px] w-[18px]" /><span className="flex-1">{label}</span>{isActive && <ChevronRight aria-hidden="true" className="h-4 w-4" />}</>}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto border-t border-line px-5 py-4 text-xs leading-5 text-muted">
        <span className="block font-semibold text-ink">Internal workspace</span>
        Authorized administrators only
      </div>
    </>
  )
}

export default function AdminLayout() {
  const { admin, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const current = navigation.find((item) => location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(`${item.to}/`)))?.label || 'Administration'
  const initials = (admin?.username || 'A').slice(0, 1).toUpperCase()

  return (
    <div className="min-h-screen bg-canvas lg:flex">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-line bg-white lg:flex">
        <Sidebar />
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="presentation">
          <button type="button" aria-label="Close navigation" onClick={() => setMenuOpen(false)} className="absolute inset-0 bg-ink/40" />
          <aside className="relative flex h-full w-[min(19rem,86vw)] flex-col border-r border-line bg-white shadow-soft" aria-label="Mobile navigation">
            <button type="button" aria-label="Close menu" onClick={() => setMenuOpen(false)} className="absolute right-3 top-5 grid h-9 w-9 place-items-center rounded-md text-muted hover:bg-canvas focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"><X className="h-5 w-5" /></button>
            <Sidebar close={() => setMenuOpen(false)} />
          </aside>
        </div>
      )}

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex min-h-[4.5rem] items-center justify-between border-b border-line bg-white/95 px-4 backdrop-blur sm:px-7">
          <div className="flex items-center gap-3">
            <button type="button" aria-label="Open navigation" onClick={() => setMenuOpen(true)} className="grid h-10 w-10 place-items-center rounded-md text-muted hover:bg-canvas focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 lg:hidden"><Menu aria-hidden="true" className="h-5 w-5" /></button>
            <p className="text-sm font-semibold text-ink">{current}</p>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-ink">{admin?.username}</p>
              <p className="text-xs text-muted">Administrator</p>
            </div>
            <div aria-hidden="true" className="grid h-9 w-9 place-items-center rounded-full bg-orange-100 text-sm font-bold text-orange-700">{initials}</div>
            <Button variant="quiet" className="min-h-9 px-2 sm:px-3" onClick={signOut} aria-label="Sign out">
              <LogOut aria-hidden="true" className="h-4 w-4" /><span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </header>
        <main id="main-content" className="mx-auto w-full max-w-[1440px] px-4 py-7 sm:px-7 sm:py-9">
          <Outlet />
        </main>
      </div>
    </div>
  )
}