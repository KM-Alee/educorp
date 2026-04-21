import { useMemo, useState, type ReactNode } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  FileUp,
  FolderOpen,
  Info,
  Layers,
  Pencil,
  Plus,
  Rocket,
  ShieldCheck,
  Trash2,
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  Clock,
  Ban,
  RotateCcw,
  Zap,
} from 'lucide-react'

import {
  activatePublishingVersion,
  approvePublishingVersion,
  cancelPublishingVersion,
  createCourse,
  createModule,
  deleteAsset,
  deleteCourse,
  deleteModule,
  getAssetDownload,
  getCourse,
  getDraftContent,
  getPublishingVersion,
  listAssets,
  listCourses,
  listModules,
  publishCourse,
  rejectPublishingVersion,
  reorderModules,
  retryPublishingVersion,
  updateCourse,
  updateDraftContent,
  updateModule,
  uploadAsset,
  validateCourseDraft,
  type AssetOut,
  type CourseCreateInput,
  type CourseListItem,
  type DraftContentDocument,
  type ModuleDetail,
  type PublishingVersion,
} from '../../lib/api'
import { AIAssistantPanel, AIEnhancementPanel } from '../ai/AIPanels'
import { getErrorMessage } from '../../lib/types'
import { useSessionState } from '../../lib/session'

const defaultCourseInput: CourseCreateInput = {
  title: '',
  description: '',
  short_description: '',
  category: '',
  difficulty: 'beginner',
  estimated_duration: 'PT4H',
  tags: [],
}

const defaultDraftContent = {
  overview: '',
  learning_objectives: [],
  lesson_notes: [],
}

function tagsFromInput(raw: string): string[] {
  return raw
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean)
}

function stringifyContent(document?: DraftContentDocument): string {
  return JSON.stringify(document?.content ?? defaultDraftContent, null, 2)
}

function parseDraftContent(raw: string): Record<string, unknown> {
  const parsed = JSON.parse(raw) as unknown
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error('Draft content must be a JSON object.')
  }
  return parsed as Record<string, unknown>
}

const PUBLISHING_STORAGE_KEY = 'educorp.phase3.publishing'

function getStoredVersionId(courseId: string): string | null {
  if (!courseId) return null
  try {
    const raw = window.localStorage.getItem(PUBLISHING_STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as Record<string, string>
    return data[courseId] ?? null
  } catch {
    return null
  }
}

function setStoredVersionId(courseId: string, versionId: string) {
  if (!courseId) return
  try {
    const raw = window.localStorage.getItem(PUBLISHING_STORAGE_KEY)
    const data = raw ? (JSON.parse(raw) as Record<string, string>) : {}
    data[courseId] = versionId
    window.localStorage.setItem(PUBLISHING_STORAGE_KEY, JSON.stringify(data))
  } catch {
    // Ignore storage errors
  }
}

function StatusMsg({ type, text }: { type: 'success' | 'error'; text: string }) {
  return <div className={`message message--${type}`}>{text}</div>
}

function CourseListItem({ course }: { course: CourseListItem }) {
  return (
    <Link className="course-item" to={`/app/courses/${course.id}`}>
      <div className="course-item__info">
        <div className="course-item__title">{course.title}</div>
        <div className="course-item__meta">
          {course.short_description || 'No description'}
        </div>
      </div>
      <div className="course-item__badges">
        {course.category ? <span className="badge">{course.category}</span> : null}
        {course.difficulty ? <span className="badge">{course.difficulty}</span> : null}
        <span className="badge badge--accent">{course.visibility}</span>
      </div>
    </Link>
  )
}

export function CourseWorkspacePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState(defaultCourseInput)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [tagsInput, setTagsInput] = useState('')

  const coursesQuery = useQuery({
    queryKey: ['courses', search, category, difficulty],
    queryFn: () =>
      listCourses({
        page: 1,
        page_size: 20,
        search,
        category,
        difficulty,
        visibility: 'DRAFT',
      }),
  })

  const createCourseMutation = useMutation({
    mutationFn: createCourse,
    onSuccess: async (course) => {
      await queryClient.invalidateQueries({ queryKey: ['courses'] })
      navigate(`/app/courses/${course.id}`)
      setDraft(defaultCourseInput)
      setTagsInput('')
    },
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Courses</h1>
        <p className="page-header__description">Create and manage draft courses.</p>
      </div>

      <div className="page-columns--wide page-columns">
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">New draft</h2>
            <p className="card__description">Create a course and start editing immediately.</p>
          </div>

          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault()
              createCourseMutation.mutate({
                ...draft,
                tags: tagsFromInput(tagsInput),
              })
            }}
          >
            <label className="form-field">
              <span className="form-field__label">Title</span>
              <input
                value={draft.title}
                onChange={(e) => setDraft((c) => ({ ...c, title: e.target.value }))}
              />
            </label>

            <label className="form-field">
              <span className="form-field__label">Description</span>
              <textarea
                value={draft.description ?? ''}
                onChange={(e) => setDraft((c) => ({ ...c, description: e.target.value }))}
              />
            </label>

            <div className="form-row">
              <label className="form-field">
                <span className="form-field__label">Short description</span>
                <input
                  value={draft.short_description ?? ''}
                  onChange={(e) => setDraft((c) => ({ ...c, short_description: e.target.value }))}
                />
              </label>
              <label className="form-field">
                <span className="form-field__label">Category</span>
                <input
                  value={draft.category ?? ''}
                  onChange={(e) => setDraft((c) => ({ ...c, category: e.target.value }))}
                />
              </label>
            </div>

            <div className="form-row">
              <label className="form-field">
                <span className="form-field__label">Difficulty</span>
                <select
                  value={draft.difficulty ?? ''}
                  onChange={(e) => setDraft((c) => ({ ...c, difficulty: e.target.value }))}
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </label>
              <label className="form-field">
                <span className="form-field__label">Estimated duration</span>
                <input
                  placeholder="PT4H"
                  value={draft.estimated_duration ?? ''}
                  onChange={(e) => setDraft((c) => ({ ...c, estimated_duration: e.target.value }))}
                />
              </label>
            </div>

            <label className="form-field">
              <span className="form-field__label">Tags</span>
              <input
                placeholder="python, ml, pedagogy"
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
              />
            </label>

            {createCourseMutation.isError ? (
              <StatusMsg type="error" text={getErrorMessage(createCourseMutation.error)} />
            ) : null}

            <div className="btn-row">
              <button className="btn btn--primary" disabled={createCourseMutation.isPending} type="submit">
                {createCourseMutation.isPending ? 'Creating...' : 'Create draft'}
              </button>
            </div>
          </form>
        </div>

        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Draft courses</h2>
            <p className="card__description">Filter and open existing drafts.</p>
          </div>

          <div className="filter-bar" style={{ marginBottom: '0.75rem' }}>
            <label className="form-field">
              <span className="form-field__label">Search</span>
              <input value={search} onChange={(e) => setSearch(e.target.value)} />
            </label>
            <label className="form-field">
              <span className="form-field__label">Category</span>
              <input value={category} onChange={(e) => setCategory(e.target.value)} />
            </label>
            <label className="form-field">
              <span className="form-field__label">Difficulty</span>
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                <option value="">All</option>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
          </div>

          {coursesQuery.isError ? (
            <StatusMsg type="error" text={getErrorMessage(coursesQuery.error)} />
          ) : null}

          <div className="course-list">
            {coursesQuery.data?.data.map((course) => (
              <CourseListItem course={course} key={course.id} />
            ))}
          </div>

          {!coursesQuery.isLoading && !coursesQuery.data?.data.length ? (
            <div className="empty">No drafts match the current filter.</div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function ModuleAssetManager({
  courseId,
  module,
}: {
  courseId: string
  module: ModuleDetail
}) {
  const queryClient = useQueryClient()
  const [assetTitle, setAssetTitle] = useState('')
  const [assetFile, setAssetFile] = useState<File | null>(null)

  const assetsQuery = useQuery({
    queryKey: ['assets', courseId, module.id],
    queryFn: () => listAssets(courseId, module.id),
  })

  const uploadMutation = useMutation({
    mutationFn: (payload: { file: File; title: string }) =>
      uploadAsset(courseId, module.id, payload),
    onSuccess: async () => {
      setAssetTitle('')
      setAssetFile(null)
      await queryClient.invalidateQueries({ queryKey: ['assets', courseId, module.id] })
      await queryClient.invalidateQueries({ queryKey: ['course', courseId] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (assetId: string) => deleteAsset(courseId, module.id, assetId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['assets', courseId, module.id] })
      await queryClient.invalidateQueries({ queryKey: ['course', courseId] })
    },
  })

  const downloadMutation = useMutation({
    mutationFn: (assetId: string) => getAssetDownload(courseId, module.id, assetId),
    onSuccess: (result) => {
      window.open(result.download_url, '_blank', 'noopener,noreferrer')
    },
  })

  return (
    <div className="module-panel__assets">
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault()
          if (!assetFile) return
          uploadMutation.mutate({ file: assetFile, title: assetTitle || assetFile.name })
        }}
      >
        <div className="form-row">
          <label className="form-field">
            <span className="form-field__label">Asset title</span>
            <input value={assetTitle} onChange={(e) => setAssetTitle(e.target.value)} />
          </label>
          <label className="form-field">
            <span className="form-field__label">File</span>
            <input
              accept=".pdf,.docx,.pptx,.txt,.md,.vtt,.srt"
              onChange={(e) => setAssetFile(e.target.files?.[0] ?? null)}
              type="file"
            />
          </label>
        </div>
        <div className="btn-row">
          <button className="btn btn--sm" disabled={!assetFile || uploadMutation.isPending} type="submit">
            {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </form>

      {uploadMutation.isError ? <StatusMsg type="error" text={getErrorMessage(uploadMutation.error)} /> : null}
      {deleteMutation.isError ? <StatusMsg type="error" text={getErrorMessage(deleteMutation.error)} /> : null}

      {assetsQuery.data?.map((asset: AssetOut) => (
        <div className="asset-row" key={asset.id}>
          <div className="asset-row__info">
            <div className="asset-row__name">{asset.title}</div>
            <div className="asset-row__file">{asset.file_name}</div>
          </div>
          <div className="btn-row">
            <button className="btn btn--sm" onClick={() => downloadMutation.mutate(asset.id)} type="button">
              Download
            </button>
            <button className="btn btn--sm btn--ghost" onClick={() => deleteMutation.mutate(asset.id)} type="button">
              Delete
            </button>
          </div>
        </div>
      ))}

      {!assetsQuery.isLoading && !assetsQuery.data?.length ? (
        <div className="empty" style={{ marginTop: '0.5rem' }}>No assets uploaded yet.</div>
      ) : null}
    </div>
  )
}

type EditorTab = 'details' | 'curriculum' | 'content' | 'publish'

/* ─── Publishing Pipeline Helpers ─── */

const STEP_LABELS: Record<string, string> = {
  preflight_review: 'Preflight check',
  extract_text: 'Extracting content',
  chunk_content: 'Processing chapters',
  generate_embeddings: 'Building search index',
  index_qdrant: 'Indexing for AI',
  generate_quality_report: 'Quality report',
  finalize_version: 'Finalizing',
}

const STATUS_LABELS: Record<string, string> = {
  PREPARING: 'Preparing',
  REVIEW_REQUIRED: 'Waiting for admin approval',
  PUBLISHING: 'Publishing in progress',
  READY: 'Published successfully',
  FAILED: 'Publishing failed',
  CANCELLED: 'Cancelled',
  SUPERSEDED: 'Replaced by newer version',
}

function PipelineStepIcon({ status }: { status: string }) {
  if (status === 'COMPLETED') return <CheckCircle2 size={16} className="pipeline-icon pipeline-icon--done" />
  if (status === 'RUNNING') return <Loader2 size={16} className="pipeline-icon pipeline-icon--running" />
  if (status === 'FAILED') return <XCircle size={16} className="pipeline-icon pipeline-icon--failed" />
  if (status === 'SKIPPED') return <Ban size={14} className="pipeline-icon pipeline-icon--skipped" />
  return <Circle size={14} className="pipeline-icon pipeline-icon--pending" />
}

function PublishingPipeline({
  publishingData,
  canReview,
  canCancel,
  onApprove,
  onReject,
  onCancel,
  onRetry,
  onActivate,
  isApprovePending,
  isRejectPending,
  isCancelPending,
  isRetryPending,
  isActivatePending,
  courseVisibility,
}: {
  publishingData: PublishingVersion
  canReview: boolean
  canCancel: boolean
  onApprove: () => void
  onReject: () => void
  onCancel: () => void
  onRetry: () => void
  onActivate: () => void
  isApprovePending: boolean
  isRejectPending: boolean
  isCancelPending: boolean
  isRetryPending: boolean
  isActivatePending: boolean
  courseVisibility: string
}) {
  const { status, approval_state, steps } = publishingData
  const isActive = status === 'PREPARING' || status === 'PUBLISHING'
  const isWaiting = status === 'REVIEW_REQUIRED'
  const isDone = status === 'READY'
  const isFailed = status === 'FAILED'
  const isCancelled = status === 'CANCELLED'

  return (
    <div className="publishing-pipeline">
      {/* Overall status banner */}
      <div className={`pipeline-status pipeline-status--${status.toLowerCase().replace('_', '-')}`}>
        <div className="pipeline-status__icon">
          {isDone && <CheckCircle2 size={22} />}
          {isActive && <Loader2 size={22} className="spin" />}
          {isWaiting && <Clock size={22} />}
          {isFailed && <XCircle size={22} />}
          {isCancelled && <Ban size={22} />}
          {status === 'SUPERSEDED' && <RotateCcw size={22} />}
        </div>
        <div className="pipeline-status__text">
          <div className="pipeline-status__title">{STATUS_LABELS[status] ?? status}</div>
          <div className="pipeline-status__sub">
            Version {publishingData.version_number}
            {publishingData.total_assets > 0 && ` · ${publishingData.total_assets} asset${publishingData.total_assets !== 1 ? 's' : ''}`}
          </div>
        </div>
      </div>

      {/* Admin action needed */}
      {isWaiting && canReview && approval_state === 'PENDING' && (
        <div className="pipeline-action-card">
          <div className="pipeline-action-card__header">
            <ShieldCheck size={18} />
            <span>Admin approval required</span>
          </div>
          <p className="pipeline-action-card__text">
            This course has passed the preflight check and needs your approval before publishing can continue.
          </p>
          <div className="btn-row">
            <button className="btn btn--primary" disabled={isApprovePending} onClick={onApprove} type="button">
              <CheckCircle2 size={16} style={{ marginRight: 4, verticalAlign: -2 }} />
              {isApprovePending ? 'Approving...' : 'Approve & continue'}
            </button>
            <button className="btn btn--danger" disabled={isRejectPending} onClick={onReject} type="button">
              <XCircle size={16} style={{ marginRight: 4, verticalAlign: -2 }} />
              {isRejectPending ? 'Rejecting...' : 'Reject'}
            </button>
          </div>
        </div>
      )}

      {/* Instructor waiting message */}
      {isWaiting && !canReview && approval_state === 'PENDING' && (
        <div className="pipeline-action-card pipeline-action-card--waiting">
          <div className="pipeline-action-card__header">
            <Clock size={18} />
            <span>Waiting for admin</span>
          </div>
          <p className="pipeline-action-card__text">
            Your course has been submitted for review. An admin will approve or reject it. You'll see the status update here automatically.
          </p>
        </div>
      )}

      {/* Approved, processing */}
      {isWaiting && approval_state === 'APPROVED' && (
        <div className="pipeline-action-card pipeline-action-card--info">
          <div className="pipeline-action-card__header">
            <Loader2 size={18} className="spin" />
            <span>Approved — resuming pipeline</span>
          </div>
        </div>
      )}

      {/* Pipeline steps timeline */}
      <div className="pipeline-timeline">
        <div className="pipeline-timeline__label">Pipeline progress</div>
        {steps.map((step) => (
          <div className={`pipeline-step ${step.status === 'RUNNING' ? 'pipeline-step--active' : ''} ${step.status === 'COMPLETED' ? 'pipeline-step--done' : ''} ${step.status === 'FAILED' ? 'pipeline-step--failed' : ''}`} key={step.id}>
            <div className="pipeline-step__indicator">
              <PipelineStepIcon status={step.status} />
              <span className="pipeline-step__line" />
            </div>
            <div className="pipeline-step__body">
              <div className="pipeline-step__name">{STEP_LABELS[step.step_name] ?? step.step_name}</div>
              <div className="pipeline-step__status">
                {step.status === 'COMPLETED' && step.completed_at
                  ? `Done ${new Date(step.completed_at).toLocaleTimeString()}`
                  : step.status === 'RUNNING'
                    ? 'In progress...'
                    : step.status === 'FAILED'
                      ? step.error_message ?? 'Failed'
                      : step.status === 'SKIPPED'
                        ? 'Skipped'
                        : 'Pending'}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom actions */}
      <div className="pipeline-actions">
        {isFailed && (
          <button className="btn btn--primary" disabled={isRetryPending} onClick={onRetry} type="button">
            <RotateCcw size={16} style={{ marginRight: 4, verticalAlign: -2 }} />
            {isRetryPending ? 'Retrying...' : 'Retry publishing'}
          </button>
        )}
        {isDone && courseVisibility !== 'PUBLISHED' && (
          <button className="btn btn--primary" disabled={isActivatePending} onClick={onActivate} type="button">
            <Zap size={16} style={{ marginRight: 4, verticalAlign: -2 }} />
            {isActivatePending ? 'Activating...' : 'Activate course'}
          </button>
        )}
        {(isActive || isWaiting) && canCancel && (
          <button className="btn btn--ghost" disabled={isCancelPending} onClick={onCancel} type="button">
            {isCancelPending ? 'Cancelling...' : 'Cancel publishing'}
          </button>
        )}
      </div>
    </div>
  )
}

interface StepInfo {
  key: EditorTab
  label: string
  icon: ReactNode
  hint: string
  done: boolean
}

function EditorStepper({ steps, active, onSelect }: { steps: StepInfo[]; active: EditorTab; onSelect: (t: EditorTab) => void }) {
  return (
    <div className="editor-stepper">
      {steps.map((step, i) => (
        <button
          key={step.key}
          className={`editor-stepper__step ${active === step.key ? 'editor-stepper__step--active' : ''} ${step.done ? 'editor-stepper__step--done' : ''}`}
          onClick={() => onSelect(step.key)}
          type="button"
        >
          <span className="editor-stepper__number">
            {step.done ? <CheckCircle2 size={18} /> : <Circle size={18} />}
          </span>
          <span className="editor-stepper__icon">{step.icon}</span>
          <span className="editor-stepper__label">{step.label}</span>
          {i < steps.length - 1 && <span className="editor-stepper__connector" />}
        </button>
      ))}
    </div>
  )
}

export function CourseEditorPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const session = useSessionState()
  const { courseId = '' } = useParams()
  const [courseFormState, setCourseFormState] = useState<{
    courseId: string
    overrides: Partial<CourseCreateInput>
  }>({ courseId, overrides: {} })
  const [courseTagsState, setCourseTagsState] = useState<{
    courseId: string
    value: string
    dirty: boolean
  }>({ courseId, value: '', dirty: false })
  const [draftContentState, setDraftContentState] = useState<{
    courseId: string
    value: string
    dirty: boolean
  }>({ courseId, value: stringifyContent(), dirty: false })
  const [draftContentError, setDraftContentError] = useState('')
  const [moduleTitle, setModuleTitle] = useState('')
  const [moduleDescription, setModuleDescription] = useState('')
  const [moduleEdits, setModuleEdits] = useState<Record<string, Pick<ModuleDetail, 'title' | 'description' | 'is_required'>>>({})
  const [publishingVersionId, setPublishingVersionId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<EditorTab>('details')

  const courseQuery = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => getCourse(courseId),
  })

  const modulesQuery = useQuery({
    queryKey: ['modules', courseId],
    queryFn: () => listModules(courseId),
  })

  const draftContentQuery = useQuery({
    queryKey: ['draft-content', courseId],
    queryFn: () => getDraftContent(courseId),
  })

  const baseCourseForm: CourseCreateInput = useMemo(() => (
    {
      title: courseQuery.data?.title ?? defaultCourseInput.title,
      description: courseQuery.data?.description ?? defaultCourseInput.description,
      short_description: courseQuery.data?.short_description ?? defaultCourseInput.short_description,
      category: courseQuery.data?.category ?? defaultCourseInput.category,
      difficulty: courseQuery.data?.difficulty ?? defaultCourseInput.difficulty,
      estimated_duration: courseQuery.data?.estimated_duration ?? defaultCourseInput.estimated_duration,
      tags: courseQuery.data?.tags ?? defaultCourseInput.tags,
      max_capacity: courseQuery.data?.max_capacity ?? undefined,
    }
  ), [courseQuery.data])

  const courseFormOverrides = courseFormState.courseId === courseId ? courseFormState.overrides : {}
  const courseForm = { ...baseCourseForm, ...courseFormOverrides }

  const courseTagsValue =
    courseTagsState.courseId === courseId && courseTagsState.dirty
      ? courseTagsState.value
      : (courseQuery.data?.tags ?? []).join(', ')

  const draftContentValue =
    draftContentState.courseId === courseId && draftContentState.dirty
      ? draftContentState.value
      : stringifyContent(draftContentQuery.data)

  const storedPublishingVersionId = useMemo(() => getStoredVersionId(courseId), [courseId])
  const effectivePublishingVersionId = publishingVersionId ?? storedPublishingVersionId

  function updateCourseForm<K extends keyof CourseCreateInput>(key: K, value: CourseCreateInput[K]) {
    setCourseFormState((prev) => {
      const overrides = prev.courseId === courseId ? prev.overrides : {}
      return { courseId, overrides: { ...overrides, [key]: value } }
    })
  }

  const updateCourseMutation = useMutation({
    mutationFn: (input: CourseCreateInput) =>
      updateCourse(courseId, { ...input, tags: tagsFromInput(courseTagsValue) }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['course', courseId] })
      await queryClient.invalidateQueries({ queryKey: ['courses'] })
    },
  })

  const deleteCourseMutation = useMutation({
    mutationFn: () => deleteCourse(courseId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['courses'] })
      navigate('/app/courses', { replace: true })
    },
  })

  const createModuleMutation = useMutation({
    mutationFn: () =>
      createModule(courseId, { title: moduleTitle, description: moduleDescription, is_required: true }),
    onSuccess: async () => {
      setModuleTitle('')
      setModuleDescription('')
      await queryClient.invalidateQueries({ queryKey: ['modules', courseId] })
      await queryClient.invalidateQueries({ queryKey: ['course', courseId] })
    },
  })

  const updateModuleMutation = useMutation({
    mutationFn: (moduleId: string) => {
      const module = modulesQuery.data?.find((item) => item.id === moduleId)
      const edits = moduleEdits[moduleId]
      return updateModule(courseId, moduleId, {
        title: edits?.title ?? module?.title,
        description: edits?.description ?? module?.description ?? undefined,
        is_required: edits?.is_required ?? module?.is_required,
      })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['modules', courseId] })
      await queryClient.invalidateQueries({ queryKey: ['course', courseId] })
    },
  })

  const deleteModuleMutation = useMutation({
    mutationFn: (moduleId: string) => deleteModule(courseId, moduleId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['modules', courseId] })
      await queryClient.invalidateQueries({ queryKey: ['course', courseId] })
    },
  })

  const reorderModulesMutation = useMutation({
    mutationFn: (order: string[]) => reorderModules(courseId, order),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['modules', courseId] })
      await queryClient.invalidateQueries({ queryKey: ['course', courseId] })
    },
  })

  const validateDraftMutation = useMutation({
    mutationFn: () => validateCourseDraft(courseId),
  })

  const publishMutation = useMutation({
    mutationFn: () => publishCourse(courseId),
    onSuccess: (result) => {
      setPublishingVersionId(result.version_id)
      setStoredVersionId(courseId, result.version_id)
      queryClient.invalidateQueries({ queryKey: ['publishing', result.version_id] })
    },
  })

  const retryMutation = useMutation({
    mutationFn: (versionId: string) => retryPublishingVersion(versionId),
    onSuccess: (result) => {
      setPublishingVersionId(result.version_id)
      setStoredVersionId(courseId, result.version_id)
      queryClient.invalidateQueries({ queryKey: ['publishing', result.version_id] })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (versionId: string) => cancelPublishingVersion(versionId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['publishing', result.version_id] })
    },
  })

  const activateMutation = useMutation({
    mutationFn: (versionId: string) => activatePublishingVersion(versionId),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['publishing', result.version_id] })
      await queryClient.invalidateQueries({ queryKey: ['course', courseId] })
      await queryClient.invalidateQueries({ queryKey: ['courses'] })
      await queryClient.invalidateQueries({ queryKey: ['catalog'] })
    },
  })

  const approveMutation = useMutation({
    mutationFn: (versionId: string) => approvePublishingVersion(versionId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['publishing', result.version_id] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (versionId: string) => rejectPublishingVersion(versionId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['publishing', result.version_id] })
    },
  })

  const saveDraftContentMutation = useMutation({
    mutationFn: (content: Record<string, unknown>) => updateDraftContent(courseId, content),
    onSuccess: async () => {
      setDraftContentError('')
      setDraftContentState((prev) => ({
        courseId,
        value: prev.courseId === courseId ? prev.value : stringifyContent(),
        dirty: false,
      }))
      await queryClient.invalidateQueries({ queryKey: ['draft-content', courseId] })
    },
  })

  const publishingQuery = useQuery<PublishingVersion>({
    queryKey: ['publishing', effectivePublishingVersionId],
    queryFn: () => getPublishingVersion(effectivePublishingVersionId ?? ''),
    enabled: Boolean(effectivePublishingVersionId),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return false
      if (data.status === 'PREPARING' || data.status === 'PUBLISHING') return 5000
      if (data.status === 'REVIEW_REQUIRED' && data.approval_state === 'APPROVED') return 5000
      return false
    },
  })

  const modules = modulesQuery.data ?? []

  function moveModule(moduleId: string, direction: -1 | 1) {
    const currentOrder = modules.map((m) => m.id)
    const idx = currentOrder.indexOf(moduleId)
    const next = idx + direction
    if (idx < 0 || next < 0 || next >= currentOrder.length) return
    const reordered = [...currentOrder]
    const swapped = reordered[next]
    reordered[next] = reordered[idx]
    reordered[idx] = swapped
    reorderModulesMutation.mutate(reordered)
  }

  if (courseQuery.isLoading) {
    return <div className="empty">Loading course...</div>
  }

  if (courseQuery.isError) {
    return <StatusMsg type="error" text={getErrorMessage(courseQuery.error)} />
  }

  const validationResult = validateDraftMutation.data
  const publishingData = publishingQuery.data
  const canCancel = session?.user.roles.includes('admin')
  const canReview = Boolean(session?.user.roles.includes('admin'))

  const hasTitle = Boolean(courseQuery.data?.title)
  const hasModules = modules.length > 0
  const hasDraftContent = Boolean(draftContentQuery.data?.content)

  const steps: StepInfo[] = [
    { key: 'details', label: 'Course details', icon: <Pencil size={16} />, hint: 'Title, description, category and tags', done: hasTitle },
    { key: 'curriculum', label: 'Modules & assets', icon: <Layers size={16} />, hint: 'Structure your course into modules, then upload files to each', done: hasModules },
    { key: 'content', label: 'Draft content', icon: <BookOpen size={16} />, hint: 'Learning objectives, overview and lesson notes', done: hasDraftContent },
    { key: 'publish', label: 'Validate & publish', icon: <Rocket size={16} />, hint: 'Check for issues, then launch your course', done: courseQuery.data?.visibility === 'PUBLISHED' },
  ]

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header__breadcrumb">
          <Link to="/app/courses">Courses</Link>
          <span>/</span>
          <span>{courseQuery.data?.title}</span>
        </div>
        <h1 className="page-header__title">{courseQuery.data?.title}</h1>
        <div className="editor-status-bar">
          <span className="badge badge--accent">{courseQuery.data?.visibility}</span>
          <span className="editor-status-bar__stat">{modules.length} module{modules.length !== 1 ? 's' : ''}</span>
          <span className="editor-status-bar__sep">·</span>
          <span className="editor-status-bar__stat">Updated {new Date(courseQuery.data?.updated_at ?? '').toLocaleDateString()}</span>
        </div>
      </div>

      <EditorStepper steps={steps} active={activeTab} onSelect={setActiveTab} />

      {/* Hint bar for active tab */}
      <div className="editor-hint">
        <Info size={16} />
        <span>{steps.find((s) => s.key === activeTab)?.hint}</span>
      </div>

      {/* ── Tab: Course Details ── */}
      {activeTab === 'details' && (
        <div className="page-columns--wide page-columns">
          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Course details</h2>
              <p className="card__description">Fill in the essential info about your course. Title and description are required.</p>
            </div>

            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault()
                updateCourseMutation.mutate(courseForm)
              }}
            >
              <label className="form-field">
                <span className="form-field__label">Title *</span>
                <input
                  placeholder="e.g. Introduction to Machine Learning"
                  value={courseForm.title}
                  onChange={(e) => updateCourseForm('title', e.target.value)}
                />
              </label>

              <label className="form-field">
                <span className="form-field__label">Description *</span>
                <textarea
                  placeholder="What will students learn? What makes this course unique?"
                  value={courseForm.description ?? ''}
                  onChange={(e) => updateCourseForm('description', e.target.value)}
                />
              </label>

              <div className="form-row">
                <label className="form-field">
                  <span className="form-field__label">Short description</span>
                  <input
                    placeholder="A brief one-liner for course cards"
                    value={courseForm.short_description ?? ''}
                    onChange={(e) => updateCourseForm('short_description', e.target.value)}
                  />
                </label>
                <label className="form-field">
                  <span className="form-field__label">Category</span>
                  <input
                    placeholder="e.g. Data Science, Web Dev"
                    value={courseForm.category ?? ''}
                    onChange={(e) => updateCourseForm('category', e.target.value)}
                  />
                </label>
              </div>

              <div className="form-row">
                <label className="form-field">
                  <span className="form-field__label">Difficulty</span>
                  <select
                    value={courseForm.difficulty ?? ''}
                    onChange={(e) => updateCourseForm('difficulty', e.target.value)}
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </label>
                <label className="form-field">
                  <span className="form-field__label">Estimated duration</span>
                  <input
                    placeholder="e.g. PT4H (4 hours)"
                    value={courseForm.estimated_duration ?? ''}
                    onChange={(e) => updateCourseForm('estimated_duration', e.target.value)}
                  />
                </label>
              </div>

              <label className="form-field">
                <span className="form-field__label">Tags</span>
                <input
                  placeholder="python, machine-learning, beginner-friendly"
                  value={courseTagsValue}
                  onChange={(e) =>
                    setCourseTagsState({ courseId, value: e.target.value, dirty: true })
                  }
                />
              </label>

              {updateCourseMutation.isError ? <StatusMsg type="error" text={getErrorMessage(updateCourseMutation.error)} /> : null}
              {updateCourseMutation.isSuccess ? <StatusMsg type="success" text="Course details saved." /> : null}

              <div className="btn-row">
                <button className="btn btn--primary" disabled={updateCourseMutation.isPending} type="submit">
                  {updateCourseMutation.isPending ? 'Saving...' : 'Save details'}
                </button>
                <button
                  className="btn btn--ghost"
                  onClick={() => setActiveTab('curriculum')}
                  type="button"
                >
                  Next: Add modules →
                </button>
              </div>
            </form>
          </div>

          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Course info</h2>
            </div>
            <div className="meta-list">
              <div className="meta-item">
                <div className="meta-item__label">Slug</div>
                <div className="meta-item__value mono">{courseQuery.data?.slug}</div>
              </div>
              <div className="meta-item">
                <div className="meta-item__label">Visibility</div>
                <div className="meta-item__value">{courseQuery.data?.visibility}</div>
              </div>
              <div className="meta-item">
                <div className="meta-item__label">Updated</div>
                <div className="meta-item__value">{new Date(courseQuery.data?.updated_at ?? '').toLocaleString()}</div>
              </div>
            </div>
            <div className="btn-row" style={{ marginTop: 'var(--space-4)' }}>
              <button
                className="btn btn--danger btn--sm"
                disabled={deleteCourseMutation.isPending}
                onClick={() => deleteCourseMutation.mutate()}
                type="button"
              >
                {deleteCourseMutation.isPending ? 'Deleting...' : 'Delete draft'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Curriculum (Modules & Assets) ── */}
      {activeTab === 'curriculum' && (
        <div className="page-stack">
          {/* Module list first — assets are right here with each module */}
          {modules.length > 0 && (
            <div className="editor-section-label">
              <ClipboardList size={16} />
              <span>{modules.length} module{modules.length !== 1 ? 's' : ''} — expand any module to upload assets</span>
            </div>
          )}

          {modules.map((mod, index) => (
            <div className="module-panel" key={mod.id}>
              <div className="module-panel__header">
                <div className="module-panel__header-left">
                  <span className="module-panel__badge">{index + 1}</span>
                  <div>
                    <div className="module-panel__title">{mod.title}</div>
                    {mod.description && (
                      <div className="module-panel__order">{mod.description}</div>
                    )}
                  </div>
                </div>
                <div className="btn-row">
                  <button className="btn btn--sm btn--ghost" disabled={index === 0 || reorderModulesMutation.isPending} onClick={() => moveModule(mod.id, -1)} type="button" title="Move up">
                    <ChevronUp size={16} />
                  </button>
                  <button className="btn btn--sm btn--ghost" disabled={index === modules.length - 1 || reorderModulesMutation.isPending} onClick={() => moveModule(mod.id, 1)} type="button" title="Move down">
                    <ChevronDown size={16} />
                  </button>
                </div>
              </div>

              <details className="module-panel__details">
                <summary className="module-panel__toggle">
                  <Pencil size={14} /> Edit module details
                </summary>

                <div className="form-stack" style={{ marginTop: 'var(--space-3)' }}>
                  <label className="form-field">
                    <span className="form-field__label">Title</span>
                    <input
                      value={moduleEdits[mod.id]?.title ?? mod.title}
                      onChange={(e) =>
                        setModuleEdits((c) => ({
                          ...c,
                          [mod.id]: {
                            ...(c[mod.id] ?? { title: mod.title, description: mod.description, is_required: mod.is_required }),
                            title: e.target.value,
                          },
                        }))
                      }
                    />
                  </label>

                  <label className="form-field">
                    <span className="form-field__label">Description</span>
                    <textarea
                      value={moduleEdits[mod.id]?.description ?? mod.description ?? ''}
                      onChange={(e) =>
                        setModuleEdits((c) => ({
                          ...c,
                          [mod.id]: {
                            ...(c[mod.id] ?? { title: mod.title, description: mod.description, is_required: mod.is_required }),
                            description: e.target.value,
                          },
                        }))
                      }
                    />
                  </label>

                  <label className="form-field--inline form-field">
                    <input
                      checked={moduleEdits[mod.id]?.is_required ?? mod.is_required}
                      onChange={(e) =>
                        setModuleEdits((c) => ({
                          ...c,
                          [mod.id]: {
                            ...(c[mod.id] ?? { title: mod.title, description: mod.description, is_required: mod.is_required }),
                            is_required: e.target.checked,
                          },
                        }))
                      }
                      type="checkbox"
                    />
                    <span className="form-field__label">Required for completion</span>
                  </label>

                  <div className="btn-row">
                    <button className="btn btn--sm" onClick={() => updateModuleMutation.mutate(mod.id)} type="button">
                      Save changes
                    </button>
                    <button className="btn btn--sm btn--danger" onClick={() => deleteModuleMutation.mutate(mod.id)} type="button">
                      <Trash2 size={14} style={{ marginRight: 4, verticalAlign: -2 }} /> Delete module
                    </button>
                  </div>
                </div>
              </details>

              {/* Assets section with guidance */}
              <div className="module-panel__assets-section">
                <div className="module-panel__assets-header">
                  <FileUp size={16} />
                  <span className="module-panel__assets-label">Assets</span>
                  <span className="module-panel__assets-hint">Upload PDFs, slides, docs, or subtitle files for this module</span>
                </div>
                <ModuleAssetManager courseId={courseId} module={mod} />
              </div>
            </div>
          ))}

          {!modulesQuery.isLoading && !modules.length ? (
            <div className="editor-empty-state">
              <FolderOpen size={40} strokeWidth={1.5} />
              <div className="editor-empty-state__title">No modules yet</div>
              <div className="editor-empty-state__text">
                Add your first module below — each module holds its own assets (PDFs, slides, docs).
              </div>
            </div>
          ) : null}

          {/* Compact add-module form */}
          <div className="module-add-form">
            <form
              className="module-add-form__inner"
              onSubmit={(e) => {
                e.preventDefault()
                createModuleMutation.mutate()
              }}
            >
              <div className="module-add-form__fields">
                <input
                  className="module-add-form__input"
                  placeholder="New module title…"
                  value={moduleTitle}
                  onChange={(e) => setModuleTitle(e.target.value)}
                />
                <input
                  className="module-add-form__input module-add-form__input--desc"
                  placeholder="Description (optional)"
                  value={moduleDescription}
                  onChange={(e) => setModuleDescription(e.target.value)}
                />
              </div>
              <button className="btn btn--primary btn--sm" disabled={!moduleTitle || createModuleMutation.isPending} type="submit">
                <Plus size={14} style={{ marginRight: 3, verticalAlign: -2 }} />
                {createModuleMutation.isPending ? 'Adding…' : 'Add module'}
              </button>
            </form>
            {createModuleMutation.isError ? <StatusMsg type="error" text={getErrorMessage(createModuleMutation.error)} /> : null}
          </div>

          {modules.length > 0 && (
            <div className="btn-row" style={{ justifyContent: 'flex-end' }}>
              <button
                className="btn btn--ghost"
                onClick={() => setActiveTab('content')}
                type="button"
              >
                Next: Draft content →
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Draft Content ── */}
      {activeTab === 'content' && (
        <div className="page-stack">
          <div className="editor-callout">
            <div className="editor-callout__icon"><BookOpen size={20} /></div>
            <div className="editor-callout__body">
              <div className="editor-callout__title">What goes here?</div>
              <div className="editor-callout__text">
                Draft content is stored separately and supports rich structured data. Use it for the course <strong>overview</strong>, <strong>learning objectives</strong>, and <strong>lesson notes</strong> per module.
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Draft content (JSON)</h2>
              <p className="card__description">Edit the structured content below. Suggested keys: <code>overview</code>, <code>learning_objectives</code>, <code>lesson_notes</code>.</p>
            </div>

            <div className="form-stack">
              <label className="form-field">
                <span className="form-field__label">JSON content</span>
                <textarea
                  className="json-editor"
                  value={draftContentValue}
                  onChange={(e) =>
                    setDraftContentState({ courseId, value: e.target.value, dirty: true })
                  }
                />
              </label>

              {draftContentError ? <StatusMsg type="error" text={draftContentError} /> : null}
              {saveDraftContentMutation.isError ? <StatusMsg type="error" text={getErrorMessage(saveDraftContentMutation.error)} /> : null}
              {saveDraftContentMutation.isSuccess ? <StatusMsg type="success" text="Draft content saved." /> : null}

              <div className="btn-row">
                <button
                  className="btn btn--primary"
                  disabled={saveDraftContentMutation.isPending}
                  onClick={() => {
                    try {
                      const parsed = parseDraftContent(draftContentValue)
                      setDraftContentError('')
                      saveDraftContentMutation.mutate(parsed)
                    } catch (err) {
                      setDraftContentError(getErrorMessage(err))
                    }
                  }}
                  type="button"
                >
                  {saveDraftContentMutation.isPending ? 'Saving...' : 'Save content'}
                </button>
                <button
                  className="btn btn--ghost"
                  onClick={() => setActiveTab('publish')}
                  type="button"
                >
                  Next: Validate & publish →
                </button>
              </div>

              <div className="meta-list">
                <div className="meta-item">
                  <div className="meta-item__label">Last saved</div>
                  <div className="meta-item__value">
                    {draftContentQuery.data?.updated_at
                      ? new Date(draftContentQuery.data.updated_at).toLocaleString()
                      : 'Not saved yet'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {courseQuery.data?.visibility === 'PUBLISHED' ? (
            <>
              <AIAssistantPanel
                courseId={courseId}
                modules={modules}
                canAsk
              />
              <AIEnhancementPanel
                courseId={courseId}
                modules={modules}
                canEnhance
              />
            </>
          ) : (
            <div className="editor-hint">
              <Zap size={16} />
              <span>AI assistant &amp; enhancements will unlock after you publish and activate this course.</span>
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Validate & Publish ── */}
      {activeTab === 'publish' && (
        <div className="page-stack">
          {/* Step 1: Validation */}
          <div className="card">
            <div className="card__header">
              <h2 className="card__title">
                <ShieldCheck size={18} style={{ marginRight: 6, verticalAlign: -3 }} />
                Step 1 — Validate your draft
              </h2>
              <p className="card__description">Check that your course has all the required info before submitting for review.</p>
            </div>

            <div className="btn-row" style={{ marginBottom: '0.75rem' }}>
              <button className="btn btn--primary" disabled={validateDraftMutation.isPending} onClick={() => validateDraftMutation.mutate()} type="button">
                {validateDraftMutation.isPending ? 'Checking...' : 'Run validation'}
              </button>
            </div>

            {validateDraftMutation.isError ? (
              <StatusMsg type="error" text={getErrorMessage(validateDraftMutation.error)} />
            ) : null}

            {validationResult ? (
              <div className="validation-result">
                <div className={`message ${validationResult.is_valid ? 'message--success' : 'message--warning'}`}>
                  {validationResult.is_valid
                    ? 'All checks passed — you can submit for publishing.'
                    : `${validationResult.issues.length} issue(s) need fixing before you can publish.`}
                </div>
                {validationResult.issues.map((issue) => (
                  <div className="validation-issue" key={`${issue.field}-${issue.message}`}>
                    <div className="validation-issue__field">{issue.field}</div>
                    <div className="validation-issue__message">{issue.message}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty">Click "Run validation" to check your draft.</div>
            )}
          </div>

          {/* Step 2: Submit for publishing */}
          <div className="card">
            <div className="card__header">
              <h2 className="card__title">
                <Rocket size={18} style={{ marginRight: 6, verticalAlign: -3 }} />
                Step 2 — Submit for publishing
              </h2>
              <p className="card__description">
                {!publishingData
                  ? 'Once validation passes, click below to submit your course. An admin will review and approve it.'
                  : 'Your course is in the publishing pipeline. Track progress below.'}
              </p>
            </div>

            {!publishingData && (
              <>
                <div className="editor-callout" style={{ marginBottom: 'var(--space-4)' }}>
                  <div className="editor-callout__icon"><Info size={20} /></div>
                  <div className="editor-callout__body">
                    <div className="editor-callout__title">How publishing works</div>
                    <div className="editor-callout__text">
                      <strong>1.</strong> You submit the draft → <strong>2.</strong> System runs a preflight check → <strong>3.</strong> An admin reviews and approves → <strong>4.</strong> Course is processed and published automatically.
                    </div>
                  </div>
                </div>

                <div className="btn-row">
                  <button
                    className="btn btn--primary"
                    disabled={publishMutation.isPending}
                    onClick={() => publishMutation.mutate()}
                    type="button"
                  >
                    <Rocket size={16} style={{ marginRight: 4, verticalAlign: -2 }} />
                    {publishMutation.isPending ? 'Submitting...' : 'Submit for publishing'}
                  </button>
                </div>

                {publishMutation.isError ? (
                  <StatusMsg type="error" text={getErrorMessage(publishMutation.error)} />
                ) : null}
              </>
            )}

            {/* Pipeline visualization */}
            {publishingData && (
              <PublishingPipeline
                publishingData={publishingData}
                canReview={canReview}
                canCancel={Boolean(canCancel)}
                onApprove={() => approveMutation.mutate(publishingData.id)}
                onReject={() => rejectMutation.mutate(publishingData.id)}
                onCancel={() => cancelMutation.mutate(publishingData.id)}
                onRetry={() => retryMutation.mutate(publishingData.id)}
                onActivate={() => activateMutation.mutate(publishingData.id)}
                isApprovePending={approveMutation.isPending}
                isRejectPending={rejectMutation.isPending}
                isCancelPending={cancelMutation.isPending}
                isRetryPending={retryMutation.isPending}
                isActivatePending={activateMutation.isPending}
                courseVisibility={courseQuery.data?.visibility ?? ''}
              />
            )}

            {/* Error display for any mutation */}
            {retryMutation.isError ? <StatusMsg type="error" text={getErrorMessage(retryMutation.error)} /> : null}
            {cancelMutation.isError ? <StatusMsg type="error" text={getErrorMessage(cancelMutation.error)} /> : null}
            {approveMutation.isError ? <StatusMsg type="error" text={getErrorMessage(approveMutation.error)} /> : null}
            {rejectMutation.isError ? <StatusMsg type="error" text={getErrorMessage(rejectMutation.error)} /> : null}
            {activateMutation.isError ? <StatusMsg type="error" text={getErrorMessage(activateMutation.error)} /> : null}
            {publishingQuery.isError ? <StatusMsg type="error" text={getErrorMessage(publishingQuery.error)} /> : null}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Instructor: Course Enrollments ─────────────────────────────────── */
import {
  listCourseEnrollments,
  type EnrollmentRecord,
} from '../../lib/api'

export function InstructorEnrollmentsPage() {
  const { courseId = '' } = useParams()
  const [status, setStatus] = useState('')

  const courseQuery = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => getCourse(courseId),
    enabled: Boolean(courseId),
  })

  const enrollmentsQuery = useQuery({
    queryKey: ['course-enrollments', courseId, status],
    queryFn: () => listCourseEnrollments(courseId, { status: status || undefined }),
    enabled: Boolean(courseId),
  })

  const course = courseQuery.data
  const enrollments: EnrollmentRecord[] = enrollmentsQuery.data?.data ?? []

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header__breadcrumb">
          <Link to="/app/courses">My courses</Link>
          <span>/</span>
          <Link to={`/app/courses/${courseId}`}>{course?.title ?? courseId.slice(0, 8)}</Link>
          <span>/</span>
          <span>Students</span>
        </div>
        <h1 className="page-header__title">Enrolled students</h1>
        <p className="page-header__description">
          Students currently enrolled in <strong>{course?.title ?? 'this course'}</strong>.
        </p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '1rem' }}>
          <label className="form-field">
            <span className="form-field__label">Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="ENROLLED">Active</option>
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
                <th>Student ID</th>
                <th>Status</th>
                <th>Enrolled on</th>
              </tr>
            </thead>
            <tbody>
              {enrollments.map((enrollment) => (
                <tr key={enrollment.id}>
                  <td className="mono">{enrollment.id.slice(0, 8)}</td>
                  <td className="mono">{enrollment.student_id.slice(0, 8)}</td>
                  <td>
                    <span className={`badge ${
                      enrollment.status === 'COMPLETED' ? 'badge--success'
                      : enrollment.status === 'CANCELLED' ? 'badge--danger'
                      : 'badge--accent'
                    }`}>
                      {enrollment.status === 'ENROLLED' ? 'Active' : enrollment.status.charAt(0) + enrollment.status.slice(1).toLowerCase()}
                    </span>
                  </td>
                  <td>{new Date(enrollment.enrolled_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!enrollmentsQuery.isLoading && !enrollments.length ? (
          <div className="empty">No students enrolled{status ? ` with status ${status}` : ''}.</div>
        ) : null}
      </div>
    </div>
  )
}
