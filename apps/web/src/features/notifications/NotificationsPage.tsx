export function NotificationsPage() {
  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Notifications</h1>
        <p className="page-header__description">
          View enrollment updates, publishing events, and platform announcements.
        </p>
      </div>

      <div className="placeholder-page">
        <div className="placeholder-page__icon">&#128276;</div>
        <h2 className="placeholder-page__title">No notifications yet</h2>
        <p className="placeholder-page__description">
          When courses are published, enrollments change status, or platform events occur,
          notifications will appear here.
        </p>
        <div className="placeholder-page__badge">
          <span className="badge badge--warning">Phase 6</span>
        </div>
      </div>
    </div>
  )
}
