import { cn } from "@/lib/utils"
import { IconInbox } from "@/components/icons"
import { StatusPill } from "@/components/ui"

/**
 * "Needs your action" section used at the top of every role-based home.
 *
 * Renders a list of actionable items, each with a count and a one-click
 * action. Items with zero counts are hidden so the section stays calm.
 */
export interface NeedItem {
  id: string
  label: string
  count: number
  description?: string
  actionLabel?: string
  onAction?: () => void
  icon?: React.ReactNode
  tone?: "brand" | "amber" | "rose" | "green" | "violet" | "teal" | "slate"
}

export function NeedsAction({
  title = "Needs your action",
  items,
  emptyMessage = "Nothing needs your attention right now.",
}: {
  title?: string
  items: NeedItem[]
  emptyMessage?: string
}) {
  const visible = items.filter((i) => i.count > 0)

  return (
    <section className="card overflow-hidden mb-0 border border-[var(--border)] bg-[var(--surface)] rounded-[var(--radius-md)]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
        <div className="flex items-center gap-2.5">
          <span className="icon-tile icon-tile-amber">
            <IconInbox className="w-4 h-4" />
          </span>
          <div>
            <h2 className="text-base font-semibold text-fg leading-tight">{title}</h2>
            <p className="text-xs text-fg-muted mt-0.5">
              {visible.length === 0 ? emptyMessage : `${visible.length} item${visible.length === 1 ? "" : "s"} waiting`}
            </p>
          </div>
        </div>
        {visible.length > 0 && (
          <StatusPill status={String(visible.reduce((s, i) => s + i.count, 0))} tone="amber" />
        )}
      </div>

      {visible.length === 0 ? (
        <div className="px-5 py-6 text-center text-sm text-fg-muted">
          {emptyMessage}
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border)]">
          {visible.map((item) => (
            <li key={item.id} className="flex items-center gap-3 px-4 py-3 hover:bg-[var(--surface-hover)] transition-colors">
              <span
                className={cn(
                  "inline-flex items-center justify-center w-8 h-8 rounded-lg text-sm font-bold shrink-0",
                  item.tone === "rose"
                    ? "bg-error-light text-error"
                    : item.tone === "amber"
                    ? "bg-warning-light text-warning"
                    : item.tone === "green"
                    ? "bg-success-light text-success-text"
                    : "bg-brand-100 text-brand-700"
                )}
                aria-hidden="true"
              >
                {item.icon ?? item.count}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-fg">{item.label}</p>
                {item.description && (
                  <p className="text-xs text-fg-muted mt-0.5">{item.description}</p>
                )}
              </div>
              <span className="text-base font-bold text-fg tabular-nums shrink-0">{item.count}</span>
              {item.onAction && (
                <button
                  type="button"
                  onClick={item.onAction}
                  className="ml-2 shrink-0 inline-flex items-center justify-center rounded-[var(--radius-md)] px-3 py-1.5 text-xs font-semibold bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transition-colors border border-transparent"
                >
                  {item.actionLabel ?? "View"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}