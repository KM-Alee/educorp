import { useEffect, useMemo, useRef, useState } from 'react'

import { askAI, createAIEnhancementJob, getAIJob, type AICitation, type AIEnhancementJob } from '../../lib/api'
import { getSession } from '../../lib/session'
import type { ModuleDetail } from '../../lib/api'

const AI_BASE = '/api/v1/ai'

interface Message {
  role: 'user' | 'assistant'
  content: string
  citations?: AICitation[]
}

interface AssistantPanelProps {
  courseId: string
  modules: ModuleDetail[]
}

interface EnhancementPanelProps {
  courseId: string
  modules: ModuleDetail[]
}

export function AIAssistantPanel({ courseId, modules }: AssistantPanelProps) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState('')
  const [selectedModule, setSelectedModule] = useState<string>('')
  const abortRef = useRef<AbortController | null>(null)

  const moduleOptions = useMemo(
    () => modules.map((module) => ({ value: module.id, label: module.title })),
    [modules],
  )

  async function handleAsk() {
    if (!question.trim()) return
    setError('')
    setIsStreaming(true)

    const userMessage: Message = { role: 'user', content: question }
    const assistantMessage: Message = { role: 'assistant', content: '', citations: [] }
    setMessages((prev) => [...prev, userMessage, assistantMessage])
    setQuestion('')

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      await streamAIAnswer(
        {
          courseId,
          question: userMessage.content,
          moduleId: selectedModule || null,
          signal: controller.signal,
          onToken: (token) => {
            setMessages((prev) => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last?.role === 'assistant') {
                next[next.length - 1] = {
                  ...last,
                  content: `${last.content}${token}`,
                }
              }
              return next
            })
          },
          onCitation: (citation) => {
            setMessages((prev) => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last?.role === 'assistant') {
                const existing = last.citations ?? []
                next[next.length - 1] = {
                  ...last,
                  citations: [...existing, citation],
                }
              }
              return next
            })
          },
          onError: (message) => {
            setError(message)
          },
        },
      )
    } catch (err) {
      setError('AI stream ended unexpectedly. Please try again.')
    } finally {
      setIsStreaming(false)
    }
  }

  async function handleAskNonStreaming() {
    if (!question.trim()) return
    setError('')

    const userMessage: Message = { role: 'user', content: question }
    setMessages((prev) => [...prev, userMessage])
    setQuestion('')

    try {
      const result = await askAI({
        course_id: courseId,
        question: userMessage.content,
        module_id: selectedModule || null,
      })

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.answer,
          citations: result.citations,
        },
      ])
    } catch (err) {
      setError('AI assistant failed. Please try again.')
    }
  }

  return (
    <section className="ai-panel">
      <div className="ai-panel__header">
        <div>
          <h2 className="ai-panel__title">Student Assistant</h2>
          <p className="ai-panel__subtitle">
            Ask course-scoped questions and get cited answers.
          </p>
        </div>
      </div>

      <div className="ai-panel__controls">
        <label className="form-field">
          <span className="form-field__label">Scope module (optional)</span>
          <select
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
          <span className="form-field__label">Question</span>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about a concept, a definition, or a lesson topic."
          />
        </label>
        {error ? <div className="message message--error">{error}</div> : null}
        <div className="btn-row">
          <button
            className="btn btn--primary"
            onClick={handleAsk}
            type="button"
            disabled={isStreaming}
          >
            {isStreaming ? 'Streaming...' : 'Ask (stream)'}
          </button>
          <button className="btn btn--ghost" onClick={handleAskNonStreaming} type="button">
            Ask (instant)
          </button>
        </div>
      </div>

      <div className="ai-panel__messages">
        {messages.length === 0 ? (
          <div className="empty">No questions yet. Start by asking about the course.</div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`ai-message ai-message--${message.role}`}
            >
              <div className="ai-message__role">{message.role === 'user' ? 'You' : 'Assistant'}</div>
              <div className="ai-message__content">{message.content}</div>
              {message.citations && message.citations.length > 0 ? (
                <div className="ai-message__citations">
                  {message.citations.map((citation) => (
                    <div key={citation.chunk_id} className="ai-citation">
                      <div className="ai-citation__title">
                        {citation.module_title} · {citation.asset_title}
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
    </section>
  )
}

export function AIEnhancementPanel({ courseId, modules }: EnhancementPanelProps) {
  const [jobType, setJobType] = useState('summary')
  const [scope, setScope] = useState('course')
  const [moduleId, setModuleId] = useState('')
  const [maxLength, setMaxLength] = useState(500)
  const [questionCount, setQuestionCount] = useState(10)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<AIEnhancementJob | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!activeJobId) return

    const interval = window.setInterval(async () => {
      try {
        const job = await getAIJob(activeJobId)
        setJobStatus(job)
        if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(job.status)) {
          window.clearInterval(interval)
          setActiveJobId(null)
        }
      } catch {
        window.clearInterval(interval)
        setActiveJobId(null)
        setError('Could not load job status.')
      }
    }, 3000)

    return () => window.clearInterval(interval)
  }, [activeJobId])

  async function handleCreateJob() {
    setError('')
    try {
      const response = await createAIEnhancementJob({
        course_id: courseId,
        job_type: jobType,
        scope,
        module_id: scope === 'module' ? moduleId : null,
        parameters: {
          max_length: maxLength,
          question_count: questionCount,
        },
      })

      setActiveJobId(response.job_id)
      setJobStatus({
        job_id: response.job_id,
        job_type: jobType,
        status: response.status,
      })
    } catch {
      setError('Failed to queue enhancement job.')
    }
  }

  return (
    <section className="ai-panel ai-panel--accent">
      <div className="ai-panel__header">
        <div>
          <h2 className="ai-panel__title">Instructor Enhancements</h2>
          <p className="ai-panel__subtitle">
            Generate summaries, objectives, quizzes, and glossaries from the current course version.
          </p>
        </div>
      </div>

      <div className="ai-panel__controls">
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
            <select value={scope} onChange={(event) => setScope(event.target.value)}>
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

        {error ? <div className="message message--error">{error}</div> : null}

        <div className="btn-row">
          <button className="btn btn--primary" onClick={handleCreateJob} type="button">
            Generate enhancement
          </button>
        </div>
      </div>

      <div className="ai-panel__result">
        {jobStatus ? (
          <>
            <div className="ai-panel__status">
              <span className="badge badge--accent">{jobStatus.status}</span>
              <span>{jobStatus.job_type}</span>
            </div>
            <pre className="ai-panel__output">
              {jobStatus.result ? JSON.stringify(jobStatus.result, null, 2) : 'Waiting for output...'}
            </pre>
          </>
        ) : (
          <div className="empty">No enhancement jobs yet. Kick off a new one above.</div>
        )}
      </div>
    </section>
  )
}

interface StreamOptions {
  courseId: string
  question: string
  moduleId?: string | null
  signal: AbortSignal
  onToken: (token: string) => void
  onCitation: (citation: AICitation) => void
  onError: (message: string) => void
}

async function streamAIAnswer(options: StreamOptions) {
  const session = getSession()
  if (!session?.accessToken) {
    throw new Error('No session token')
  }

  const params = new URLSearchParams({
    course_id: options.courseId,
    question: options.question,
  })
  if (options.moduleId) {
    params.set('module_id', options.moduleId)
  }

  const response = await fetch(`${AI_BASE}/ask/stream?${params.toString()}`, {
    headers: {
      Accept: 'text/event-stream',
      Authorization: `Bearer ${session.accessToken}`,
    },
    signal: options.signal,
  })

  if (!response.ok || !response.body) {
    throw new Error('Stream failed')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let separatorIndex = buffer.indexOf('\n\n')
    while (separatorIndex >= 0) {
      const rawEvent = buffer.slice(0, separatorIndex).trim()
      buffer = buffer.slice(separatorIndex + 2)

      if (rawEvent) {
        const parsed = parseSseEvent(rawEvent)
        if (parsed.event === 'token') {
          const payload = JSON.parse(parsed.data ?? '{}') as { text?: string }
          if (payload.text) options.onToken(payload.text)
        }
        if (parsed.event === 'citation') {
          const payload = JSON.parse(parsed.data ?? '{}') as AICitation
          options.onCitation(payload)
        }
        if (parsed.event === 'error') {
          const payload = JSON.parse(parsed.data ?? '{}') as { message?: string }
          options.onError(payload.message ?? 'AI error')
        }
      }

      separatorIndex = buffer.indexOf('\n\n')
    }
  }
}

function parseSseEvent(rawEvent: string): { event: string; data: string | null } {
  const lines = rawEvent.split('\n')
  let event = 'message'
  let data = ''

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.replace('event:', '').trim()
    }
    if (line.startsWith('data:')) {
      data += line.replace('data:', '').trim()
    }
  }

  return { event, data: data || null }
}
