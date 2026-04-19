import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  cancelEnrollment,
  completeModule,
  getCertificate,
  getEnrollment,
  getEnrollmentProgress,
  getProgressDashboard,
  listCertificates,
  listEnrollments,
  type CertificateDetail,
  type CertificateSummary,
  type DashboardCourse,
  type EnrollmentProgress,
  type EnrollmentRecord,
} from '../../lib/api'
import { getErrorMessage } from '../../lib/types'

function statusBadgeClass(status: string): string {
  const normalized = status.toUpperCase()
  if (normalized === 'COMPLETED') return 'badge badge--success'
  if (normalized === 'CANCELLED') return 'badge badge--danger'
  if (normalized === 'IN_PROGRESS') return 'badge badge--accent'
  return 'badge badge--warning'
}

function DashboardCourseCard({ course }: { course: DashboardCourse }) {
  return (
    <Link className="course-item" to="/app/learning">
      <div className="course-item__info">
        <div className="course-item__title">{course.course_title}</div>
        <div className="course-item__meta">
          {course.last_activity_at
            ? `Last activity ${new Date(course.last_activity_at).toLocaleString()}`
            : 'No activity yet'}
        </div>
      </div>
      <div className="course-item__badges">
        <span className={statusBadgeClass(course.status)}>{course.status}</span>
        <span className="badge">{course.progress_percent.toFixed(0)}%</span>
      </div>
    </Link>
  )
}

function EnrollmentCard({ enrollment }: { enrollment: EnrollmentRecord }) {
  return (
    <Link className="course-item" to={`/app/learning/${enrollment.id}`}>
      <div className="course-item__info">
        <div className="course-item__title mono">Enrollment {enrollment.id.slice(0, 8)}</div>
        <div className="course-item__meta">
          Enrolled {new Date(enrollment.enrolled_at).toLocaleString()}
        </div>
      </div>
      <div className="course-item__badges">
        <span className={statusBadgeClass(enrollment.status)}>{enrollment.status}</span>
      </div>
    </Link>
  )
}

function CertificateCard({ certificate }: { certificate: CertificateSummary }) {
  return (
    <Link className="course-item" to={`/certificates/${certificate.id}`}>
      <div className="course-item__info">
        <div className="course-item__title">{certificate.course_title}</div>
        <div className="course-item__meta mono">{certificate.certificate_number}</div>
      </div>
      <div className="course-item__badges">
        <span className="badge badge--success">
          {new Date(certificate.issued_at).toLocaleDateString()}
        </span>
      </div>
    </Link>
  )
}

function LearningSummary({ progress }: { progress: EnrollmentProgress }) {
  const completedModules = progress.modules.filter((module) => module.is_completed).length

  return (
    <div className="stat-row">
      <div className="stat-item">
        <div className="stat-item__label">Progress</div>
        <div className="stat-item__value">{progress.progress_percent.toFixed(0)}%</div>
      </div>
      <div className="stat-item">
        <div className="stat-item__label">Status</div>
        <div className="stat-item__value">{progress.status}</div>
      </div>
      <div className="stat-item">
        <div className="stat-item__label">Modules completed</div>
        <div className="stat-item__value">
          {completedModules}/{progress.modules.length}
        </div>
      </div>
      <div className="stat-item">
        <div className="stat-item__label">Last activity</div>
        <div className="stat-item__value">
          {progress.last_activity_at
            ? new Date(progress.last_activity_at).toLocaleString()
            : 'Not started'}
        </div>
      </div>
    </div>
  )
}

export function DashboardPage() {
  const dashboardQuery = useQuery({
    queryKey: ['progress-dashboard'],
    queryFn: getProgressDashboard,
  })

  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', 'dashboard'],
    queryFn: () => listEnrollments({ page: 1, page_size: 10 }),
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Learning dashboard</h1>
        <p className="page-header__description">
          Track active courses, resume work, and find recent certificates.
        </p>
      </div>

      {dashboardQuery.data ? (
        <div className="stat-row">
          <div className="stat-item">
            <div className="stat-item__label">Active courses</div>
            <div className="stat-item__value">{dashboardQuery.data.active_courses}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__label">Completed courses</div>
            <div className="stat-item__value">{dashboardQuery.data.completed_courses}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__label">Certificates</div>
            <div className="stat-item__value">{dashboardQuery.data.total_certificates}</div>
          </div>
        </div>
      ) : null}

      <div className="page-columns page-columns--wide">
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">In progress</h2>
            <p className="card__description">Resume active learning directly from your dashboard.</p>
          </div>

          {dashboardQuery.isError ? (
            <div className="message message--error">{getErrorMessage(dashboardQuery.error)}</div>
          ) : null}

          <div className="course-list">
            {dashboardQuery.data?.courses.map((course) => (
              <DashboardCourseCard course={course} key={course.course_id} />
            ))}
          </div>

          {!dashboardQuery.isLoading && !dashboardQuery.data?.courses.length ? (
            <div className="empty">No learning activity yet. Enroll in a course from the catalog.</div>
          ) : null}
        </div>

        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Recent enrollments</h2>
            <p className="card__description">Jump into an enrollment or manage its current status.</p>
          </div>

          {enrollmentsQuery.isError ? (
            <div className="message message--error">{getErrorMessage(enrollmentsQuery.error)}</div>
          ) : null}

          <div className="course-list">
            {enrollmentsQuery.data?.data.map((enrollment) => (
              <EnrollmentCard enrollment={enrollment} key={enrollment.id} />
            ))}
          </div>

          {!enrollmentsQuery.isLoading && !enrollmentsQuery.data?.data.length ? (
            <div className="empty">No enrollments yet.</div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export function LearningPage() {
  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', 'learning'],
    queryFn: () => listEnrollments({ page: 1, page_size: 50 }),
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">My learning</h1>
        <p className="page-header__description">All enrollments, with status-aware entry points.</p>
      </div>

      <div className="card">
        {enrollmentsQuery.isError ? (
          <div className="message message--error">{getErrorMessage(enrollmentsQuery.error)}</div>
        ) : null}

        <div className="course-list">
          {enrollmentsQuery.data?.data.map((enrollment) => (
            <EnrollmentCard enrollment={enrollment} key={enrollment.id} />
          ))}
        </div>

        {!enrollmentsQuery.isLoading && !enrollmentsQuery.data?.data.length ? (
          <div className="empty">You have not enrolled in any courses yet.</div>
        ) : null}
      </div>
    </div>
  )
}

export function LearningEnrollmentPage() {
  const { enrollmentId = '' } = useParams()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const enrollmentQuery = useQuery({
    queryKey: ['enrollment', enrollmentId],
    queryFn: () => getEnrollment(enrollmentId),
  })

  const progressQuery = useQuery({
    queryKey: ['enrollment-progress', enrollmentId],
    queryFn: () => getEnrollmentProgress(enrollmentId),
  })

  const completeMutation = useMutation({
    mutationFn: (moduleId: string) => completeModule({ enrollment_id: enrollmentId, module_id: moduleId }),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['enrollment-progress', enrollmentId] })
      await queryClient.invalidateQueries({ queryKey: ['progress-dashboard'] })
      await queryClient.invalidateQueries({ queryKey: ['certificates'] })
      if (result.certificate?.id) {
        navigate(`/certificates/${result.certificate.id}`)
      }
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => cancelEnrollment(enrollmentId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['enrollment', enrollmentId] })
      await queryClient.invalidateQueries({ queryKey: ['enrollment-progress', enrollmentId] })
      await queryClient.invalidateQueries({ queryKey: ['enrollments'] })
      await queryClient.invalidateQueries({ queryKey: ['progress-dashboard'] })
    },
  })

  if (enrollmentQuery.isLoading || progressQuery.isLoading) {
    return <div className="empty">Loading learning workspace...</div>
  }

  if (enrollmentQuery.isError) {
    return <div className="message message--error">{getErrorMessage(enrollmentQuery.error)}</div>
  }

  if (progressQuery.isError) {
    return <div className="message message--error">{getErrorMessage(progressQuery.error)}</div>
  }

  const enrollment = enrollmentQuery.data
  const progress = progressQuery.data

  if (!enrollment || !progress) {
    return <div className="empty">Learning workspace not found.</div>
  }

  const canCancel = enrollment.status === 'ENROLLED'
  const isLocked = enrollment.status === 'CANCELLED' || progress.status === 'CANCELLED'

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header__breadcrumb">
          <Link to="/app/learning">My learning</Link>
          <span>/</span>
          <span className="mono">{enrollment.id.slice(0, 8)}</span>
        </div>
        <h1 className="page-header__title">Enrollment workspace</h1>
        <p className="page-header__description">
          Completion is tracked per required module for this enrollment.
        </p>
      </div>

      <LearningSummary progress={progress} />

      {cancelMutation.isError ? (
        <div className="message message--error">{getErrorMessage(cancelMutation.error)}</div>
      ) : null}

      <div className="card">
        <div className="card__header">
          <h2 className="card__title">Enrollment</h2>
          <p className="card__description">Use this route as the active learning surface for progress updates.</p>
        </div>

        <div className="meta-list">
          <div className="meta-item">
            <div className="meta-item__label">Enrollment status</div>
            <div className="meta-item__value">
              <span className={statusBadgeClass(enrollment.status)}>{enrollment.status}</span>
            </div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">Course ID</div>
            <div className="meta-item__value mono">{progress.course_id}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">Started</div>
            <div className="meta-item__value">
              {progress.started_at ? new Date(progress.started_at).toLocaleString() : 'Not started'}
            </div>
          </div>
        </div>

        {canCancel ? (
          <div className="btn-row" style={{ marginTop: '1rem' }}>
            <button
              className="btn btn--danger"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              type="button"
            >
              {cancelMutation.isPending ? 'Cancelling...' : 'Cancel enrollment'}
            </button>
          </div>
        ) : null}
      </div>

      <div className="card">
        <div className="card__header">
          <h2 className="card__title">Required modules</h2>
          <p className="card__description">Completing all required modules awards the course certificate.</p>
        </div>

        {completeMutation.isError ? (
          <div className="message message--error">{getErrorMessage(completeMutation.error)}</div>
        ) : null}

        <div className="course-list">
          {progress.modules.map((module) => (
            <div className="course-item" key={module.module_id}>
              <div className="course-item__info">
                <div className="course-item__title">{module.module_title}</div>
                <div className="course-item__meta">
                  {module.is_completed
                    ? `Completed ${module.completed_at ? new Date(module.completed_at).toLocaleString() : ''}`
                    : `${module.progress_percent.toFixed(0)}% complete`}
                </div>
              </div>
              <div className="course-item__badges">
                <span className={module.is_completed ? 'badge badge--success' : 'badge badge--warning'}>
                  {module.is_completed ? 'Completed' : 'Pending'}
                </span>
                <button
                  className="btn btn--sm btn--primary"
                  disabled={module.is_completed || isLocked || completeMutation.isPending}
                  onClick={() => completeMutation.mutate(module.module_id)}
                  type="button"
                >
                  {module.is_completed ? 'Done' : 'Mark complete'}
                </button>
              </div>
            </div>
          ))}
        </div>

        {!progress.modules.length ? (
          <div className="empty">No required modules were captured for this enrollment.</div>
        ) : null}
      </div>
    </div>
  )
}

export function CertificatesPage() {
  const certificatesQuery = useQuery({
    queryKey: ['certificates'],
    queryFn: listCertificates,
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Certificates</h1>
        <p className="page-header__description">Issued certificates for completed courses.</p>
      </div>

      <div className="card">
        {certificatesQuery.isError ? (
          <div className="message message--error">{getErrorMessage(certificatesQuery.error)}</div>
        ) : null}

        <div className="course-list">
          {certificatesQuery.data?.map((certificate) => (
            <CertificateCard certificate={certificate} key={certificate.id} />
          ))}
        </div>

        {!certificatesQuery.isLoading && !certificatesQuery.data?.length ? (
          <div className="empty">No certificates issued yet.</div>
        ) : null}
      </div>
    </div>
  )
}

function CertificateDetailCard({ certificate }: { certificate: CertificateDetail }) {
  return (
    <div className="card">
      <div className="card__header">
        <h1 className="card__title">{certificate.course_title}</h1>
        <p className="card__description">Certificate of completion</p>
      </div>

      <div className="meta-list">
        <div className="meta-item">
          <div className="meta-item__label">Learner</div>
          <div className="meta-item__value">{certificate.student_name}</div>
        </div>
        <div className="meta-item">
          <div className="meta-item__label">Certificate number</div>
          <div className="meta-item__value mono">{certificate.certificate_number}</div>
        </div>
        <div className="meta-item">
          <div className="meta-item__label">Issued</div>
          <div className="meta-item__value">
            {new Date(certificate.issued_at).toLocaleString()}
          </div>
        </div>
        <div className="meta-item">
          <div className="meta-item__label">Enrollment</div>
          <div className="meta-item__value mono">{certificate.enrollment_id}</div>
        </div>
      </div>
    </div>
  )
}

export function CertificateDetailPage() {
  const { certificateId = '' } = useParams()
  const certificateQuery = useQuery({
    queryKey: ['certificate', certificateId],
    queryFn: () => getCertificate(certificateId),
  })

  if (certificateQuery.isLoading) {
    return <div className="empty">Loading certificate...</div>
  }

  if (certificateQuery.isError) {
    return <div className="message message--error">{getErrorMessage(certificateQuery.error)}</div>
  }

  if (!certificateQuery.data) {
    return <div className="empty">Certificate not found.</div>
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header__breadcrumb">
          <Link to="/app/certificates">Certificates</Link>
          <span>/</span>
          <span className="mono">{certificateId.slice(0, 8)}</span>
        </div>
      </div>
      <CertificateDetailCard certificate={certificateQuery.data} />
    </div>
  )
}
