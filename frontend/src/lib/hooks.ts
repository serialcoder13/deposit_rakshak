import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, getToken, type Stage } from '../api'
import { STAGE_INFO } from './journey'

/** The signed-in user. Cached and shared by every screen. */
export function useMe(poll = false) {
  return useQuery({
    queryKey: ['me'],
    queryFn: api.me,
    enabled: !!getToken(),
    refetchInterval: poll ? 3000 : false,
  })
}

/** Toast once when a polled stage changes (not on first load). */
export function useStageToast(stage: Stage | undefined) {
  const prev = useRef<Stage | undefined>(undefined)
  useEffect(() => {
    if (!stage) return
    if (prev.current && prev.current !== stage) {
      toast.success(`Moved to: ${STAGE_INFO[stage].label}`)
    }
    prev.current = stage
  }, [stage])
}

/** Online / offline state */
export function useOnline() {
  const [online, setOnline] = useState(typeof navigator === 'undefined' ? true : navigator.onLine)
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])
  return online
}

/** Animate a number from its previous value to the new one. */
export function useCountUp(value: number, duration = 900) {
  const [shown, setShown] = useState(0)
  const from = useRef(0)
  useEffect(() => {
    const start = from.current
    const t0 = performance.now()
    let raf = 0
    const step = (now: number) => {
      const p = Math.min((now - t0) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      const v = start + (value - start) * eased
      setShown(v)
      if (p < 1) raf = requestAnimationFrame(step)
      else from.current = value
    }
    raf = requestAnimationFrame(step)
    return () => {
      cancelAnimationFrame(raf)
      from.current = value
    }
  }, [value, duration])
  return shown
}
