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
      <div className="page-header">
        <h1 className="page-header__title">Instructor applications</h1>
        <p className="page-header__description">Review and manage instructor role requests.</p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
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
