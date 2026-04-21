import { forwardRef, type SelectHTMLAttributes } from 'react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: Array<{ value: string; label: string }>
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, className = '', id, ...props }, ref) => {
    const selectId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

    return (
      <div className={`form-field ${className}`}>
        {label ? (
          <label className="form-field__label" htmlFor={selectId}>
            {label}
          </label>
        ) : null}
        <select ref={ref} id={selectId} {...props}>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error ? <span className="form-field__error">{error}</span> : null}
      </div>
    )
  },
)

Select.displayName = 'Select'
