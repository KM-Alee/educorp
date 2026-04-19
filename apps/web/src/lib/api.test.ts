import { afterEach, describe, expect, it, vi } from 'vitest'

import { getProfile, registerUser, streamAIAssistant, uploadAsset } from './api'
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

function eventStream(...chunks: string[]): Response {
  return new Response(
    new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder()
        chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
        controller.close()
      },
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
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

  it('sends multipart uploads without forcing a JSON content type', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      success({
        id: 'asset-id',
        module_id: 'module-id',
        title: 'Lecture notes',
        asset_type: 'pdf',
        file_name: 'notes.pdf',
        file_size: 1024,
        mime_type: 'application/pdf',
        storage_path: 'course-assets/path',
        checksum: 'checksum',
        sort_order: 0,
        upload_status: 'UPLOADED',
        created_at: '2026-04-13T00:00:00Z',
        updated_at: '2026-04-13T00:00:00Z',
      }),
    )

    vi.stubGlobal('fetch', fetchMock)

    setSession({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'user-id',
        email: 'instructor@example.com',
        roles: ['instructor'],
      },
    })

    await uploadAsset('course-id', 'module-id', {
      file: new File(['%PDF-1.4'], 'notes.pdf', { type: 'application/pdf' }),
      title: 'Lecture notes',
    })

    const [, init] = fetchMock.mock.calls[0]
    const headers = new Headers(init?.headers)

    expect(headers.has('Content-Type')).toBe(false)
    expect(headers.get('Authorization')).toBe('Bearer access-token')
    expect(init?.body).toBeInstanceOf(FormData)
  })

  it('parses CRLF-delimited SSE events for assistant streaming', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      eventStream(
        'event: token\r\ndata: {"text":"Hello"}\r\n\r\n',
        'event: done\r\ndata: {"query_id":"query-1"}\r\n\r\n',
      ),
    )

    vi.stubGlobal('fetch', fetchMock)

    setSession({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'user-id',
        email: 'student@example.com',
        roles: ['student'],
      },
    })

    const seenEvents: Array<{ event: string; data: string | null }> = []

    await streamAIAssistant({
      course_id: 'course-id',
      question: 'hello',
      signal: new AbortController().signal,
      onEvent: (event) => seenEvents.push(event),
    })

    expect(seenEvents).toEqual([
      { event: 'token', data: '{"text":"Hello"}' },
      { event: 'done', data: '{"query_id":"query-1"}' },
    ])

    const [path, init] = fetchMock.mock.calls[0]
    expect(path).toContain('/api/v1/ai/ask/stream?')
    expect(path).toContain('question=hello')

    const headers = new Headers(init?.headers)
    expect(headers.get('Accept')).toBe('text/event-stream')
    expect(headers.get('Authorization')).toBe('Bearer access-token')
  })
})