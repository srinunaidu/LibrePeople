import { Alert } from "@/components/ui/feedback"

/**
 * Single source for the 409 pending_verification gate.
 * Zero duplicated amber strings should remain elsewhere — grep pending_verification
 * only in this component + PayRuns badge.
 */
export function PendingVerificationAlert({ className }: { className?: string }) {
  return (
    <Alert tone="warning" title="Calculation blocked — pending verification" className={className}>
      <span>
        configurable calculation, cannot calculate — the rule pack is pending verification. No computed data is returned while pending, per{" "}
        <a href="/docs/PAYROLL.md#33" className="underline font-mono">
          docs/PAYROLL.md §3.3
        </a>
        .
      </span>
    </Alert>
  )
}

export default PendingVerificationAlert
