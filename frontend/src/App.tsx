import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import WelcomePage from './pages/WelcomePage'
import HomePage from './pages/HomePage'
import TenancyPage from './pages/TenancyPage'
import CapturePage from './pages/CapturePage'
import ReviewSignPage from './pages/ReviewSignPage'
import AgentRunPage from './pages/AgentRunPage'
import ReportPage from './pages/ReportPage'
import SettlementPage from './pages/SettlementPage'
import { OfflineBanner } from './components/ui'
import { getToken } from './api'

function RequireAuth({ children }: { children: React.ReactNode }) {
  return getToken() ? <>{children}</> : <Navigate to="/login" replace />
}

const authed = (el: React.ReactNode) => <RequireAuth>{el}</RequireAuth>

export default function App() {
  return (
    <BrowserRouter>
      <OfflineBanner />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/welcome" element={authed(<WelcomePage />)} />
        <Route path="/" element={authed(<HomePage />)} />
        <Route path="/tenancies/:tenancyId" element={authed(<TenancyPage />)} />
        <Route path="/tenancies/:tenancyId/report" element={authed(<ReportPage />)} />
        <Route path="/tenancies/:tenancyId/settlement" element={authed(<SettlementPage />)} />
        <Route path="/inspections/:inspectionId/capture" element={authed(<CapturePage />)} />
        <Route path="/inspections/:inspectionId/review" element={authed(<ReviewSignPage />)} />
        <Route path="/runs/:runId" element={authed(<AgentRunPage />)} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
