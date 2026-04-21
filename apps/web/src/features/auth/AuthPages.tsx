import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'

import {
  forgotPassword,
  loginUser,
  registerUser,
  resetPassword,
  verifyEmailToken,
} from '../../lib/api'
import { defaultRouteForSession, setSession } from '../../lib/session'
import { getErrorMessage } from '../../lib/types'

const registerSchema = z.object({
  firstName: z.string().min(1, 'First name is required.'),
  lastName: z.string().min(1, 'Last name is required.'),
  email: z.email('Enter a valid email address.'),
  password: z.string().min(8, 'Use at least 8 characters.'),
})

const loginSchema = z.object({
  email: z.email('Enter a valid email address.'),
  password: z.string().min(8, 'Use at least 8 characters.'),
})

const verifySchema = z.object({
  token: z.string().min(10, 'Paste the verification token.'),
})

const forgotPasswordSchema = z.object({
  email: z.email('Enter a valid email address.'),
})

const resetPasswordSchema = z.object({
  token: z.string().min(10, 'Paste the password reset token.'),
  newPassword: z.string().min(8, 'Use at least 8 characters.'),
})

type RegisterValues = z.infer<typeof registerSchema>
type LoginValues = z.infer<typeof loginSchema>
type VerifyValues = z.infer<typeof verifySchema>
type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>
type ResetPasswordValues = z.infer<typeof resetPasswordSchema>

function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div className="auth-card">
      <div className="auth-card__header">
        <div className="auth-card__logo">EduCorp</div>
        <h1 className="auth-card__title">{title}</h1>
        <p className="auth-card__subtitle">{subtitle}</p>
      </div>
      {children}
    </div>
  )
}

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <label className="form-field">
      <span className="form-field__label">{label}</span>
      {children}
      {error ? <span className="form-field__error">{error}</span> : null}
    </label>
  )
}

function StatusMessage({ type, text }: { type: 'success' | 'error'; text: string }) {
  return (
    <div className={`message message--${type}`} role={type === 'error' ? 'alert' : 'status'}>
      {text}
    </div>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })
  const mutation = useMutation({
    mutationFn: loginUser,
    onSuccess: (session) => {
      setSession(session)
      navigate(defaultRouteForSession(session), { replace: true })
    },
  })

  return (
    <AuthCard title="Sign in" subtitle="Access your EduCorp account.">
      <form className="form-stack" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <Field label="Email" error={form.formState.errors.email?.message}>
          <input autoComplete="email" {...form.register('email')} />
        </Field>

        <Field label="Password" error={form.formState.errors.password?.message}>
          <input autoComplete="current-password" type="password" {...form.register('password')} />
        </Field>

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="btn-row">
          <button className="btn btn--primary" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Signing in...' : 'Sign in'}
          </button>
          <Link className="btn btn--ghost" to="/forgot-password">
            Forgot password?
          </Link>
        </div>

        <p className="auth-hint">Admin seed: admin@educorp.dev / AdminPass123!</p>

        <div className="auth-footer">
          <Link to="/register">Create account</Link>
          <Link to="/verify-email">Verify email</Link>
        </div>
      </form>
    </AuthCard>
  )
}

export function RegisterPage() {
  const [queryParams, setQueryParams] = useSearchParams()
  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      firstName: '',
      lastName: '',
      email: queryParams.get('email') ?? '',
      password: '',
    },
  })
  const mutation = useMutation({
    mutationFn: async (values: RegisterValues) =>
      registerUser({
        email: values.email,
        password: values.password,
        first_name: values.firstName,
        last_name: values.lastName,
      }),
    onSuccess: (user) => {
      setQueryParams({ email: user.email })
      form.reset({
        firstName: user.first_name,
        lastName: user.last_name,
        email: user.email,
        password: '',
      })
    },
  })

  return (
    <AuthCard title="Create account" subtitle="Register a new student account.">
      <form className="form-stack" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <div className="form-row">
          <Field label="First name" error={form.formState.errors.firstName?.message}>
            <input autoComplete="given-name" {...form.register('firstName')} />
          </Field>
          <Field label="Last name" error={form.formState.errors.lastName?.message}>
            <input autoComplete="family-name" {...form.register('lastName')} />
          </Field>
        </div>

        <Field label="Email" error={form.formState.errors.email?.message}>
          <input autoComplete="email" {...form.register('email')} />
        </Field>

        <Field label="Password" error={form.formState.errors.password?.message}>
          <input autoComplete="new-password" type="password" {...form.register('password')} />
        </Field>

        {mutation.isSuccess ? (
          <StatusMessage
            type="success"
            text={`Account created for ${mutation.data.email}. Verify your email before signing in.`}
          />
        ) : null}

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="btn-row">
          <button className="btn btn--primary" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Creating...' : 'Create account'}
          </button>
          <Link className="btn btn--ghost" to="/verify-email">
            Verify email
          </Link>
        </div>

        <div className="auth-footer">
          <Link to="/login">Already have an account?</Link>
        </div>
      </form>
    </AuthCard>
  )
}

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const form = useForm<VerifyValues>({
    resolver: zodResolver(verifySchema),
    defaultValues: { token: searchParams.get('token') ?? '' },
  })
  const mutation = useMutation({
    mutationFn: async (values: VerifyValues) => verifyEmailToken(values.token),
  })

  return (
    <AuthCard title="Verify email" subtitle="Paste the token from your verification email.">
      <form className="form-stack" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <Field label="Verification token" error={form.formState.errors.token?.message}>
          <textarea {...form.register('token')} />
        </Field>

        {mutation.isSuccess ? (
          <StatusMessage type="success" text={mutation.data.message} />
        ) : null}

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="btn-row">
          <button className="btn btn--primary" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Verifying...' : 'Verify'}
          </button>
          <Link className="btn btn--ghost" to="/login">
            Back to sign in
          </Link>
        </div>
      </form>
    </AuthCard>
  )
}

export function ForgotPasswordPage() {
  const form = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  })
  const mutation = useMutation({
    mutationFn: async (values: ForgotPasswordValues) => forgotPassword(values.email),
  })

  return (
    <AuthCard title="Reset password" subtitle="Enter your email to receive a reset token.">
      <form className="form-stack" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <Field label="Email" error={form.formState.errors.email?.message}>
          <input autoComplete="email" {...form.register('email')} />
        </Field>

        {mutation.isSuccess ? (
          <StatusMessage type="success" text={mutation.data.message} />
        ) : null}

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="btn-row">
          <button className="btn btn--primary" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Sending...' : 'Send reset request'}
          </button>
          <Link className="btn btn--ghost" to="/reset-password">
            I have a token
          </Link>
        </div>

        <div className="auth-footer">
          <Link to="/login">Back to sign in</Link>
        </div>
      </form>
    </AuthCard>
  )
}

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const form = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      token: searchParams.get('token') ?? '',
      newPassword: '',
    },
  })
  const mutation = useMutation({
    mutationFn: async (values: ResetPasswordValues) =>
      resetPassword(values.token, values.newPassword),
  })

  return (
    <AuthCard title="Set new password" subtitle="Enter the reset token and your new password.">
      <form className="form-stack" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <Field label="Reset token" error={form.formState.errors.token?.message}>
          <textarea {...form.register('token')} />
        </Field>

        <Field label="New password" error={form.formState.errors.newPassword?.message}>
          <input autoComplete="new-password" type="password" {...form.register('newPassword')} />
        </Field>

        {mutation.isSuccess ? (
          <StatusMessage type="success" text={mutation.data.message} />
        ) : null}

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="btn-row">
          <button className="btn btn--primary" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Resetting...' : 'Reset password'}
          </button>
          <Link className="btn btn--ghost" to="/login">
            Back to sign in
          </Link>
        </div>
      </form>
    </AuthCard>
  )
}
