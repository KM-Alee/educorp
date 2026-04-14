import type { SessionState } from './session'
import { clearSession, getSession, setSession } from './session'
import {
  ApiError,
  type ApiErrorBody,
  type ApiErrorResponse,
  type PaginatedResponse,
  type SuccessResponse,
} from './types'

const AUTH_BASE = '/api/v1/auth'
const COURSE_BASE = '/api/v1/courses'

export interface RegisterInput {
  email: string
  password: string
  first_name: string
  last_name: string
}

export interface LoginInput {
  email: string
  password: string
}

export interface UserProfile {
  id: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  is_verified: boolean
  roles: string[]
  avatar_url: string | null
  created_at: string
  updated_at: string
}

export interface UserCreated {
  id: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  is_verified: boolean
  roles: string[]
  created_at: string
}

export interface TokenUser {
  id: string
  email: string
  roles: string[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: TokenUser
}

export interface RefreshTokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface MessageResponse {
  message: string
}

export interface InstructorApplication {
  id: string
  status: string
  created_at: string
}

export interface AdminUser {
  id: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  is_verified: boolean
  roles: string[]
  created_at: string
  updated_at: string
}

export interface CourseListItem {
  id: string
  instructor_id: string
  title: string
  slug: string
  short_description: string | null
  category: string | null
  difficulty: string | null
  estimated_duration: string | null
  tags: string[]
  thumbnail_url: string | null
  visibility: string
  created_at: string
}

export interface CourseModuleSummary {
  id: string
  title: string
  description: string | null
  sort_order: number
  is_required: boolean
  asset_count: number
}

export interface CourseDetail {
  id: string
  instructor_id: string
  title: string
  slug: string
  description: string | null
  short_description: string | null
  category: string | null
  difficulty: string | null
  estimated_duration: string | null
  tags: string[]
  thumbnail_url: string | null
  is_public_preview: boolean
  max_capacity: number | null
  prerequisites: string[]
  visibility: string
  current_version_id: string | null
  modules: CourseModuleSummary[]
  created_at: string
  updated_at: string
}

export interface CourseCreateInput {
  title: string
  description?: string
  short_description?: string
  category?: string
  difficulty?: string
  estimated_duration?: string
  tags?: string[]
  max_capacity?: number
  prerequisites?: string[]
}

export interface ModuleDetail {
  id: string
  course_id: string
  title: string
  description: string | null
  sort_order: number
  is_required: boolean
  estimated_duration: string | null
  created_at: string
  updated_at: string
}

export interface ModuleCreateInput {
  title: string
  description?: string
  sort_order?: number
  is_required?: boolean
}

export interface AssetOut {
  id: string
  module_id: string
  title: string
  asset_type: string
  file_name: string
  file_size: number
  mime_type: string
  storage_path: string
  checksum: string | null
  sort_order: number
  upload_status: string
  created_at: string
  updated_at: string
}

export interface AssetDownload {
  download_url: string
  expires_in: number
}

export interface DraftValidationIssue {
  field: string
  message: string
  severity: string
}

export interface DraftValidationResult {
  is_valid: boolean
  issues: DraftValidationIssue[]
}

export interface DraftContentDocument {
  course_id: string
  content: Record<string, unknown>
  updated_at: string | null
}

async function parsePayload<T>(response: Response): Promise<T | null> {
  const text = await response.text()
  if (!text) {
    return null
  }
  return JSON.parse(text) as T
}

function createError(status: number, body: ApiErrorBody | undefined): ApiError {
  return new ApiError(status, body)
}

async function refreshSession(): Promise<boolean> {
  const currentSession = getSession()
  if (!currentSession) {
    return false
  }

  const response = await fetch(`${AUTH_BASE}/refresh`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh_token: currentSession.refreshToken }),
  })

  const payload = await parsePayload<
    SuccessResponse<RefreshTokenResponse> | ApiErrorResponse
  >(response)

  if (!response.ok || !payload || !('data' in payload)) {
    clearSession()
    return false
  }

  setSession({
    ...currentSession,
    accessToken: payload.data.access_token,
    refreshToken: payload.data.refresh_token,
    tokenType: payload.data.token_type,
    expiresIn: payload.data.expires_in,
  })

  return true
}

async function requestEnvelope<T>(
  path: string,
  init: RequestInit = {},
  options: { auth?: boolean; retry?: boolean } = {},
): Promise<SuccessResponse<T>> {
  const session = getSession()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')

  if (init.body && !headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (options.auth && session?.accessToken) {
    headers.set('Authorization', `Bearer ${session.accessToken}`)
  }

  const response = await fetch(path, { ...init, headers })

  if (response.status === 401 && options.auth && options.retry !== false) {
    const refreshed = await refreshSession()
    if (refreshed) {
      return requestEnvelope<T>(path, init, { ...options, retry: false })
    }
  }

  const payload = await parsePayload<SuccessResponse<T> | ApiErrorResponse>(response)

  if (!response.ok || !payload || !('data' in payload)) {
    if (payload && 'error' in payload) {
      throw createError(response.status, payload.error)
    }
    throw createError(response.status, undefined)
  }

  return payload
}

async function requestPaginated<T>(
  path: string,
  init: RequestInit = {},
): Promise<PaginatedResponse<T>> {
  const session = getSession()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')

  if (session?.accessToken) {
    headers.set('Authorization', `Bearer ${session.accessToken}`)
  }

  const response = await fetch(path, { ...init, headers })

  if (response.status === 401) {
    const refreshed = await refreshSession()
    if (refreshed) {
      return requestPaginated<T>(path, init)
    }
  }

  const payload = await parsePayload<PaginatedResponse<T> | ApiErrorResponse>(response)

  if (!response.ok || !payload || !('data' in payload)) {
    if (payload && 'error' in payload) {
      throw createError(response.status, payload.error)
    }
    throw createError(response.status, undefined)
  }

  return payload
}

export async function registerUser(input: RegisterInput): Promise<UserCreated> {
  const response = await requestEnvelope<UserCreated>(`${AUTH_BASE}/register`, {
    method: 'POST',
    body: JSON.stringify(input),
  })

  return response.data
}

export async function loginUser(input: LoginInput): Promise<SessionState> {
  const response = await requestEnvelope<TokenResponse>(`${AUTH_BASE}/login`, {
    method: 'POST',
    body: JSON.stringify(input),
  })

  return {
    accessToken: response.data.access_token,
    refreshToken: response.data.refresh_token,
    tokenType: response.data.token_type,
    expiresIn: response.data.expires_in,
    user: response.data.user,
  }
}

export async function verifyEmailToken(token: string): Promise<MessageResponse> {
  const response = await requestEnvelope<MessageResponse>(`${AUTH_BASE}/verify-email`, {
    method: 'POST',
    body: JSON.stringify({ token }),
  })

  return response.data
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  const response = await requestEnvelope<MessageResponse>(`${AUTH_BASE}/forgot-password`, {
    method: 'POST',
    body: JSON.stringify({ email }),
  })

  return response.data
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<MessageResponse> {
  const response = await requestEnvelope<MessageResponse>(`${AUTH_BASE}/reset-password`, {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  })

  return response.data
}

export async function getProfile(): Promise<UserProfile> {
  const response = await requestEnvelope<UserProfile>(`${AUTH_BASE}/me`, {}, { auth: true })
  return response.data
}

export async function updateProfile(input: {
  first_name?: string
  last_name?: string
  avatar_url?: string
}): Promise<UserProfile> {
  const response = await requestEnvelope<UserProfile>(
    `${AUTH_BASE}/me`,
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
    { auth: true },
  )

  return response.data
}

export async function createInstructorApplication(
  reason: string,
): Promise<InstructorApplication> {
  const response = await requestEnvelope<InstructorApplication>(
    `${AUTH_BASE}/instructor-application`,
    {
      method: 'POST',
      body: JSON.stringify({ reason }),
    },
    { auth: true },
  )

  return response.data
}

export async function listAdminUsers(filters: {
  role?: string
  search?: string
  isActive?: string
}): Promise<PaginatedResponse<AdminUser>> {
  const params = new URLSearchParams()
  params.set('page', '1')
  params.set('page_size', '25')

  if (filters.role) {
    params.set('role', filters.role)
  }

  if (filters.search) {
    params.set('search', filters.search)
  }

  if (filters.isActive) {
    params.set('is_active', filters.isActive)
  }

  return requestPaginated<AdminUser>(`${AUTH_BASE}/admin/users?${params.toString()}`)
}

export async function updateAdminUserRoles(input: {
  userId: string
  add_roles: string[]
  remove_roles: string[]
}): Promise<MessageResponse> {
  const response = await requestEnvelope<MessageResponse>(
    `${AUTH_BASE}/admin/users/${input.userId}/roles`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        add_roles: input.add_roles,
        remove_roles: input.remove_roles,
      }),
    },
    { auth: true },
  )

  return response.data
}

export async function updateAdminUserStatus(input: {
  userId: string
  is_active: boolean
}): Promise<MessageResponse> {
  const response = await requestEnvelope<MessageResponse>(
    `${AUTH_BASE}/admin/users/${input.userId}/status`,
    {
      method: 'PATCH',
      body: JSON.stringify({ is_active: input.is_active }),
    },
    { auth: true },
  )

  return response.data
}

export async function listCourses(filters: {
  page?: number
  page_size?: number
  category?: string
  difficulty?: string
  search?: string
  visibility?: string
  instructor_id?: string
}): Promise<PaginatedResponse<CourseListItem>> {
  const params = new URLSearchParams()
  params.set('page', String(filters.page ?? 1))
  params.set('page_size', String(filters.page_size ?? 20))

  if (filters.category) {
    params.set('category', filters.category)
  }
  if (filters.difficulty) {
    params.set('difficulty', filters.difficulty)
  }
  if (filters.search) {
    params.set('search', filters.search)
  }
  if (filters.visibility) {
    params.set('visibility', filters.visibility)
  }
  if (filters.instructor_id) {
    params.set('instructor_id', filters.instructor_id)
  }

  return requestPaginated<CourseListItem>(`${COURSE_BASE}/?${params.toString()}`)
}

export async function createCourse(input: CourseCreateInput): Promise<CourseDetail> {
  const response = await requestEnvelope<CourseDetail>(
    `${COURSE_BASE}/`,
    {
      method: 'POST',
      body: JSON.stringify(input),
    },
    { auth: true },
  )

  return response.data
}

export async function getCourse(courseId: string): Promise<CourseDetail> {
  const response = await requestEnvelope<CourseDetail>(`${COURSE_BASE}/${courseId}`, {}, { auth: true })
  return response.data
}

export async function updateCourse(
  courseId: string,
  input: Partial<CourseCreateInput>,
): Promise<CourseDetail> {
  const response = await requestEnvelope<CourseDetail>(
    `${COURSE_BASE}/${courseId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
    { auth: true },
  )

  return response.data
}

export async function deleteCourse(courseId: string): Promise<void> {
  await requestEnvelope<null>(
    `${COURSE_BASE}/${courseId}`,
    { method: 'DELETE' },
    { auth: true },
  )
}

export async function listModules(courseId: string): Promise<ModuleDetail[]> {
  const response = await requestEnvelope<ModuleDetail[]>(
    `${COURSE_BASE}/${courseId}/modules`,
    {},
    { auth: true },
  )
  return response.data
}

export async function createModule(
  courseId: string,
  input: ModuleCreateInput,
): Promise<ModuleDetail> {
  const response = await requestEnvelope<ModuleDetail>(
    `${COURSE_BASE}/${courseId}/modules`,
    {
      method: 'POST',
      body: JSON.stringify(input),
    },
    { auth: true },
  )
  return response.data
}

export async function updateModule(
  courseId: string,
  moduleId: string,
  input: Partial<ModuleCreateInput>,
): Promise<ModuleDetail> {
  const response = await requestEnvelope<ModuleDetail>(
    `${COURSE_BASE}/${courseId}/modules/${moduleId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
    { auth: true },
  )
  return response.data
}

export async function deleteModule(courseId: string, moduleId: string): Promise<void> {
  await requestEnvelope<null>(
    `${COURSE_BASE}/${courseId}/modules/${moduleId}`,
    { method: 'DELETE' },
    { auth: true },
  )
}

export async function reorderModules(courseId: string, order: string[]): Promise<ModuleDetail[]> {
  const response = await requestEnvelope<ModuleDetail[]>(
    `${COURSE_BASE}/${courseId}/modules/reorder`,
    {
      method: 'PATCH',
      body: JSON.stringify({ order }),
    },
    { auth: true },
  )

  return response.data
}

export async function listAssets(courseId: string, moduleId: string): Promise<AssetOut[]> {
  const response = await requestEnvelope<AssetOut[]>(
    `${COURSE_BASE}/${courseId}/modules/${moduleId}/assets`,
    {},
    { auth: true },
  )
  return response.data
}

export async function uploadAsset(
  courseId: string,
  moduleId: string,
  input: { file: File; title: string; sort_order?: number },
): Promise<AssetOut> {
  const body = new FormData()
  body.set('file', input.file)
  body.set('title', input.title)
  if (typeof input.sort_order === 'number') {
    body.set('sort_order', String(input.sort_order))
  }

  const response = await requestEnvelope<AssetOut>(
    `${COURSE_BASE}/${courseId}/modules/${moduleId}/assets/upload`,
    {
      method: 'POST',
      body,
    },
    { auth: true },
  )

  return response.data
}

export async function getAssetDownload(
  courseId: string,
  moduleId: string,
  assetId: string,
): Promise<AssetDownload> {
  const response = await requestEnvelope<AssetDownload>(
    `${COURSE_BASE}/${courseId}/modules/${moduleId}/assets/${assetId}/download`,
    {},
    { auth: true },
  )

  return response.data
}

export async function deleteAsset(courseId: string, moduleId: string, assetId: string): Promise<void> {
  await requestEnvelope<null>(
    `${COURSE_BASE}/${courseId}/modules/${moduleId}/assets/${assetId}`,
    { method: 'DELETE' },
    { auth: true },
  )
}

export async function validateCourseDraft(courseId: string): Promise<DraftValidationResult> {
  const response = await requestEnvelope<DraftValidationResult>(
    `${COURSE_BASE}/${courseId}/validate`,
    { method: 'POST' },
    { auth: true },
  )
  return response.data
}

export async function getDraftContent(courseId: string): Promise<DraftContentDocument> {
  const response = await requestEnvelope<DraftContentDocument>(
    `${COURSE_BASE}/${courseId}/draft-content`,
    {},
    { auth: true },
  )
  return response.data
}

export async function updateDraftContent(
  courseId: string,
  content: Record<string, unknown>,
): Promise<DraftContentDocument> {
  const response = await requestEnvelope<DraftContentDocument>(
    `${COURSE_BASE}/${courseId}/draft-content`,
    {
      method: 'PATCH',
      body: JSON.stringify({ content }),
    },
    { auth: true },
  )
  return response.data
}

export async function listInstructorApplications(
  status = 'pending',
): Promise<PaginatedResponse<InstructorApplication>> {
  const params = new URLSearchParams({ page: '1', page_size: '25' })
  if (status) {
    params.set('status', status)
  }
  return requestPaginated<InstructorApplication>(
    `${AUTH_BASE}/admin/instructor-applications?${params.toString()}`,
  )
}

export async function reviewInstructorApplication(input: {
  applicationId: string
  status: 'APPROVED' | 'REJECTED'
}): Promise<InstructorApplication> {
  const response = await requestEnvelope<InstructorApplication>(
    `${AUTH_BASE}/admin/instructor-applications/${input.applicationId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ status: input.status }),
    },
    { auth: true },
  )

  return response.data
}