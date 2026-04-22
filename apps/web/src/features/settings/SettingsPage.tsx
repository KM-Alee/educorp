import { useEffect, useState } from 'react'

import { useMutation, useQuery } from '@tanstack/react-query'

import {
  getNotificationPreferences,
  updateNotificationPreferences,
  type NotificationPreferences,
} from '../../lib/api'
import { getErrorMessage } from '../../lib/types'

export function SettingsPage() {
  const preferencesQuery = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: getNotificationPreferences,
  })
  const [form, setForm] = useState<Partial<NotificationPreferences>>({})

  useEffect(() => {
    if (preferencesQuery.data) {
      setForm(preferencesQuery.data)
    }
  }, [preferencesQuery.data])

  const updateMutation = useMutation({
    mutationFn: updateNotificationPreferences,
  })

  function updateField<K extends keyof NotificationPreferences>(key: K, value: NotificationPreferences[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Settings</h1>
        <p className="page-header__description">
          Manage account preferences, notification settings, and platform configuration.
        </p>
      </div>

      <div className="page-columns">
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Notification preferences</h2>
            <p className="card__description">Control which notifications you receive.</p>
          </div>

          {preferencesQuery.isError ? (
            <div className="message message--error" role="alert">
              {getErrorMessage(preferencesQuery.error)}
            </div>
          ) : null}

          <div className="form-stack">
            <label className="form-field--inline form-field">
              <input
                type="checkbox"
                checked={Boolean(form.enrollment_confirmed_in_app)}
                onChange={(e) => updateField('enrollment_confirmed_in_app', e.target.checked)}
              />
              <span className="form-field__label">In-app notifications for enrollment changes</span>
            </label>
            <label className="form-field--inline form-field">
              <input
                type="checkbox"
                checked={Boolean(form.enrollment_confirmed_email)}
                onChange={(e) => updateField('enrollment_confirmed_email', e.target.checked)}
              />
              <span className="form-field__label">Email notifications for enrollment changes</span>
            </label>
            <label className="form-field--inline form-field">
              <input
                type="checkbox"
                checked={Boolean(form.course_published_in_app)}
                onChange={(e) => updateField('course_published_in_app', e.target.checked)}
              />
              <span className="form-field__label">In-app course publishing updates</span>
            </label>
            <label className="form-field--inline form-field">
              <input
                type="checkbox"
                checked={Boolean(form.course_published_email)}
                onChange={(e) => updateField('course_published_email', e.target.checked)}
              />
              <span className="form-field__label">Email course publishing updates</span>
            </label>
            <label className="form-field--inline form-field">
              <input
                type="checkbox"
                checked={Boolean(form.course_completed_in_app)}
                onChange={(e) => updateField('course_completed_in_app', e.target.checked)}
              />
              <span className="form-field__label">In-app course completion alerts</span>
            </label>
            <label className="form-field--inline form-field">
              <input
                type="checkbox"
                checked={Boolean(form.course_completed_email)}
                onChange={(e) => updateField('course_completed_email', e.target.checked)}
              />
              <span className="form-field__label">Email course completion alerts</span>
            </label>
          </div>

          {updateMutation.isError ? (
            <div className="message message--error" role="alert" style={{ marginTop: '1rem' }}>
              {getErrorMessage(updateMutation.error)}
            </div>
          ) : null}

          {updateMutation.isSuccess ? (
            <div className="message message--success" role="status" style={{ marginTop: '1rem' }}>
              Preferences saved.
            </div>
          ) : null}

          <div className="btn-row" style={{ marginTop: '1.5rem' }}>
            <button
              className="btn btn--primary"
              disabled={updateMutation.isPending || preferencesQuery.isLoading}
              onClick={() => updateMutation.mutate(form)}
              type="button"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save preferences'}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Display</h2>
            <p className="card__description">Theme and appearance settings.</p>
          </div>

          <div className="meta-list">
            <div className="meta-item">
              <div className="meta-item__label">Theme</div>
              <div className="meta-item__value">Cream (default)</div>
            </div>
            <div className="meta-item">
              <div className="meta-item__label">Language</div>
              <div className="meta-item__value">English</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
