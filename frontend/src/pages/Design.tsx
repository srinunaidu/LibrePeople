import { Layout } from "@/components/Layout"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, SectionCard } from "@/components/ui/card"
import { Input, Select, Textarea, Checkbox, Switch } from "@/components/ui/inputs"
import { Badge, badgeVariants } from "@/components/ui/badge"
import { Avatar } from "@/components/ui/avatar"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { StatusPill } from "@/components/ui/status-pill"
import { Alert, EmptyState, Meter } from "@/components/ui/feedback"
import { RetryableAlert } from "@/components/ui"
import { Skeleton, CardSkeleton, TableSkeleton, LoadingRegion } from "@/components/ui/skeleton"
import { PageHeader, Field, FormSection, Toolbar, Breadcrumb, SubmitBar } from "@/components/ui/layout"
import { toast } from "@/components/ui/sonner"
import { IconCheck, IconGrid, IconInbox, IconPlus, IconSparkle, IconX } from "@/components/icons"
import { cn } from "@/lib/utils"
import * as React from "react"
import { useState } from "react"

/**
 * Internal design-system showcase.
 * Route: /design (protected). For review during Phase 1.
 */
export default function DesignShowcase() {
  const [switchOn, setSwitchOn] = useState(true)
  const [checked, setChecked] = useState(false)

  return (
    <Layout>
      <PageHeader compact
        icon={<IconGrid />}
        title="Design System"
        description="Component library and token reference for the LibrePeople HCM revamp."
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => toast.success("Toast works!", { description: "This is a Sonner toast." })}>
              Trigger Toast
            </Button>
            <Button size="sm" onClick={() => toast.error("Error toast", { description: "Something went wrong." })}>
              Error Toast
            </Button>
          </div>
        }
      />

      {/* ---- Typography ---- */}
      <SectionCard compact icon={<IconSparkle />} title="Typography" className="mb-6">
        <div className="p-5 space-y-4">
          <div>
            <p className="text-display">Display 56/64</p>
          </div>
          <div>
            <p className="text-h1">H1 44/52</p>
          </div>
          <div>
            <p className="text-h1-app">H1 App 24/32</p>
          </div>
          <div>
            <p className="text-h2">H2 32/40</p>
          </div>
          <div>
            <p className="text-h2-app">H2 App 20/28</p>
          </div>
          <div>
            <p className="text-h3">H3 24/32</p>
          </div>
          <div>
            <p className="text-h3-app">H3 App 16/24</p>
          </div>
          <div>
            <p className="text-body">Body 16/24 — The quick brown fox jumps over the lazy dog.</p>
          </div>
          <div>
            <p className="text-body-sm">Body SM 14/20 — Dense UI text for tables and forms.</p>
          </div>
          <div>
            <p className="text-caption">Caption 12/16 — Metadata and labels.</p>
          </div>
        </div>
      </SectionCard>

      {/* ---- Buttons ---- */}
      <SectionCard compact icon={<IconPlus />} title="Buttons" className="mb-6">
        <div className="p-5 space-y-5">
          <div>
            <h3 className="text-h3-app mb-3">Variants</h3>
            <div className="flex flex-wrap gap-2">
              <Button variant="primary">Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="danger">Danger</Button>
              <Button variant="outline">Outline</Button>
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Sizes</h3>
            <div className="flex flex-wrap items-center gap-2">
              <Button size="xs">Extra Small</Button>
              <Button size="sm">Small</Button>
              <Button size="md">Medium</Button>
              <Button size="lg">Large</Button>
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">States</h3>
            <div className="flex flex-wrap gap-2">
              <Button disabled>Disabled</Button>
              <Button loading>Loading…</Button>
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ---- Form Controls ---- */}
      <SectionCard compact icon={<IconCheck />} title="Form Controls" className="mb-6">
        <div className="p-5">
          <FormSection title="Inputs" columns={2}>
            <Field label="Text Input" htmlFor="demo-text" hint="Helper text goes here">
              <Input id="demo-text" placeholder="Enter some text…" />
            </Field>
            <Field label="Email" htmlFor="demo-email">
              <Input id="demo-email" type="email" placeholder="user@example.com" />
            </Field>
            <Field label="With Error" htmlFor="demo-error" error="This field is required">
              <Input id="demo-error" error placeholder="Will not submit" />
            </Field>
            <Field label="Select" htmlFor="demo-select">
              <Select id="demo-select">
                <option value="">Select an option…</option>
                <option value="1">Option 1</option>
                <option value="2">Option 2</option>
                <option value="3">Option 3</option>
              </Select>
            </Field>
            <Field label="Textarea" htmlFor="demo-textarea">
              <Textarea id="demo-textarea" placeholder="Multi-line text…" rows={3} />
            </Field>
            <div className="flex flex-col gap-3">
              <Checkbox id="demo-check" label="Checkbox option" checked={checked} onChange={() => setChecked(!checked)} />
              <Switch id="demo-switch" label="Toggle switch" checked={switchOn} onChange={() => setSwitchOn(!switchOn)} />
            </div>
          </FormSection>
        </div>
      </SectionCard>

      {/* ---- Badges & Status ---- */}
      <SectionCard compact icon={<IconGrid />} title="Badges & Status Pills" className="mb-6">
        <div className="p-5 space-y-5">
          <div>
            <h3 className="text-h3-app mb-3">Badge Variants</h3>
            <div className="flex flex-wrap gap-2">
              <Badge variant="brand">Brand</Badge>
              <Badge variant="teal">Teal</Badge>
              <Badge variant="green">Green</Badge>
              <Badge variant="violet">Violet</Badge>
              <Badge variant="amber">Amber</Badge>
              <Badge variant="rose">Rose</Badge>
              <Badge variant="slate">Slate</Badge>
              <Badge variant="outline">Outline</Badge>
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Badge Sizes</h3>
            <div className="flex flex-wrap items-center gap-2">
              <Badge size="sm" variant="brand">Small</Badge>
              <Badge size="md" variant="brand">Medium</Badge>
              <Badge size="md" variant="green" dot>With Dot</Badge>
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Status Pills</h3>
            <div className="flex flex-wrap gap-2">
              <StatusPill status="Active" />
              <StatusPill status="Pending" />
              <StatusPill status="Approved" />
              <StatusPill status="Rejected" />
              <StatusPill status="Draft" />
              <StatusPill status="Completed" />
              <StatusPill status="Hired" />
              <StatusPill status="OnHold" />
              <StatusPill status="Closed" />
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ---- Avatars ---- */}
      <SectionCard compact icon={<IconGrid />} title="Avatars" className="mb-6">
        <div className="p-5 space-y-5">
          <div>
            <h3 className="text-h3-app mb-3">Sizes</h3>
            <div className="flex items-center gap-3">
              <Avatar size="xs" alt="XS" />
              <Avatar size="sm" alt="SM" />
              <Avatar size="md" alt="MD" />
              <Avatar size="lg" alt="LG" />
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Fallback Initials</h3>
            <div className="flex items-center gap-3">
              <Avatar alt="Srinivas Naidu" size="md" />
              <Avatar alt="Jane Doe" size="md" />
              <Avatar alt="Alex Kim" size="md" />
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ---- Tabs ---- */}
      <SectionCard compact icon={<IconGrid />} title="Tabs" className="mb-6">
        <div className="p-5">
          <Tabs defaultValue="tab1">
            <TabsList>
              <TabsTrigger value="tab1">Overview</TabsTrigger>
              <TabsTrigger value="tab2">Details</TabsTrigger>
              <TabsTrigger value="tab3">Settings</TabsTrigger>
            </TabsList>
            <TabsContent value="tab1">
              <p className="text-sm text-fg-muted">Tab content for Overview.</p>
            </TabsContent>
            <TabsContent value="tab2">
              <p className="text-sm text-fg-muted">Tab content for Details.</p>
            </TabsContent>
            <TabsContent value="tab3">
              <p className="text-sm text-fg-muted">Tab content for Settings.</p>
            </TabsContent>
          </Tabs>
        </div>
      </SectionCard>

      {/* ---- Alerts ---- */}
      <SectionCard compact icon={<IconGrid />} title="Alerts" className="mb-6">
        <div className="p-5 space-y-3">
          <Alert tone="info" title="Information">
            This is an informational message.
          </Alert>
          null /* toast.success replaces Alert success */
          <Alert tone="error" title="Error">
            Something went wrong. Please try again.
            <div className="mt-2">
              <Button size="sm" variant="secondary" onClick={() => toast.info("Retrying…")}>
                Retry
              </Button>
            </div>
          </Alert>
        </div>
      </SectionCard>

      {/* ---- Skeletons & Empty States ---- */}
      <SectionCard compact icon={<IconInbox />} title="Skeletons & Empty States" className="mb-6">
        <div className="p-5 space-y-5">
          <div>
            <h3 className="text-h3-app mb-3">Card Skeleton</h3>
            <CardSkeleton lines={3} />
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Table Skeleton</h3>
            <Card padded={false}>
              <TableSkeleton rows={4} cols={4} />
            </Card>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Empty State</h3>
            <EmptyState
              icon={<IconInbox className="w-5 h-5" />}
              title="No items yet"
              description="Create your first item to get started."
              action={<Button size="sm">Create Item</Button>}
            />
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Progress Meter</h3>
            <Meter percent={65} label="65% complete" />
          </div>
        </div>
      </SectionCard>

      {/* ---- Layout Primitives ---- */}
      <SectionCard compact icon={<IconGrid />} title="Layout Primitives" className="mb-6">
        <div className="p-5 space-y-5">
          <div>
            <h3 className="text-h3-app mb-3">Toolbar</h3>
            <Card padded={false}>
              <Toolbar>
                <Input placeholder="Search…" aria-label="Search input" className="max-w-[200px]" />
                <Select className="w-40" aria-label="Filter category">
                  <option value="">All</option>
                  <option value="1">Option 1</option>
                </Select>
                <Button variant="secondary">Filter</Button>
              </Toolbar>
              <div className="p-5 text-sm text-fg-muted">Toolbar content area below.</div>
            </Card>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Breadcrumbs</h3>
            <Breadcrumb
              items={[
                { label: "Home", href: "/dashboard" },
                { label: "People" },
                { label: "Employees" },
              ]}
            />
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Submit Bar</h3>
            <Card padded={false}>
              <SubmitBar submitLabel="Save Changes" dirty />
            </Card>
          </div>
        </div>
      </SectionCard>

      {/* ---- Color Tokens ---- */}
      <SectionCard compact icon={<IconGrid />} title="Color Tokens" className="mb-6">
        <div className="p-5 space-y-5">
          <div>
            <h3 className="text-h3-app mb-3">Brand Ramp</h3>
            <div className="flex flex-wrap gap-1">
              {[50, 100, 200, 300, 400, 500, 600, 700, 800, 900].map((s) => {
                const bg = { backgroundColor: `var(--brand-${s})` } as React.CSSProperties
                return (
                  <div key={s} className="flex flex-col items-center gap-1">
                    <div className="h-10 w-10 rounded-md border border-border-subtle" style={bg} />
                    <span className="text-[10px] text-fg-muted">{s}</span>
                  </div>
                )
              })}
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Accent Ramps</h3>
            <div className="flex gap-4">
              {["teal", "green", "violet"].map((c) => (
                <div key={c} className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-fg-muted capitalize mb-1">{c}</span>
                  {[100, 300, 500, 700].map((s) => {
                    const bg = { backgroundColor: `var(--${c}-${s})` } as React.CSSProperties
                    return <div key={s} className="h-6 w-16 rounded border border-border-subtle" style={bg} />
                  })}
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Semantic Surfaces</h3>
            <div className="flex flex-wrap gap-2">
              {["surface", "surface-raised", "surface-sunken", "surface-inset"].map((t) => {
                const bg = { backgroundColor: `var(--${t})` } as React.CSSProperties
                return (
                  <div key={t} className="flex flex-col items-center gap-1">
                    <div className="h-12 w-16 rounded-md border border-border" style={bg} />
                    <span className="text-[10px] text-fg-muted">{t}</span>
                  </div>
                )
              })}
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Status Colors</h3>
            <div className="flex flex-wrap gap-2">
              {["error", "warning", "success", "info"].map((c) => {
                const bg = { backgroundColor: `var(--${c})` } as React.CSSProperties
                return (
                  <div key={c} className="flex flex-col items-center gap-1">
                    <div className="h-8 w-12 rounded" style={bg} />
                    <span className="text-[10px] text-fg-muted">{c}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ---- Shadows & Radius ---- */}
      <SectionCard compact icon={<IconGrid />} title="Shadows & Radius" className="mb-6">
        <div className="p-5 space-y-5">
          <div>
            <h3 className="text-h3-app mb-3">Shadows</h3>
            <div className="flex flex-wrap gap-4">
              {["sm", "md", "lg", "xl"].map((s) => {
                const shadow = { boxShadow: `var(--shadow-${s})` } as React.CSSProperties
                return (
                  <div key={s} className="flex flex-col items-center gap-2">
                    <div className="h-16 w-24 rounded-lg bg-surface border border-border" style={shadow} />
                    <span className="text-xs text-fg-muted">{s}</span>
                  </div>
                )
              })}
            </div>
          </div>
          <div>
            <h3 className="text-h3-app mb-3">Radius</h3>
            <div className="flex flex-wrap gap-4">
              {["sm", "md", "lg", "xl"].map((r) => {
                const radius = { borderRadius: `var(--radius-${r})` } as React.CSSProperties
                return (
                  <div key={r} className="flex flex-col items-center gap-2">
                    <div className="h-12 w-20 bg-brand-100 border border-brand-200" style={radius} />
                    <span className="text-xs text-fg-muted">{r}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </SectionCard>

      {/* ---- Dark Mode Toggle ---- */}
      <SectionCard compact icon={<IconGrid />} title="Dark Mode Preview" className="mb-6">
        <div className="p-5">
          <p className="text-sm text-fg-muted mb-4">
            Toggle dark mode via the theme toggle in the user menu (Phase 2). This section previews the dark token values.
          </p>
          <div className="dark rounded-lg border border-border-strong p-4 bg-surface-sunken">
            <div className="flex items-center gap-3 mb-3">
              <Avatar alt="Demo User" size="sm" />
              <div>
                <p className="text-sm font-medium text-white">Dark Mode Card</p>
                <p className="text-xs text-fg-subtle">surface: var(--surface) · raised: var(--surface-raised) · fg: var(--fg)</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="brand">Brand</Badge>
              <Badge variant="green">Green</Badge>
              <Badge variant="rose">Rose</Badge>
              <StatusPill status="Active" />
              <Button size="sm">Button</Button>
            </div>
          </div>
        </div>
      </SectionCard>
    </Layout>
  )
}
