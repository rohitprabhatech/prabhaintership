import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth/AuthProvider.jsx'
import { LoadingState } from './components/ui.jsx'
import AdminLayout from './layout/AdminLayout.jsx'
import BatchesPage from './pages/BatchesPage.jsx'
import CertificatesPage from './pages/CertificatesPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import EnrollmentsPage from './pages/EnrollmentsPage.jsx'
import FinancePage from './pages/FinancePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProgramsPage from './pages/ProgramsPage.jsx'
import ProjectsPage from './pages/ProjectsPage.jsx'
import ReportsPage from './pages/ReportsPage.jsx'
import StudentProfilePage from './pages/StudentProfilePage.jsx'
import StudentsPage from './pages/StudentsPage.jsx'
import WorkspacePage from './pages/WorkspacePage.jsx'

function ProtectedRoutes() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'checking') return <LoadingState label="Checking administrator session" />
  if (status !== 'authenticated') return <Navigate to="/login" replace state={{ from: location.pathname }} />

  return (
    <Routes>
      <Route element={<AdminLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="students" element={<StudentsPage />} />
        <Route path="students/:studentId" element={<StudentProfilePage />} />
        <Route path="programs" element={<ProgramsPage />} />
        <Route path="batches" element={<BatchesPage />} />
        <Route path="enrollments" element={<EnrollmentsPage />} />
        <Route path="finance" element={<FinancePage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="certificates" element={<CertificatesPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  const { status } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={status === 'authenticated' ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/*" element={<ProtectedRoutes />} />
    </Routes>
  )
}