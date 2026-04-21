import { forwardRef, type InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

    return (
      <div className={`form-field ${className}`}>
        {label ? (
          <label className="form-field__label" htmlFor={inputId}>
            {label}
          </label>
        ) : null}
        <input ref={ref} id={inputId} {...props} />
        {error ? <span className="form-field__error">{error}</span> : null}
      </div>
    )
  },
)

Input.displayName = 'Input'
