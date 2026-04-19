import { useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  getAdminWorkflow,
  getPlatformAnalytics,
  listAdminUsers,
  listAdminAuditLog,
  listAdminDlq,
  listAdminWorkflows,
  listInstructorApplications,
  replayAdminDlqMessage,
  reviewInstructorApplication,
  retryAdminWorkflow,
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
  const today = new Date().toISOString().slice(0, 10)
  const [fromDate, setFromDate] = useState(today)
  const [toDate, setToDate] = useState(today)

  const analyticsQuery = useQuery({
    queryKey: ['admin-platform-analytics', fromDate, toDate],
    queryFn: () => getPlatformAnalytics({ from_date: fromDate, to_date: toDate }),
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Platform analytics</h1>
        <p className="page-header__description">
          Enrollment trends, course completion rates, and platform health metrics.
        </p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">From</span>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </label>
          <label className="form-field">
            <span className="form-field__label">To</span>
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </label>
        </div>

        {analyticsQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(analyticsQuery.error)}
          </div>
        ) : null}

        <div className="stat-row">
          <div className="stat-item">
            <div className="stat-item__label">Total users</div>
            <div className="stat-item__value">{analyticsQuery.data?.total_students ?? '--'}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__label">Enrollments</div>
            <div className="stat-item__value">{analyticsQuery.data?.enrollments ?? '--'}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__label">Completions</div>
            <div className="stat-item__value">{analyticsQuery.data?.completions ?? '--'}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__label">Published courses</div>
            <div className="stat-item__value">{analyticsQuery.data?.published_courses ?? '--'}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__label">AI usage</div>
            <div className="stat-item__value">{analyticsQuery.data?.ai_usage ?? '--'}</div>
          </div>
        </div>
        <div className="table-wrap">
          <table className="table">
            <tbody>
              <tr>
                <th>Window</th>
                <td>{fromDate} to {toDate}</td>
              </tr>
              <tr>
                <th>Completion ratio</th>
                <td>
                  {analyticsQuery.data && analyticsQuery.data.enrollments > 0
                    ? `${((analyticsQuery.data.completions / analyticsQuery.data.enrollments) * 100).toFixed(1)}%`
                    : '--'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export function AdminWorkflowsPage() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('')
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null)

  const workflowsQuery = useQuery({
    queryKey: ['admin-workflows', status],
    queryFn: () => listAdminWorkflows({ status }),
  })

  const workflowDetailQuery = useQuery({
    queryKey: ['admin-workflow-detail', selectedWorkflowId],
    queryFn: () => getAdminWorkflow(selectedWorkflowId as string),
    enabled: Boolean(selectedWorkflowId),
  })

  const retryMutation = useMutation({
    mutationFn: retryAdminWorkflow,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['admin-workflows'] })
      if (selectedWorkflowId) {
        await queryClient.invalidateQueries({ queryKey: ['admin-workflow-detail', selectedWorkflowId] })
      }
    },
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Workflow operations</h1>
        <p className="page-header__description">
          Monitor Temporal publishing workflows, retry failed runs, and inspect execution history.
        </p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="FAILED">Failed</option>
              <option value="READY">Ready</option>
              <option value="PREPARING">Preparing</option>
              <option value="PUBLISHING">Publishing</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </label>
        </div>

        {workflowsQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(workflowsQuery.error)}
          </div>
        ) : null}

        {retryMutation.isError ? (
          <div className="message message--error" role="alert" style={{ marginBottom: '0.75rem' }}>
            {getErrorMessage(retryMutation.error)}
          </div>
        ) : null}

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Status</th>
                <th>Course</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {workflowsQuery.data?.data.map((workflow) => (
                <tr key={workflow.workflow_id ?? workflow.version_id}>
                  <td>
                    <div className="mono">{workflow.workflow_id ?? workflow.version_id}</div>
                    <div className="table__secondary">Version {workflow.version_id}</div>
                  </td>
                  <td>
                    <span className="badge">{workflow.status}</span>
                  </td>
                  <td className="mono">{workflow.course_id}</td>
                  <td>
                    <div className="btn-row">
                      <button className="btn btn--sm btn--ghost" type="button" onClick={() => setSelectedWorkflowId(workflow.workflow_id)}>
                        Inspect
                      </button>
                      <button
                        className="btn btn--sm btn--primary"
                        disabled={retryMutation.isPending || !workflow.workflow_id || workflow.status !== 'FAILED'}
                        type="button"
                        onClick={() => workflow.workflow_id && retryMutation.mutate(workflow.workflow_id)}
                      >
                        Retry
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedWorkflowId && workflowDetailQuery.data ? (
          <div className="card card--subtle" style={{ marginTop: '1rem' }}>
            <div className="card__header">
              <h2 className="card__title">Workflow detail</h2>
              <p className="card__description mono">{selectedWorkflowId}</p>
            </div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Step</th>
                    <th>Status</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {workflowDetailQuery.data.steps.map((step, index) => (
                    <tr key={`${String(step.id ?? index)}`}>
                      <td>{String(step.step_name ?? 'unknown')}</td>
                      <td>{String(step.status ?? 'unknown')}</td>
                      <td>{String(step.error_message ?? '')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

export function AdminAuditLogPage() {
  const [actorId, setActorId] = useState('')
  const [action, setAction] = useState('')

  const auditQuery = useQuery({
    queryKey: ['admin-audit-log', actorId, action],
    queryFn: () => listAdminAuditLog({ actor_id: actorId, action }),
  })

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
            <input placeholder="User ID" value={actorId} onChange={(e) => setActorId(e.target.value)} />
          </label>
          <label className="form-field">
            <span className="form-field__label">Action type</span>
            <select value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="">All actions</option>
              <option value="user.roles_updated">Role change</option>
              <option value="user.status_updated">Account status</option>
              <option value="enrollment.created">Enrollment created</option>
            </select>
          </label>
        </div>

        {auditQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(auditQuery.error)}
          </div>
        ) : null}

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>When</th>
                <th>Source</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Correlation</th>
              </tr>
            </thead>
            <tbody>
              {auditQuery.data?.data.map((entry) => (
                <tr key={`${entry.source}-${entry.id}`}>
                  <td>{new Date(entry.created_at).toLocaleString()}</td>
                  <td><span className="badge">{entry.source}</span></td>
                  <td>{entry.action}</td>
                  <td>
                    <div>{entry.resource_type}</div>
                    <div className="table__secondary mono">{entry.resource_id ?? '-'}</div>
                  </td>
                  <td className="mono">{entry.correlation_id ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!auditQuery.isLoading && !auditQuery.data?.data.length ? (
          <div className="empty">No audit records match the current filters.</div>
        ) : null}
      </div>
    </div>
  )
}

export function AdminDLQPage() {
  const queryClient = useQueryClient()
  const [topic, setTopic] = useState('')

  const dlqQuery = useQuery({
    queryKey: ['admin-dlq', topic],
    queryFn: () => listAdminDlq({ topic }),
  })

  const replayMutation = useMutation({
    mutationFn: replayAdminDlqMessage,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['admin-dlq'] })
    },
  })

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

        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">Topic</span>
            <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="course.lifecycle" />
          </label>
        </div>

        {dlqQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(dlqQuery.error)}
          </div>
        ) : null}

        {replayMutation.isError ? (
          <div className="message message--error" role="alert" style={{ marginBottom: '0.75rem' }}>
            {getErrorMessage(replayMutation.error)}
          </div>
        ) : null}

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Topic</th>
                <th>Error</th>
                <th>Replay</th>
              </tr>
            </thead>
            <tbody>
              {dlqQuery.data?.data.map((message) => (
                <tr key={`${message.source}-${message.id}`}>
                  <td><span className="badge">{message.source}</span></td>
                  <td>
                    <div>{message.topic}</div>
                    <div className="table__secondary mono">{message.event_type ?? '-'}</div>
                  </td>
                  <td>{message.error_message}</td>
                  <td>
                    <button
                      className="btn btn--sm btn--primary"
                      type="button"
                      disabled={replayMutation.isPending}
                      onClick={() => replayMutation.mutate({ messageId: message.id, source: message.source })}
                    >
                      Replay
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!dlqQuery.isLoading && !dlqQuery.data?.data.length ? (
          <div className="empty">No dead-letter messages right now.</div>
        ) : null}
      </div>
    </div>
  )
}
