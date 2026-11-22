import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import TenancyPage from './pages/TenancyPage'
import CapturePage from './pages/CapturePage'
import ReviewSignPage from './pages/ReviewSignPage'
import AgentRunPage from './pages/AgentRunPage'
import ReportPage from './pages/ReportPage'
import SettlementPage from './pages/SettlementPage'
import { getToken } from './api'

function RequireAuth({ children }: { children: React.ReactNode }) {
  return getToken() ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Screen 1 — Login */}
        <Route path="/login" element={<LoginPage />} />

        {/* Screen 2 — Home */}
        <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />

        {/* Screen 3 — Tenancy overview */}
        <Route path="/tenancies/:tenancyId" element={<RequireAuth><TenancyPage /></RequireAuth>} />

        {/* Screen 4 — Guided capture */}
        <Route path="/inspections/:inspectionId/capture" element={<RequireAuth><CapturePage /></RequireAuth>} />

        {/* Screen 5 — Review and sign */}
        <Route path="/inspections/:inspectionId/review" element={<RequireAuth><ReviewSignPage /></RequireAuth>} />

        {/* Screen 6 — Agent run trace */}
        <Route path="/runs/:runId" element={<RequireAuth><AgentRunPage /></RequireAuth>} />

        {/* Screen 7 — Report with findings */}
        <Route path="/tenancies/:tenancyId/report" element={<RequireAuth><ReportPage /></RequireAuth>} />

        {/* Screen 8 — Settlement */}
        <Route path="/tenancies/:tenancyId/settlement" element={<RequireAuth><SettlementPage /></RequireAuth>} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
