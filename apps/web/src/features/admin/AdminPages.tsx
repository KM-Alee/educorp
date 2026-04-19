import { useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  listAdminUsers,
  listInstructorApplications,
  reviewInstructorApplication,
  updateAdminUserRoles,
  updateAdminUserStatus,
} from '../../lib/api'
import { getErrorMessage } from '../../lib/types'

function roleTogglePayload(roles: string[], role: string) {
  return roles.includes(role)
    ? { add_roles: [] as string[], remove_roles: [role] }
    : { add_roles: [role], remove_roles: [] as string[] }
}

export function AdminUsersPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [isActive, setIsActive] = useState('')

  const usersQuery = useQuery({
    queryKey: ['admin-users', search, role, isActive],
    queryFn: () => listAdminUsers({ search, role, isActive }),
  })

  const rolesMutation = useMutation({
    mutationFn: updateAdminUserRoles,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const statusMutation = useMutation({
    mutationFn: updateAdminUserStatus,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Users</h1>
        <p className="page-header__description">Manage user accounts, roles, and activation status.</p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">Search</span>
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name or email" />
          </label>
          <label className="form-field">
            <span className="form-field__label">Role</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="">All roles</option>
              <option value="student">Student</option>
              <option value="instructor">Instructor</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <label className="form-field">
            <span className="form-field__label">Status</span>
            <select value={isActive} onChange={(e) => setIsActive(e.target.value)}>
              <option value="">All</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </label>
        </div>

        {usersQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(usersQuery.error)}
          </div>
        ) : null}

        {(rolesMutation.isError || statusMutation.isError) ? (
          <div className="message message--error" role="alert" style={{ marginBottom: '0.75rem' }}>
            {getErrorMessage(rolesMutation.error ?? statusMutation.error)}
          </div>
        ) : null}

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>User</th>
                <th>Roles</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {usersQuery.data?.data.map((user) => (
                <tr key={user.id}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{user.first_name} {user.last_name}</div>
                    <div className="table__secondary">{user.email}</div>
                    <div className="table__secondary mono">{user.id}</div>
                  </td>
                  <td>
                    <div className="badge-group">
                      {user.roles.map((r) => (
                        <span className="badge" key={r}>{r}</span>
                      ))}
                    </div>
                  </td>
                  <td>
                    <div>{user.is_active ? 'Active' : 'Inactive'}</div>
                    <div className="table__secondary">
                      {user.is_verified ? 'Verified' : 'Unverified'}
                    </div>
                  </td>
                  <td>
                    <div className="btn-row">
                      <button
                        className="btn btn--sm"
                        onClick={() =>
                          rolesMutation.mutate({
                            userId: user.id,
                            ...roleTogglePayload(user.roles, 'instructor'),
                          })
                        }
                        type="button"
                      >
                        {user.roles.includes('instructor') ? '- Instructor' : '+ Instructor'}
                      </button>
                      <button
                        className="btn btn--sm"
                        onClick={() =>
                          rolesMutation.mutate({
                            userId: user.id,
                            ...roleTogglePayload(user.roles, 'admin'),
                          })
                        }
                        type="button"
                      >
                        {user.roles.includes('admin') ? '- Admin' : '+ Admin'}
                      </button>
                      <button
                        className="btn btn--sm btn--ghost"
                        onClick={() =>
                          statusMutation.mutate({ userId: user.id, is_active: !user.is_active })
                        }
                        type="button"
                      >
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!usersQuery.isLoading && !usersQuery.data?.data.length ? (
          <div className="empty">No users match the current filter.</div>
        ) : null}
      </div>
    </div>
  )
}

export function AdminApplicationsPage() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('PENDING')

  const applicationsQuery = useQuery({
    queryKey: ['instructor-applications', status],
    queryFn: () => listInstructorApplications(status),
  })

  const reviewMutation = useMutation({
    mutationFn: reviewInstructorApplication,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['instructor-applications'] })
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Instructor applications</h1>
        <p className="page-header__description">Review and manage instructor role requests.</p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="PENDING">Pending</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </label>
        </div>

        {applicationsQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(applicationsQuery.error)}
          </div>
        ) : null}

        {reviewMutation.isError ? (
          <div className="message message--error" role="alert" style={{ marginBottom: '0.75rem' }}>
            {getErrorMessage(reviewMutation.error)}
          </div>
        ) : null}

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Application ID</th>
                <th>Status</th>
                <th>Created</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {applicationsQuery.data?.data.map((application) => (
                <tr key={application.id}>
                  <td className="mono">{application.id}</td>
                  <td>
                    <span className={`badge ${application.status === 'APPROVED' ? 'badge--success' : application.status === 'REJECTED' ? 'badge--danger' : 'badge--warning'}`}>
                      {application.status}
                    </span>
                  </td>
                  <td>{new Date(application.created_at).toLocaleString()}</td>
                  <td>
                    <div className="btn-row">
                      <button
                        className="btn btn--sm btn--primary"
                        disabled={reviewMutation.isPending || application.status !== 'PENDING'}
                        onClick={() =>
                          reviewMutation.mutate({
                            applicationId: application.id,
                            status: 'APPROVED',
                          })
                        }
                        type="button"
                      >
                        Approve
                      </button>
                      <button
                        className="btn btn--sm btn--danger"
                        disabled={reviewMutation.isPending || application.status !== 'PENDING'}
                        onClick={() =>
                          reviewMutation.mutate({
                            applicationId: application.id,
                            status: 'REJECTED',
                          })
                        }
                        type="button"
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!applicationsQuery.isLoading && !applicationsQuery.data?.data.length ? (
          <div className="empty">No applications in this state.</div>
        ) : null}
      </div>
    </div>
  )
}

export function AdminAnalyticsPage() {
  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Platform analytics</h1>
        <p className="page-header__description">
          Enrollment trends, course completion rates, and platform health metrics.
        </p>
      </div>

      <div className="stat-row">
        <div className="stat-item">
          <div className="stat-item__label">Total users</div>
          <div className="stat-item__value">--</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Active enrollments</div>
          <div className="stat-item__value">--</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Certificates issued</div>
          <div className="stat-item__value">--</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Published courses</div>
          <div className="stat-item__value">--</div>
        </div>
      </div>

      <div className="placeholder-page">
        <div className="placeholder-page__icon">&#128200;</div>
        <h2 className="placeholder-page__title">Analytics dashboard coming soon</h2>
        <p className="placeholder-page__description">
          Kafka consumers will aggregate enrollment, completion, and engagement events
          into real-time analytics views.
        </p>
        <div className="placeholder-page__badge">
          <span className="badge badge--warning">Phase 6</span>
        </div>
      </div>
    </div>
  )
}

export function AdminWorkflowsPage() {
  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Workflow operations</h1>
        <p className="page-header__description">
          Monitor Temporal publishing workflows, retry failed runs, and inspect execution history.
        </p>
      </div>

      <div className="placeholder-page">
        <div className="placeholder-page__icon">&#9881;</div>
        <h2 className="placeholder-page__title">Workflow monitor</h2>
        <p className="placeholder-page__description">
          Active publishing workflows, their current step, and completion status will be
          displayed here. Admins can retry or cancel stuck workflows.
        </p>
        <div className="placeholder-page__badge">
          <span className="badge badge--warning">Phase 6</span>
        </div>
      </div>
    </div>
  )
}

export function AdminAuditLogPage() {
  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Audit log</h1>
        <p className="page-header__description">
          Immutable record of administrative actions, role changes, and security events.
        </p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">Actor</span>
            <input placeholder="User ID or email" disabled />
          </label>
          <label className="form-field">
            <span className="form-field__label">Action type</span>
            <select disabled>
              <option value="">All actions</option>
              <option value="role_change">Role change</option>
              <option value="publish">Publish</option>
              <option value="account_status">Account status</option>
            </select>
          </label>
        </div>

        <div className="empty">
          Audit events will appear here once the analytics Kafka consumers are operational.
        </div>
      </div>
    </div>
  )
}

export function AdminDLQPage() {
  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Dead letter queue</h1>
        <p className="page-header__description">
          Inspect and replay failed Kafka messages that exceeded retry limits.
        </p>
      </div>

      <div className="card">
        <div className="card__header">
          <h2 className="card__title">Failed messages</h2>
          <p className="card__description">
            Messages that could not be processed after maximum retries. Review the payload and replay or discard.
          </p>
        </div>

        <div className="empty">
          No dead-letter messages. The Kafka consumer pipeline will populate this queue when
          message processing fails after retries.
        </div>
      </div>
    </div>
  )
}
