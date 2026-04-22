import { useState } from 'react'

import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { searchCourses, type CourseSearchItem } from '../../lib/api'
import { getErrorMessage } from '../../lib/types'
import { useSessionState } from '../../lib/session'

function ResultCard({ course }: { course: CourseSearchItem }) {
  const session = useSessionState()
  const to = session ? `/app/catalog/${course.course_id}` : `/catalog/${course.course_id}`
  return (
    <Link className="course-item" to={to}>
      <div className="course-item__info">
        <div className="course-item__title">{course.title}</div>
        <div className="course-item__meta">{course.short_description || 'No description'}</div>
      </div>
      <div className="course-item__badges">
        {course.category ? <span className="badge">{course.category}</span> : null}
        {course.difficulty ? <span className="badge">{course.difficulty}</span> : null}
        <span className="badge badge--accent">READY</span>
      </div>
    </Link>
  )
}

export function CatalogPage() {
  const [category, setCategory] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [tags, setTags] = useState('')

  const catalogQuery = useQuery({
    queryKey: ['catalog', category, difficulty, tags],
    queryFn: () =>
      searchCourses({
        category: category || undefined,
        difficulty: difficulty || undefined,
        tags: tags || undefined,
      }),
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Course catalog</h1>
        <p className="page-header__description">Browse READY courses in the catalog.</p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '0.75rem' }}>
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
          <label className="form-field">
            <span className="form-field__label">Tags</span>
            <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="python, ml" />
          </label>
        </div>

        {catalogQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(catalogQuery.error)}
          </div>
        ) : null}

        <div className="course-list">
          {catalogQuery.data?.data.map((course) => (
            <ResultCard course={course} key={course.course_id} />
          ))}
        </div>

        {!catalogQuery.isLoading && !catalogQuery.data?.data.length ? (
          <div className="empty">No courses match the current filter.</div>
        ) : null}
      </div>
    </div>
  )
}

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [tags, setTags] = useState('')

  const searchQuery = useQuery({
    queryKey: ['search', query, category, difficulty, tags],
    queryFn: () =>
      searchCourses({
        q: query || undefined,
        category: category || undefined,
        difficulty: difficulty || undefined,
        tags: tags || undefined,
      }),
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Search</h1>
        <p className="page-header__description">Keyword search over READY courses.</p>
      </div>

      <div className="card">
        <div className="filter-bar" style={{ marginBottom: '0.75rem' }}>
          <label className="form-field">
            <span className="form-field__label">Query</span>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="machine learning" />
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
          <label className="form-field">
            <span className="form-field__label">Tags</span>
            <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="python, ml" />
          </label>
        </div>

        {searchQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(searchQuery.error)}
          </div>
        ) : null}

        <div className="course-list">
          {searchQuery.data?.data.map((course) => (
            <ResultCard course={course} key={course.course_id} />
          ))}
        </div>

        {!searchQuery.isLoading && !searchQuery.data?.data.length ? (
          <div className="empty">No search results yet.</div>
        ) : null}
      </div>
    </div>
  )
}
