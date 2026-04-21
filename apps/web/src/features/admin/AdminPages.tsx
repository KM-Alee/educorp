import { useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Users,
  ClipboardList,
  BarChart3,
  Zap,
  ScrollText,
  Wrench,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Clock,
  BookOpen,
} from 'lucide-react'

import {
  getAdminWorkflow,
  getPlatformAnalytics,
  listAdminUsers,
  listAdminAuditLog,
  listAdminDlq,
  listAdminWorkflows,
  listInstructorApplications,
  listAllEnrollments,
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
        <h1 className="page-header__title">Publishing queue</h1>
        <p className="page-header__description">
          Monitor course publishing jobs, retry failures, and review submission history.
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
        <h1 className="page-header__title">Activity log</h1>
        <p className="page-header__description">
          A record of admin actions, role changes, and account updates.
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
        <h1 className="page-header__title">Failed messages</h1>
        <p className="page-header__description">
          Review and retry messages that could not be delivered.
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

/* ─── Admin Dashboard ─────────────────────────────────────────────────── */
export function AdminDashboardPage() {
  const today = new Date().toISOString().slice(0, 10)
  const analyticsQuery = useQuery({
    queryKey: ['admin-platform-analytics', today, today],
    queryFn: () => getPlatformAnalytics({ from_date: today, to_date: today }),
  })
  const applicationsQuery = useQuery({
    queryKey: ['instructor-applications', 'PENDING'],
    queryFn: () => listInstructorApplications('PENDING'),
  })
  const enrollmentsQuery = useQuery({
    queryKey: ['admin-enrollments', 'PENDING'],
    queryFn: () => listAllEnrollments({ status: 'PENDING', page_size: 5 }),
  })

  const stats = analyticsQuery.data
  const pendingApps = applicationsQuery.data?.data.length ?? 0
  const pendingEnrollments = enrollmentsQuery.data?.data.length ?? 0

  return (
    <div className="page-stack">
      <div className="admin-hero">
        <div className="admin-hero__badge">
          <ShieldAlert size={16} />
          Administrator
        </div>
        <h1 className="admin-hero__title">Platform Control Centre</h1>
        <p className="admin-hero__sub">
          You have full authority over users, enrollments, publishing workflows, and audit records.
        </p>
      </div>

      {/* Authority stat strip */}
      <div className="stat-row">
        <div className="stat-item stat-item--dark">
          <div className="stat-item__label">Total users</div>
          <div className="stat-item__value">{stats?.total_students ?? '--'}</div>
        </div>
        <div className="stat-item stat-item--dark">
          <div className="stat-item__label">Enrollments</div>
          <div className="stat-item__value">{stats?.enrollments ?? '--'}</div>
        </div>
        <div className="stat-item stat-item--dark">
          <div className="stat-item__label">Published courses</div>
          <div className="stat-item__value">{stats?.published_courses ?? '--'}</div>
        </div>
        <div className="stat-item stat-item--warning">
          <div className="stat-item__label">Pending applications</div>
          <div className="stat-item__value">{pendingApps}</div>
        </div>
        <div className="stat-item stat-item--warning">
          <div className="stat-item__label">Pending enrollments</div>
          <div className="stat-item__value">{pendingEnrollments}</div>
        </div>
      </div>

      {/* Quick authority actions */}
      <div className="admin-quick-grid">
        <Link className="admin-quick-card" to="/app/admin/users">
          <Users size={24} />
          <div>
            <p className="admin-quick-card__title">Manage users</p>
            <p className="admin-quick-card__desc">Assign roles, activate or deactivate accounts</p>
          </div>
        </Link>
        <Link className="admin-quick-card admin-quick-card--highlight" to="/app/admin/enrollments">
          <BookOpen size={24} />
          <div>
            <p className="admin-quick-card__title">Enrollment approvals</p>
            <p className="admin-quick-card__desc">Approve or reject student enrollment requests</p>
          </div>
          {pendingEnrollments > 0 ? (
            <span className="admin-quick-card__badge">{pendingEnrollments}</span>
          ) : null}
        </Link>
        <Link className="admin-quick-card admin-quick-card--highlight" to="/app/admin/instructor-applications">
          <ClipboardList size={24} />
          <div>
            <p className="admin-quick-card__title">Instructor applications</p>
            <p className="admin-quick-card__desc">Review and approve instructor role requests</p>
          </div>
          {pendingApps > 0 ? (
            <span className="admin-quick-card__badge">{pendingApps}</span>
          ) : null}
        </Link>
        <Link className="admin-quick-card" to="/app/admin/analytics">
          <BarChart3 size={24} />
          <div>
            <p className="admin-quick-card__title">Platform analytics</p>
            <p className="admin-quick-card__desc">Trends, completions, and AI usage</p>
          </div>
        </Link>
        <Link className="admin-quick-card" to="/app/admin/workflows">
          <Zap size={24} />
          <div>
            <p className="admin-quick-card__title">Workflow operations</p>
            <p className="admin-quick-card__desc">Monitor and retry Temporal publishing workflows</p>
          </div>
        </Link>
        <Link className="admin-quick-card" to="/app/admin/audit-log">
          <ScrollText size={24} />
          <div>
            <p className="admin-quick-card__title">Audit log</p>
            <p className="admin-quick-card__desc">Immutable record of all admin actions</p>
          </div>
        </Link>
        <Link className="admin-quick-card" to="/app/admin/dlq">
          <Wrench size={24} />
          <div>
            <p className="admin-quick-card__title">Dead letter queue</p>
            <p className="admin-quick-card__desc">Inspect and replay failed Kafka messages</p>
          </div>
        </Link>
      </div>
    </div>
  )
}

/* ─── Admin Enrollment Approvals ─────────────────────────────────────── */
export function AdminEnrollmentsPage() {
  const [status, setStatus] = useState('')

  const enrollmentsQuery = useQuery({
    queryKey: ['admin-enrollments', status],
    queryFn: () => listAllEnrollments({ status: status || undefined, page_size: 50 }),
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header__badge"><ShieldAlert size={14} /> Admin only</div>
        <h1 className="page-header__title">All enrollments</h1>
        <p className="page-header__description">
          Monitor enrollment activity across every course on the platform.
        </p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All statuses</option>
              <option value="ENROLLED">Enrolled</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </label>
        </div>

        {enrollmentsQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(enrollmentsQuery.error)}
          </div>
        ) : null}

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Enrollment</th>
                <th>Course</th>
                <th>Student</th>
                <th>Status</th>
                <th>Enrolled</th>
              </tr>
            </thead>
            <tbody>
              {enrollmentsQuery.data?.data.map((enrollment) => (
                <tr key={enrollment.id}>
                  <td className="mono">{enrollment.id.slice(0, 8)}</td>
                  <td className="mono">{enrollment.course_id.slice(0, 8)}</td>
                  <td className="mono">{enrollment.student_id.slice(0, 8)}</td>
                  <td>
                    <span className={`badge ${
                      enrollment.status === 'ACTIVE' ? 'badge--success'
                      : enrollment.status === 'CANCELLED' ? 'badge--danger'
                      : 'badge--warning'
                    }`}>
                      {enrollment.status === 'PENDING' ? <Clock size={11} /> : null}
                      {enrollment.status === 'ACTIVE' ? <CheckCircle2 size={11} /> : null}
                      {enrollment.status === 'CANCELLED' ? <XCircle size={11} /> : null}
                      {' '}{enrollment.status}
                    </span>
                  </td>
                  <td>{new Date(enrollment.enrolled_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!enrollmentsQuery.isLoading && !enrollmentsQuery.data?.data.length ? (
          <div className="empty">
            No enrollments found{status ? ` with status ${status}` : ''}.
          </div>
        ) : null}
      </div>
    </div>
  )
}
