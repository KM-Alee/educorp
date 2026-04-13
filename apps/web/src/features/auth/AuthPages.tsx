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

function AuthLayout({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <div className="auth-layout page">
      <aside className="auth-aside">
        <div className="auth-brand">
          <span className="eyebrow">{eyebrow}</span>
          <h1>Warm, operational auth.</h1>
          <p>
            EduCorp&apos;s first web slice focuses on real account work: register,
            verify, recover, and move between student and admin duties without a
            marketing-shell detour.
          </p>
        </div>

        <div className="timeline">
          <div className="timeline-item timeline-item--thinking">
            <strong>Think</strong>
            <span>Readable forms, explicit states, no decorative clutter.</span>
          </div>
          <div className="timeline-item timeline-item--grep">
            <strong>Gate</strong>
            <span>Role-aware routing keeps admin surfaces separate from learner flow.</span>
          </div>
          <div className="timeline-item timeline-item--read">
            <strong>Recover</strong>
            <span>Verification and password reset are first-class routes, not edge cases.</span>
          </div>
          <div className="timeline-item timeline-item--edit">
            <strong>Review</strong>
            <span>Phase 1 already includes a thin admin desk for roles and applications.</span>
          </div>
        </div>
      </aside>

      <section className="auth-panel">
        <div className="panel">
          <header className="panel-header">
            <span className="eyebrow">EduCorp Web</span>
            <h2>{title}</h2>
            <p className="lede">{description}</p>
          </header>
          {children}
        </div>
      </section>
    </div>
  )
}

function InputField({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {error ? <span className="field-error">{error}</span> : null}
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
    <AuthLayout
      eyebrow="Phase 1"
      title="Sign in"
      description="Use the live auth service through Traefik. Admin accounts land on the operational desk; everyone else lands on profile."
    >
      <form className="form-grid" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <InputField label="Email" error={form.formState.errors.email?.message}>
          <input autoComplete="email" {...form.register('email')} />
        </InputField>

        <InputField label="Password" error={form.formState.errors.password?.message}>
          <input autoComplete="current-password" type="password" {...form.register('password')} />
        </InputField>

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="button-row">
          <button className="button button--accent" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Signing in...' : 'Sign in'}
          </button>
          <Link className="button button--ghost" to="/forgot-password">
            Forgot password
          </Link>
        </div>

        <p className="support-copy">Phase 1 admin seed: admin@educorp.dev / AdminPass123!.</p>

        <div className="auth-links">
          <Link to="/register">Create account</Link>
          <Link to="/verify-email">Verify email</Link>
        </div>
      </form>
    </AuthLayout>
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
    <AuthLayout
      eyebrow="Phase 1"
      title="Register"
      description="Student accounts are created inactive and unverified. Use the verification screen with the token from the mock backend flow."
    >
      <form className="form-grid" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <div className="split-grid">
          <InputField label="First name" error={form.formState.errors.firstName?.message}>
            <input autoComplete="given-name" {...form.register('firstName')} />
          </InputField>
          <InputField label="Last name" error={form.formState.errors.lastName?.message}>
            <input autoComplete="family-name" {...form.register('lastName')} />
          </InputField>
        </div>

        <InputField label="Email" error={form.formState.errors.email?.message}>
          <input autoComplete="email" {...form.register('email')} />
        </InputField>

        <InputField label="Password" error={form.formState.errors.password?.message}>
          <input autoComplete="new-password" type="password" {...form.register('password')} />
        </InputField>

        {mutation.isSuccess ? (
          <StatusMessage
            type="success"
            text={`Account created for ${mutation.data.email}. Verify the address before signing in.`}
          />
        ) : null}

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="button-row">
          <button className="button button--accent" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Creating...' : 'Create account'}
          </button>
          <Link className="button button--ghost" to="/verify-email">
            Verify email
          </Link>
        </div>

        <p className="fine-print">
          Password validation is enforced by the auth API. Use mixed case and at least one digit.
        </p>

        <div className="auth-links">
          <Link to="/login">Already have an account?</Link>
        </div>
      </form>
    </AuthLayout>
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
    <AuthLayout
      eyebrow="Phase 1"
      title="Verify email"
      description="Paste the token emitted by the mock verification flow. Once verified, the account becomes active and can log in."
    >
      <form className="form-grid" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <InputField label="Verification token" error={form.formState.errors.token?.message}>
          <textarea {...form.register('token')} />
        </InputField>

        {mutation.isSuccess ? (
          <StatusMessage type="success" text={mutation.data.message} />
        ) : null}

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="button-row">
          <button className="button button--accent" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Verifying...' : 'Verify'}
          </button>
          <Link className="button button--ghost" to="/login">
            Back to login
          </Link>
        </div>
      </form>
    </AuthLayout>
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
    <AuthLayout
      eyebrow="Recovery"
      title="Request password reset"
      description="The backend returns a generic response either way. Use the reset screen once you have the token from the mock flow."
    >
      <form className="form-grid" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <InputField label="Email" error={form.formState.errors.email?.message}>
          <input autoComplete="email" {...form.register('email')} />
        </InputField>

        {mutation.isSuccess ? (
          <StatusMessage type="success" text={mutation.data.message} />
        ) : null}

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="button-row">
          <button className="button button--accent" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Submitting...' : 'Send reset request'}
          </button>
          <Link className="button button--ghost" to="/reset-password">
            I have a token
          </Link>
        </div>
      </form>
    </AuthLayout>
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
    <AuthLayout
      eyebrow="Recovery"
      title="Reset password"
      description="Use the reset token from the mock backend flow. Refresh tokens are revoked when the password changes."
    >
      <form className="form-grid" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <InputField label="Reset token" error={form.formState.errors.token?.message}>
          <textarea {...form.register('token')} />
        </InputField>

        <InputField label="New password" error={form.formState.errors.newPassword?.message}>
          <input autoComplete="new-password" type="password" {...form.register('newPassword')} />
        </InputField>

        {mutation.isSuccess ? (
          <StatusMessage type="success" text={mutation.data.message} />
        ) : null}

        {mutation.isError ? (
          <StatusMessage type="error" text={getErrorMessage(mutation.error)} />
        ) : null}

        <div className="button-row">
          <button className="button button--accent" disabled={mutation.isPending} type="submit">
            {mutation.isPending ? 'Resetting...' : 'Reset password'}
          </button>
          <Link className="button button--ghost" to="/login">
            Back to login
          </Link>
        </div>
      </form>
    </AuthLayout>
  )
}