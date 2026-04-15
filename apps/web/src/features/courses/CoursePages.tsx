import { useEffect, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
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

export function CourseEditorPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const session = useSessionState()
  const { courseId = '' } = useParams()
  const [courseForm, setCourseForm] = useState<CourseCreateInput>(defaultCourseInput)
  const [courseTagsInput, setCourseTagsInput] = useState('')
  const [draftContentText, setDraftContentText] = useState(stringifyContent())
  const [draftContentError, setDraftContentError] = useState('')
  const [moduleTitle, setModuleTitle] = useState('')
  const [moduleDescription, setModuleDescription] = useState('')
  const [moduleEdits, setModuleEdits] = useState<Record<string, Pick<ModuleDetail, 'title' | 'description' | 'is_required'>>>({})
  const [publishingVersionId, setPublishingVersionId] = useState<string | null>(() => getStoredVersionId(courseId))

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

  useEffect(() => {
    if (!courseQuery.data) return
    setCourseForm({
      title: courseQuery.data.title,
      description: courseQuery.data.description ?? '',
      short_description: courseQuery.data.short_description ?? '',
      category: courseQuery.data.category ?? '',
      difficulty: courseQuery.data.difficulty ?? 'beginner',
      estimated_duration: courseQuery.data.estimated_duration ?? '',
      tags: courseQuery.data.tags ?? [],
      max_capacity: courseQuery.data.max_capacity ?? undefined,
    })
    setCourseTagsInput((courseQuery.data.tags ?? []).join(', '))
  }, [courseQuery.data])

  useEffect(() => {
    if (!courseId) return
    setPublishingVersionId(getStoredVersionId(courseId))
  }, [courseId])

  useEffect(() => {
    if (!draftContentQuery.data) return
    setDraftContentText(stringifyContent(draftContentQuery.data))
  }, [draftContentQuery.data])

  useEffect(() => {
    if (!modulesQuery.data) return
    setModuleEdits(
      modulesQuery.data.reduce<Record<string, Pick<ModuleDetail, 'title' | 'description' | 'is_required'>>>((acc, m) => {
        acc[m.id] = { title: m.title, description: m.description, is_required: m.is_required }
        return acc
      }, {}),
    )
  }, [modulesQuery.data])

  const updateCourseMutation = useMutation({
    mutationFn: (input: CourseCreateInput) =>
      updateCourse(courseId, { ...input, tags: tagsFromInput(courseTagsInput) }),
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
    mutationFn: (moduleId: string) =>
      updateModule(courseId, moduleId, {
        title: moduleEdits[moduleId]?.title,
        description: moduleEdits[moduleId]?.description ?? undefined,
        is_required: moduleEdits[moduleId]?.is_required,
      }),
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
      await queryClient.invalidateQueries({ queryKey: ['draft-content', courseId] })
    },
  })

  const publishingQuery = useQuery<PublishingVersion>({
    queryKey: ['publishing', publishingVersionId],
    queryFn: () => getPublishingVersion(publishingVersionId ?? ''),
    enabled: Boolean(publishingVersionId),
    refetchInterval: (data) => {
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
  const canReview = Boolean(session?.user.roles.some((role) => role === 'admin' || role === 'instructor'))
  const preflightSummary = publishingData?.preflight_summary_json

  return (
    <div className="page-stack">
      <div className="page-header">
        <div className="page-header__breadcrumb">
          <Link to="/app/courses">Courses</Link>
          <span>/</span>
          <span>{courseQuery.data?.title}</span>
        </div>
        <h1 className="page-header__title">{courseQuery.data?.title}</h1>
        <p className="page-header__description">Edit course details, manage modules and assets, and validate the draft.</p>
      </div>

      <div className="stat-row">
        <div className="stat-item">
          <div className="stat-item__label">Visibility</div>
          <div className="stat-item__value">{courseQuery.data?.visibility}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Modules</div>
          <div className="stat-item__value">{modules.length}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Slug</div>
          <div className="stat-item__value mono">{courseQuery.data?.slug}</div>
        </div>
        <div className="stat-item">
          <div className="stat-item__label">Updated</div>
          <div className="stat-item__value">{new Date(courseQuery.data?.updated_at ?? '').toLocaleString()}</div>
        </div>
      </div>

      {/* Details + Validation */}
      <div className="page-columns--wide page-columns">
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Course details</h2>
          </div>

          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault()
              updateCourseMutation.mutate(courseForm)
            }}
          >
            <label className="form-field">
              <span className="form-field__label">Title</span>
              <input
                value={courseForm.title}
                onChange={(e) => setCourseForm((c) => ({ ...c, title: e.target.value }))}
              />
            </label>

            <label className="form-field">
              <span className="form-field__label">Description</span>
              <textarea
                value={courseForm.description ?? ''}
                onChange={(e) => setCourseForm((c) => ({ ...c, description: e.target.value }))}
              />
            </label>

            <div className="form-row">
              <label className="form-field">
                <span className="form-field__label">Short description</span>
                <input
                  value={courseForm.short_description ?? ''}
                  onChange={(e) => setCourseForm((c) => ({ ...c, short_description: e.target.value }))}
                />
              </label>
              <label className="form-field">
                <span className="form-field__label">Category</span>
                <input
                  value={courseForm.category ?? ''}
                  onChange={(e) => setCourseForm((c) => ({ ...c, category: e.target.value }))}
                />
              </label>
            </div>

            <div className="form-row">
              <label className="form-field">
                <span className="form-field__label">Difficulty</span>
                <select
                  value={courseForm.difficulty ?? ''}
                  onChange={(e) => setCourseForm((c) => ({ ...c, difficulty: e.target.value }))}
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </label>
              <label className="form-field">
                <span className="form-field__label">Estimated duration</span>
                <input
                  value={courseForm.estimated_duration ?? ''}
                  onChange={(e) => setCourseForm((c) => ({ ...c, estimated_duration: e.target.value }))}
                />
              </label>
            </div>

            <label className="form-field">
              <span className="form-field__label">Tags</span>
              <input value={courseTagsInput} onChange={(e) => setCourseTagsInput(e.target.value)} />
            </label>

            {updateCourseMutation.isError ? <StatusMsg type="error" text={getErrorMessage(updateCourseMutation.error)} /> : null}
            {updateCourseMutation.isSuccess ? <StatusMsg type="success" text="Course details saved." /> : null}

            <div className="btn-row">
              <button className="btn btn--primary" disabled={updateCourseMutation.isPending} type="submit">
                {updateCourseMutation.isPending ? 'Saving...' : 'Save details'}
              </button>
              <button
                className="btn btn--danger"
                disabled={deleteCourseMutation.isPending}
                onClick={() => deleteCourseMutation.mutate()}
                type="button"
              >
                {deleteCourseMutation.isPending ? 'Deleting...' : 'Delete draft'}
              </button>
            </div>
          </form>
        </div>

        <div className="page-stack">
          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Draft validation</h2>
              <p className="card__description">Check if the draft is ready for publishing.</p>
            </div>

            <div className="btn-row" style={{ marginBottom: '0.75rem' }}>
              <button className="btn btn--primary" disabled={validateDraftMutation.isPending} onClick={() => validateDraftMutation.mutate()} type="button">
                {validateDraftMutation.isPending ? 'Validating...' : 'Run validation'}
              </button>
            </div>

            {validateDraftMutation.isError ? (
              <StatusMsg type="error" text={getErrorMessage(validateDraftMutation.error)} />
            ) : null}

            {validationResult ? (
              <div className="validation-result">
                <div className={`message ${validationResult.is_valid ? 'message--success' : 'message--warning'}`}>
                  {validationResult.is_valid
                    ? 'Draft is valid and ready for publishing.'
                    : `${validationResult.issues.length} issue(s) need attention.`}
                </div>
                {validationResult.issues.map((issue) => (
                  <div className="validation-issue" key={`${issue.field}-${issue.message}`}>
                    <div className="validation-issue__field">{issue.field}</div>
                    <div className="validation-issue__message">{issue.message}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty">No validation run yet.</div>
            )}
          </div>

          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Publishing</h2>
              <p className="card__description">Launch the publishing pipeline and track progress.</p>
            </div>

            <div className="btn-row" style={{ marginBottom: '0.75rem' }}>
              <button
                className="btn btn--primary"
                disabled={publishMutation.isPending}
                onClick={() => publishMutation.mutate()}
                type="button"
              >
                {publishMutation.isPending ? 'Publishing...' : 'Publish draft'}
              </button>
              {publishingData?.status === 'FAILED' ? (
                <button
                  className="btn btn--ghost"
                  disabled={retryMutation.isPending}
                  onClick={() => retryMutation.mutate(publishingData.id)}
                  type="button"
                >
                  {retryMutation.isPending ? 'Retrying...' : 'Retry'}
                </button>
              ) : null}
              {publishingData?.status === 'REVIEW_REQUIRED' && canReview ? (
                <>
                  <button
                    className="btn btn--primary"
                    disabled={approveMutation.isPending || publishingData.approval_state === 'APPROVED'}
                    onClick={() => approveMutation.mutate(publishingData.id)}
                    type="button"
                  >
                    {approveMutation.isPending ? 'Approving...' : 'Approve'}
                  </button>
                  <button
                    className="btn btn--danger"
                    disabled={rejectMutation.isPending || publishingData.approval_state === 'REJECTED'}
                    onClick={() => rejectMutation.mutate(publishingData.id)}
                    type="button"
                  >
                    {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
                  </button>
                </>
              ) : null}
              {(publishingData?.status === 'PUBLISHING' || publishingData?.status === 'REVIEW_REQUIRED') && canCancel ? (
                <button
                  className="btn btn--danger"
                  disabled={cancelMutation.isPending}
                  onClick={() => cancelMutation.mutate(publishingData.id)}
                  type="button"
                >
                  {cancelMutation.isPending ? 'Cancelling...' : 'Cancel'}
                </button>
              ) : null}
            </div>

            {publishMutation.isError ? (
              <StatusMsg type="error" text={getErrorMessage(publishMutation.error)} />
            ) : null}
            {retryMutation.isError ? (
              <StatusMsg type="error" text={getErrorMessage(retryMutation.error)} />
            ) : null}
            {cancelMutation.isError ? (
              <StatusMsg type="error" text={getErrorMessage(cancelMutation.error)} />
            ) : null}
            {approveMutation.isError ? (
              <StatusMsg type="error" text={getErrorMessage(approveMutation.error)} />
            ) : null}
            {rejectMutation.isError ? (
              <StatusMsg type="error" text={getErrorMessage(rejectMutation.error)} />
            ) : null}

            {publishingQuery.isError ? (
              <StatusMsg type="error" text={getErrorMessage(publishingQuery.error)} />
            ) : null}

            {publishingData ? (
              <div className="validation-result">
                <div className={`message ${publishingData.status === 'READY' ? 'message--success' : publishingData.status === 'FAILED' || publishingData.status === 'CANCELLED' ? 'message--error' : 'message--warning'}`}>
                  Status: {publishingData.status}
                </div>
                <div className="meta-list">
                  <div className="meta-item">
                    <div className="meta-item__label">Version</div>
                    <div className="meta-item__value">{publishingData.version_number}</div>
                  </div>
                  <div className="meta-item">
                    <div className="meta-item__label">Assets</div>
                    <div className="meta-item__value">{publishingData.total_assets}</div>
                  </div>
                  <div className="meta-item">
                    <div className="meta-item__label">Chunks</div>
                    <div className="meta-item__value">{publishingData.total_chunks}</div>
                  </div>
                  <div className="meta-item">
                    <div className="meta-item__label">Approval</div>
                    <div className="meta-item__value">{publishingData.approval_state}</div>
                  </div>
                  <div className="meta-item">
                    <div className="meta-item__label">Manifest hash</div>
                    <div className="meta-item__value mono">{publishingData.manifest_hash.slice(0, 12)}...</div>
                  </div>
                </div>
                {preflightSummary ? (
                  <div className="meta-list" style={{ marginBottom: '0.75rem' }}>
                    <div className="meta-item">
                      <div className="meta-item__label">Estimated pages</div>
                      <div className="meta-item__value">{String(preflightSummary.estimated_pages ?? '0')}</div>
                    </div>
                    <div className="meta-item">
                      <div className="meta-item__label">Flagged assets</div>
                      <div className="meta-item__value">{String(preflightSummary.flagged_assets ?? '0')}</div>
                    </div>
                  </div>
                ) : null}
                <div className="validation-list">
                  {publishingData.steps.map((step) => (
                    <div className="validation-issue" key={step.id}>
                      <div className="validation-issue__field">{step.step_name}</div>
                      <div className="validation-issue__message">{step.status}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty">No publishing run yet.</div>
            )}
          </div>

          <div className="card">
            <div className="card__header">
              <h2 className="card__title">Draft content</h2>
              <p className="card__description">Persist rich authoring content in MongoDB.</p>
            </div>

            <div className="form-stack">
              <label className="form-field">
                <span className="form-field__label">JSON content</span>
                <textarea className="json-editor" value={draftContentText} onChange={(e) => setDraftContentText(e.target.value)} />
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
                      const parsed = parseDraftContent(draftContentText)
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
                <div className="meta-item">
                  <div className="meta-item__label">Suggested keys</div>
                  <div className="meta-item__value mono">overview, learning_objectives, lesson_notes</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modules */}
      <div className="card">
        <div className="card__header">
          <h2 className="card__title">Modules &amp; assets</h2>
          <p className="card__description">Structure the course and manage files.</p>
        </div>

        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault()
            createModuleMutation.mutate()
          }}
          style={{ marginBottom: '1.25rem' }}
        >
          <div className="form-row">
            <label className="form-field">
              <span className="form-field__label">Module title</span>
              <input value={moduleTitle} onChange={(e) => setModuleTitle(e.target.value)} />
            </label>
            <label className="form-field">
              <span className="form-field__label">Description</span>
              <input value={moduleDescription} onChange={(e) => setModuleDescription(e.target.value)} />
            </label>
          </div>
          <div className="btn-row">
            <button className="btn" disabled={!moduleTitle || createModuleMutation.isPending} type="submit">
              {createModuleMutation.isPending ? 'Adding...' : 'Add module'}
            </button>
          </div>
        </form>

        {createModuleMutation.isError ? <StatusMsg type="error" text={getErrorMessage(createModuleMutation.error)} /> : null}

        {modules.map((mod, index) => (
          <div className="module-panel" key={mod.id}>
            <div className="module-panel__header">
              <div>
                <div className="module-panel__title">{mod.title}</div>
                <div className="module-panel__order">Position {mod.sort_order}</div>
              </div>
              <div className="btn-row">
                <button className="btn btn--sm" disabled={index === 0 || reorderModulesMutation.isPending} onClick={() => moveModule(mod.id, -1)} type="button">
                  Up
                </button>
                <button className="btn btn--sm" disabled={index === modules.length - 1 || reorderModulesMutation.isPending} onClick={() => moveModule(mod.id, 1)} type="button">
                  Down
                </button>
              </div>
            </div>

            <div className="form-stack">
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
            </div>

            <div className="btn-row" style={{ marginTop: '0.75rem' }}>
              <button className="btn btn--sm" onClick={() => updateModuleMutation.mutate(mod.id)} type="button">
                Save module
              </button>
              <button className="btn btn--sm btn--ghost" onClick={() => deleteModuleMutation.mutate(mod.id)} type="button">
                Delete
              </button>
            </div>

            <ModuleAssetManager courseId={courseId} module={mod} />
          </div>
        ))}

        {!modulesQuery.isLoading && !modules.length ? (
          <div className="empty">No modules yet. Add one above to start building the course.</div>
        ) : null}
      </div>
    </div>
  )
}
