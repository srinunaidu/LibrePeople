import { QueryClient } from "@tanstack/react-query"

/**
 * Shared TanStack Query client.
 *
 * Stale times are short on purpose: this is an HCM portal where approval
 * queues, attendance and leave balances change constantly, and the product
 * goal is that the UI feels live. `refetchOnWindowFocus` keeps data fresh
 * when the user tabs back in without a manual refresh.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
})