import { useEffect } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'

import {
  createInstructorApplication,
  getProfile,
  updateProfile,
  type UserProfile,
} from '../../lib/api'
import { getSession, updateSession, useSessionState } from '../../lib/session'
import { getErrorMessage } from '../../lib/types'

interface ProfileFormValues {
  first_name: string
  last_name: string
  avatar_url: string
}

interface ApplicationFormValues {
  reason: string
}

function syncSession(profile: UserProfile): void {
  const currentSession = getSession()
  if (!currentSession) {
    return
  }

  updateSession((session) =>
    session
      ? {
          ...session,
          user: {
            id: profile.id,
            email: profile.email,
            roles: profile.roles,
          },
        }
      : null,
  )
}

export function ProfilePage() {
  const session = useSessionState()
  const queryClient = useQueryClient()
  const profileQuery = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  })

  const profileForm = useForm<ProfileFormValues>({
    defaultValues: {
      first_name: '',
      last_name: '',
      avatar_url: '',
    },
  })
  const applicationForm = useForm<ApplicationFormValues>({
    defaultValues: { reason: '' },
  })

  useEffect(() => {
    if (profileQuery.data) {
      profileForm.reset({
        first_name: profileQuery.data.first_name,
        last_name: profileQuery.data.last_name,
        avatar_url: profileQuery.data.avatar_url ?? '',
      })
      syncSession(profileQuery.data)
    }
  }, [profileForm, profileQuery.data])

  const profileMutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: async (profile) => {
      syncSession(profile)
      await queryClient.invalidateQueries({ queryKey: ['profile'] })
    },
  })

  const applicationMutation = useMutation({
    mutationFn: async (values: ApplicationFormValues) =>
      createInstructorApplication(values.reason),
  })

  const isAdmin = session?.user.roles.includes('admin') ?? false
  const isInstructor = session?.user.roles.includes('instructor') ?? false

  return (
    <div className="page-stack">
      <section className="page-hero">
        <span className="eyebrow">Profile</span>
        <div className="page-stack">
          <h1 className="page-title">Account center</h1>
          <p className="lede">
            Phase 1 uses the same auth API as Swagger and curl-based verification, but exercises it through a calmer operational shell.
          </p>
        </div>
      </section>

      <section className="stat-grid">
        <article className="stat-card">
          <strong>Signed in as</strong>
          <span>{session?.user.email ?? 'Unknown user'}</span>
        </article>
        <article className="stat-card">
          <strong>Roles</strong>
          <span>{session?.user.roles.join(', ') ?? 'None'}</span>
        </article>
        <article className="stat-card">
          <strong>Status</strong>
          <span>{profileQuery.data?.is_verified ? 'Verified' : 'Verification pending'}</span>
        </article>
      </section>

      <section className="content-grid">
        <article className="section-card">
          <div className="page-stack">
            <div>
              <h2>Personal details</h2>
              <p>Update the fields exposed by PATCH /auth/me.</p>
            </div>

            {profileQuery.isError ? (
              <div className="message message--error" role="alert">
                {getErrorMessage(profileQuery.error)}
              </div>
            ) : null}

            <form
              className="form-grid"
              onSubmit={profileForm.handleSubmit((values) => profileMutation.mutate(values))}
            >
              <div className="split-grid">
                <label className="field">
                  <span>First name</span>
                  <input {...profileForm.register('first_name')} />
                </label>
                <label className="field">
                  <span>Last name</span>
                  <input {...profileForm.register('last_name')} />
                </label>
              </div>

              <label className="field">
                <span>Avatar URL</span>
                <input placeholder="https://example.com/avatar.jpg" {...profileForm.register('avatar_url')} />
              </label>

              {profileMutation.isError ? (
                <div className="message message--error" role="alert">
                  {getErrorMessage(profileMutation.error)}
                </div>
              ) : null}

              {profileMutation.isSuccess ? (
                <div className="message message--success" role="status">
                  Profile updated.
                </div>
              ) : null}

              <div className="button-row">
                <button className="button button--accent" disabled={profileMutation.isPending} type="submit">
                  {profileMutation.isPending ? 'Saving...' : 'Save profile'}
                </button>
              </div>
            </form>
          </div>
        </article>

        <aside className="section-card">
          <div className="page-stack">
            <div>
              <h2>Session notes</h2>
              <p>Auth remains server-authoritative. The UI only mirrors what the API returns.</p>
            </div>

            <div className="meta-list">
              <div className="meta-card" style={{ padding: '0.95rem' }}>
                <strong>Account ID</strong>
                <span className="mono">{profileQuery.data?.id ?? session?.user.id}</span>
              </div>
              <div className="meta-card" style={{ padding: '0.95rem' }}>
                <strong>Verified</strong>
                <span>{profileQuery.data?.is_verified ? 'Yes' : 'No'}</span>
              </div>
              <div className="meta-card" style={{ padding: '0.95rem' }}>
                <strong>Admin desk</strong>
                <span>{isAdmin ? 'Available in navigation' : 'Hidden until role changes'}</span>
              </div>
            </div>

            {!isAdmin && !isInstructor ? (
              <form
                className="form-grid"
                onSubmit={applicationForm.handleSubmit((values) => applicationMutation.mutate(values))}
              >
                <div>
                  <h3>Instructor application</h3>
                  <p>Submit the Phase 1 student-to-instructor request from the profile surface.</p>
                </div>

                <label className="field">
                  <span>Reason</span>
                  <textarea placeholder="Share why you should teach on EduCorp." {...applicationForm.register('reason')} />
                </label>

                {applicationMutation.isError ? (
                  <div className="message message--error" role="alert">
                    {getErrorMessage(applicationMutation.error)}
                  </div>
                ) : null}

                {applicationMutation.isSuccess ? (
                  <div className="message message--success" role="status">
                    Application submitted with status {applicationMutation.data.status}.
                  </div>
                ) : null}

                <button className="button" disabled={applicationMutation.isPending} type="submit">
                  {applicationMutation.isPending ? 'Submitting...' : 'Apply'}
                </button>
              </form>
            ) : null}
          </div>
        </aside>
      </section>
    </div>
  )
}