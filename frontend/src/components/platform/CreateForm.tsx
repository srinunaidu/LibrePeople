import { useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { Input, Select } from "@/components/ui/inputs"
import { Field } from "@/components/ui/layout"
import { Alert } from "@/components/ui/feedback"
import { cn } from "@/lib/utils"

interface CreateFormField {
  name: string
  label: string
  placeholder?: string
  required?: boolean
  options?: { value: string; label: string }[]
}

interface CreateFormProps {
  legend: string
  hint?: string
  fields: CreateFormField[]
  onSubmit: (values: Record<string, string>) => Promise<void>
  submitLabel: string
}

export function CreateForm({ legend, hint, fields, onSubmit, submitLabel }: CreateFormProps) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError("")
    try {
      await onSubmit(values)
      setValues({})
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not save. Please try again.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={cn("mb-4 mk-card p-4", "border border-border")}>
      <h2 className="mk-h2 text-fg mb-1">{legend}</h2>
      {hint && <p className="text-sm text-fg-muted mb-3">{hint}</p>}
      {error && <Alert tone="error" className="mb-3">{error}</Alert>}
      <div className="flex flex-wrap gap-4 items-end">
        {fields.map((f) => (
          <Field
            key={f.name}
            label={f.label}
            htmlFor={`${legend}-${f.name}`}
            required={f.required}
            className="flex-1 min-w-[160px]"
          >
            {f.options ? (
              <Select
                id={`${legend}-${f.name}`}
                name={f.name}
                required={f.required}
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
              >
                <option value="">Select…</option>
                {f.options.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                id={`${legend}-${f.name}`}
                name={f.name}
                placeholder={f.placeholder}
                required={f.required}
                value={values[f.name] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [f.name]: e.target.value }))}
              />
            )}
          </Field>
        ))}
        <Button type="submit" disabled={busy} className="w-full sm:w-auto">
          {busy ? "Saving…" : submitLabel}
        </Button>
      </div>
    </form>
  )
}