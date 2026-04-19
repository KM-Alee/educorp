import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  enrollInCourse,
  getCourse,
  getEnrollmentStatus,
  listModules,
  type ModuleDetail,
} from '../../lib/api'
import { useSessionState } from '../../lib/session'
import { AIAssistantPanel, AIEnhancementPanel } from '../ai/AIPanels'
import { getErrorMessage } from '../../lib/types'

function statusBadgeClass(status: string): string {
  const normalized = status.toUpperCase()
  if (normalized === 'COMPLETED') return 'badge badge--success'
  if (normalized === 'CANCELLED') return 'badge badge--danger'
  if (normalized === 'ENROLLED' || normalized === 'IN_PROGRESS') return 'badge badge--accent'
  return 'badge badge--warning'
}

export function StudentCoursePage() {
  const { courseId = '' } = useParams()
  const session = useSessionState()
  const queryClient = useQueryClient()
  const canEnhance = Boolean(
    session?.user.roles.some((role) => role === 'instructor' || role === 'admin'),
  )

  const courseQuery = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => getCourse(courseId),
  })

  const modulesQuery = useQuery({
    queryKey: ['modules', courseId],
    queryFn: () => listModules(courseId),
  })

  const enrollmentStatusQuery = useQuery({
    queryKey: ['enrollment-status', courseId],
    queryFn: () => getEnrollmentStatus(courseId),
    enabled: Boolean(session?.user.roles.includes('student')),
  })

  const enrollMutation = useMutation({
    mutationFn: () =>
      enrollInCourse({
        course_id: courseId,
        idempotency_key: `web-${courseId}`,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['enrollment-status', courseId] })
      await queryClient.invalidateQueries({ queryKey: ['enrollments'] })
      await queryClient.invalidateQueries({ queryKey: ['progress-dashboard'] })
    },
  })

  if (courseQuery.isLoading) {
    return (
      <div className="page-stack">
        <div className="card">
          <div className="empty">Loading course...</div>
        </div>
      </div>
    )
  }

  if (courseQuery.isError) {
    return (
      <div className="page-stack">
        <div className="card">
          <div className="message message--error">{getErrorMessage(courseQuery.error)}</div>
        </div>
      </div>
    )
  }

  const course = courseQuery.data
  if (!course) {
    return (
      <div className="page-stack">
        <div className="card">
          <div className="empty">Course not found.</div>
        </div>
      </div>
    )
  }

  const modules: ModuleDetail[] = modulesQuery.data ?? []
  const enrollmentStatus = enrollmentStatusQuery.data
  const isStudent = Boolean(session?.user.roles.includes('student'))
  const canUseAssistant = !isStudent || Boolean(enrollmentStatus?.is_enrolled)
  const assistantDisabledMessage = isStudent && !enrollmentStatus?.is_enrolled
    ? 'Enroll in this course to use the student assistant and track progress.'
    : undefined

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">{course.title}</h1>
        <p className="page-header__description">{course.description}</p>
      </div>

      <div className="stat-row">
        <div className="stat-item">
          <div className="stat-item__label">Category</div>
          <div className="stat-item__value">{course.category || 'N/A'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Difficulty</div>
          <div className="stat-item__value">{course.difficulty || 'N/A'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Duration</div>
          <div className="stat-item__value">{course.estimated_duration || 'N/A'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Modules</div>
          <div className="stat-item__value">{modules.length}</div>
        </div>
      </div>

      <div className="page-columns page-columns--wide">
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Catalog detail</h2>
            <p className="card__description">
              Browse the published shape of this course before starting an enrollment.
            </p>
          </div>

          {course.short_description ? <p>{course.short_description}</p> : null}

          {course.prerequisites.length ? (
            <div className="meta-list" style={{ marginTop: '1rem' }}>
              <div className="meta-item">
                <div className="meta-item__label">Prerequisites</div>
                <div className="meta-item__value">{course.prerequisites.join(', ')}</div>
              </div>
            </div>
          ) : null}

          {course.tags.length ? (
            <div className="badge-group" style={{ marginTop: '1rem' }}>
              {course.tags.map((tag) => (
                <span className="badge" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </div>

        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Enrollment</h2>
            <p className="card__description">
              Students move from catalog detail into an enrollment-scoped learning route.
            </p>
          </div>

          {enrollmentStatusQuery.isError ? (
            <div className="message message--error">{getErrorMessage(enrollmentStatusQuery.error)}</div>
          ) : null}
          {enrollMutation.isError ? (
            <div className="message message--error">{getErrorMessage(enrollMutation.error)}</div>
          ) : null}

          {isStudent ? (
            enrollmentStatus?.is_enrolled && enrollmentStatus.enrollment_id ? (
              <div className="page-stack">
                <div className="message message--success">
                  <span className={statusBadgeClass(enrollmentStatus.status ?? 'ENROLLED')}>
                    {enrollmentStatus.status ?? 'ENROLLED'}
                  </span>{' '}
                  {typeof enrollmentStatus.progress_percent === 'number'
                    ? `Progress ${enrollmentStatus.progress_percent.toFixed(0)}%`
                    : 'Enrollment is active.'}
                </div>
                <div className="btn-row">
                  <Link className="btn btn--primary" to={`/app/learning/${enrollmentStatus.enrollment_id}`}>
                    Open learning workspace
                  </Link>
                </div>
              </div>
            ) : (
              <div className="page-stack">
                <div className="message message--warning">
                  You are viewing catalog detail only. Enroll to start tracked learning and unlock AI help.
                </div>
                <div className="btn-row">
                  <button
                    className="btn btn--primary"
                    onClick={() => enrollMutation.mutate()}
                    type="button"
                    disabled={enrollMutation.isPending}
                  >
                    {enrollMutation.isPending ? 'Enrolling...' : 'Enroll now'}
                  </button>
                </div>
              </div>
            )
          ) : (
            <div className="message message--warning">
              Enrollment actions are available in the student experience.
            </div>
          )}
        </div>
      </div>

      <div className="page-stack">
        <AIAssistantPanel
          courseId={courseId}
          modules={modules}
          canAsk={canUseAssistant}
          disabledMessage={assistantDisabledMessage}
        />
        {canEnhance ? <AIEnhancementPanel courseId={courseId} modules={modules} /> : null}
      </div>

      {modulesQuery.isLoading ? (
        <div className="card">
          <div className="empty">Loading modules...</div>
        </div>
      ) : null}

      {modules.length > 0 ? (
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Published modules</h2>
            <p className="card__description">
              Required modules become tracked items once the learner enters an enrollment workspace.
            </p>
          </div>
          <div className="module-list">
            {modules.map((module) => (
              <div key={module.id} className="module-item">
                <div className="module-item__title">{module.title}</div>
                <div className="module-item__description">
                  {module.description || 'No description'}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
