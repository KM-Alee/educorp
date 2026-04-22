import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowRight,
  Compass,
  BookOpen,
  Award,
  UserCog,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  GraduationCap,
  FolderOpen,
  ClipboardList,
  PlayCircle,
  Trophy,
  ChevronDown,
  Download,
  FileText,
  Layers,
  Tag,
  Clock,
} from 'lucide-react'

import {
  cancelEnrollment,
  completeModule,
  getCertificate,
  getCourse,
  getEnrollment,
  getEnrollmentProgress,
  getProgressDashboard,
  listCertificates,
  listEnrollments,
  listAssets,
  getAssetContentBlob,
  type AssetOut,
  type DashboardCourse,
  type EnrollmentRecord,
  type ModuleDetail,
} from '../../lib/api'
import { AIAssistantPanel } from '../ai/AIPanels'
import { getErrorMessage } from '../../lib/types'

function statusBadgeClass(status: string): string {
  const normalized = status.toUpperCase()
  if (normalized === 'COMPLETED') return 'badge badge--success'
  if (normalized === 'CANCELLED') return 'badge badge--danger'
  if (normalized === 'IN_PROGRESS') return 'badge badge--accent'
  return 'badge badge--warning'
}

function DashboardCourseCard({ course, enrollmentId }: { course: DashboardCourse; enrollmentId?: string }) {
  return (
    <Link className="course-item" to={enrollmentId ? `/app/learning/${enrollmentId}` : '/app/learning'}>
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

function EnrollmentCard({
  enrollment,
  course,
}: {
  enrollment: EnrollmentRecord
  course?: DashboardCourse
}) {
  return (
    <Link className="learning-enrollment-card" to={`/app/learning/${enrollment.id}`}>
      <div className="learning-enrollment-card__top">
        <span className={statusBadgeClass(enrollment.status)}>{enrollment.status}</span>
        {typeof course?.progress_percent === 'number' ? (
          <span className="badge">{course.progress_percent.toFixed(0)}%</span>
        ) : null}
      </div>
      <div className="learning-enrollment-card__title">
        {course?.course_title ?? `Course ${enrollment.course_id.slice(0, 8)}`}
      </div>
      <div className="learning-enrollment-card__meta">
        <span>
          <Clock3 size={14} />
          Enrolled {new Date(enrollment.enrolled_at).toLocaleString()}
        </span>
        {course?.last_activity_at ? (
          <span>Last activity {new Date(course.last_activity_at).toLocaleDateString()}</span>
        ) : null}
      </div>
      {typeof course?.progress_percent === 'number' ? (
        <div className="learning-enrollment-card__progress">
          <div
            className="learning-enrollment-card__progress-fill"
            style={{ width: `${course.progress_percent}%` }}
          />
        </div>
      ) : null}
      <div className="learning-enrollment-card__footer">
        <span>{course?.status === 'COMPLETED' ? 'Review completed course' : 'Resume learning'}</span>
        <ArrowRight size={16} />
      </div>
    </Link>
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

  const enrollmentIdByCourseId = new Map(
    (enrollmentsQuery.data?.data ?? []).map((enrollment) => [enrollment.course_id, enrollment.id]),
  )

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
              <DashboardCourseCard
                course={course}
                enrollmentId={enrollmentIdByCourseId.get(course.course_id)}
                key={course.course_id}
              />
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
  const dashboardQuery = useQuery({
    queryKey: ['progress-dashboard', 'learning-page'],
    queryFn: getProgressDashboard,
  })
  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', 'learning'],
    queryFn: () => listEnrollments({ page: 1, page_size: 50 }),
  })

  const courseByEnrollment = new Map(
    (dashboardQuery.data?.courses ?? []).map((course) => [course.course_id, course]),
  )

  const allEnrollments = enrollmentsQuery.data?.data ?? []
  const activeEnrollments = allEnrollments.filter((e) =>
    ['ENROLLED', 'IN_PROGRESS'].includes(e.status.toUpperCase()),
  )
  const completedEnrollments = allEnrollments.filter((e) => e.status.toUpperCase() === 'COMPLETED')
  const cancelledEnrollments = allEnrollments.filter((e) => e.status.toUpperCase() === 'CANCELLED')

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">My learning</h1>
        <p className="page-header__description">
          Pick up active courses, review completed work, and jump back into the exact module you
          last touched.
        </p>
      </div>

      {dashboardQuery.data ? (
        <div className="stat-row">
          <div className="stat-item">
            <div className="stat-item__icon"><PlayCircle size={20} /></div>
            <div className="stat-item__label">Active now</div>
            <div className="stat-item__value">{dashboardQuery.data.active_courses}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__icon"><CheckCircle2 size={20} /></div>
            <div className="stat-item__label">Completed</div>
            <div className="stat-item__value">{dashboardQuery.data.completed_courses}</div>
          </div>
          <div className="stat-item">
            <div className="stat-item__icon"><Award size={20} /></div>
            <div className="stat-item__label">Certificates</div>
            <div className="stat-item__value">{dashboardQuery.data.total_certificates}</div>
          </div>
        </div>
      ) : null}

      {enrollmentsQuery.isError ? (
        <div className="message message--error">{getErrorMessage(enrollmentsQuery.error)}</div>
      ) : null}

      {/* Active / in-progress courses */}
      {activeEnrollments.length > 0 ? (
        <div className="learning-section">
          <div className="learning-section__header">
            <div>
              <h2 className="learning-section__title">
                <PlayCircle size={20} />
                Continue learning
              </h2>
              <p className="learning-section__desc">Pick up where you left off.</p>
            </div>
            <Link className="btn btn--sm btn--secondary" to="/app/catalog">Browse more</Link>
          </div>
          <div className="learning-enrollment-grid">
            {activeEnrollments.map((enrollment) => (
              <EnrollmentCard
                course={courseByEnrollment.get(enrollment.course_id)}
                enrollment={enrollment}
                key={enrollment.id}
              />
            ))}
          </div>
        </div>
      ) : null}

      {/* Completed courses */}
      {completedEnrollments.length > 0 ? (
        <div className="learning-section">
          <div className="learning-section__header">
            <div>
              <h2 className="learning-section__title">
                <CheckCircle2 size={20} />
                Completed
              </h2>
              <p className="learning-section__desc">Courses you've finished — review anytime.</p>
            </div>
          </div>
          <div className="learning-enrollment-grid learning-enrollment-grid--compact">
            {completedEnrollments.map((enrollment) => (
              <EnrollmentCard
                course={courseByEnrollment.get(enrollment.course_id)}
                enrollment={enrollment}
                key={enrollment.id}
              />
            ))}
          </div>
        </div>
      ) : null}

      {/* Cancelled courses (collapsed / muted) */}
      {cancelledEnrollments.length > 0 ? (
        <div className="learning-section learning-section--muted">
          <div className="learning-section__header">
            <div>
              <h2 className="learning-section__title">Cancelled</h2>
              <p className="learning-section__desc">These enrollments are no longer active.</p>
            </div>
          </div>
          <div className="learning-enrollment-grid learning-enrollment-grid--compact">
            {cancelledEnrollments.map((enrollment) => (
              <EnrollmentCard
                course={courseByEnrollment.get(enrollment.course_id)}
                enrollment={enrollment}
                key={enrollment.id}
              />
            ))}
          </div>
        </div>
      ) : null}

      {!enrollmentsQuery.isLoading && allEnrollments.length === 0 ? (
        <div className="empty">
          <div className="empty__icon"><BookOpen size={40} /></div>
          <div className="empty__title">No enrollments yet</div>
          <div className="empty__description">
            Browse the catalog to find your first course and start learning.
          </div>
          <Link className="btn btn--primary" style={{ marginTop: '1rem' }} to="/app/catalog">
            Browse catalog
          </Link>
        </div>
      ) : null}
    </div>
  )
}

/** Per-module asset list with download support (used inside the learning player) */
function LearningModuleAssets({
  courseId,
  moduleId,
  isLocked,
}: {
  courseId: string
  moduleId: string
  isLocked: boolean
}) {
  const assetsQuery = useQuery({
    queryKey: ['learning-assets', courseId, moduleId],
    queryFn: () => listAssets(courseId, moduleId),
    enabled: !isLocked,
  })

  const handleDownload = async (asset: AssetOut) => {
    try {
      const response = await getAssetContentBlob(courseId, moduleId, asset.id, 'attachment')
      const objectUrl = URL.createObjectURL(response.blob)
      const anchor = document.createElement('a')
      anchor.href = objectUrl
      anchor.download = response.fileName ?? asset.file_name
      anchor.click()
      URL.revokeObjectURL(objectUrl)
    } catch {
      alert('Download failed. Please try again.')
    }
  }

  if (isLocked) {
    return <div className="module-item__assets-empty">This enrollment is locked.</div>
  }
  if (assetsQuery.isLoading) {
    return <div className="module-item__assets-loading">Loading materials…</div>
  }
  if (assetsQuery.isError) {
    return <div className="module-item__assets-empty">Could not load materials.</div>
  }
  const assets: AssetOut[] = assetsQuery.data ?? []
  if (!assets.length) {
    return <div className="module-item__assets-empty">No study materials uploaded yet.</div>
  }

  return (
    <div className="module-item__assets">
      {assets.map((asset) => (
        <div key={asset.id} className="module-asset-btn module-asset-btn--card">
          <div className="module-asset-btn__lead">
            <FileText size={16} />
            <div className="module-asset-btn__copy">
              <span className="module-asset-btn__name">{asset.title || asset.file_name}</span>
              <span className="module-asset-btn__file">
                {asset.file_name} · {asset.asset_type.toUpperCase()}
              </span>
            </div>
          </div>
          <div className="module-asset-btn__actions">
            <button
              className="btn btn--sm btn--secondary"
              onClick={() => handleDownload(asset)}
              type="button"
            >
              <Download size={14} />
              Download
            </button>
          </div>
        </div>
      ))}
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

  const courseQuery = useQuery({
    queryKey: ['learning-course', progressQuery.data?.course_id],
    queryFn: () => getCourse(progressQuery.data?.course_id ?? ''),
    enabled: Boolean(progressQuery.data?.course_id),
  })

  const completeMutation = useMutation({
    mutationFn: (moduleId: string) =>
      completeModule({ enrollment_id: enrollmentId, module_id: moduleId }),
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

  const enrollment = enrollmentQuery.data ?? null
  const progress = progressQuery.data ?? null
  const progressModules = progress?.modules ?? []
  const isLocked = enrollment?.status === 'CANCELLED' || progress?.status === 'CANCELLED'

  const canCancel = enrollment?.status === 'ENROLLED' || enrollment?.status === 'IN_PROGRESS'
  const completedCount = progressModules.filter((m) => m.is_completed).length
  const totalCount = progressModules.length
  const allDone = totalCount > 0 && completedCount === totalCount

  const course = courseQuery.data
  const courseModuleById = new Map(
    (course?.modules ?? []).map((m) => [m.id, m]),
  )

  const assistantModules: ModuleDetail[] = course
    ? course.modules.map((m) => ({
        id: m.id,
        course_id: course.id,
        title: m.title,
        description: m.description,
        sort_order: m.sort_order,
        is_required: m.is_required,
        estimated_duration: null,
        created_at: course.created_at,
        updated_at: course.updated_at,
      }))
    : progressModules.map((m, index) => ({
        id: m.module_id,
        course_id: progress?.course_id ?? '',
        title: m.module_title,
        description: null,
        sort_order: index,
        is_required: true,
        estimated_duration: null,
        created_at: enrollment?.enrolled_at ?? '',
        updated_at: enrollment?.enrolled_at ?? '',
      }))

  if (enrollmentQuery.isLoading || progressQuery.isLoading) {
    return <div className="empty">Loading your course...</div>
  }
  if (enrollmentQuery.isError) {
    return <div className="message message--error">{getErrorMessage(enrollmentQuery.error)}</div>
  }
  if (progressQuery.isError) {
    return <div className="message message--error">{getErrorMessage(progressQuery.error)}</div>
  }
  if (!enrollment || !progress) {
    return <div className="empty">Course workspace not found.</div>
  }

  return (
    <div className="page-stack">
      {/* ── Header ── */}
      <div className="course-detail-hero">
        <div className="page-header__breadcrumb">
          <Link to="/app/learning">My learning</Link>
          <span>/</span>
          <span>Course player</span>
        </div>
        <h1 className="course-detail-hero__title">
          {allDone ? (
            <><Trophy size={28} style={{ verticalAlign: 'middle', marginRight: 8 }} />Course complete!</>
          ) : (
            course?.title ?? 'Continue learning'
          )}
        </h1>
        {course?.short_description ? (
          <p className="course-detail-hero__sub">{course.short_description}</p>
        ) : null}
      </div>

      {/* ── Stat bar ── */}
      {course ? (
        <div className="stat-row">
          {course.category ? (
            <div className="stat-item">
              <div className="stat-item__icon"><Tag size={18} /></div>
              <div className="stat-item__label">Category</div>
              <div className="stat-item__value">{course.category}</div>
            </div>
          ) : null}
          {course.difficulty ? (
            <div className="stat-item">
              <div className="stat-item__icon"><GraduationCap size={18} /></div>
              <div className="stat-item__label">Difficulty</div>
              <div className="stat-item__value">{course.difficulty}</div>
            </div>
          ) : null}
          {course.estimated_duration ? (
            <div className="stat-item">
              <div className="stat-item__icon"><Clock size={18} /></div>
              <div className="stat-item__label">Duration</div>
              <div className="stat-item__value">{course.estimated_duration}</div>
            </div>
          ) : null}
          <div className="stat-item">
            <div className="stat-item__icon"><Layers size={18} /></div>
            <div className="stat-item__label">Modules</div>
            <div className="stat-item__value">{totalCount}</div>
          </div>
        </div>
      ) : null}

      {/* ── Progress hero ── */}
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
          {progress.last_activity_at ? (
            <p className="learning-progress-hero__meta">
              Last activity {new Date(progress.last_activity_at).toLocaleString()}
            </p>
          ) : null}
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

      {/* ── Module sections ── */}
      <div className="card">
        <div className="card__header">
          <h2 className="card__title">
            <Layers size={18} style={{ marginRight: 6, verticalAlign: -3 }} />
            {totalCount} {totalCount === 1 ? 'module' : 'modules'}
          </h2>
          <p className="card__description">
            Expand a module to view materials and mark it complete when you finish.
          </p>
        </div>
        <div className="module-list">
          {progressModules.map((progressModule, index) => {
            const courseModule = courseModuleById.get(progressModule.module_id)
            const isNextUp = !progressModule.is_completed &&
              progressModules.slice(0, index).every((m) => m.is_completed)

            return (
              <details
                key={progressModule.module_id}
                className="module-item module-item--expandable"
                open={isNextUp}
              >
                <summary className="module-item__summary">
                  <span className={`module-item__badge${progressModule.is_completed ? ' module-item__badge--done' : ''}`}>
                    {progressModule.is_completed ? <CheckCircle2 size={16} /> : index + 1}
                  </span>
                  <div className="module-item__info">
                    <div className="module-item__title">{progressModule.module_title}</div>
                    {courseModule?.description ? (
                      <div className="module-item__description">{courseModule.description}</div>
                    ) : null}
                    <div className="module-item__meta-row">
                      {progressModule.is_completed ? (
                        <span className="badge badge--success">Completed</span>
                      ) : (
                        <span className="badge badge--accent">
                          {progressModule.progress_percent.toFixed(0)}% complete
                        </span>
                      )}
                      {isNextUp && !isLocked ? (
                        <span className="badge">Up next</span>
                      ) : null}
                    </div>
                  </div>
                  <ChevronDown size={16} className="module-item__chevron" />
                </summary>

                <div className="module-item__content">
                  <LearningModuleAssets
                    courseId={progress.course_id}
                    moduleId={progressModule.module_id}
                    isLocked={isLocked}
                  />

                  {!progressModule.is_completed && !isLocked ? (
                    <div className="module-item__actions">
                      <button
                        className="btn btn--primary btn--sm"
                        disabled={completeMutation.isPending}
                        onClick={() => completeMutation.mutate(progressModule.module_id)}
                        type="button"
                      >
                        <BookOpenCheck size={15} />
                        {completeMutation.isPending ? 'Saving…' : 'Mark lesson complete'}
                      </button>
                    </div>
                  ) : progressModule.is_completed ? (
                    <div className="module-item__actions">
                      <span className="badge badge--success">
                        <CheckCircle2 size={14} />
                        Lesson complete
                      </span>
                    </div>
                  ) : null}
                </div>
              </details>
            )
          })}
        </div>
      </div>

      {/* ── AI assistant ── */}
      <AIAssistantPanel
        canAsk={!isLocked}
        courseId={progress.course_id}
        disabledMessage={
          isLocked ? 'The assistant is unavailable for cancelled enrollments.' : undefined
        }
        modules={assistantModules}
      />
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

      {certificatesQuery.isError ? (
        <div className="message message--error">{getErrorMessage(certificatesQuery.error)}</div>
      ) : null}

      {!certificatesQuery.isLoading && certificatesQuery.data?.length ? (
        <div className="cert-grid">
          {certificatesQuery.data.map((certificate) => (
            <Link className="cert-card" to={`/app/certificates/${certificate.id}`} key={certificate.id}>
              <div className="cert-card__icon">
                <Trophy size={24} />
              </div>
              <div className="cert-card__body">
                <div className="cert-card__title">{certificate.course_title}</div>
                <div className="cert-card__number mono">{certificate.certificate_number}</div>
                <div className="cert-card__date">
                  Issued {new Date(certificate.issued_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}
                </div>
              </div>
              <span className="badge badge--success cert-card__badge">Completed</span>
            </Link>
          ))}
        </div>
      ) : null}

      {!certificatesQuery.isLoading && !certificatesQuery.data?.length ? (
        <div className="empty">
          <div className="empty__icon"><Trophy size={40} /></div>
          <div className="empty__title">No certificates yet</div>
          <div className="empty__description">
            Complete a course to earn your first certificate.
          </div>
          <Link className="btn btn--primary" style={{ marginTop: '1rem' }} to="/app/catalog">
            Browse courses
          </Link>
        </div>
      ) : null}
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

  const cert = certificateQuery.data

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header__breadcrumb">
          <Link to="/app/certificates">Certificates</Link>
          <span>/</span>
          <span className="mono">{certificateId.slice(0, 8)}</span>
        </div>
        <h1 className="page-header__title">Certificate of Completion</h1>
        <p className="page-header__description">Official credential issued by EduCorp.</p>
      </div>

      {/* Visual certificate */}
      <div className="certificate-frame">
        <div className="certificate-frame__outer">
          <div className="certificate-frame__inner">
            <div className="certificate-frame__brand">
              <span className="certificate-frame__logo">E</span>
              <span className="certificate-frame__brand-name">EduCorp</span>
            </div>
            <p className="certificate-frame__eyebrow">Certificate of Completion</p>
            <p className="certificate-frame__presented">This certifies that</p>
            <h2 className="certificate-frame__student">{cert.student_name}</h2>
            <p className="certificate-frame__completed">has successfully completed</p>
            <h3 className="certificate-frame__course">{cert.course_title}</h3>
            <div className="certificate-frame__divider" />
            <div className="certificate-frame__meta">
              <div className="certificate-frame__meta-item">
                <span className="certificate-frame__meta-label">Issued</span>
                <span className="certificate-frame__meta-value">
                  {new Date(cert.issued_at).toLocaleDateString(undefined, {
                    year: 'numeric', month: 'long', day: 'numeric',
                  })}
                </span>
              </div>
              <div className="certificate-frame__meta-item">
                <span className="certificate-frame__meta-label">Certificate number</span>
                <span className="certificate-frame__meta-value mono">{cert.certificate_number}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Details card */}
      <div className="card card--subtle">
        <div className="stat-row" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <div>
            <p style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--black-faint)', marginBottom: 4 }}>Learner</p>
            <p style={{ fontWeight: 600 }}>{cert.student_name}</p>
          </div>
          <div>
            <p style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--black-faint)', marginBottom: 4 }}>Course</p>
            <p style={{ fontWeight: 600 }}>{cert.course_title}</p>
          </div>
          <div>
            <p style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--black-faint)', marginBottom: 4 }}>Enrollment</p>
            <p className="mono" style={{ fontSize: 13 }}>{cert.enrollment_id.slice(0, 16)}…</p>
          </div>
        </div>
      </div>
    </div>
  )
}
