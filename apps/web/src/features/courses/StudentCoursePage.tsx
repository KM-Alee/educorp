import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import { getCourse, listModules, type ModuleDetail } from '../../lib/api'
import { useSessionState } from '../../lib/session'
import { AIAssistantPanel, AIEnhancementPanel } from '../ai/AIPanels'
import { getErrorMessage } from '../../lib/types'

export function StudentCoursePage() {
  const { courseId = '' } = useParams()
  const session = useSessionState()
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
          <div className="message message--error">
            {getErrorMessage(courseQuery.error)}
          </div>
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

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">{course.title}</h1>
        <p className="page-header__description">{course.description}</p>
      </div>

      <div className="card">
        <div className="meta-list">
          <div className="meta-item">
            <div className="meta-item__label">Category</div>
            <div className="meta-item__value">{course.category || 'N/A'}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">Difficulty</div>
            <div className="meta-item__value">{course.difficulty || 'N/A'}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">Duration</div>
            <div className="meta-item__value">{course.estimated_duration || 'N/A'}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">Status</div>
            <div className="meta-item__value">
              <span className="badge badge--accent">READY</span>
            </div>
          </div>
        </div>
      </div>

      <div className="page-stack">
        <AIAssistantPanel courseId={courseId} modules={modules} />
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
            <h2 className="card__title">Course modules</h2>
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
