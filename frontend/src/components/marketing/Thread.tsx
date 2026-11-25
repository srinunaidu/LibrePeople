import { THREAD_STAGES, type ThreadStage } from "@/lib/designSystem"

/**
 * The Thread — Karmathy's signature design element (Phase T).
 *
 * One continuous line of lifecycle nodes. The hero variant draws the full
 * thread across the page on load; the compact variant marks the module the
 * visitor is standing in during an inner page.
 *
 * Accessibility: the SVG rail is `aria-hidden`; the node labels carry the
 * meaning, so the thread is never conveyed by graphics alone. The line draws
 * once on load and every reduced-motion user sees the final state immediately.
 */

const NODE_FILLED = "bg-brand-600 border-brand-600"
const NODE_OUTLINED = "border-border-subtle bg-white"
const NODE_MISSING = "thread-node-missing bg-white border-border-subtle"

interface ThreadBaseProps {
  stages?: ThreadStage[]
}

/** Full-width horizontal thread — used on marketing heroes. */
export function ThreadHero({
  stages = THREAD_STAGES,
  className,
  broken = false,
}: ThreadBaseProps & { className?: string; broken?: boolean }) {
  return (
    <div className={`relative w-full ${className ?? ""}`} data-testid="thread-hero">
      {/* Vertical rail — mobile (the thread stacks; labels sit under nodes). */}
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 top-0 bottom-0 md:hidden"
      >
        <line x1="0" y1="0" x2="0" y2="1" pathLength={1} className="thread-svg-line" />
      </svg>
      {/* Horizontal rail — desktop. */}
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-1/2 hidden h-0.5 -translate-y-1/2 md:block"
      >
        <line x1="0" y1="0" x2="100" y2="0" pathLength={1} className="thread-svg-line" />
      </svg>

      <ol className="relative flex flex-col md:flex-row">
        {stages.map((stage, index) => {
          const isLast = index === stages.length - 1
          const isMissing = Boolean(stage.missing) || (broken && isLast)
          return (
            <li
              key={stage.id}
              className="relative flex flex-1 flex-col items-center gap-2 py-4 md:flex-row md:items-center"
            >
              <span
                className={`thread-node block h-3.5 w-3.5 rounded-full border-[2px] ${isMissing ? NODE_MISSING : isLast ? NODE_FILLED : NODE_OUTLINED}`}
                data-active={!isMissing && isLast ? true : undefined}
              />
              <span className="thread-label font-medium text-caption text-fg-muted">{stage.label}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

/**
 * Compact thread — used on inner pages to show where the current module sits
 * in the lifecycle. The active node is filled blue; the rest are outlined.
 */
export function ThreadCompact({
  stages = THREAD_STAGES,
  currentStageId,
}: ThreadBaseProps & { currentStageId?: string }) {
  const activeIndex = stages.findIndex((s) => s.id === currentStageId)
  return (
    <div className="relative w-full" data-testid="thread-compact">
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 top-0 bottom-0"
      >
        <line x1="0" y1="0" x2="0" y2="1" pathLength={1} className="thread-svg-line" />
      </svg>

      <ol className="relative flex flex-col gap-0">
        {stages.map((stage, index) => {
          const isActive = stage.id === currentStageId
          const isDone = activeIndex >= 0 && index <= activeIndex
          return (
            <li key={stage.id} className="relative flex items-start gap-3 py-2">
              <span
                className={`thread-node mt-1 block h-3.5 w-3.5 shrink-0 rounded-full border-[2px] ${isActive ? NODE_FILLED : NODE_OUTLINED} ${isDone && !isActive ? "opacity-60" : ""}`}
                data-active={isActive || undefined}
              />
              <span className="thread-label pt-0.5 font-medium text-body-sm text-fg-muted">{stage.label}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
