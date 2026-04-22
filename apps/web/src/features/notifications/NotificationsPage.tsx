import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../lib/api'
import { getErrorMessage } from '../../lib/types'

export function NotificationsPage() {
  const queryClient = useQueryClient()
  const notificationsQuery = useQuery({
    queryKey: ['notifications'],
    queryFn: () => listNotifications({ limit: 50 }),
  })

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  return (
    <div className="page-stack">
      <div className="page-header">
        <h1 className="page-header__title">Notifications</h1>
        <p className="page-header__description">
          View enrollment updates, publishing events, and platform announcements.
        </p>
      </div>

      <div className="card">
        <div className="card__header-row">
          <div>
            <h2 className="card__title">Inbox</h2>
            <p className="card__description">Recent in-app notifications for your account.</p>
          </div>
          <button
            className="btn btn--sm btn--secondary"
            disabled={markAllMutation.isPending || !notificationsQuery.data?.some((item) => !item.is_read)}
            onClick={() => markAllMutation.mutate()}
            type="button"
          >
            {markAllMutation.isPending ? 'Marking...' : 'Mark all read'}
          </button>
        </div>

        {notificationsQuery.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(notificationsQuery.error)}
          </div>
        ) : null}

        {markReadMutation.isError || markAllMutation.isError ? (
          <div className="message message--error" role="alert">
            {getErrorMessage(markReadMutation.error ?? markAllMutation.error)}
          </div>
        ) : null}

        <div className="course-list">
          {notificationsQuery.data?.map((notification) => (
            <div className="course-item" key={notification.id}>
              <div className="course-item__info">
                <div className="course-item__title">{notification.title}</div>
                <div className="course-item__meta">{notification.message}</div>
                <div className="table__secondary">{new Date(notification.created_at).toLocaleString()}</div>
              </div>
              <div className="course-item__badges">
                <span className={`badge ${notification.is_read ? '' : 'badge--accent'}`}>
                  {notification.is_read ? 'Read' : 'Unread'}
                </span>
                {!notification.is_read ? (
                  <button
                    className="btn btn--sm btn--ghost"
                    disabled={markReadMutation.isPending}
                    onClick={() => markReadMutation.mutate(notification.id)}
                    type="button"
                  >
                    Mark read
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        {!notificationsQuery.isLoading && !notificationsQuery.data?.length ? (
          <div className="empty">No notifications yet.</div>
        ) : null}
      </div>
    </div>
  )
}
