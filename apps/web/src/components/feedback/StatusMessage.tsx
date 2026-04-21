type StatusVariant = 'success' | 'error' | 'warning' | 'info'

interface StatusMessageProps {
  type: StatusVariant
  text: string
}

const typeToClass: Record<StatusVariant, string> = {
  success: 'message--success',
  error: 'message--error',
  warning: 'message--warning',
  info: 'message--info',
}

export function StatusMessage({ type, text }: StatusMessageProps) {
  return (
    <div className={`message ${typeToClass[type]}`} role={type === 'error' ? 'alert' : 'status'}>
      {text}
    </div>
  )
}
