import { afterEach, describe, expect, it, vi } from 'vitest'

import { getProfile, registerUser } from './api'
import { clearSession, getSession, setSession } from './session'
import { ApiError } from './types'

function success<T>(data: T): Response {
  return new Response(
    JSON.stringify({
      data,
      meta: {
        correlation_id: 'corr-id',
        timestamp: '2026-04-13T00:00:00Z',
      },
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    },
  )
}

function error(status: number, message: string): Response {
  return new Response(
    JSON.stringify({
      error: {
        code: 'VALIDATION_ERROR',
        message,
        correlation_id: 'corr-id',
      },
    }),
    {
      status,
      headers: { 'Content-Type': 'application/json' },
    },
  )
}

describe('api client', () => {
  afterEach(() => {
    clearSession()
    vi.restoreAllMocks()
  })

  it('refreshes the access token and retries protected calls', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(error(401, 'Expired token'))
      .mockResolvedValueOnce(
        success({
          access_token: 'fresh-access',
          refresh_token: 'fresh-refresh',
          token_type: 'bearer',
          expires_in: 900,
        }),
      )
      .mockResolvedValueOnce(
        success({
          id: 'user-id',
          email: 'student@example.com',
          first_name: 'Student',
          last_name: 'Example',
          is_active: true,
          is_verified: true,
          roles: ['student'],
          avatar_url: null,
          created_at: '2026-04-13T00:00:00Z',
          updated_at: '2026-04-13T00:00:00Z',
        }),
      )

    vi.stubGlobal('fetch', fetchMock)

    setSession({
      accessToken: 'expired-access',
      refreshToken: 'refresh-token',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'user-id',
        email: 'student@example.com',
        roles: ['student'],
      },
    })

    const profile = await getProfile()

    expect(profile.email).toBe('student@example.com')
    expect(getSession()?.accessToken).toBe('fresh-access')
    expect(getSession()?.refreshToken).toBe('fresh-refresh')
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('throws ApiError for invalid requests', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(error(422, 'Invalid request body')))

    await expect(
      registerUser({
        email: 'broken@example.com',
        password: 'short',
        first_name: 'Broken',
        last_name: 'Case',
      }),
    ).rejects.toBeInstanceOf(ApiError)
  })
})