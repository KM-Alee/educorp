import { afterEach, describe, expect, it, vi } from 'vitest'

import { clearSession, getSession, setSession, subscribe } from './session'

describe('session store', () => {
  afterEach(() => {
    clearSession()
  })

  it('persists and clears session state', () => {
    setSession({
      accessToken: 'access',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'user-id',
        email: 'user@example.com',
        roles: ['student'],
      },
    })

    expect(getSession()?.user.email).toBe('user@example.com')

    clearSession()

    expect(getSession()).toBeNull()
  })

  it('notifies subscribers when the session changes', () => {
    const listener = vi.fn()
    const unsubscribe = subscribe(listener)

    setSession({
      accessToken: 'access',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'user-id',
        email: 'user@example.com',
        roles: ['student'],
      },
    })
    clearSession()

    unsubscribe()

    expect(listener).toHaveBeenCalledTimes(2)
  })
})