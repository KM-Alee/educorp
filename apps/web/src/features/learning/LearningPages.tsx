import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Compass,
  BookOpen,
  Award,
  UserCog,
  BookOpenCheck,
  CheckCircle2,
  GraduationCap,
  FolderOpen,
  ClipboardList,
  Play,
  Lock,
  FileText,
  Download,
  ChevronDown,
  ChevronUp,
  Circle,
  Trophy,
} from 'lucide-react'

import {
  cancelEnrollment,
  completeModule,
  getCertificate,
  getEnrollment,
  getEnrollmentProgress,
  getProgressDashboard,
  listCertificates,
  listEnrollments,
  listAssets,
  getAssetDownload,
  type AssetOut,
  type CertificateDetail,
  type CertificateSummary,
  type DashboardCourse,
  type EnrollmentProgress,
  type EnrollmentRecord,
  type LearningModuleProgress,
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
      {/* Welcome banner */}
      <div className="welcome-banner">
        <h1 className="welcome-banner__title">Welcome back</h1>
        <p className="welcome-banner__subtitle">
          Track active courses, resume your learning, and earn certificates.
        </p>
        <div className="welcome-banner__actions">
          <Link className="btn btn--primary" to="/app/catalog">Browse catalog</Link>
          <Link className="btn btn--outline" to="/app/certificates">My certificates</Link>
        </div>
      </div>

      {/* Quick actions */}
      <div className="quick-actions">
        <Link className="quick-action" to="/app/catalog">
          <div className="quick-action__icon"><Compass size={22} /></div>
          <div>
            <div className="quick-action__label">Find courses</div>
            <div className="quick-action__description">Explore the catalog</div>
          </div>
        </Link>
        <Link className="quick-action" to="/app/learning">
          <div className="quick-action__icon"><BookOpen size={22} /></div>
          <div>
            <div className="quick-action__label">My learning</div>
            <div className="quick-action__description">Continue where you left off</div>
          </div>
        </Link>
        <Link className="quick-action" to="/app/certificates">
          <div className="quick-action__icon"><Award size={22} /></div>
          <div>
            <div className="quick-action__label">Certificates</div>
            <div className="quick-action__description">View earned credentials</div>
          </div>
        </Link>
        <Link className="quick-action" to="/app/profile">
          <div className="quick-action__icon"><UserCog size={22} /></div>
          <div>
            <div className="quick-action__label">Profile</div>
            <div className="quick-action__description">Manage your account</div>
          </div>
        </Link>
      </div>

      {/* Stats */}
      {dashboardQuery.data ? (
        <div className="stat-row">
          <div className="stat-item">
            <div className="stat-item__icon"><BookOpenCheck size={20} /></div>
            <div className="stat-item__label">Active courses</div>
            <div className="stat-item__value">{dashboardQuery.data.active_courses}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__icon"><CheckCircle2 size={20} /></div>
            <div className="stat-item__label">Completed</div>
            <div className="stat-item__value">{dashboardQuery.data.completed_courses}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__icon"><GraduationCap size={20} /></div>
            <div className="stat-item__label">Certificates</div>
            <div className="stat-item__value">{dashboardQuery.data.total_certificates}</div>
          </div>
        </div>
      ) : null}

      {/* Main content */}
      <div className="page-columns page-columns--wide">
        <div className="card">
          <div className="card__header-row">
            <div>
              <h2 className="card__title">In progress</h2>
              <p className="card__description">Resume active learning directly from your dashboard.</p>
            </div>
            <Link className="btn btn--sm btn--secondary" to="/app/learning">View all</Link>
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
            <div className="empty">
              <div className="empty__icon"><FolderOpen size={36} /></div>
              <div className="empty__title">No courses yet</div>
              <div className="empty__description">Enroll in a course from the catalog to start learning.</div>
            </div>
          ) : null}
        </div>

        <div className="card">
          <div className="card__header-row">
            <div>
              <h2 className="card__title">Recent enrollments</h2>
              <p className="card__description">Jump into an enrollment or manage its status.</p>
            </div>
            <Link className="btn btn--sm btn--secondary" to="/app/learning">View all</Link>
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
            <div className="empty">
              <div className="empty__icon"><ClipboardList size={36} /></div>
              <div className="empty__title">No enrollments</div>
              <div className="empty__description">Start by browsing the course catalog.</div>
            </div>
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
  const [expandedModule, setExpandedModule] = useState<string | null>(null)

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
    return <div className="empty">Loading your course...</div>
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
    return <div className="empty">Course workspace not found.</div>
  }

  const isLocked = enrollment.status === 'CANCELLED' || progress.status === 'CANCELLED'
  const canCancel = enrollment.status === 'ENROLLED' || enrollment.status === 'IN_PROGRESS'
  const completedCount = progress.modules.filter((m) => m.is_completed).length
  const totalCount = progress.modules.length
  const allDone = totalCount > 0 && completedCount === totalCount

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header__breadcrumb">
          <Link to="/app/learning">My learning</Link>
          <span>/</span>
          <span>Course player</span>
        </div>
        <h1 className="page-header__title">
          {allDone ? <><Trophy size={28} style={{ verticalAlign: 'middle', marginRight: 8 }} />Course complete!</> : 'Continue learning'}
        </h1>
        <p className="page-header__description">
          Work through each module below. Mark each one complete when you're done — you'll receive your certificate automatically.
        </p>
      </div>

      {/* Progress hero */}
      <div className="learning-progress-hero">
        <div className="learning-progress-hero__ring">
          <svg viewBox="0 0 64 64" className="learning-progress-hero__svg">
            <circle cx="32" cy="32" r="27" className="learning-progress-hero__track" />
            <circle
              cx="32" cy="32" r="27"
              className="learning-progress-hero__fill"
              strokeDasharray={`${(progress.progress_percent / 100) * 169.6} 169.6`}
              strokeDashoffset="0"
              transform="rotate(-90 32 32)"
            />
          </svg>
          <span className="learning-progress-hero__pct">{progress.progress_percent.toFixed(0)}%</span>
        </div>
        <div className="learning-progress-hero__info">
          <p className="learning-progress-hero__headline">
            {allDone
              ? 'You finished every module — great work.'
              : `${completedCount} of ${totalCount} modules complete`}
          </p>
          <p className="learning-progress-hero__sub">
            {isLocked
              ? 'This enrollment has been cancelled.'
              : allDone
              ? 'Your certificate has been issued. Check the Certificates page.'
              : 'Keep going — you can pick up right where you left off.'}
          </p>
          <div className="learning-progress-bar">
            <div
              className="learning-progress-bar__fill"
              style={{ width: `${progress.progress_percent}%` }}
            />
          </div>
        </div>
        {canCancel && !allDone ? (
          <button
            className="btn btn--sm btn--ghost"
            disabled={cancelMutation.isPending}
            onClick={() => cancelMutation.mutate()}
            type="button"
          >
            {cancelMutation.isPending ? 'Cancelling…' : 'Cancel enrollment'}
          </button>
        ) : null}
      </div>

      {cancelMutation.isError ? (
        <div className="message message--error">{getErrorMessage(cancelMutation.error)}</div>
      ) : null}
      {completeMutation.isError ? (
        <div className="message message--error">{getErrorMessage(completeMutation.error)}</div>
      ) : null}

      {/* Module list */}
      <div className="learning-modules">
        {progress.modules.map((module, index) => (
          <LearningModuleCard
            key={module.module_id}
            courseId={progress.course_id}
            index={index}
            isLocked={isLocked}
            isPending={completeMutation.isPending}
            module={module}
            expanded={expandedModule === module.module_id}
            onToggle={() =>
              setExpandedModule((prev) => (prev === module.module_id ? null : module.module_id))
            }
            onComplete={() => completeMutation.mutate(module.module_id)}
          />
        ))}

        {!progress.modules.length ? (
          <div className="empty">No modules found for this enrollment.</div>
        ) : null}
      </div>
    </div>
  )
}

function LearningModuleCard({
  module,
  courseId,
  index,
  isLocked,
  isPending,
  expanded,
  onToggle,
  onComplete,
}: {
  module: LearningModuleProgress
  courseId: string
  index: number
  isLocked: boolean
  isPending: boolean
  expanded: boolean
  onToggle: () => void
  onComplete: () => void
}) {
  const assetsQuery = useQuery({
    queryKey: ['assets', courseId, module.module_id],
    queryFn: () => listAssets(courseId, module.module_id),
    enabled: expanded,
  })

  const handleDownload = async (asset: AssetOut) => {
    try {
      const dl = await getAssetDownload(courseId, module.module_id, asset.id)
      window.open(dl.download_url, '_blank')
    } catch {
      /* no-op */
    }
  }

  return (
    <div className={`learning-module-card ${module.is_completed ? 'learning-module-card--done' : ''} ${isLocked ? 'learning-module-card--locked' : ''}`}>
      <button className="learning-module-card__header" type="button" onClick={onToggle}>
        <span className="learning-module-card__num">
          {module.is_completed
            ? <CheckCircle2 size={20} className="learning-module-card__check" />
            : isLocked
            ? <Lock size={18} />
            : <span className="learning-module-card__index">{index + 1}</span>}
        </span>
        <span className="learning-module-card__title">{module.module_title}</span>
        <span className="learning-module-card__meta">
          {module.is_completed
            ? <span className="badge badge--success">Completed</span>
            : <span className="badge">{module.progress_percent.toFixed(0)}%</span>}
        </span>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {expanded ? (
        <div className="learning-module-card__body">
          {module.is_completed && module.completed_at ? (
            <p className="learning-module-card__completed-at">
              <CheckCircle2 size={14} /> Completed on {new Date(module.completed_at).toLocaleString()}
            </p>
          ) : null}

          <div className="learning-module-card__assets">
            {assetsQuery.isLoading ? (
              <p className="learning-module-card__assets-hint">Loading materials…</p>
            ) : assetsQuery.data?.length ? (
              assetsQuery.data.map((asset) => (
                <button
                  key={asset.id}
                  className="module-asset-btn"
                  onClick={() => handleDownload(asset)}
                  type="button"
                >
                  <FileText size={15} />
                  <span className="module-asset-btn__name">{asset.title || asset.file_name}</span>
                  <Download size={13} />
                </button>
              ))
            ) : (
              <p className="learning-module-card__assets-hint">No study materials for this module.</p>
            )}
          </div>

          {!module.is_completed && !isLocked ? (
            <div className="learning-module-card__footer">
              <button
                className="btn btn--primary"
                disabled={isPending}
                onClick={onComplete}
                type="button"
              >
                <BookOpenCheck size={16} />
                {isPending ? 'Saving…' : 'Mark as complete'}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
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
