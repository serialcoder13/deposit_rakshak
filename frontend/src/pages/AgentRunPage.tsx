/**
 * AgentRunPage.tsx — Screen 6 (SPEC §11)
 * Live SSE trace of agent steps. Navigates to report on "done".
 */
import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getToken, type AgentStepEvent } from '../api'

const KIND_ICON: Record<string, string> = {
  thought: '💭',
  tool_call: '🔧',
  tool_result: '📋',
  error: '❌',
  done: '✅',
  failed: '💥',
}

export default function AgentRunPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [steps, setSteps] = useState<AgentStepEvent[]>([])
  const [status, setStatus] = useState<'running' | 'done' | 'failed'>('running')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!runId) return
    const token = getToken()
    const url = `/api/runs/${runId}/events${token ? `?token=${token}` : ''}`

    // Use EventSource; auth header not supported by EventSource API — append token as query param
    // The backend should accept ?token= as a fallback (implement in task A3 if needed)
    const es = new EventSource(url)

    es.onmessage = (e: MessageEvent) => {
      try {
        const step = JSON.parse(e.data) as AgentStepEvent
        setSteps(prev => [...prev, step])

        if (step.kind === 'done') {
          setStatus('done')
          es.close()
          // Navigate to report after a short pause
          setTimeout(() => {
            // We need tenancy_id — the run page should get it from the run; for now navigate back
            navigate(-1)
          }, 2000)
        }
        if (step.kind === 'failed' || step.kind === 'error') {
          setStatus('failed')
          es.close()
        }
      } catch {
        // ignore parse errors
      }
    }

    es.onerror = () => {
      setStatus('failed')
      es.close()
    }

    return () => es.close()
  }, [runId, navigate])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps])

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <button onClick={() => navigate(-1)} style={styles.backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>Agent Run</h2>
        <StatusDot status={status} />
      </div>

      <div style={styles.traceList}>
        {steps.length === 0 && (
          <div style={{ padding: '32px', textAlign: 'center', color: '#9ca3af' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>🤔</div>
            <p>Thinking…</p>
          </div>
        )}
        {steps.map((step, i) => (
          <div key={i} style={styles.stepRow}>
            <span style={{ fontSize: 20, marginRight: 10 }}>{KIND_ICON[step.kind] ?? '•'}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{step.label || step.kind}</div>
              {step.tool_name && <div style={{ fontSize: 12, color: '#7c3aed' }}>{step.tool_name}</div>}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {status === 'done' && (
        <div style={{ padding: '16px 20px', background: '#d1fae5', textAlign: 'center', fontWeight: 600, color: '#065f46' }}>
          ✅ Run complete — navigating to report…
        </div>
      )}
      {status === 'failed' && (
        <div style={{ padding: '16px 20px', background: '#fee2e2', textAlign: 'center', fontWeight: 600, color: '#991b1b' }}>
          ❌ Run failed — check logs
        </div>
      )}
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = { running: '#f59e0b', done: '#10b981', failed: '#ef4444' }
  return (
    <div style={{ width: 10, height: 10, borderRadius: '50%', background: colors[status] ?? '#9ca3af', boxShadow: status === 'running' ? '0 0 0 3px #fde68a' : 'none' }} />
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 480, margin: '0 auto', display: 'flex', flexDirection: 'column', height: '100dvh', fontFamily: 'system-ui, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #e5e7eb' },
  traceList: { flex: 1, overflowY: 'auto', padding: '16px 20px' },
  stepRow: { display: 'flex', alignItems: 'flex-start', padding: '10px 0', borderBottom: '1px solid #f3f4f6' },
  backBtn: { background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', color: '#3b82d4' },
}
