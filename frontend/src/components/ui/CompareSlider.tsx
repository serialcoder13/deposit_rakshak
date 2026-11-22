import { useRef, useState } from 'react'
import { ChevronsLeftRight, ImageOff } from 'lucide-react'

interface CompareSliderProps {
  before: string | null
  after: string | null
  /** [x, y, w, h] in 0..1 of the after image */
  bbox?: [number, number, number, number] | null
  className?: string
}

/** Before / after photos with a draggable divider. */
export function CompareSlider({ before, after, bbox, className }: CompareSliderProps) {
  const [pos, setPos] = useState(50)
  const box = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  function move(clientX: number) {
    const el = box.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const p = ((clientX - rect.left) / rect.width) * 100
    setPos(Math.min(100, Math.max(0, p)))
  }

  if (!before && !after) {
    return (
      <div className={`aspect-[4/3] rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 ${className ?? ''}`}>
        <ImageOff className="w-8 h-8" />
      </div>
    )
  }

  return (
    <div
      ref={box}
      className={`relative aspect-[4/3] rounded-2xl overflow-hidden bg-slate-900 select-none touch-pan-y ${className ?? ''}`}
      onPointerDown={(e) => {
        dragging.current = true
        ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
        move(e.clientX)
      }}
      onPointerMove={(e) => dragging.current && move(e.clientX)}
      onPointerUp={() => (dragging.current = false)}
      onPointerCancel={() => (dragging.current = false)}
    >
      {/* After (full) */}
      {after && <img src={after} alt="After" className="absolute inset-0 w-full h-full object-cover" draggable={false} />}
      {after && bbox && (
        <div
          className="absolute rounded-lg border-2 border-rose-500 shadow-[0_0_0_9999px_rgba(15,23,42,0.25)] pointer-events-none"
          style={{
            left: `${bbox[0] * 100}%`,
            top: `${bbox[1] * 100}%`,
            width: `${bbox[2] * 100}%`,
            height: `${bbox[3] * 100}%`,
          }}
        >
          <span className="absolute -inset-1 rounded-xl border-2 border-rose-400/60 animate-pulse" />
        </div>
      )}
      {/* Before (clipped) */}
      {before && (
        <div className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
          <img src={before} alt="Before" className="absolute inset-0 w-full h-full object-cover" draggable={false} />
        </div>
      )}
      <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-slate-900/70 text-white text-[11px] font-semibold backdrop-blur">
        Move-in
      </span>
      <span className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-slate-900/70 text-white text-[11px] font-semibold backdrop-blur">
        Move-out
      </span>
      {/* Divider */}
      <div className="absolute inset-y-0 w-0.5 bg-white shadow-[0_0_8px_rgba(0,0,0,.4)]" style={{ left: `${pos}%` }}>
        <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 left-1/2 w-10 h-10 rounded-full bg-white shadow-soft-lg flex items-center justify-center">
          <ChevronsLeftRight className="w-5 h-5 text-slate-700" />
        </div>
      </div>
    </div>
  )
}
