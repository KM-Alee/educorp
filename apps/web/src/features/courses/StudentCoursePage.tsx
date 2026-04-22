import { useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import {
  BookOpen,
  Bot,
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  FileText,
  GraduationCap,
  Layers,
  Sparkles,
  Tag,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react'

import {
  getAssetContentBlob,
  enrollInCourse,
  getAssetDownload,
  getCourse,
  getEnrollmentStatus,
  listAssets,
  type AssetOut,
  type ModuleDetail,
} from '../../lib/api'
import { useSessionState } from '../../lib/session'
import { AIAssistantPanel, AIEnhancementPanel } from '../ai/AIPanels'
import { getErrorMessage } from '../../lib/types'

type CourseTab = 'overview' | 'modules' | 'ai'

function statusBadgeClass(status: string): string {
  const normalized = status.toUpperCase()
  if (normalized === 'COMPLETED') return 'badge badge--success'
  if (normalized === 'CANCELLED') return 'badge badge--danger'
  if (normalized === 'ENROLLED' || normalized === 'IN_PROGRESS') return 'badge badge--accent'
  return 'badge badge--warning'
}

/* Inline component: shows downloadable assets for a module */
function ModuleAssetList({
  courseId,
  moduleId,
  canViewAssets,
}: {
  courseId: string
  moduleId: string
  canViewAssets: boolean
}) {
  const assetsQuery = useQuery({
    queryKey: ['assets', courseId, moduleId],
    queryFn: () => listAssets(courseId, moduleId),
    enabled: canViewAssets,
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

  const handlePreview = async (asset: AssetOut) => {
    try {
      const dl = await getAssetDownload(courseId, moduleId, asset.id)
      window.open(dl.view_url ?? dl.download_url, '_blank', 'noopener,noreferrer')
    } catch {
      alert('Preview failed. Please try again.')
    }
  }

  if (!canViewAssets) {
    return <div className="module-item__assets-empty">Enroll or sign in to view downloadable materials.</div>
  }

  if (assetsQuery.isLoading) return <div className="module-item__assets-loading">Loading materials…</div>

  const assets: AssetOut[] = assetsQuery.data ?? []
  if (!assets.length) return <div className="module-item__assets-empty">No study materials uploaded yet.</div>

  return (
    <div className="module-item__assets">
      {assets.map((asset) => (
        <div key={asset.id} className="module-asset-btn module-asset-btn--card">
          <div className="module-asset-btn__lead">
            <FileText size={16} />
            <div className="module-asset-btn__copy">
              <span className="module-asset-btn__name">{asset.title || asset.file_name}</span>
              <span className="module-asset-btn__file">{asset.file_name}</span>
            </div>
          </div>
          <div className="module-asset-btn__actions">
            <button className="btn btn--sm btn--secondary" onClick={() => handleDownload(asset)} type="button">
              <Download size={14} />
              Download
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

export function StudentCoursePage() {
  const { courseId = '' } = useParams()
  const session = useSessionState()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<CourseTab>('overview')

  const courseQuery = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => getCourse(courseId),
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
        <div className="card"><div className="empty">Loading course...</div></div>
      </div>
    )
  }

  if (courseQuery.isError) {
    return (
      <div className="page-stack">
        <div className="card"><div className="message message--error">{getErrorMessage(courseQuery.error)}</div></div>
      </div>
    )
  }

  const course = courseQuery.data
  if (!course) {
    return (
      <div className="page-stack">
        <div className="card"><div className="empty">Course not found.</div></div>
      </div>
    )
  }

  const isAdmin = session?.user.roles.includes('admin') ?? false
  const isOwnerInstructor = Boolean(
    session?.user.roles.includes('instructor') && session.user.id === course.instructor_id,
  )
  const canEnhance = isAdmin || isOwnerInstructor
  const modules: ModuleDetail[] = course.modules.map((module) => ({
    id: module.id,
    course_id: course.id,
    title: module.title,
    description: module.description,
    sort_order: module.sort_order,
    is_required: module.is_required,
    estimated_duration: null,
    created_at: course.created_at,
    updated_at: course.updated_at,
  }))
  const enrollmentStatus = enrollmentStatusQuery.data
  const isStudent = Boolean(session?.user.roles.includes('student'))
  const canViewAssets = isAdmin || isOwnerInstructor || Boolean(enrollmentStatus?.is_enrolled)
  const canUseAssistant = Boolean(session) && (!isStudent || Boolean(enrollmentStatus?.is_enrolled))
  const assistantDisabledMessage = !session
    ? 'Sign in to use the assistant.'
    : isStudent && !enrollmentStatus?.is_enrolled
      ? 'Enroll in this course to use the student assistant and track progress.'
      : undefined

  const catalogBase = session ? '/app/catalog' : '/catalog'

  return (
    <div className="page-stack">
      {/* ── Hero ── */}
      <div className="course-detail-hero">
        <div className="page-header__breadcrumb">
          <Link to={catalogBase}>Catalog</Link>
          <span>/</span>
          <span>{course.title}</span>
        </div>
        <h1 className="course-detail-hero__title">{course.title}</h1>
        {course.short_description ? (
          <p className="course-detail-hero__sub">{course.short_description}</p>
        ) : null}
      </div>

      {/* ── Stat bar ── */}
      <div className="stat-row">
        <div className="stat-item">
          <div className="stat-item__icon"><Tag size={18} /></div>
          <div className="stat-item__label">Category</div>
          <div className="stat-item__value">{course.category || '—'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__icon"><GraduationCap size={18} /></div>
          <div className="stat-item__label">Difficulty</div>
          <div className="stat-item__value">{course.difficulty || '—'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__icon"><Clock size={18} /></div>
          <div className="stat-item__label">Duration</div>
          <div className="stat-item__value">{course.estimated_duration || '—'}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__icon"><Layers size={18} /></div>
          <div className="stat-item__label">Modules</div>
          <div className="stat-item__value">{modules.length}</div>
        </div>
      </div>

      {/* ── Tab nav ── */}
      <div className="tab-nav">
        <button
          className={`tab-nav__item${activeTab === 'overview' ? ' active' : ''}`}
          onClick={() => setActiveTab('overview')}
          type="button"
        >
          <BookOpen size={15} style={{ marginRight: 6, verticalAlign: -2 }} />
          Overview
        </button>
        <button
          className={`tab-nav__item${activeTab === 'modules' ? ' active' : ''}`}
          onClick={() => setActiveTab('modules')}
          type="button"
        >
          <Layers size={15} style={{ marginRight: 6, verticalAlign: -2 }} />
          Modules
          {modules.length > 0 ? (
            <span className="tab-nav__count">{modules.length}</span>
          ) : null}
        </button>
        <button
          className={`tab-nav__item${activeTab === 'ai' ? ' active' : ''}`}
          onClick={() => setActiveTab('ai')}
          type="button"
        >
          <Bot size={15} style={{ marginRight: 6, verticalAlign: -2 }} />
          AI Assistant
        </button>
        {canEnhance ? (
          <span className="tab-nav__badge">Instructor tools in AI tab</span>
        ) : null}
      </div>

      {/* ── Overview tab ── */}
      {activeTab === 'overview' ? (
        <div className="page-columns">
          {/* Left: course info */}
          <div className="flex-col gap-6">
            {course.description ? (
              <div className="card">
                <div className="card__header">
                  <h2 className="card__title">About this course</h2>
                </div>
                <p style={{ fontSize: 15, lineHeight: 1.7, color: 'var(--black-muted)' }}>
                  {course.description}
                </p>
                {course.tags.length > 0 ? (
                  <div className="badge-group" style={{ marginTop: 'var(--space-4)' }}>
                    <Tag size={14} style={{ color: 'var(--black-faint)', flexShrink: 0 }} />
                    {course.tags.map((tag) => (
                      <span className="badge" key={tag}>{tag}</span>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            {course.prerequisites.length > 0 ? (
              <div className="card card--subtle">
                <div className="card__header">
                  <h2 className="card__title">Prerequisites</h2>
                  <p className="card__description">You should be familiar with these topics before enrolling.</p>
                </div>
                <div className="course-prereq-list">
                  {course.prerequisites.map((prereq) => (
                    <div className="course-prereq-item" key={prereq}>
                      <CheckCircle2 size={16} />
                      <span className="mono" style={{ fontSize: 13 }}>{prereq}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {!course.description && !course.prerequisites.length ? (
              <div className="card">
                <div className="empty">No additional information available for this course.</div>
              </div>
            ) : null}
          </div>

          {/* Right: enrollment widget */}
          <div className="course-enroll-widget">
            <div className="card">
              <div className="card__header">
                <h2 className="card__title">Enrollment</h2>
                <p className="card__description">Start your learning journey.</p>
              </div>

              {enrollmentStatusQuery.isError ? (
                <div className="message message--error">{getErrorMessage(enrollmentStatusQuery.error)}</div>
              ) : null}
              {enrollMutation.isError ? (
                <div className="message message--error">{getErrorMessage(enrollMutation.error)}</div>
              ) : null}

              {isStudent ? (
                enrollmentStatus?.is_enrolled && enrollmentStatus.enrollment_id ? (
                  <div className="course-enroll-active">
                    <div className="course-enroll-active__status">
                      <span className={statusBadgeClass(enrollmentStatus.status ?? 'ENROLLED')}>
                        {enrollmentStatus.status ?? 'ENROLLED'}
                      </span>
                      {typeof enrollmentStatus.progress_percent === 'number' ? (
                        <span className="badge">{enrollmentStatus.progress_percent.toFixed(0)}% complete</span>
                      ) : null}
                    </div>
                    {typeof enrollmentStatus.progress_percent === 'number' ? (
                      <div className="progress-bar" style={{ margin: 'var(--space-3) 0' }}>
                        <div
                          className="progress-bar__fill"
                          style={{ width: `${enrollmentStatus.progress_percent}%` }}
                        />
                      </div>
                    ) : null}
                    <Link
                      className="btn btn--primary"
                      style={{ width: '100%', justifyContent: 'center', marginTop: 'var(--space-3)' }}
                      to={`/app/learning/${enrollmentStatus.enrollment_id}`}
                    >
                      Open learning workspace
                      <ArrowRight size={16} />
                    </Link>
                  </div>
                ) : (
                  <div className="flex-col gap-4">
                    <p style={{ fontSize: 14, color: 'var(--black-muted)', lineHeight: 1.6 }}>
                      Enroll to start tracked learning, access study materials, and use the AI assistant.
                    </p>
                    <button
                      className="btn btn--primary"
                      style={{ width: '100%', justifyContent: 'center' }}
                      onClick={() => enrollMutation.mutate()}
                      type="button"
                      disabled={enrollMutation.isPending}
                    >
                      {enrollMutation.isPending ? 'Enrolling...' : 'Enroll now'}
                      {!enrollMutation.isPending ? <ArrowRight size={16} /> : null}
                    </button>
                  </div>
                )
              ) : (
                <p style={{ fontSize: 14, color: 'var(--black-muted)', lineHeight: 1.6 }}>
                  {session
                    ? 'Enrollment is available to students.'
                    : 'Sign in with a student account to enroll in this course.'}
                </p>
              )}
            </div>

            {course.max_capacity ? (
              <div className="card card--subtle">
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', fontSize: 14 }}>
                  <span style={{ color: 'var(--black-faint)' }}>Max capacity:</span>
                  <strong>{course.max_capacity}</strong>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* ── Modules tab ── */}
      {activeTab === 'modules' ? (
        modules.length > 0 ? (
          <div className="card">
            <div className="card__header">
              <h2 className="card__title">
                <Layers size={18} style={{ marginRight: 6, verticalAlign: -3 }} />
                {modules.length} {modules.length === 1 ? 'module' : 'modules'}
              </h2>
              <p className="card__description">
                {canViewAssets
                  ? 'Expand a module to view and download study materials.'
                  : 'Enroll to access downloadable study materials for each module.'}
              </p>
            </div>
            <div className="module-list">
              {modules.map((module, index) => (
                <details key={module.id} className="module-item module-item--expandable">
                  <summary className="module-item__summary">
                    <span className="module-item__badge">{index + 1}</span>
                    <div className="module-item__info">
                      <div className="module-item__title">{module.title}</div>
                      {module.description ? (
                        <div className="module-item__description">{module.description}</div>
                      ) : null}
                    </div>
                    <ChevronDown size={16} className="module-item__chevron" />
                  </summary>
                  <div className="module-item__content">
                    <ModuleAssetList courseId={courseId} moduleId={module.id} canViewAssets={canViewAssets} />
                  </div>
                </details>
              ))}
            </div>
          </div>
        ) : (
          <div className="card">
            <div className="empty">
              <div className="empty__icon"><Layers size={36} /></div>
              <div className="empty__title">No modules yet</div>
              <div className="empty__description">This course doesn't have any modules added yet.</div>
            </div>
          </div>
        )
      ) : null}

      {/* ── AI tab ── */}
      {activeTab === 'ai' ? (
        <div className="flex-col gap-6">
          <AIAssistantPanel
            courseId={courseId}
            modules={modules}
            canAsk={canUseAssistant}
            disabledMessage={assistantDisabledMessage}
          />
          {canEnhance ? (
            <div className="card card--subtle">
              <div className="card__header">
                <h2 className="card__title">
                  <Sparkles size={18} style={{ marginRight: 6, verticalAlign: -3, color: 'var(--accent)' }} />
                  Instructor tools
                </h2>
                <p className="card__description">AI-powered enhancement utilities for course owners and admins.</p>
              </div>
              <AIEnhancementPanel courseId={courseId} modules={modules} />
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
