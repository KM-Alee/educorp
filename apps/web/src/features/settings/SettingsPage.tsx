export function SettingsPage() {
  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Settings</h1>
        <p className="page-header__description">
          Manage account preferences, notification settings, and platform configuration.
        </p>
      </div>

      <div className="page-columns">
        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Notification preferences</h2>
            <p className="card__description">Control which notifications you receive.</p>
          </div>

          <div className="form-stack">
            <label className="form-field--inline form-field">
              <input type="checkbox" defaultChecked />
              <span className="form-field__label">Email notifications for enrollment changes</span>
            </label>
            <label className="form-field--inline form-field">
              <input type="checkbox" defaultChecked />
              <span className="form-field__label">Publishing pipeline status updates</span>
            </label>
            <label className="form-field--inline form-field">
              <input type="checkbox" defaultChecked />
              <span className="form-field__label">Certificate issuance alerts</span>
            </label>
            <label className="form-field--inline form-field">
              <input type="checkbox" />
              <span className="form-field__label">Platform announcements</span>
            </label>
          </div>

          <div className="placeholder-page__badge" style={{ marginTop: '1.5rem' }}>
            <span className="badge badge--warning">Phase 6 — preferences not persisted yet</span>
          </div>
        </div>

        <div className="card">
          <div className="card__header">
            <h2 className="card__title">Display</h2>
            <p className="card__description">Theme and appearance settings.</p>
          </div>

          <div className="meta-list">
            <div className="meta-item">
              <div className="meta-item__label">Theme</div>
              <div className="meta-item__value">Cream (default)</div>
            </div>
            <div className="meta-item">
              <div className="meta-item__label">Language</div>
              <div className="meta-item__value">English</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
