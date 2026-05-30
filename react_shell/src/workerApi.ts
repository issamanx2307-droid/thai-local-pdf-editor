const BRIDGE_BASE_URL = (import.meta.env.VITE_PDF_BRIDGE_URL || 'http://127.0.0.1:5178').replace(/\/$/, '')

export type WorkerCommandName =
  | 'add_highlight_overlay'
  | 'add_image_overlay'
  | 'add_text_overlay'
  | 'batch'
  | 'close_document'
  | 'create_visual_signature'
  | 'delete_page'
  | 'draw_rectangle_overlay'
  | 'duplicate_page'
  | 'go_to_page'
  | 'move_page'
  | 'open_pdf'
  | 'render_page'
  | 'save_copy'
  | 'search_text'

export type WorkerSearchResult = {
  page_index: number
  match_index: number
  rect: [number, number, number, number]
  label: string
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

export type DemoPathResponse = {
  ok: boolean
  path: string
}

export type UploadedImageResponse = {
  ok: boolean
  path: string
  file_name: string
}

export async function getBridgeHealth(): Promise<{ ok: boolean; bridge: string; state: WorkerState }> {
  return fetchJson('/api/health')
}

export async function getDemoPath(): Promise<string> {
  const response = await fetchJson<DemoPathResponse>('/api/demo')
  if (!response.ok || !response.path) {
    throw new Error('ไม่พบไฟล์ตัวอย่างจาก bridge')
  }
  return response.path
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

export async function openDemoDocument(): Promise<WorkerResponse> {
  const path = await getDemoPath()
  return callWorker({
    command: 'batch',
    commands: [
      { command: 'open_pdf', payload: { path } },
      { command: 'render_page', payload: { page_index: 0, zoom: 1 } },
    ],
  })
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
  const response = await fetch(`${BRIDGE_BASE_URL}${path}`, init)
  const payload = (await response.json()) as T
  if (!response.ok) {
    throw new Error(errorMessage(payload) || `bridge request failed: ${response.status}`)
  }
  return payload
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
