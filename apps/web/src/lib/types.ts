export interface ResponseMeta {
  correlation_id: string
  timestamp: string
}

export interface SuccessResponse<T> {
  data: T
  meta: ResponseMeta
}

export interface Pagination {
  page: number
  page_size: number
  total_items: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface PaginatedResponse<T> extends SuccessResponse<T[]> {
  pagination: Pagination
}

export interface ApiErrorBody {
  code: string
  message: string
  details?: unknown
  correlation_id?: string
  timestamp?: string
}

export interface ApiErrorResponse {
  error: ApiErrorBody
}

export class ApiError extends Error {
  status: number
  code: string
  correlationId?: string
  details?: unknown

  constructor(status: number, body?: ApiErrorBody) {
    super(body?.message ?? 'Request failed')
    this.name = 'ApiError'
    this.status = status
    this.code = body?.code ?? 'HTTP_ERROR'
    this.correlationId = body?.correlation_id
    this.details = body?.details
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong while talking to the API.'
}