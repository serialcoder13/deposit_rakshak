import { motion, AnimatePresence, useDragControls } from 'framer-motion'
import type { ReactNode } from 'react'
import clsx from 'clsx'

interface BottomSheetProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  className?: string
}

export function BottomSheet({ open, onClose, title, children, className }: BottomSheetProps) {
  const dragControls = useDragControls()

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          {/* Sheet */}
          <motion.div
            className={clsx(
              'fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-3xl',
              'pb-safe shadow-soft-lg max-h-[90dvh] overflow-y-auto',
              className,
            )}
            drag="y"
            dragControls={dragControls}
            dragConstraints={{ top: 0 }}
            dragElastic={{ top: 0, bottom: 0.3 }}
            onDragEnd={(_, info) => { if (info.offset.y > 80) onClose() }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          >
            {/* Drag handle */}
            <div
              className="flex justify-center pt-3 pb-1 cursor-grab active:cursor-grabbing"
              onPointerDown={e => dragControls.start(e)}
            >
              <div className="w-10 h-1 rounded-full bg-slate-200" />
            </div>
            {title && (
              <div className="px-5 pb-3 border-b border-slate-100">
                <h3 className="text-base font-semibold text-slate-800">{title}</h3>
              </div>
            )}
            <div className="p-5">{children}</div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
