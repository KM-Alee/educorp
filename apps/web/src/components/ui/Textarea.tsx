import { forwardRef, type TextareaHTMLAttributes } from 'react'

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = '', id, ...props }, ref) => {
    const textareaId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

    return (
      <div className={`form-field ${className}`}>
        {label ? (
          <label className="form-field__label" htmlFor={textareaId}>
            {label}
          </label>
        ) : null}
        <textarea ref={ref} id={textareaId} {...props} />
        {error ? <span className="form-field__error">{error}</span> : null}
      </div>
    )
  },
)

Textarea.displayName = 'Textarea'
