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
const PUBLISHING_BASE = '/api/v1/publishing'
const SEARCH_BASE = '/api/v1/search'
const AI_BASE = '/api/v1/ai'

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

export interface PublishVersionResponse {
  version_id: string
  version_number: number
  status: string
  approval_state: string | null
  workflow_id: string | null
  message: string
}

export interface PublishingArtifact {
  id: string
  artifact_type: string
  object_path: string
  sha256: string
  content_type: string
  size_bytes: number
  metadata: Record<string, unknown>
  created_at: string
}

export interface PublishingStep {
  id: string
  step_name: string
  status: string
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  metadata: Record<string, unknown>
}

export interface PublishingVersion {
  id: string
  course_id: string
  version_number: number
  status: string
  approval_state: string
  initiated_by: string
  workflow_id: string | null
  run_id: string | null
  manifest_hash: string
  preflight_summary_json: Record<string, unknown> | null
  error_details: Record<string, unknown> | null
  total_chunks: number
  total_assets: number
  processing_started_at: string | null
  processing_completed_at: string | null
  created_at: string
  ready_at: string | null
  activated_at: string | null
  superseded_at: string | null
  steps: PublishingStep[]
  artifacts: PublishingArtifact[]
}

export interface CourseSearchItem {
  course_id: string
  title: string
  short_description: string | null
  instructor_name?: string | null
  category: string | null
  difficulty: string | null
  relevance_score: number
  matched_in: string[]
}

export interface AICitation {
  chunk_id: string
  module_title?: string | null
  asset_title?: string | null
  text_snippet: string
  page_number?: number | null
}

export interface AIAnswer {
  query_id: string
  answer: string
  citations: AICitation[]
  confidence: string
  course_id: string
  version_id: string
  response_type: string
}

export interface AIEnhancementJob {
  job_id: string
  job_type: string
  status: string
  result?: Record<string, unknown> | null
  created_at?: string | null
  completed_at?: string | null
}

export interface AIEnhanceResponse {
  job_id: string
  status: string
  message: string
}

export interface AIJobList {
  items: AIEnhancementJob[]
  total: number
}

async function parsePayload<T>(response: Response): Promise<T | null> {
  const text = await response.text()
  const trimmed = text.trim()
  if (!trimmed) {
    return null
  }

  const contentType = response.headers.get('Content-Type') ?? ''
  if (!contentType.includes('application/json')) {
    // Backend returned non-JSON (e.g. HTML error page from gateway)
    throw new ApiError(response.status, {
      code: 'NON_JSON_RESPONSE',
      message: `Server returned an unexpected response (${response.status}). Please try again later.`,
    })
  }

  try {
    return JSON.parse(trimmed) as T
  } catch {
    throw new ApiError(response.status, {
      code: 'INVALID_JSON',
      message: `Server returned malformed data (${response.status}). Please try again later.`,
    })
  }
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

  let payload: SuccessResponse<RefreshTokenResponse> | ApiErrorResponse | null
  try {
    payload = await parsePayload<
      SuccessResponse<RefreshTokenResponse> | ApiErrorResponse
    >(response)
  } catch {
    clearSession()
    return false
  }

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

export async function publishCourse(courseId: string): Promise<PublishVersionResponse> {
  const response = await requestEnvelope<PublishVersionResponse>(
    `${COURSE_BASE}/${courseId}/publish`,
    { method: 'POST' },
    { auth: true },
  )
  return response.data
}

export async function getPublishingVersion(versionId: string): Promise<PublishingVersion> {
  const response = await requestEnvelope<PublishingVersion>(
    `${PUBLISHING_BASE}/versions/${versionId}`,
    {},
    { auth: true },
  )
  return response.data
}

export async function retryPublishingVersion(versionId: string): Promise<PublishVersionResponse> {
  const response = await requestEnvelope<PublishVersionResponse>(
    `${PUBLISHING_BASE}/versions/${versionId}/retry`,
    { method: 'POST' },
    { auth: true },
  )
  return response.data
}

export async function cancelPublishingVersion(versionId: string): Promise<PublishVersionResponse> {
  const response = await requestEnvelope<PublishVersionResponse>(
    `${PUBLISHING_BASE}/versions/${versionId}/cancel`,
    { method: 'POST' },
    { auth: true },
  )
  return response.data
}

export async function approvePublishingVersion(versionId: string): Promise<PublishVersionResponse> {
  const response = await requestEnvelope<PublishVersionResponse>(
    `${PUBLISHING_BASE}/versions/${versionId}/approve`,
    { method: 'POST' },
    { auth: true },
  )
  return response.data
}

export async function rejectPublishingVersion(versionId: string): Promise<PublishVersionResponse> {
  const response = await requestEnvelope<PublishVersionResponse>(
    `${PUBLISHING_BASE}/versions/${versionId}/reject`,
    { method: 'POST' },
    { auth: true },
  )
  return response.data
}

export async function searchCourses(filters: {
  q?: string
  category?: string
  difficulty?: string
  tags?: string
  page?: number
  page_size?: number
}): Promise<PaginatedResponse<CourseSearchItem>> {
  const params = new URLSearchParams()
  if (filters.q) params.set('q', filters.q)
  if (filters.category) params.set('category', filters.category)
  if (filters.difficulty) params.set('difficulty', filters.difficulty)
  if (filters.tags) params.set('tags', filters.tags)
  params.set('page', String(filters.page ?? 1))
  params.set('page_size', String(filters.page_size ?? 20))

  return requestPaginated<CourseSearchItem>(`${SEARCH_BASE}/courses?${params.toString()}`)
}

export async function listInstructorApplications(
  status = 'PENDING',
): Promise<PaginatedResponse<InstructorApplication>> {
  const params = new URLSearchParams({ page: '1', page_size: '25' })
  const normalized = status ? status.toUpperCase() : ''
  if (normalized) {
    params.set('status', normalized)
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

export async function askAI(input: {
  course_id: string
  question: string
  module_id?: string | null
}): Promise<AIAnswer> {
  const response = await requestEnvelope<AIAnswer>(
    `${AI_BASE}/ask`,
    {
      method: 'POST',
      body: JSON.stringify(input),
    },
    { auth: true },
  )

  return response.data
}

export async function createAIEnhancementJob(input: {
  course_id: string
  job_type: string
  scope: string
  module_id?: string | null
  parameters?: Record<string, unknown>
}): Promise<AIEnhanceResponse> {
  const response = await requestEnvelope<AIEnhanceResponse>(
    `${AI_BASE}/instructor/enhance`,
    {
      method: 'POST',
      body: JSON.stringify({
        course_id: input.course_id,
        job_type: input.job_type,
        scope: input.scope,
        module_id: input.module_id ?? null,
        parameters: input.parameters ?? {},
      }),
    },
    { auth: true },
  )

  return response.data
}

export async function getAIJob(jobId: string): Promise<AIEnhancementJob> {
  const response = await requestEnvelope<AIEnhancementJob>(
    `${AI_BASE}/instructor/jobs/${jobId}`,
    {},
    { auth: true },
  )

  return response.data
}

export async function listAIJobs(filters: {
  course_id?: string
  status?: string
  job_type?: string
  page?: number
  page_size?: number
}): Promise<AIJobList> {
  const params = new URLSearchParams()
  if (filters.course_id) params.set('course_id', filters.course_id)
  if (filters.status) params.set('status', filters.status)
  if (filters.job_type) params.set('job_type', filters.job_type)
  params.set('page', String(filters.page ?? 1))
  params.set('page_size', String(filters.page_size ?? 20))

  const response = await requestEnvelope<AIJobList>(
    `${AI_BASE}/instructor/jobs?${params.toString()}`,
    {},
    { auth: true },
  )

  return response.data
}