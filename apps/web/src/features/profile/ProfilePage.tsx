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
      <div className="page-header">
        <h1 className="page-header__title">Profile</h1>
        <p className="page-header__description">Manage your account details and settings.</p>
      </div>

      <div className="stat-row">
        <div className="stat-item">
          <div className="stat-item__label">Email</div>
          <div className="stat-item__value">{session?.user.email ?? 'Unknown'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Roles</div>
          <div className="stat-item__value">{session?.user.roles.join(', ') ?? 'None'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Status</div>
          <div className="stat-item__value">
            {profileQuery.data?.is_verified ? 'Verified' : 'Pending verification'}
          </div>
        </div>
      </div>

      <div className="page-columns">
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Personal details</h2>
            <p className="card__description">Update your name and avatar.</p>
          </div>

          {profileQuery.isError ? (
            <div className="message message--error" role="alert">
              {getErrorMessage(profileQuery.error)}
            </div>
          ) : null}

          <form
            className="form-stack"
            onSubmit={profileForm.handleSubmit((values) => profileMutation.mutate(values))}
          >
            <div className="form-row">
              <label className="form-field">
                <span className="form-field__label">First name</span>
                <input {...profileForm.register('first_name')} />
              </label>
              <label className="form-field">
                <span className="form-field__label">Last name</span>
                <input {...profileForm.register('last_name')} />
              </label>
            </div>

            <label className="form-field">
              <span className="form-field__label">Avatar URL</span>
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

            <div className="btn-row">
              <button className="btn btn--primary" disabled={profileMutation.isPending} type="submit">
                {profileMutation.isPending ? 'Saving...' : 'Save changes'}
              </button>
            </div>
          </form>
        </div>

        <div className="page-stack">
          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Account info</h2>
            </div>
            <div className="meta-list">
              <div className="meta-item">
                <div className="meta-item__label">Account ID</div>
                <div className="meta-item__value mono">{profileQuery.data?.id ?? session?.user.id}</div>
              </div>
              <div className="meta-item">
                <div className="meta-item__label">Verified</div>
                <div className="meta-item__value">{profileQuery.data?.is_verified ? 'Yes' : 'No'}</div>
              </div>
              <div className="meta-item">
                <div className="meta-item__label">Admin access</div>
                <div className="meta-item__value">{isAdmin ? 'Enabled' : 'Disabled'}</div>
              </div>
            </div>
          </div>

          {!isAdmin && !isInstructor ? (
            <div className="card">
              <div className="card__header">
                <h2 className="card__title">Instructor application</h2>
                <p className="card__description">Apply to become an instructor on EduCorp.</p>
              </div>

              <form
                className="form-stack"
                onSubmit={applicationForm.handleSubmit((values) => applicationMutation.mutate(values))}
              >
                <label className="form-field">
                  <span className="form-field__label">Reason</span>
                  <textarea placeholder="Describe why you want to teach on EduCorp." {...applicationForm.register('reason')} />
                </label>

                {applicationMutation.isError ? (
                  <div className="message message--error" role="alert">
                    {getErrorMessage(applicationMutation.error)}
                  </div>
                ) : null}

                {applicationMutation.isSuccess ? (
                  <div className="message message--success" role="status">
                    Application submitted ({applicationMutation.data.status}).
                  </div>
                ) : null}

                <button className="btn btn--primary" disabled={applicationMutation.isPending} type="submit">
                  {applicationMutation.isPending ? 'Submitting...' : 'Submit application'}
                </button>
              </form>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
