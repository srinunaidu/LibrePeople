import { cn } from "@/lib/utils"
import * as React from "react"

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, "aria-describedby": ariaDescribedBy, "aria-invalid": ariaInvalid, id, ...props }, ref) => {
    const errorId = error && id ? `${id}-error` : undefined
    return (
      <input
        ref={ref}
        id={id}
        aria-invalid={error ? true : ariaInvalid}
        aria-describedby={errorId ?? ariaDescribedBy}
        className={cn(
          "input",
          error && "border-error focus:border-error focus:shadow-[0_0_0_3px_var(--error-border)]",
          className
        )}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, "aria-describedby": ariaDescribedBy, "aria-invalid": ariaInvalid, id, ...props }, ref) => {
    const errorId = error && id ? `${id}-error` : undefined
    return (
      <textarea
        ref={ref}
        id={id}
        aria-invalid={error ? true : ariaInvalid}
        aria-describedby={errorId ?? ariaDescribedBy}
        className={cn(
          "input min-h-[80px] resize-y",
          error && "border-error",
          className
        )}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, error, children, "aria-describedby": ariaDescribedBy, "aria-invalid": ariaInvalid, id, ...props }, ref) => {
    const errorId = error && id ? `${id}-error` : undefined
    return (
      <select
        ref={ref}
        id={id}
        aria-invalid={error ? true : ariaInvalid}
        aria-describedby={errorId ?? ariaDescribedBy}
        className={cn(
          "input appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2216%22 height=%2216%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%2394a3b8%22 stroke-width=%222%22%3E%3Cpath d=%22m6 9 6 6 6-6%22/%3E%3C/svg%3E')] bg-[right_0.625rem_center] bg-no-repeat pr-9",
          error && "border-error",
          className
        )}
        {...props}
      >
        {children}
      </select>
    )
  }
)
Select.displayName = "Select"

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, ...props }, ref) => (
    <div className="flex items-center gap-2">
      <div className="inline-flex items-center justify-center min-h-[44px] min-w-[44px] -m-3 p-3">
        <input
          ref={ref}
          id={id}
          type="checkbox"
          className={cn(
            "h-5 w-5 rounded border-border-strong text-brand-600 accent-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600",
            className
          )}
          {...props}
        />
      </div>
      {label && (
        <label htmlFor={id} className="text-sm text-fg">
          {label}
        </label>
      )}
    </div>
  )
)
Checkbox.displayName = "Checkbox"

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string
}

export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, label, id, ...props }, ref) => (
    <div className="flex items-center gap-2">
      <button
        type="button"
        role="switch"
        aria-checked={props.checked ?? false}
        aria-label={label}
        className={cn(
          "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] border border-[var(--border)]",
          props.checked ? "bg-[var(--accent)]" : "bg-[var(--surface-elevated)]"
        )}
        onClick={() => {
          props.onChange?.({ target: { checked: !props.checked } } as React.ChangeEvent<HTMLInputElement>)
        }}
      >
        <span
          className={cn(
            "inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform",
            props.checked ? "translate-x-[22px]" : "translate-x-[3px]"
          )}
        />
      </button>
      {label && (
        <span className="text-sm text-fg select-none">{label}</span>
      )}
      <input ref={ref} id={id} type="checkbox" className="sr-only" tabIndex={-1} aria-hidden="true" {...props} />
    </div>
  )
)
Switch.displayName = "Switch"