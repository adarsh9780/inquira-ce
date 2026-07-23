export interface ApiErrorDetail {
  code?: string
  message: string
  field?: string
}

export interface ApiError {
  code: string
  message: string
  details?: ApiErrorDetail[]
  cause?: unknown
}

export type ApiResult<Value> =
  | { ok: true; value: Value }
  | { ok: false; error: ApiError }

export interface NativeStreamEnvelope<Event> {
  client_request_id: string
  event: Event
}
