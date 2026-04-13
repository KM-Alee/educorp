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
      <section className="page-hero">
        <span className="eyebrow">Admin</span>
        <h1 className="page-title">User desk</h1>
        <p className="lede">Review the seeded accounts, role assignments, and active status exposed by the auth service.</p>
      </section>

      <section className="admin-card">
        <div className="page-stack">
          <div className="filter-row">
            <label className="field" style={{ minWidth: '14rem' }}>
              <span>Search</span>
              <input value={search} onChange={(event) => setSearch(event.target.value)} />
            </label>
            <label className="field" style={{ minWidth: '12rem' }}>
              <span>Role</span>
              <select value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="">All roles</option>
                <option value="student">Student</option>
                <option value="instructor">Instructor</option>
                <option value="admin">Admin</option>
              </select>
            </label>
            <label className="field" style={{ minWidth: '12rem' }}>
              <span>Status</span>
              <select value={isActive} onChange={(event) => setIsActive(event.target.value)}>
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
            <div className="message message--error" role="alert">
              {getErrorMessage(rolesMutation.error ?? statusMutation.error)}
            </div>
          ) : null}

          <div className="table-shell">
            <table className="data-table">
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
                      <strong>{user.first_name} {user.last_name}</strong>
                      <div className="table-note">{user.email}</div>
                      <div className="table-note mono">{user.id}</div>
                    </td>
                    <td>
                      <div className="pill-group">
                        {user.roles.map((entry) => (
                          <span className="pill" key={entry}>{entry}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <div>{user.is_active ? 'Active' : 'Inactive'}</div>
                      <div className="table-note">{user.is_verified ? 'Verified' : 'Pending verification'}</div>
                    </td>
                    <td>
                      <div className="button-row">
                        <button
                          className="button button--small"
                          onClick={() =>
                            rolesMutation.mutate({
                              userId: user.id,
                              ...roleTogglePayload(user.roles, 'instructor'),
                            })
                          }
                          type="button"
                        >
                          {user.roles.includes('instructor') ? 'Remove instructor' : 'Grant instructor'}
                        </button>
                        <button
                          className="button button--small"
                          onClick={() =>
                            rolesMutation.mutate({
                              userId: user.id,
                              ...roleTogglePayload(user.roles, 'admin'),
                            })
                          }
                          type="button"
                        >
                          {user.roles.includes('admin') ? 'Remove admin' : 'Grant admin'}
                        </button>
                        <button
                          className="button button--small button--ghost"
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
            <div className="empty-state">No users match the current filter.</div>
          ) : null}
        </div>
      </section>
    </div>
  )
}

export function AdminApplicationsPage() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('pending')

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
      <section className="page-hero">
        <span className="eyebrow">Admin</span>
        <h1 className="page-title">Instructor queue</h1>
        <p className="lede">Approve or reject the student applications exposed by the Phase 1 auth service.</p>
      </section>

      <section className="admin-card">
        <div className="page-stack">
          <div className="filter-row">
            <label className="field" style={{ minWidth: '14rem' }}>
              <span>Status</span>
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="pending">Pending</option>
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
            <div className="message message--error" role="alert">
              {getErrorMessage(reviewMutation.error)}
            </div>
          ) : null}

          <div className="table-shell">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Application</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Review</th>
                </tr>
              </thead>
              <tbody>
                {applicationsQuery.data?.data.map((application) => (
                  <tr key={application.id}>
                    <td className="mono">{application.id}</td>
                    <td>{application.status}</td>
                    <td>{new Date(application.created_at).toLocaleString()}</td>
                    <td>
                      <div className="button-row">
                        <button
                          className="button button--small button--accent"
                          disabled={reviewMutation.isPending}
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
                          className="button button--small button--danger"
                          disabled={reviewMutation.isPending}
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
            <div className="empty-state">No applications in this state yet.</div>
          ) : null}
        </div>
      </section>
    </div>
  )
}