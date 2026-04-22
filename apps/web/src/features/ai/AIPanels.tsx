import { useEffect, useMemo, useRef, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CornerDownLeft, SendHorizontal, Sparkles } from 'lucide-react'

import {
  askAI,
  askAIClarify,
  cancelAIJob,
  createAIEnhancementJob,
  getAIJob,
  listAssets,
  listAIJobs,
  streamAIAssistant,
  streamAIEnhancement,
  type AICitation,
  type AssetOut,
  type AIEnhancementJob,
  type EventStreamMessage,
  type ModuleDetail,
} from '../../lib/api'
import { getErrorMessage } from '../../lib/types'
import { MarkdownContent } from '../../components/content/MarkdownContent'

interface Message {
  role: 'user' | 'assistant'
  content: string
  citations?: AICitation[]
}

interface AssistantPanelProps {
  courseId: string
  modules: ModuleDetail[]
  canAsk?: boolean
  disabledMessage?: string
}

interface EnhancementPanelProps {
  courseId: string
  modules: ModuleDetail[]
  canEnhance?: boolean
  disabledMessage?: string
}

function statusBadgeClass(status: string): string {
  const normalized = status.toUpperCase()
  if (normalized === 'COMPLETED') return 'badge badge--success'
  if (normalized === 'FAILED' || normalized === 'CANCELLED') return 'badge badge--danger'
  if (normalized === 'RUNNING') return 'badge badge--accent'
  return 'badge badge--warning'
}

function parseJson<T>(data: string | null): T | null {
  if (!data) {
    return null
  }

  try {
    return JSON.parse(data) as T
  } catch {
    return null
  }
}

function renderJobOutput(job: AIEnhancementJob | null): string {
  if (job?.error?.message) {
    return job.error.message
  }

  if (!job?.result) {
    return 'Waiting for output...'
  }

  const content = job.result.content
  if (typeof content === 'string' && content.trim()) {
    return content
  }

  return JSON.stringify(job.result, null, 2)
}

function hasRichJobOutput(job: AIEnhancementJob | null): boolean {
  return typeof job?.result?.content === 'string' && Boolean(job.result.content.trim())
}

export function AIAssistantPanel({
  courseId,
  modules,
  canAsk = true,
  disabledMessage,
}: AssistantPanelProps) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState('')
  const [selectedModule, setSelectedModule] = useState<string>('')
  const [selectedAsset, setSelectedAsset] = useState<string>('')
  const [pendingClarificationQueryId, setPendingClarificationQueryId] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const messagesViewportRef = useRef<HTMLDivElement | null>(null)
  const clarificationPendingRef = useRef(false)
  const starterQuestions = useMemo(
    () => [
      'Summarize the main takeaways from this course so far.',
      'Explain the hardest concept in simpler terms with examples.',
      'Turn this lesson into a short study checklist.',
    ],
    [],
  )

  const moduleOptions = useMemo(
    () => modules.map((module) => ({ value: module.id, label: module.title })),
    [modules],
  )
  const assetsQuery = useQuery({
    queryKey: ['ai-assistant-assets', courseId, selectedModule],
    queryFn: () => listAssets(courseId, selectedModule),
    enabled: canAsk && Boolean(selectedModule),
  })
  const assetOptions = useMemo(
    () => (assetsQuery.data ?? []).map((asset: AssetOut) => ({ value: asset.id, label: asset.title })),
    [assetsQuery.data],
  )

  useEffect(() => {
    setSelectedAsset('')
  }, [selectedModule])

  useEffect(() => {
    const viewport = messagesViewportRef.current
    if (!viewport) {
      return
    }

    viewport.scrollTo({ top: viewport.scrollHeight, behavior: 'smooth' })
  }, [messages, isStreaming])

  const selectedModuleLabel = moduleOptions.find((option) => option.value === selectedModule)?.label ?? 'All modules'
  const selectedAssetLabel = assetOptions.find((option) => option.value === selectedAsset)?.label ?? 'All files'

  function appendAssistantText(text: string) {
    setMessages((prev) => {
      const next = [...prev]
      const last = next[next.length - 1]
      if (last?.role === 'assistant') {
        next[next.length - 1] = {
          ...last,
          content: `${last.content}${text}`,
        }
      } else {
        next.push({ role: 'assistant', content: text, citations: [] })
      }
      return next
    })
  }

  function appendCitation(citation: AICitation) {
    setMessages((prev) => {
      const next = [...prev]
      const last = next[next.length - 1]
      if (last?.role === 'assistant') {
        next[next.length - 1] = {
          ...last,
          citations: [...(last.citations ?? []), citation],
        }
      } else {
        next.push({ role: 'assistant', content: '', citations: [citation] })
      }
      return next
    })
  }

  async function handleAskNonStreaming(promptOverride?: string) {
    const prompt = (promptOverride ?? question).trim()
    if (!canAsk || !prompt) {
      return
    }

    setError('')
    const isClarification = Boolean(pendingClarificationQueryId)
    const userMessage: Message = { role: 'user', content: prompt }
    setMessages((prev) => [...prev, userMessage])
    setQuestion('')

    try {
      const result = isClarification && pendingClarificationQueryId
        ? await askAIClarify({
            course_id: courseId,
            original_query_id: pendingClarificationQueryId,
            clarification: prompt,
          })
        : await askAI({
            course_id: courseId,
            question: prompt,
            module_id: selectedModule || null,
            asset_id: selectedAsset || null,
          })

      setPendingClarificationQueryId(
        result.response_type === 'clarification' ? result.query_id : null,
      )
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.answer,
          citations: result.citations,
        },
      ])
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleAsk() {
    const prompt = question.trim()
    if (!canAsk || !prompt) {
      return
    }

    if (pendingClarificationQueryId) {
      await handleAskNonStreaming(prompt)
      return
    }

    setError('')
    setIsStreaming(true)
    setPendingClarificationQueryId(null)
    clarificationPendingRef.current = false

    const userMessage: Message = { role: 'user', content: prompt }
    const assistantMessage: Message = { role: 'assistant', content: '', citations: [] }
    setMessages((prev) => [...prev, userMessage, assistantMessage])
    setQuestion('')

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      await streamAIAssistant({
        course_id: courseId,
        question: userMessage.content,
        module_id: selectedModule || null,
        asset_id: selectedAsset || null,
        signal: controller.signal,
        onEvent: (event: EventStreamMessage) => {
          if (event.event === 'token') {
            const payload = parseJson<{ text?: string }>(event.data)
            if (payload?.text) {
              appendAssistantText(payload.text)
            }
            return
          }

          if (event.event === 'citation') {
            const payload = parseJson<AICitation>(event.data)
            if (payload) {
              appendCitation(payload)
            }
            return
          }

          if (event.event === 'clarification') {
            const payload = parseJson<{ message?: string }>(event.data)
            clarificationPendingRef.current = true
            appendAssistantText(payload?.message ?? 'Please clarify your question.')
            return
          }

          if (event.event === 'refusal') {
            const payload = parseJson<{ message?: string }>(event.data)
            appendAssistantText(payload?.message ?? 'The assistant could not answer from course materials.')
            return
          }

          if (event.event === 'error') {
            const payload = parseJson<{ message?: string }>(event.data)
            setError(payload?.message ?? 'AI assistant failed.')
            return
          }

          if (event.event === 'done') {
            const payload = parseJson<{ query_id?: string }>(event.data)
            if (payload?.query_id && clarificationPendingRef.current) {
              setPendingClarificationQueryId(payload.query_id)
            }
          }
        },
      })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <section className="ai-panel ai-panel--assistant">
      <div className="ai-panel__header">
        <div>
          <h2 className="ai-panel__title">Student Assistant</h2>
          <p className="ai-panel__subtitle">
            Ask in natural language, get cited answers in markdown, and stay inside the current
            course context.
          </p>
        </div>
        <div className="ai-panel__header-badge">
          <Sparkles size={14} />
          Course grounded
        </div>
      </div>

      {!canAsk && disabledMessage ? <div className="message message--warning">{disabledMessage}</div> : null}

      <div className="ai-assistant-layout">
        <aside className="ai-assistant-layout__sidebar">
          <div className="ai-assistant-card ai-assistant-card--scope">
            <div className="ai-assistant-card__header">
              <h3 className="ai-assistant-card__title">Ask with context</h3>
              <p className="ai-assistant-card__copy">Focus answers on a lesson or specific file when you need tighter grounding.</p>
            </div>

            <div className="form-row">
              <label className="form-field">
                <span className="form-field__label">Scope module</span>
                <select
                  disabled={!canAsk}
                  value={selectedModule}
                  onChange={(event) => setSelectedModule(event.target.value)}
                >
                  <option value="">All modules</option>
                  {moduleOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span className="form-field__label">Specific file</span>
                <select
                  disabled={!canAsk || !selectedModule || assetsQuery.isLoading}
                  value={selectedAsset}
                  onChange={(event) => setSelectedAsset(event.target.value)}
                >
                  <option value="">All files</option>
                  {assetOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="ai-context-summary">
              <div className="ai-context-summary__item">
                <span className="ai-context-summary__label">Module</span>
                <strong>{selectedModuleLabel}</strong>
              </div>
              <div className="ai-context-summary__item">
                <span className="ai-context-summary__label">Source</span>
                <strong>{selectedAssetLabel}</strong>
              </div>
            </div>

            {selectedModule && assetsQuery.isError ? (
              <div className="message message--error">{getErrorMessage(assetsQuery.error)}</div>
            ) : null}
            {selectedAsset ? (
              <div className="message message--success">
                The assistant will use the full indexed contents of the selected file.
              </div>
            ) : null}
          </div>

          <div className="ai-assistant-card">
            <div className="ai-assistant-card__header">
              <h3 className="ai-assistant-card__title">Prompt starters</h3>
              <p className="ai-assistant-card__copy">Jump in with structured study prompts instead of starting from a blank box.</p>
            </div>
            <div className="ai-panel__suggestions ai-panel__suggestions--stacked">
              {starterQuestions.map((prompt) => (
                <button
                  key={prompt}
                  className="ai-panel__suggestion ai-panel__suggestion--block"
                  onClick={() => setQuestion(prompt)}
                  type="button"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <div className="ai-chat">
          <div className="ai-chat__header">
            <div>
              <p className="ai-chat__eyebrow">Conversation</p>
              <h3 className="ai-chat__title">
                {pendingClarificationQueryId ? 'Clarification needed' : 'Scrollable study chat'}
              </h3>
            </div>
            <div className="ai-chat__status">
              <span className={`badge${isStreaming ? ' badge--accent' : ''}`}>
                {isStreaming ? 'Streaming' : messages.length ? `${messages.length} messages` : 'Ready'}
              </span>
            </div>
          </div>

          <div className="ai-chat__viewport" ref={messagesViewportRef}>
            {messages.length === 0 ? (
              <div className="ai-chat__empty">
                <div className="ai-chat__empty-title">No questions yet</div>
                <div className="ai-chat__empty-copy">
                  Start with a study prompt, scope the assistant to a lesson, or ask your own question.
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`ai-message ai-message--${message.role}`}
                >
                  <div className="ai-message__role">{message.role === 'user' ? 'You' : 'Assistant'}</div>
                  {message.role === 'assistant' ? (
                    <MarkdownContent
                      className="ai-message__content ai-message__content--assistant"
                      content={message.content || 'Working on it...'}
                    />
                  ) : (
                    <div className="ai-message__content ai-message__content--user">{message.content}</div>
                  )}
                  {message.citations && message.citations.length > 0 ? (
                    <div className="ai-message__citations">
                      {message.citations.map((citation) => (
                        <div key={`${citation.chunk_id}-${citation.page_number ?? 'none'}`} className="ai-citation">
                          <div className="ai-citation__title">
                            {citation.module_title || 'Course material'} · {citation.asset_title || 'Source'}
                            {citation.page_number ? ` · p. ${citation.page_number}` : ''}
                          </div>
                          <div className="ai-citation__snippet">{citation.text_snippet}</div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </div>

          <div className="ai-chat__composer">
            <label className="form-field">
              <span className="form-field__label">
                {pendingClarificationQueryId ? 'Clarification' : 'Question'}
              </span>
              <textarea
                disabled={!canAsk}
                value={question}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void handleAsk()
                  }
                }}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={
                  pendingClarificationQueryId
                    ? 'Add the missing detail the assistant asked for.'
                    : 'Ask about a concept, definition, or lesson topic.'
                }
              />
            </label>
            {error ? <div className="message message--error">{error}</div> : null}
            <div className="btn-row ai-panel__composer-actions">
              <div className="ai-panel__composer-hint">
                <CornerDownLeft size={13} />
                Press Enter to send, Shift+Enter for a new line.
              </div>
              <div className="ai-chat__composer-buttons">
                <button
                  className="btn btn--primary"
                  onClick={handleAsk}
                  type="button"
                  disabled={isStreaming || !canAsk}
                >
                  <SendHorizontal size={14} />
                  {isStreaming ? 'Streaming...' : pendingClarificationQueryId ? 'Clarify' : 'Ask (stream)'}
                </button>
                <button
                  className="btn btn--ghost"
                  onClick={() => handleAskNonStreaming()}
                  type="button"
                  disabled={!canAsk}
                >
                  {pendingClarificationQueryId ? 'Clarify (instant)' : 'Ask (instant)'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export function AIEnhancementPanel({ courseId, modules, canEnhance = true, disabledMessage }: EnhancementPanelProps) {
  const queryClient = useQueryClient()
  const [jobType, setJobType] = useState('summary')
  const [scope, setScope] = useState('course')
  const [moduleId, setModuleId] = useState('')
  const [maxLength, setMaxLength] = useState(500)
  const [questionCount, setQuestionCount] = useState(10)
  const [difficulty, setDifficulty] = useState('intermediate')
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<AIEnhancementJob | null>(null)
  const [streamedOutput, setStreamedOutput] = useState('')
  const [streamedCitations, setStreamedCitations] = useState<AICitation[]>([])
  const [error, setError] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const streamAbortRef = useRef<AbortController | null>(null)

  const jobsQuery = useQuery({
    queryKey: ['ai-jobs', courseId],
    queryFn: () => listAIJobs({ course_id: courseId, page: 1, page_size: 10 }),
  })

  useEffect(() => {
    if (!activeJobId) return

    const interval = window.setInterval(async () => {
      try {
        const job = await getAIJob(activeJobId)
        setJobStatus(job)
        if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(job.status)) {
          window.clearInterval(interval)
          setActiveJobId(null)
          await queryClient.invalidateQueries({ queryKey: ['ai-jobs', courseId] })
        }
      } catch (err) {
        window.clearInterval(interval)
        setActiveJobId(null)
        setError(getErrorMessage(err))
      }
    }, 3000)

    return () => window.clearInterval(interval)
  }, [activeJobId, courseId, queryClient])

  const createJobMutation = useMutation({
    mutationFn: () =>
      createAIEnhancementJob({
        course_id: courseId,
        job_type: jobType,
        scope,
        module_id: scope === 'module' ? moduleId : null,
        parameters: {
          max_length: maxLength,
          question_count: questionCount,
          difficulty,
        },
      }),
    onSuccess: async (response) => {
      setActiveJobId(response.job_id)
      setJobStatus({
        job_id: response.job_id,
        job_type: jobType,
        status: response.status,
        input: {
          scope,
          module_id: scope === 'module' ? moduleId : null,
          parameters: { max_length: maxLength, question_count: questionCount, difficulty },
        },
      })
      await queryClient.invalidateQueries({ queryKey: ['ai-jobs', courseId] })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => cancelAIJob(jobId),
    onSuccess: async (_, jobId) => {
      if (activeJobId === jobId) {
        setActiveJobId(null)
      }
      setJobStatus((prev) =>
        prev && prev.job_id === jobId ? { ...prev, status: 'CANCELLED' } : prev,
      )
      await queryClient.invalidateQueries({ queryKey: ['ai-jobs', courseId] })
    },
  })

  function validateModuleSelection(): boolean {
    if (scope !== 'module') {
      return true
    }
    if (moduleId) {
      return true
    }
    setError('Select a module before running a module-scoped enhancement job.')
    return false
  }

  async function handleCreateJob() {
    setError('')
    if (!validateModuleSelection()) {
      return
    }

    try {
      await createJobMutation.mutateAsync()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleStreamJob() {
    setError('')
    if (!validateModuleSelection()) {
      return
    }

    streamAbortRef.current?.abort()
    const controller = new AbortController()
    streamAbortRef.current = controller

    setIsStreaming(true)
    setStreamedOutput('')
    setStreamedCitations([])

    try {
      await streamAIEnhancement({
        course_id: courseId,
        job_type: jobType,
        scope,
        module_id: scope === 'module' ? moduleId : null,
        max_length: maxLength,
        question_count: questionCount,
        difficulty,
        signal: controller.signal,
        onEvent: (event) => {
          if (event.event === 'token') {
            const payload = parseJson<{ text?: string }>(event.data)
            if (payload?.text) {
              setStreamedOutput((prev) => `${prev}${payload.text}`)
            }
            return
          }

          if (event.event === 'citation') {
            const payload = parseJson<AICitation>(event.data)
            if (payload) {
              setStreamedCitations((prev) => [...prev, payload])
            }
            return
          }

          if (event.event === 'error') {
            const payload = parseJson<{ message?: string }>(event.data)
            setError(payload?.message ?? 'Enhancement stream failed.')
          }
        },
      })
      await queryClient.invalidateQueries({ queryKey: ['ai-jobs', courseId] })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <section className="ai-panel ai-panel--accent ai-workbench-panel">
      <div className="ai-panel__header">
        <div>
          <h2 className="ai-panel__title">Instructor Enhancements</h2>
          <p className="ai-panel__subtitle">
            Generate summaries, objectives, quizzes, and glossaries from the current course version.
          </p>
        </div>
        <div className="ai-panel__header-badge">Teacher workspace</div>
      </div>

      {!canEnhance && disabledMessage ? <div className="message message--warning">{disabledMessage}</div> : null}

      <div className="ai-workbench">
        <div className="ai-workbench__controls">
          <div className="ai-assistant-card ai-assistant-card--scope">
            <div className="ai-assistant-card__header">
              <h3 className="ai-assistant-card__title">Configure output</h3>
              <p className="ai-assistant-card__copy">Set the job type, scope, and output length before you queue or preview.</p>
            </div>

            <div className="form-row">
              <label className="form-field">
                <span className="form-field__label">Job type</span>
                <select value={jobType} onChange={(event) => setJobType(event.target.value)}>
                  <option value="summary">Summary</option>
                  <option value="objectives">Objectives</option>
                  <option value="quiz">Quiz</option>
                  <option value="glossary">Glossary</option>
                </select>
              </label>
              <label className="form-field">
                <span className="form-field__label">Scope</span>
                <select
                  value={scope}
                  onChange={(event) => {
                    const nextScope = event.target.value
                    setScope(nextScope)
                    if (nextScope !== 'module') {
                      setModuleId('')
                    }
                  }}
                >
                  <option value="course">Course</option>
                  <option value="module">Module</option>
                </select>
              </label>
            </div>

            {scope === 'module' ? (
              <label className="form-field">
                <span className="form-field__label">Module</span>
                <select value={moduleId} onChange={(event) => setModuleId(event.target.value)}>
                  <option value="">Select a module</option>
                  {modules.map((module) => (
                    <option key={module.id} value={module.id}>
                      {module.title}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <div className="form-row">
              <label className="form-field">
                <span className="form-field__label">Max length</span>
                <input
                  type="number"
                  value={maxLength}
                  onChange={(event) => setMaxLength(Number(event.target.value))}
                  min={100}
                  max={2000}
                />
              </label>
              <label className="form-field">
                <span className="form-field__label">Quiz questions</span>
                <input
                  type="number"
                  value={questionCount}
                  onChange={(event) => setQuestionCount(Number(event.target.value))}
                  min={5}
                  max={30}
                  disabled={jobType !== 'quiz'}
                />
              </label>
            </div>

            <label className="form-field">
              <span className="form-field__label">Difficulty</span>
              <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>

            <div className="ai-context-summary">
              <div className="ai-context-summary__item">
                <span className="ai-context-summary__label">Output</span>
                <strong>{jobType}</strong>
              </div>
              <div className="ai-context-summary__item">
                <span className="ai-context-summary__label">Target</span>
                <strong>{scope === 'module' ? (modules.find((module) => module.id === moduleId)?.title ?? 'Select a module') : 'Full course'}</strong>
              </div>
            </div>

            {error ? <div className="message message--error">{error}</div> : null}

            <div className="btn-row ai-chat__composer-buttons">
              <button
                className="btn btn--primary"
                onClick={handleCreateJob}
                type="button"
                disabled={createJobMutation.isPending || !canEnhance}
              >
                {createJobMutation.isPending ? 'Queueing...' : 'Queue enhancement'}
              </button>
              <button
                className="btn btn--ghost"
                onClick={handleStreamJob}
                type="button"
                disabled={isStreaming || !canEnhance}
              >
                {isStreaming ? 'Streaming...' : 'Preview stream'}
              </button>
              {jobStatus?.job_id && ['QUEUED', 'RUNNING'].includes(jobStatus.status) ? (
                <button
                  className="btn btn--danger"
                  onClick={() => cancelMutation.mutate(jobStatus.job_id)}
                  type="button"
                  disabled={cancelMutation.isPending}
                >
                  {cancelMutation.isPending ? 'Cancelling...' : 'Cancel active job'}
                </button>
              ) : null}
            </div>
          </div>
        </div>

        <div className="ai-workbench__stage">
          <div className="ai-panel__result ai-panel__result--stage">
            <div className="ai-panel__status">
              <span className={jobStatus ? statusBadgeClass(jobStatus.status) : 'badge'}>
                {jobStatus?.status ?? 'READY'}
              </span>
              <span>{jobStatus?.job_type ?? 'Latest queued output'}</span>
              {jobStatus?.error?.message ? <span>{jobStatus.error.message}</span> : null}
            </div>
            {jobStatus ? (
              hasRichJobOutput(jobStatus) ? (
                <div className="ai-panel__output ai-panel__output--markdown">
                  <MarkdownContent content={renderJobOutput(jobStatus)} />
                </div>
              ) : (
                <pre className="ai-panel__output">{renderJobOutput(jobStatus)}</pre>
              )
            ) : (
              <div className="empty">No enhancement jobs yet. Kick off a new one from the control column.</div>
            )}
          </div>

          {isStreaming || streamedOutput ? (
            <div className="ai-panel__result ai-panel__result--stage">
              <div className="ai-panel__status">
                <span className="badge badge--accent">STREAM</span>
                <span>{jobType}</span>
              </div>
              <div className="ai-panel__output ai-panel__output--markdown">
                <MarkdownContent content={streamedOutput || 'Waiting for streamed tokens...'} />
              </div>
              {streamedCitations.length ? (
                <div className="ai-panel__messages ai-panel__messages--citations">
                  {streamedCitations.map((citation) => (
                    <div className="ai-citation" key={`${citation.chunk_id}-${citation.page_number ?? 'none'}`}>
                      <div className="ai-citation__title">
                        {citation.module_title || 'Course material'} · {citation.asset_title || 'Source'}
                        {citation.page_number ? ` · p. ${citation.page_number}` : ''}
                      </div>
                      <div className="ai-citation__snippet">{citation.text_snippet}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      <div className="card">
        <div className="card__header">
          <h3 className="card__title">Recent jobs</h3>
          <p className="card__description">Recent enhancement history for this course.</p>
        </div>

        {jobsQuery.isError ? (
          <div className="message message--error">{getErrorMessage(jobsQuery.error)}</div>
        ) : null}

        <div className="course-list">
          {jobsQuery.data?.items.map((job) => (
            <div className="course-item" key={job.job_id}>
              <div className="course-item__info">
                <div className="course-item__title">{job.job_type}</div>
                <div className="course-item__meta">
                  {job.input?.scope ?? 'course'}
                  {job.input?.module_id ? ` · ${job.input.module_id}` : ''}
                  {job.created_at ? ` · ${new Date(job.created_at).toLocaleString()}` : ''}
                </div>
              </div>
              <div className="course-item__badges">
                <span className={statusBadgeClass(job.status)}>{job.status}</span>
                {['QUEUED', 'RUNNING'].includes(job.status) ? (
                  <button
                    className="btn btn--sm btn--ghost"
                    onClick={() => cancelMutation.mutate(job.job_id)}
                    type="button"
                    disabled={cancelMutation.isPending}
                  >
                    Cancel
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        {!jobsQuery.isLoading && !jobsQuery.data?.items.length ? (
          <div className="empty">No job history for this course yet.</div>
        ) : null}
      </div>
    </section>
  )
}
