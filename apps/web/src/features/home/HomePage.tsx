import { Link } from 'react-router-dom'
import {
  PenLine,
  Sparkles,
  TrendingUp,
  Search,
  ShieldCheck,
  Rocket,
  ArrowRight,
  Play,
  GraduationCap,
  BookOpen,
  Award,
  CheckCircle,
} from 'lucide-react'

import { useSessionState, defaultRouteForSession } from '../../lib/session'

export function HomePage() {
  const session = useSessionState()

  return (
    <>
      {/* ── Hero ── */}
      <section className="lp-hero">

        <div className="lp-hero__inner">

          <h1 className="lp-hero__headline">
            The smarter way<br />
            to <em className="lp-hero__headline-em">teach &amp; learn</em>
          </h1>

          <p className="lp-hero__sub">
            AI-powered course creation, real-time progress analytics,
            and industry-recognised certificates — all in one platform.
          </p>

          <div className="lp-hero__actions">
            {session ? (
              <Link className="btn lp-btn--primary" to={defaultRouteForSession(session)}>
                Go to dashboard <ArrowRight size={18} />
              </Link>
            ) : (
              <>
                <Link className="btn lp-btn--primary" to="/register">
                  Create free account <ArrowRight size={18} />
                </Link>
                <Link className="btn lp-btn--ghost" to="/catalog">
                  <Play size={14} fill="currentColor" /> Browse catalog
                </Link>
              </>
            )}
          </div>

          <div className="lp-hero__stats">
            <div className="lp-hero__stat">
              <span className="lp-hero__stat-val">500+</span>
              <span className="lp-hero__stat-lab">Courses</span>
            </div>
            <div className="lp-hero__stat-sep" />
            <div className="lp-hero__stat">
              <span className="lp-hero__stat-val">50 K+</span>
              <span className="lp-hero__stat-lab">Learners</span>
            </div>
            <div className="lp-hero__stat-sep" />
            <div className="lp-hero__stat">
              <span className="lp-hero__stat-val">98 %</span>
              <span className="lp-hero__stat-lab">Completion rate</span>
            </div>
          </div>
        </div>

        {/* Role strip */}
        <div className="lp-hero__roles">
          <div className="lp-hero__role">
            <GraduationCap size={16} />
            <strong>Students</strong>
            <span>— Enroll, learn at your pace, earn certificates</span>
          </div>
          <div className="lp-hero__role-sep" />
          <div className="lp-hero__role">
            <BookOpen size={16} />
            <strong>Instructors</strong>
            <span>— Create, publish and grow your audience</span>
          </div>
          <div className="lp-hero__role-sep" />
          <div className="lp-hero__role">
            <Award size={16} />
            <strong>Organisations</strong>
            <span>— Track teams, manage access, own analytics</span>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="lp-section lp-section--features">
        <div className="lp-section__inner">
          <p className="lp-overline">Everything in one place</p>
          <h2 className="lp-section__heading">Built for modern education</h2>
          <p className="lp-section__lead">
            A full-stack platform that handles course creation, publishing workflows,
            AI-powered assistance, and analytics — so you can focus on what matters.
          </p>

          <div className="lp-feature-grid">
            <div className="lp-feature-card">
              <div className="lp-feature-card__icon"><PenLine size={22} /></div>
              <h3 className="lp-feature-card__title">Course authoring</h3>
              <p className="lp-feature-card__body">
                Build rich courses with modules, assets, draft editing, and a structured publishing pipeline with approval workflows.
              </p>
            </div>
            <div className="lp-feature-card">
              <div className="lp-feature-card__icon"><Sparkles size={22} /></div>
              <h3 className="lp-feature-card__title">AI assistant</h3>
              <p className="lp-feature-card__body">
                RAG-powered Q&amp;A with citations for students. AI summaries, quizzes, and glossary generation for instructors.
              </p>
            </div>
            <div className="lp-feature-card">
              <div className="lp-feature-card__icon"><TrendingUp size={22} /></div>
              <h3 className="lp-feature-card__title">Progress tracking</h3>
              <p className="lp-feature-card__body">
                Real-time enrollment tracking, module completion dashboards, and automatic certificate generation.
              </p>
            </div>
            <div className="lp-feature-card">
              <div className="lp-feature-card__icon"><Search size={22} /></div>
              <h3 className="lp-feature-card__title">Semantic search</h3>
              <p className="lp-feature-card__body">
                Keyword + vector search across the full catalog. Filter by category, difficulty, tags, and more.
              </p>
            </div>
            <div className="lp-feature-card">
              <div className="lp-feature-card__icon"><ShieldCheck size={22} /></div>
              <h3 className="lp-feature-card__title">Role-based access</h3>
              <p className="lp-feature-card__body">
                Three-tier RBAC: students learn, instructors create, admins govern. JWT auth with application workflow.
              </p>
            </div>
            <div className="lp-feature-card">
              <div className="lp-feature-card__icon"><Rocket size={22} /></div>
              <h3 className="lp-feature-card__title">Publishing pipeline</h3>
              <p className="lp-feature-card__body">
                Validation, asset extraction, vector embedding, admin review, and activation — all automated step by step.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="lp-cta">
        <div className="lp-cta__inner">
          <h2 className="lp-cta__heading">Ready to start learning?</h2>
          <p className="lp-cta__sub">
            Join 50,000+ learners already on EduCorp.<br />
            Create a free account — no credit card required.
          </p>
          <ul className="lp-cta__checklist">
            <li><CheckCircle size={16} /> Free to sign up</li>
            <li><CheckCircle size={16} /> 500+ courses across all levels</li>
            <li><CheckCircle size={16} /> Earn verified certificates</li>
          </ul>
          <div className="lp-cta__actions">
            {session ? (
              <Link className="btn lp-btn--cta" to={defaultRouteForSession(session)}>
                Go to dashboard <ArrowRight size={18} />
              </Link>
            ) : (
              <>
                <Link className="btn lp-btn--cta" to="/register">
                  Get started free <ArrowRight size={18} />
                </Link>
                <Link className="btn lp-btn--cta-ghost" to="/login">
                  Already have an account? Sign in
                </Link>
              </>
            )}
          </div>
        </div>
      </section>
    </>
  )
}
