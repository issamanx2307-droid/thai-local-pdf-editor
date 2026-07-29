const BRIDGE_BASE_URL = (import.meta.env.VITE_PDF_BRIDGE_URL || 'http://127.0.0.1:5178').replace(/\/$/, '')

export type WorkerCommandName =
  | 'add_highlight_overlay'
  | 'add_image_overlay'
  | 'add_redaction_overlay'
  | 'add_text_overlay'
  | 'batch'
  | 'batch_export_jpg'
  | 'close_document'
  | 'crop_page'
  | 'create_visual_signature'
  | 'delete_page'
  | 'draw_rectangle_overlay'
  | 'duplicate_page'
  | 'export_jpg'
  | 'extract_page'
  | 'go_to_page'
  | 'list_form_fields'
  | 'list_metadata'
  | 'list_printers'
  | 'merge_pdfs'
  | 'move_page'
  | 'open_pdf'
  | 'print_pdf'
  | 'render_page'
  | 'redo_pending'
  | 'replace_text'
  | 'rotate_page'
  | 'save_copy'
  | 'search_text'
  | 'undo_pending'
  | 'update_form_fields'
  | 'update_metadata'

export type WorkerSearchResult = {
  page_index: number
  match_index: number
  rect: [number, number, number, number]
  label: string
}

export type WorkerFormField = {
  xref: number
  page_index: number
  name: string
  field_type: number
  field_type_label: string
  value: string | boolean
  is_checkbox: boolean
}

export type WorkerState = {
  has_document: boolean
  current_file_path: string | null
  working_copy_path: string | null
  total_pages: number
  current_page_index: number
  display_page_number: number
  zoom_level: number
  dirty: boolean
  can_undo: boolean
  can_redo: boolean
  selected_page_indices: number[]
  selected_tool: string | null
}

export type WorkerRequest = {
  command: WorkerCommandName
  payload?: Record<string, unknown>
  commands?: WorkerRequest[]
}

export type WorkerResponse = {
  ok: boolean
  command: WorkerCommandName
  state: WorkerState
  payload: Record<string, unknown>
  responses?: WorkerResponse[]
  error?: {
    type?: string
    message: string
    detail?: string
  }
}

export type UploadedImageResponse = {
  ok: boolean
  path: string
  file_name: string
}

export type UploadedPdfResponse = {
  ok: boolean
  path: string
  file_name: string
  page_count: number
}

export type ConverterOutputFormat = 'docx' | 'xlsx' | 'pdf' | 'jpg'

export type ConverterJobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export type ConverterJobOptions = {
  output_format: ConverterOutputFormat
  start_page: number
  end_page: number | null
  workers: number
  dpi: number
  lang: string
  use_cache: boolean
  use_preprocessing: boolean
}

export type ConverterJob = {
  id: string
  status: ConverterJobStatus
  source_filename: string
  pdf_type: string | null
  done_pages: number
  total_pages: number
  progress_percent: number
  failed_pages: number[]
  error: string | null
  options: Partial<ConverterJobOptions>
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
  download_url: string | null
}

export async function getBridgeHealth(retries = 10, delayMs = 300): Promise<{
  ok: boolean
  bridge: string
  state: WorkerState
  default_downloads_dir?: string
}> {
  let lastError: unknown
  for (let i = 0; i < retries; i++) {
    try {
      return await fetchJson('/api/health')
    } catch (err) {
      lastError = err
      await new Promise((resolve) => setTimeout(resolve, delayMs))
    }
  }
  throw lastError || new Error('ไม่สามารถเชื่อมต่อบริการประมวลผล PDF ได้')
}

export async function callWorker(request: WorkerRequest): Promise<WorkerResponse> {
  const response = await fetchJson<WorkerResponse>('/api/worker', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(response.error?.message || 'worker ทำงานไม่สำเร็จ')
  }
  return response
}

export async function uploadLocalImage(file: File): Promise<UploadedImageResponse> {
  const dataUrl = await readFileAsDataUrl(file)
  const response = await fetchJson<UploadedImageResponse>('/api/upload-image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_name: file.name, data_url: dataUrl }),
  })
  if (!response.ok || !response.path) {
    throw new Error('อัปโหลดรูปภาพเข้า local bridge ไม่สำเร็จ')
  }
  return response
}

export async function uploadLocalPdf(file: File): Promise<UploadedPdfResponse> {
  const dataUrl = await readFileAsDataUrl(file)
  const response = await fetchJson<UploadedPdfResponse>('/api/upload-pdf', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_name: file.name, data_url: dataUrl }),
  })
  if (!response.ok || !response.path) {
    throw new Error('อัปโหลด PDF เข้า local bridge ไม่สำเร็จ')
  }
  return response
}

export async function startConverterJob(
  sourcePath: string,
  options: Partial<ConverterJobOptions>,
): Promise<ConverterJob> {
  return fetchJson<ConverterJob>('/api/converter/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_path: sourcePath, options }),
  })
}

export async function getConverterJob(jobId: string): Promise<ConverterJob> {
  return fetchJson<ConverterJob>(`/api/converter/jobs/${encodeURIComponent(jobId)}`)
}

export async function cancelConverterJob(jobId: string): Promise<void> {
  await fetchJson(`/api/converter/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' })
}

export async function retryConverterJob(jobId: string): Promise<ConverterJob> {
  return fetchJson<ConverterJob>(`/api/converter/jobs/${encodeURIComponent(jobId)}/retry`, { method: 'POST' })
}

export function converterDownloadUrl(job: ConverterJob): string | null {
  return job.download_url ? `${BRIDGE_BASE_URL}${job.download_url}` : null
}

export async function downloadConverterResult(job: ConverterJob): Promise<Blob> {
  const url = converterDownloadUrl(job)
  if (!url) {
    throw new Error('ยังไม่มีไฟล์ผลลัพธ์ให้ดาวน์โหลด')
  }
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`ดาวน์โหลดไฟล์ไม่สำเร็จ: ${response.status}`)
  }
  return response.blob()
}

export function converterResultFileName(job: ConverterJob): string {
  const format = job.options.output_format || 'docx'
  const stem = job.source_filename.replace(/\.[^./\\]+$/, '') || 'converted'
  const extension = format === 'jpg' ? 'zip' : format
  return `${stem}.${extension}`
}

export function lastRenderResponse(response: WorkerResponse): WorkerResponse | undefined {
  if (response.command === 'render_page') {
    return response
  }
  return response.responses?.findLast((item) => item.command === 'render_page')
}

export function previewUrlFrom(response: WorkerResponse | undefined): string | null {
  const previewUrl = response?.payload.preview_url
  return typeof previewUrl === 'string' ? `${BRIDGE_BASE_URL}${previewUrl}` : null
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const response = await fetch(`${BRIDGE_BASE_URL}${path}`, init)
    const payload = (await response.json()) as T
    if (!response.ok) {
      throw new Error(errorMessage(payload) || `bridge request failed: ${response.status}`)
    }
    return payload
  } catch (error) {
    if (error instanceof TypeError || (error instanceof Error && error.message.toLowerCase().includes('fetch'))) {
      throw new Error('ไม่สามารถเชื่อมต่อบริการประมวลผล PDF ได้ กรุณาลองใหม่อีกครั้ง', { cause: error })
    }
    throw error
  }
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.addEventListener('load', () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result)
      } else {
        reject(new Error('อ่านไฟล์รูปภาพไม่สำเร็จ'))
      }
    })
    reader.addEventListener('error', () => reject(reader.error || new Error('อ่านไฟล์รูปภาพไม่สำเร็จ')))
    reader.readAsDataURL(file)
  })
}

function errorMessage(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object' || !('error' in payload)) {
    return null
  }
  const error = (payload as { error?: { message?: unknown } }).error
  return typeof error?.message === 'string' ? error.message : null
}
