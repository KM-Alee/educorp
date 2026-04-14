import { useEffect, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  createCourse,
  createModule,
  deleteAsset,
  deleteCourse,
  deleteModule,
  getAssetDownload,
  getCourse,
  getDraftContent,
  listAssets,
  listCourses,
  listModules,
  reorderModules,
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
} from '../../lib/api'
import { getErrorMessage } from '../../lib/types'

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

function PageMessage({ type, text }: { type: 'success' | 'error'; text: string }) {
  return <div className={`message message--${type}`}>{text}</div>
}

function CourseSummaryCard({
  course,
  active,
}: {
  course: CourseListItem
  active: boolean
}) {
  return (
    <Link className={`course-card ${active ? 'course-card--active' : ''}`} to={`/app/courses/${course.id}`}>
      <div className="course-card__header">
        <div>
          <strong>{course.title}</strong>
          <div className="table-note">{course.short_description || 'No short description yet.'}</div>
        </div>
        <span className="pill">{course.visibility}</span>
      </div>

      <div className="pill-group">
        {course.category ? <span className="pill">{course.category}</span> : null}
        {course.difficulty ? <span className="pill">{course.difficulty}</span> : null}
        {course.estimated_duration ? <span className="pill mono">{course.estimated_duration}</span> : null}
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
      <section className="page-hero phase-banner phase-banner--authoring">
        <div className="page-stack">
          <span className="eyebrow">Phase 2</span>
          <h1 className="page-title">Course authoring desk</h1>
          <p className="lede">
            Create draft courses, move into module and asset work, and validate drafts from the same operational surface used to test the course service.
          </p>
        </div>
      </section>

      <section className="content-grid content-grid--wide">
        <article className="section-card">
          <div className="page-stack">
            <div>
              <h2>Create a draft course</h2>
              <p>Start from the live course API and jump directly into editing once the draft is created.</p>
            </div>

            <form
              className="form-grid"
              onSubmit={(event) => {
                event.preventDefault()
                createCourseMutation.mutate({
                  ...draft,
                  tags: tagsFromInput(tagsInput),
                })
              }}
            >
              <label className="field">
                <span>Title</span>
                <input
                  value={draft.title}
                  onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
                />
              </label>

              <label className="field">
                <span>Description</span>
                <textarea
                  value={draft.description ?? ''}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, description: event.target.value }))
                  }
                />
              </label>

              <div className="split-grid">
                <label className="field">
                  <span>Short description</span>
                  <input
                    value={draft.short_description ?? ''}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, short_description: event.target.value }))
                    }
                  />
                </label>

                <label className="field">
                  <span>Category</span>
                  <input
                    value={draft.category ?? ''}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, category: event.target.value }))
                    }
                  />
                </label>
              </div>

              <div className="split-grid">
                <label className="field">
                  <span>Difficulty</span>
                  <select
                    value={draft.difficulty ?? ''}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, difficulty: event.target.value }))
                    }
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </label>

                <label className="field">
                  <span>Estimated duration</span>
                  <input
                    placeholder="PT4H"
                    value={draft.estimated_duration ?? ''}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, estimated_duration: event.target.value }))
                    }
                  />
                </label>
              </div>

              <label className="field">
                <span>Tags</span>
                <input
                  placeholder="python, ml, pedagogy"
                  value={tagsInput}
                  onChange={(event) => setTagsInput(event.target.value)}
                />
              </label>

              {createCourseMutation.isError ? (
                <PageMessage type="error" text={getErrorMessage(createCourseMutation.error)} />
              ) : null}

              <div className="button-row">
                <button className="button button--accent" disabled={createCourseMutation.isPending} type="submit">
                  {createCourseMutation.isPending ? 'Creating...' : 'Create draft'}
                </button>
              </div>
            </form>
          </div>
        </article>

        <aside className="section-card">
          <div className="page-stack">
            <div>
              <h2>Open a draft</h2>
              <p>Filter the live draft catalog, then open a course to manage modules, assets, validation, and rich content.</p>
            </div>

            <div className="filter-row">
              <label className="field field--compact">
                <span>Search</span>
                <input value={search} onChange={(event) => setSearch(event.target.value)} />
              </label>
              <label className="field field--compact">
                <span>Category</span>
                <input value={category} onChange={(event) => setCategory(event.target.value)} />
              </label>
              <label className="field field--compact">
                <span>Difficulty</span>
                <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
                  <option value="">All</option>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </label>
            </div>

            {coursesQuery.isError ? (
              <PageMessage type="error" text={getErrorMessage(coursesQuery.error)} />
            ) : null}

            <div className="course-card-list">
              {coursesQuery.data?.data.map((course) => (
                <CourseSummaryCard active={false} course={course} key={course.id} />
              ))}
            </div>

            {!coursesQuery.isLoading && !coursesQuery.data?.data.length ? (
              <div className="empty-state">No drafts match the current filter.</div>
            ) : null}
          </div>
        </aside>
      </section>
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
    <div className="module-assets page-stack">
      <form
        className="form-grid form-grid--inline"
        onSubmit={(event) => {
          event.preventDefault()
          if (!assetFile) {
            return
          }

          uploadMutation.mutate({ file: assetFile, title: assetTitle || assetFile.name })
        }}
      >
        <label className="field field--compact">
          <span>Asset title</span>
          <input value={assetTitle} onChange={(event) => setAssetTitle(event.target.value)} />
        </label>

        <label className="field field--compact">
          <span>File</span>
          <input
            accept=".pdf,.docx,.pptx,.txt,.md,.vtt,.srt"
            onChange={(event) => setAssetFile(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>

        <button className="button button--small" disabled={!assetFile || uploadMutation.isPending} type="submit">
          {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
        </button>
      </form>

      {uploadMutation.isError ? <PageMessage type="error" text={getErrorMessage(uploadMutation.error)} /> : null}
      {deleteMutation.isError ? <PageMessage type="error" text={getErrorMessage(deleteMutation.error)} /> : null}
      {downloadMutation.isError ? <PageMessage type="error" text={getErrorMessage(downloadMutation.error)} /> : null}

      <div className="course-panel-list">
        {assetsQuery.data?.map((asset: AssetOut) => (
          <article className="meta-card asset-row" key={asset.id}>
            <div>
              <strong>{asset.title}</strong>
              <div className="table-note mono">{asset.file_name}</div>
            </div>
            <div className="button-row">
              <button className="button button--small" onClick={() => downloadMutation.mutate(asset.id)} type="button">
                Download
              </button>
              <button
                className="button button--small button--ghost"
                onClick={() => deleteMutation.mutate(asset.id)}
                type="button"
              >
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>

      {!assetsQuery.isLoading && !assetsQuery.data?.length ? (
        <div className="empty-state">No assets uploaded for this module yet.</div>
      ) : null}
    </div>
  )
}

export function CourseEditorPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { courseId = '' } = useParams()
  const [courseForm, setCourseForm] = useState<CourseCreateInput>(defaultCourseInput)
  const [courseTagsInput, setCourseTagsInput] = useState('')
  const [draftContentText, setDraftContentText] = useState(stringifyContent())
  const [draftContentError, setDraftContentError] = useState('')
  const [moduleTitle, setModuleTitle] = useState('')
  const [moduleDescription, setModuleDescription] = useState('')
  const [moduleEdits, setModuleEdits] = useState<Record<string, Pick<ModuleDetail, 'title' | 'description' | 'is_required'>>>({})

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
    if (!courseQuery.data) {
      return
    }

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
    if (!draftContentQuery.data) {
      return
    }

    setDraftContentText(stringifyContent(draftContentQuery.data))
  }, [draftContentQuery.data])

  useEffect(() => {
    if (!modulesQuery.data) {
      return
    }

    setModuleEdits(
      modulesQuery.data.reduce<Record<string, Pick<ModuleDetail, 'title' | 'description' | 'is_required'>>>((accumulator, module) => {
        accumulator[module.id] = {
          title: module.title,
          description: module.description,
          is_required: module.is_required,
        }
        return accumulator
      }, {}),
    )
  }, [modulesQuery.data])

  const updateCourseMutation = useMutation({
    mutationFn: (input: CourseCreateInput) =>
      updateCourse(courseId, {
        ...input,
        tags: tagsFromInput(courseTagsInput),
      }),
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
      createModule(courseId, {
        title: moduleTitle,
        description: moduleDescription,
        is_required: true,
      }),
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

  const saveDraftContentMutation = useMutation({
    mutationFn: (content: Record<string, unknown>) => updateDraftContent(courseId, content),
    onSuccess: async () => {
      setDraftContentError('')
      await queryClient.invalidateQueries({ queryKey: ['draft-content', courseId] })
    },
  })

  const modules = modulesQuery.data ?? []

  function moveModule(moduleId: string, direction: -1 | 1) {
    const currentOrder = modules.map((module) => module.id)
    const currentIndex = currentOrder.indexOf(moduleId)
    const nextIndex = currentIndex + direction

    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= currentOrder.length) {
      return
    }

    const reordered = [...currentOrder]
    const swapped = reordered[nextIndex]
    reordered[nextIndex] = reordered[currentIndex]
    reordered[currentIndex] = swapped
    reorderModulesMutation.mutate(reordered)
  }

  if (courseQuery.isLoading) {
    return <div className="empty-state">Loading course workspace...</div>
  }

  if (courseQuery.isError) {
    return <PageMessage type="error" text={getErrorMessage(courseQuery.error)} />
  }

  const validationResult = validateDraftMutation.data

  return (
    <div className="page-stack">
      <section className="page-hero phase-banner phase-banner--editor">
        <div className="page-stack">
          <div className="inline-links">
            <Link to="/app/courses">Back to draft list</Link>
          </div>
          <span className="eyebrow">Phase 2</span>
          <h1 className="page-title">{courseQuery.data?.title}</h1>
          <p className="lede">
            Edit the draft, structure modules, attach assets, validate readiness, and persist richer authoring content in MongoDB.
          </p>
        </div>
      </section>

      <section className="stat-grid stat-grid--four">
        <article className="stat-card">
          <strong>Visibility</strong>
          <span>{courseQuery.data?.visibility}</span>
        </article>
        <article className="stat-card">
          <strong>Modules</strong>
          <span>{modules.length}</span>
        </article>
        <article className="stat-card">
          <strong>Slug</strong>
          <span className="mono">{courseQuery.data?.slug}</span>
        </article>
        <article className="stat-card">
          <strong>Last update</strong>
          <span>{new Date(courseQuery.data?.updated_at ?? '').toLocaleString()}</span>
        </article>
      </section>

      <section className="content-grid content-grid--wide">
        <article className="section-card page-stack">
          <div>
            <h2>Course details</h2>
            <p>PATCH the live course record and keep metadata in a publishable state.</p>
          </div>

          <form
            className="form-grid"
            onSubmit={(event) => {
              event.preventDefault()
              updateCourseMutation.mutate(courseForm)
            }}
          >
            <label className="field">
              <span>Title</span>
              <input
                value={courseForm.title}
                onChange={(event) =>
                  setCourseForm((current) => ({ ...current, title: event.target.value }))
                }
              />
            </label>

            <label className="field">
              <span>Description</span>
              <textarea
                value={courseForm.description ?? ''}
                onChange={(event) =>
                  setCourseForm((current) => ({ ...current, description: event.target.value }))
                }
              />
            </label>

            <div className="split-grid">
              <label className="field">
                <span>Short description</span>
                <input
                  value={courseForm.short_description ?? ''}
                  onChange={(event) =>
                    setCourseForm((current) => ({ ...current, short_description: event.target.value }))
                  }
                />
              </label>
              <label className="field">
                <span>Category</span>
                <input
                  value={courseForm.category ?? ''}
                  onChange={(event) =>
                    setCourseForm((current) => ({ ...current, category: event.target.value }))
                  }
                />
              </label>
            </div>

            <div className="split-grid">
              <label className="field">
                <span>Difficulty</span>
                <select
                  value={courseForm.difficulty ?? ''}
                  onChange={(event) =>
                    setCourseForm((current) => ({ ...current, difficulty: event.target.value }))
                  }
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </label>
              <label className="field">
                <span>Estimated duration</span>
                <input
                  value={courseForm.estimated_duration ?? ''}
                  onChange={(event) =>
                    setCourseForm((current) => ({ ...current, estimated_duration: event.target.value }))
                  }
                />
              </label>
            </div>

            <label className="field">
              <span>Tags</span>
              <input value={courseTagsInput} onChange={(event) => setCourseTagsInput(event.target.value)} />
            </label>

            {updateCourseMutation.isError ? (
              <PageMessage type="error" text={getErrorMessage(updateCourseMutation.error)} />
            ) : null}

            {updateCourseMutation.isSuccess ? <PageMessage type="success" text="Course details saved." /> : null}

            <div className="button-row">
              <button className="button button--accent" disabled={updateCourseMutation.isPending} type="submit">
                {updateCourseMutation.isPending ? 'Saving...' : 'Save details'}
              </button>
              <button
                className="button button--ghost"
                disabled={deleteCourseMutation.isPending}
                onClick={() => deleteCourseMutation.mutate()}
                type="button"
              >
                {deleteCourseMutation.isPending ? 'Removing...' : 'Delete draft'}
              </button>
            </div>
          </form>
        </article>

        <aside className="section-card page-stack">
          <div>
            <h2>Draft validation</h2>
            <p>Run the same pre-publish checks the backend uses before the publishing workflow starts in Phase 3.</p>
          </div>

          <div className="button-row">
            <button className="button button--accent" disabled={validateDraftMutation.isPending} onClick={() => validateDraftMutation.mutate()} type="button">
              {validateDraftMutation.isPending ? 'Validating...' : 'Run validation'}
            </button>
          </div>

          {validateDraftMutation.isError ? (
            <PageMessage type="error" text={getErrorMessage(validateDraftMutation.error)} />
          ) : null}

          {validationResult ? (
            <div className="validation-shell">
              <div className={`validation-summary ${validationResult.is_valid ? 'validation-summary--success' : 'validation-summary--warning'}`}>
                {validationResult.is_valid ? 'Draft is currently valid for publish preparation.' : `${validationResult.issues.length} issue(s) still need work.`}
              </div>
              <div className="course-panel-list">
                {validationResult.issues.map((issue) => (
                  <article className="meta-card validation-issue" key={`${issue.field}-${issue.message}`}>
                    <strong>{issue.field}</strong>
                    <span>{issue.message}</span>
                  </article>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state">No validation run yet for this draft.</div>
          )}
        </aside>
      </section>

      <section className="content-grid content-grid--wide">
        <article className="section-card page-stack">
          <div>
            <h2>Modules and assets</h2>
            <p>Structure the course, adjust sort order, and manage MinIO-backed assets inline.</p>
          </div>

          <form
            className="form-grid form-grid--inline"
            onSubmit={(event) => {
              event.preventDefault()
              createModuleMutation.mutate()
            }}
          >
            <label className="field field--compact">
              <span>Module title</span>
              <input value={moduleTitle} onChange={(event) => setModuleTitle(event.target.value)} />
            </label>
            <label className="field field--compact field--wide">
              <span>Description</span>
              <input value={moduleDescription} onChange={(event) => setModuleDescription(event.target.value)} />
            </label>
            <button className="button" disabled={!moduleTitle || createModuleMutation.isPending} type="submit">
              {createModuleMutation.isPending ? 'Adding...' : 'Add module'}
            </button>
          </form>

          {createModuleMutation.isError ? (
            <PageMessage type="error" text={getErrorMessage(createModuleMutation.error)} />
          ) : null}

          <div className="course-panel-list">
            {modules.map((module, index) => (
              <article className="module-card" key={module.id}>
                <div className="module-card__header">
                  <div>
                    <strong>{module.title}</strong>
                    <div className="table-note">Sort order {module.sort_order}</div>
                  </div>
                  <div className="button-row">
                    <button className="button button--small" disabled={index === 0 || reorderModulesMutation.isPending} onClick={() => moveModule(module.id, -1)} type="button">
                      Move up
                    </button>
                    <button className="button button--small" disabled={index === modules.length - 1 || reorderModulesMutation.isPending} onClick={() => moveModule(module.id, 1)} type="button">
                      Move down
                    </button>
                  </div>
                </div>

                <div className="form-grid">
                  <label className="field field--compact">
                    <span>Title</span>
                    <input
                      value={moduleEdits[module.id]?.title ?? module.title}
                      onChange={(event) =>
                        setModuleEdits((current) => ({
                          ...current,
                          [module.id]: {
                            ...(current[module.id] ?? {
                              title: module.title,
                              description: module.description,
                              is_required: module.is_required,
                            }),
                            title: event.target.value,
                          },
                        }))
                      }
                    />
                  </label>

                  <label className="field field--compact">
                    <span>Description</span>
                    <textarea
                      value={moduleEdits[module.id]?.description ?? module.description ?? ''}
                      onChange={(event) =>
                        setModuleEdits((current) => ({
                          ...current,
                          [module.id]: {
                            ...(current[module.id] ?? {
                              title: module.title,
                              description: module.description,
                              is_required: module.is_required,
                            }),
                            description: event.target.value,
                          },
                        }))
                      }
                    />
                  </label>

                  <label className="field-checkbox">
                    <input
                      checked={moduleEdits[module.id]?.is_required ?? module.is_required}
                      onChange={(event) =>
                        setModuleEdits((current) => ({
                          ...current,
                          [module.id]: {
                            ...(current[module.id] ?? {
                              title: module.title,
                              description: module.description,
                              is_required: module.is_required,
                            }),
                            is_required: event.target.checked,
                          },
                        }))
                      }
                      type="checkbox"
                    />
                    Required for completion
                  </label>
                </div>

                <div className="button-row">
                  <button className="button button--small" onClick={() => updateModuleMutation.mutate(module.id)} type="button">
                    Save module
                  </button>
                  <button className="button button--small button--ghost" onClick={() => deleteModuleMutation.mutate(module.id)} type="button">
                    Delete module
                  </button>
                </div>

                <ModuleAssetManager courseId={courseId} module={module} />
              </article>
            ))}
          </div>

          {!modulesQuery.isLoading && !modules.length ? (
            <div className="empty-state">This draft has no modules yet. Add one to start composing the course.</div>
          ) : null}
        </article>

        <aside className="section-card page-stack">
          <div>
            <h2>Draft content</h2>
            <p>Persist richer authoring content in MongoDB now so the publishing and extraction pipeline has clean raw material in Phase 3.</p>
          </div>

          <label className="field">
            <span>JSON content</span>
            <textarea className="json-editor" value={draftContentText} onChange={(event) => setDraftContentText(event.target.value)} />
          </label>

          {draftContentError ? <PageMessage type="error" text={draftContentError} /> : null}
          {saveDraftContentMutation.isError ? (
            <PageMessage type="error" text={getErrorMessage(saveDraftContentMutation.error)} />
          ) : null}
          {saveDraftContentMutation.isSuccess ? <PageMessage type="success" text="Draft content saved to MongoDB." /> : null}

          <div className="button-row">
            <button
              className="button button--accent"
              disabled={saveDraftContentMutation.isPending}
              onClick={() => {
                try {
                  const parsed = parseDraftContent(draftContentText)
                  setDraftContentError('')
                  saveDraftContentMutation.mutate(parsed)
                } catch (error) {
                  setDraftContentError(getErrorMessage(error))
                }
              }}
              type="button"
            >
              {saveDraftContentMutation.isPending ? 'Saving...' : 'Save draft content'}
            </button>
          </div>

          <div className="meta-list">
            <div className="meta-card" style={{ padding: '0.95rem' }}>
              <strong>Mongo last update</strong>
              <span>
                {draftContentQuery.data?.updated_at
                  ? new Date(draftContentQuery.data.updated_at).toLocaleString()
                  : 'Not saved yet'}
              </span>
            </div>
            <div className="meta-card" style={{ padding: '0.95rem' }}>
              <strong>Suggested keys</strong>
              <span className="mono">overview, learning_objectives, lesson_notes</span>
            </div>
          </div>
        </aside>
      </section>
    </div>
  )
}