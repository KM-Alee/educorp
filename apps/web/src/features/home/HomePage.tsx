import { Link } from 'react-router-dom'

import { useSessionState } from '../../lib/session'
import { defaultRouteForSession } from '../../lib/session'

export function HomePage() {
  const session = useSessionState()

  return (
    <>
      {/* Hero */}
      <section className="hero">
        <h1 className="hero__display">
          Learn without limits
        </h1>
        <p className="hero__subtitle">
          EduCorp is an intelligent course delivery platform with AI-powered learning,
          real-time progress tracking, and industry-recognized certificates.
        </p>
        <div className="hero__actions">
          {session ? (
            <Link className="btn btn--primary" to={defaultRouteForSession(session)}>
              Go to dashboard
            </Link>
          ) : (
            <>
              <Link className="btn btn--primary" to="/register">
                Get started free
              </Link>
              <Link className="btn btn--outline" to="/catalog">
                Browse catalog
              </Link>
            </>
          )}
        </div>

        <div className="hero__stats">
          <div className="hero__stat">
            <div className="hero__stat-value">500+</div>
            <div className="hero__stat-label">Courses</div>
          </div>
          <div className="hero__stat">
            <div className="hero__stat-value">50K+</div>
            <div className="hero__stat-label">Learners</div>
          </div>
          <div className="hero__stat">
            <div className="hero__stat-value">98%</div>
            <div className="hero__stat-label">Completion</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="section">
        <h2 className="section__heading">Everything you need to teach and learn</h2>
        <p className="section__lead">
          A full-stack platform that handles course creation, publishing workflows,
          AI-powered assistance, and analytics — so you can focus on what matters.
        </p>

        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-card__icon">&#9881;</div>
            <h3 className="feature-card__title">Course authoring</h3>
            <p className="feature-card__body">
              Build rich courses with modules, assets, draft content editing, and a structured publishing pipeline with approval workflows.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card__icon">&#9889;</div>
            <h3 className="feature-card__title">AI assistant</h3>
            <p className="feature-card__body">
              Students get a RAG-powered assistant that answers questions from course materials with full citations. Instructors get AI tools for summaries, quizzes, and glossaries.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card__icon">&#9733;</div>
            <h3 className="feature-card__title">Progress tracking</h3>
            <p className="feature-card__body">
              Real-time enrollment tracking, module completion, progress dashboards, and automatic certificate generation when courses are finished.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card__icon">&#128269;</div>
            <h3 className="feature-card__title">Semantic search</h3>
            <p className="feature-card__body">
              Find courses instantly with keyword and semantic vector search across the full catalog. Filter by category, difficulty, and tags.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card__icon">&#128272;</div>
            <h3 className="feature-card__title">Role-based access</h3>
            <p className="feature-card__body">
              Three-tier RBAC: students learn, instructors create, admins govern. JWT authentication with instructor application workflow.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card__icon">&#128200;</div>
            <h3 className="feature-card__title">Publishing pipeline</h3>
            <p className="feature-card__body">
              Temporal-powered publishing workflow: validation, asset extraction, vector embedding, admin review, and activation — all tracked step by step.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section" style={{ textAlign: 'center', paddingBottom: '6rem' }}>
        <h2 className="section__heading" style={{ maxWidth: '640px', margin: '0 auto 1rem' }}>
          Ready to start learning?
        </h2>
        <p className="section__lead" style={{ margin: '0 auto 2rem' }}>
          Create a free account and enroll in your first course today.
        </p>
        <div className="hero__actions">
          {session ? (
            <Link className="btn btn--primary" to={defaultRouteForSession(session)}>
              Go to dashboard
            </Link>
          ) : (
            <>
              <Link className="btn btn--primary" to="/register">
                Create account
              </Link>
              <Link className="btn btn--outline" to="/login">
                Sign in
              </Link>
            </>
          )}
        </div>
      </section>
    </>
  )
}
