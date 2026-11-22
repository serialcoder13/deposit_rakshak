/**
 * CapturePage.tsx — Screen 4 (SPEC §11)
 * Guided slot-by-slot camera capture with ghost overlay for move-out.
 * Camera component, photo hashing, and upload live here (implement in F3/F4).
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

export default function CapturePage() {
  const { inspectionId } = useParams<{ inspectionId: string }>()
  const navigate = useNavigate()
  const [currentSlotIndex, setCurrentSlotIndex] = useState(0)

  const { data: inspection, isLoading } = useQuery({
    queryKey: ['inspection', inspectionId],
    queryFn: () => api.getInspection(inspectionId!),
  })

  if (isLoading || !inspection) return <div style={styles.center}>Loading…</div>

  const slots = inspection.slots
  const slot = slots[currentSlotIndex]
  const progress = `${currentSlotIndex + 1} of ${slots.length}`

  function handleNext() {
    if (currentSlotIndex < slots.length - 1) {
      setCurrentSlotIndex(i => i + 1)
    } else {
      navigate(`/inspections/${inspectionId}/review`)
    }
  }

  return (
    <div style={styles.page}>
      {/* Progress bar */}
      <div style={styles.header}>
        <button onClick={() => navigate(-1)} style={styles.backBtn}>✕</button>
        <span style={{ fontWeight: 600 }}>Capture · {progress}</span>
        <div />
      </div>

      {/* Slot info */}
      <div style={styles.slotInfo}>
        <h2 style={{ margin: '0 0 4px' }}>{slot.label}</h2>
        <p style={{ margin: 0, color: '#57606a', fontSize: 14 }}>{slot.guidance}</p>
      </div>

      {/* Camera area — full implementation in F3/F4 */}
      <div style={styles.cameraArea}>
        {slot.captured ? (
          <div style={{ textAlign: 'center' }}>
            <img src={slot.photo!.url} alt={slot.label} style={{ maxWidth: '100%', maxHeight: 320, borderRadius: 12 }} />
            <p style={{ color: '#059669', fontWeight: 600, marginTop: 12 }}>✓ Photo captured</p>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: '#9ca3af' }}>
            <div style={{ fontSize: 64 }}>📷</div>
            <p>Camera capture — implement in task F3</p>
            <p style={{ fontSize: 12 }}>getUserMedia, resize to 1280px, SHA-256, upload</p>
          </div>
        )}
      </div>

      {/* Controls */}
      <div style={styles.controls}>
        {inspection.type === 'move_out' && (
          <p style={{ fontSize: 12, color: '#57606a', margin: '0 0 8px' }}>
            👻 Ghost overlay at 40% opacity — implement in F4
          </p>
        )}
        <button style={styles.btn} onClick={handleNext}>
          {currentSlotIndex < slots.length - 1 ? 'Next slot →' : 'Done — Review'}
        </button>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 480, margin: '0 auto', display: 'flex', flexDirection: 'column', height: '100dvh', fontFamily: 'system-ui, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #e5e7eb' },
  slotInfo: { padding: '16px 20px', background: 'rgba(0,0,0,0.03)' },
  cameraArea: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', color: '#fff' },
  controls: { padding: '16px 20px', borderTop: '1px solid #e5e7eb' },
  btn: { width: '100%', padding: '14px', fontSize: 16, fontWeight: 600, background: '#1e40af', color: '#fff', border: 'none', borderRadius: 10, cursor: 'pointer' },
  backBtn: { background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#fff' },
  center: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontFamily: 'system-ui' },
}
