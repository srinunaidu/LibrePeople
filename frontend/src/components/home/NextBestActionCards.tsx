import { cn } from "@/lib/utils"
import { IconAlert, IconCalendar, IconClock, IconPalm } from "@/components/icons"

export interface ActionCard {
  id: string
  title: string
  description: string
  count: number
  priority: number
  ctaLabel: string
  onCta: () => void
  tone: "brand" | "amber" | "rose" | "green"
  icon?: React.ReactNode
}

const toneIcon: Record<string, React.ReactNode> = {
  brand: <IconAlert className="w-4 h-4" />,
  amber: <IconClock className="w-4 h-4" />,
  rose: <IconCalendar className="w-4 h-4" />,
  green: <IconPalm className="w-4 h-4" />,
}

const toneClasses: Record<string, string> = {
  brand: "bg-brand-100 text-brand-700",
  amber: "bg-warning-light text-warning-text border-warning",
  rose: "bg-error-light text-error-text border-error",
  green: "bg-success-light text-success-text border-success",
}

/**
 * Ranked Next Best Action cards — reuse NeedsAction pattern but as cards.
 * Driven by tenant state counts; sorted by priority.
 */
export function NextBestActionCards({
  cards,
  emptyMessage = "You're all caught up — no pending actions.",
}: {
  cards: ActionCard[]
  emptyMessage?: string
}) {
  const visible = [...cards].filter((c) => c.count > 0).sort((a, b) => a.priority - b.priority)

  if (visible.length === 0) {
    return (
      <div className="mk-card p-6 text-center mb-6">
        <p className="text-sm text-fg-muted">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="mb-6">
      <h2 className="text-h2-app text-fg mb-3">Next best actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {visible.map((card) => (
          <div
            key={card.id}
            className="mk-card p-4 flex flex-col gap-3 hover:shadow-md transition-shadow duration-150"
          >
            <div className="flex items-start gap-3">
              <span className={cn("inline-flex items-center justify-center w-8 h-8 rounded-lg shrink-0", toneClasses[card.tone])}>
                {card.icon ?? toneIcon[card.tone]}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-fg leading-tight">{card.title}</p>
                <p className="text-xs text-fg-muted mt-1">{card.description}</p>
              </div>
              <span className="text-base font-bold text-fg tabular-nums">{card.count}</span>
            </div>
            <button
              type="button"
              onClick={card.onCta}
              className="btn btn-primary btn-sm w-full min-h-[44px]"
            >
              {card.ctaLabel}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Pure helper — derive cards from tenant state, useful for unit testing */
export function deriveActionCards(input: {
  pendingApprovals: number
  unfilledShifts: number
  upcomingDeadlines: number
  onApprovals: () => void
  onShifts: () => void
  onDeadlines: () => void
}): ActionCard[] {
  return [
    {
      id: "approvals",
      title: "Pending approvals",
      description: "Leave and roster items awaiting your decision",
      count: input.pendingApprovals,
      priority: 1,
      ctaLabel: "Review",
      onCta: input.onApprovals,
      tone: "rose" as const,
    },
    {
      id: "shifts",
      title: "Unfilled shifts",
      description: "Open shifts that need coverage",
      count: input.unfilledShifts,
      priority: 2,
      ctaLabel: "Fill shifts",
      onCta: input.onShifts,
      tone: "amber" as const,
    },
    {
      id: "deadlines",
      title: "Upcoming deadlines",
      description: "Items due within the next 7 days",
      count: input.upcomingDeadlines,
      priority: 3,
      ctaLabel: "View",
      onCta: input.onDeadlines,
      tone: "brand" as const,
    },
  ]
}
