import { useSyncExternalStore } from 'react'

export interface SessionUser {
  id: string
  email: string
  roles: string[]
}

export interface SessionState {
  accessToken: string
  refreshToken: string
  tokenType: string
  expiresIn: number
  user: SessionUser
}

const STORAGE_KEY = 'educorp.phase1.session'

const listeners = new Set<() => void>()

const fallbackStorage = new Map<string, string>()

type StorageLike = {
  getItem: (key: string) => string | null
  setItem: (key: string, value: string) => void
  removeItem: (key: string) => void
}

function getStorage(): StorageLike {
  if (canUseStorage()) {
    const candidate = window.localStorage as Partial<StorageLike>
    if (
      typeof candidate.getItem === 'function' &&
      typeof candidate.setItem === 'function' &&
      typeof candidate.removeItem === 'function'
    ) {
      return candidate as StorageLike
    }
  }

  return {
    getItem: (key) => fallbackStorage.get(key) ?? null,
    setItem: (key, value) => {
      fallbackStorage.set(key, value)
    },
    removeItem: (key) => {
      fallbackStorage.delete(key)
    },
  }
}

function canUseStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

function readSession(): SessionState | null {
  const raw = getStorage().getItem(STORAGE_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as SessionState
  } catch {
    getStorage().removeItem(STORAGE_KEY)
    return null
  }
}

let sessionState = readSession()

function emitChange(): void {
  listeners.forEach((listener) => listener())
}

export function getSession(): SessionState | null {
  return sessionState
}

export function setSession(session: SessionState): void {
  sessionState = session
  getStorage().setItem(STORAGE_KEY, JSON.stringify(session))
  emitChange()
}

export function updateSession(
  updater: (session: SessionState | null) => SessionState | null,
): void {
  const nextSession = updater(sessionState)
  if (nextSession) {
    setSession(nextSession)
    return
  }

  clearSession()
}

export function clearSession(): void {
  sessionState = null
  getStorage().removeItem(STORAGE_KEY)
  emitChange()
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useSessionState(): SessionState | null {
  return useSyncExternalStore(subscribe, getSession, getSession)
}

export function defaultRouteForSession(session: SessionState): string {
  if (session.user.roles.includes('instructor') || session.user.roles.includes('admin')) {
    return '/app/courses'
  }

  return '/app/dashboard'
}
