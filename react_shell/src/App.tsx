import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from 'react'
import { listen } from '@tauri-apps/api/event'
import { invoke } from '@tauri-apps/api/core'
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Ban,
  Crop,
  FileDown,
  FileText,
  FolderOpen,
  Image,
  Layers,
  Maximize2,
  Minus,
  MousePointer2,
  Printer,
  Redo2,
  RefreshCw,
  RotateCcw,
  RotateCw,
  Save,
  Search,
  Square,
  Type,
  Undo2,
  Wand2,
  X,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import {
  callWorker,
  cancelConverterJob,
  converterResultFileName,
  downloadConverterResult,
  getBridgeHealth,
  getConverterJob,
  lastRenderResponse,
  previewUrlFrom,
  retryConverterJob,
  startConverterJob,
  uploadLocalImage,
  uploadLocalPdf,
  type ConverterJob,
  type ConverterOutputFormat,
  type WorkerCommandName,
  type WorkerFormField,
  type WorkerResponse,
  type WorkerSearchResult,
  type WorkerState,
} from './workerApi'
import './App.css'

const fallbackPages: number[] = []
const defaultZoomPercent = 100
const minZoomPercent = 50
const maxZoomPercent = 240

const commandNames: WorkerCommandName[] = [
  'add_highlight_overlay',
  'add_image_overlay',
  'add_redaction_overlay',
  'add_text_overlay',
  'batch_export_jpg',
  'close_document',
  'crop_page',
  'draw_rectangle_overlay',
  'create_visual_signature',
  'export_jpg',
  'open_pdf',
  'render_page',
  'go_to_page',
  'list_metadata',
  'update_metadata',
  'list_form_fields',
  'update_form_fields',
  'list_printers',
  'merge_pdfs',
  'move_page',
  'rotate_page',
  'duplicate_page',
  'extract_page',
  'delete_page',
  'replace_text',
  'search_text',
  'save_copy',
  'print_pdf',
  'undo_pending',
  'redo_pending',
]
type BridgeStatus = 'idle' | 'connecting' | 'ready' | 'error'
type PreviewImageSize = {
  width: number
  height: number
  zoom: number
}
type MetadataFields = {
  title: string
  author: string
  subject: string
  keywords: string
}
type PageScope = 'current' | 'all'
type ToolTab = 'search' | 'edit' | 'data' | 'export' | 'status'

const emptyMetadata: MetadataFields = {
  title: '',
  author: '',
  subject: '',
  keywords: '',
}
const unsavedChangesMessage = 'ไฟล์มีการเปลี่ยนแปลงที่ยังไม่ได้บันทึก ต้องการทิ้งการเปลี่ยนแปลงและทำต่อหรือไม่'

function searchResultsFrom(response: WorkerResponse): WorkerSearchResult[] {
  const results = response.payload.results
  if (!Array.isArray(results)) {
    return []
  }
  return results.filter(isWorkerSearchResult)
}

function isWorkerSearchResult(value: unknown): value is WorkerSearchResult {
  if (!value || typeof value !== 'object') {
    return false
  }
  const item = value as Partial<WorkerSearchResult>
  return (
    typeof item.page_index === 'number' &&
    typeof item.match_index === 'number' &&
    Array.isArray(item.rect) &&
    item.rect.length === 4 &&
    item.rect.every((coordinate) => typeof coordinate === 'number') &&
    typeof item.label === 'string'
  )
}

function responseFor(response: WorkerResponse, command: WorkerCommandName): WorkerResponse | undefined {
  if (response.command === command) {
    return response
  }
  return response.responses?.find((item) => item.command === command)
}

function metadataFromPayload(response: WorkerResponse): MetadataFields {
  const metadata = response.payload.metadata
  if (!metadata || typeof metadata !== 'object') {
    return emptyMetadata
  }
  const raw = metadata as Partial<Record<keyof MetadataFields, unknown>>
  return {
    title: typeof raw.title === 'string' ? raw.title : '',
    author: typeof raw.author === 'string' ? raw.author : '',
    subject: typeof raw.subject === 'string' ? raw.subject : '',
    keywords: typeof raw.keywords === 'string' ? raw.keywords : '',
  }
}

function formFieldsFromPayload(response: WorkerResponse): WorkerFormField[] {
  const fields = response.payload.fields
  if (!Array.isArray(fields)) {
    return []
  }
  return fields.filter(isWorkerFormField)
}

function isWorkerFormField(value: unknown): value is WorkerFormField {
  if (!value || typeof value !== 'object') {
    return false
  }
  const field = value as Partial<WorkerFormField>
  return (
    typeof field.xref === 'number' &&
    typeof field.page_index === 'number' &&
    typeof field.name === 'string' &&
    typeof field.field_type === 'number' &&
    typeof field.field_type_label === 'string' &&
    (typeof field.value === 'string' || typeof field.value === 'boolean') &&
    typeof field.is_checkbox === 'boolean'
  )
}

function fileNameFromPath(path: string): string {
  return path.split(/[\\/]/).pop() || path
}

function clampZoomPercent(value: number): number {
  return Math.max(minZoomPercent, Math.min(maxZoomPercent, Math.round(value)))
}

function App() {
  const [pages, setPages] = useState(fallbackPages)
  const [selectedPageIndex, setSelectedPageIndex] = useState(0)
  const [zoomPercent, setZoomPercent] = useState(defaultZoomPercent)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [documentPath, setDocumentPath] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [canUndo, setCanUndo] = useState(false)
  const [canRedo, setCanRedo] = useState(false)
  const [bridgeStatus, setBridgeStatus] = useState<BridgeStatus>('idle')
  const [statusMessage, setStatusMessage] = useState('พร้อมใช้งาน — กรุณากดเปิดไฟล์ PDF')
  const [lastCommand, setLastCommand] = useState<WorkerCommandName | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<WorkerSearchResult[]>([])
  const [activeSearchIndex, setActiveSearchIndex] = useState(-1)
  const [textOverlayValue, setTextOverlayValue] = useState('')
  const [textOverlayFontSize, setTextOverlayFontSize] = useState('16')
  const [selectedImagePath, setSelectedImagePath] = useState<string | null>(null)
  const [selectedImageName, setSelectedImageName] = useState('')
  const [imageOverlayWidth, setImageOverlayWidth] = useState('140')
  const [signatureText, setSignatureText] = useState('ลายเซ็นภาพ')
  const [cropMarginPercent, setCropMarginPercent] = useState('8')
  const [replaceSearchText, setReplaceSearchText] = useState('')
  const [replaceTextValue, setReplaceTextValue] = useState('')
  const [replacePageScope, setReplacePageScope] = useState<PageScope>('current')
  const [metadataFields, setMetadataFields] = useState<MetadataFields>(emptyMetadata)
  const [formFields, setFormFields] = useState<WorkerFormField[]>([])
  const [jpgPageScope, setJpgPageScope] = useState<PageScope>('current')
  const [jpgDpi, setJpgDpi] = useState('300')
  const [jpgQuality, setJpgQuality] = useState('100')
  const [jpgOutputDir, setJpgOutputDir] = useState('')
  const [batchJpgFileNames, setBatchJpgFileNames] = useState<string[]>([])
  const [activeToolTab, setActiveToolTab] = useState<ToolTab>('edit')
  const [isGuideOpen, setIsGuideOpen] = useState(false)
  const [isPrintDialogOpen, setIsPrintDialogOpen] = useState(false)
  const [printers, setPrinters] = useState<string[]>([])
  const [selectedPrinter, setSelectedPrinter] = useState('')
  const [printCopies, setPrintCopies] = useState('1')
  const [isConvertDialogOpen, setIsConvertDialogOpen] = useState(false)
  const [convertFormat, setConvertFormat] = useState<ConverterOutputFormat>('docx')
  const [convertPageScope, setConvertPageScope] = useState<PageScope>('all')
  const [convertJob, setConvertJob] = useState<ConverterJob | null>(null)
  const [convertError, setConvertError] = useState<string | null>(null)
  const [isConvertStarting, setIsConvertStarting] = useState(false)
  const convertPollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [previewImageSize, setPreviewImageSize] = useState<PreviewImageSize | null>(null)
  const [isViewerExpanded, setIsViewerExpanded] = useState(false)
  const [isDiscardDialogOpen, setIsDiscardDialogOpen] = useState(false)
  const appShellRef = useRef<HTMLElement | null>(null)
  const viewerStageRef = useRef<HTMLDivElement | null>(null)
  const openPdfInputRef = useRef<HTMLInputElement | null>(null)
  const imageInputRef = useRef<HTMLInputElement | null>(null)
  const mergePdfInputRef = useRef<HTMLInputElement | null>(null)
  const batchJpgInputRef = useRef<HTMLInputElement | null>(null)
  const discardResolveRef = useRef<((confirmed: boolean) => void) | null>(null)

  const totalPages = pages.length
  const selectedPageNumber = selectedPageIndex + 1
  const hasDocument = Boolean(documentPath)
  const searchResultSummary =
    searchResults.length > 0 && activeSearchIndex >= 0 ? `${activeSearchIndex + 1}/${searchResults.length}` : ''

  useEffect(() => {
    if (!dirty) {
      return
    }

    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }

    window.addEventListener('beforeunload', warnBeforeUnload)
    return () => window.removeEventListener('beforeunload', warnBeforeUnload)
  }, [dirty])

  const confirmDiscardDirty = useCallback(() => {
    if (!dirty) {
      return Promise.resolve(true)
    }

    setIsDiscardDialogOpen(true)
    setStatusMessage('มีงานที่ยังไม่ได้บันทึก กรุณายืนยันก่อนทำต่อ')
    return new Promise<boolean>((resolve) => {
      discardResolveRef.current = resolve
    })
  }, [dirty])

  const answerDiscardPrompt = useCallback((confirmed: boolean) => {
    discardResolveRef.current?.(confirmed)
    discardResolveRef.current = null
    setIsDiscardDialogOpen(false)
    setStatusMessage(confirmed ? 'ยืนยันการทิ้งงานที่ยังไม่ได้บันทึก' : 'ยกเลิกเพื่อเก็บงานที่ยังไม่ได้บันทึกไว้')
  }, [])

  const applyResponse = useCallback((response: WorkerResponse, renderResponse = lastRenderResponse(response)) => {
    const nextState: WorkerState = renderResponse?.state || response.state
    if (!nextState.has_document) {
      setPages(fallbackPages)
      setSelectedPageIndex(0)
      setZoomPercent(defaultZoomPercent)
      setDocumentPath(null)
      setDirty(false)
      setCanUndo(false)
      setCanRedo(false)
      setPreviewUrl(null)
      setPreviewImageSize(null)
      setMetadataFields(emptyMetadata)
      setFormFields([])
      document.title = 'โปรแกรมแก้ไข PDF ภาษาไทย'
      return
    }

    const pageCount = Math.max(1, nextState.total_pages || 1)
    setPages((currentPages) => {
      if (currentPages.length === pageCount) {
        return currentPages
      }
      return Array.from({ length: pageCount }, (_, index) => index + 1)
    })
    setSelectedPageIndex(Math.min(Math.max(0, nextState.current_page_index), pageCount - 1))
    setZoomPercent(Math.round((nextState.zoom_level || 1) * 100))
    setDocumentPath(nextState.current_file_path)
    setDirty(nextState.dirty)
    setCanUndo(Boolean(nextState.can_undo))
    setCanRedo(Boolean(nextState.can_redo))

    if (nextState.current_file_path) {
      const fileName = nextState.current_file_path.split(/[\\/]/).pop() || nextState.current_file_path
      document.title = `${fileName} - โปรแกรมแก้ไข PDF ภาษาไทย`
    } else {
      document.title = 'โปรแกรมแก้ไข PDF ภาษาไทย'
    }

    const nextPreviewUrl = previewUrlFrom(renderResponse)
    if (nextPreviewUrl) {
      setPreviewUrl(`${nextPreviewUrl}?v=${Date.now()}`)
    }
    const imageWidth = renderResponse?.payload.image_width
    const imageHeight = renderResponse?.payload.image_height
    if (typeof imageWidth === 'number' && typeof imageHeight === 'number' && imageWidth > 0 && imageHeight > 0) {
      setPreviewImageSize({
        width: imageWidth,
        height: imageHeight,
        zoom: nextState.zoom_level || 1,
      })
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    getBridgeHealth()
      .then((health) => {
        if (!cancelled && health.default_downloads_dir) {
          setJpgOutputDir((current) => (current ? current : health.default_downloads_dir ?? current))
        }
        if (!cancelled && health.state && health.state.has_document && health.state.current_file_path) {
          applyResponse({ ok: true, command: 'open_pdf', state: health.state, payload: {} })
        }
      })
      .catch(() => {
        // Bridge not reachable yet; the JPG export field just stays empty
        // and the Python worker falls back to its own default directory.
      })
    return () => {
      cancelled = true
    }
  }, [applyResponse])

  const openPdfByPath = useCallback(
    async (filePath: string) => {
      if (!filePath) {
        return
      }
      if (!(await confirmDiscardDirty())) {
        return
      }

      setIsBusy(true)
      setLastCommand('open_pdf')
      setBridgeStatus('connecting')
      const fileName = filePath.split(/[\\/]/).pop() || filePath
      setStatusMessage(`กำลังเปิด PDF: ${fileName}`)
      try {
        await getBridgeHealth()
        const response = await callWorker({
          command: 'batch',
          commands: [
            { command: 'open_pdf', payload: { path: filePath } },
            { command: 'render_page', payload: { page_index: 0, zoom: defaultZoomPercent / 100 } },
          ],
        })
        applyResponse(response)
        setSearchQuery('')
        setSearchResults([])
        setActiveSearchIndex(-1)
        setSelectedImagePath(null)
        setSelectedImageName('')
        setMetadataFields(emptyMetadata)
        setFormFields([])
        setBridgeStatus('ready')
        setStatusMessage(`เปิดไฟล์แล้ว: ${fileName}`)
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : 'เปิดไฟล์ PDF ไม่สำเร็จ')
        setPreviewUrl(null)
      } finally {
        setIsBusy(false)
      }
    },
    [applyResponse, confirmDiscardDirty],
  )

  useEffect(() => {
    // 1. Check if Tauri launched with a file path argument (Explorer double-click)
    invoke<string | null>('get_initial_pdf_path')
      .then((path) => {
        if (path) {
          void openPdfByPath(path)
        }
      })
      .catch(() => {
        // Not running inside Tauri
      })

    // 2. Listen for 'open-pdf' events emitted dynamically
    let unlisten: (() => void) | undefined
    listen<string>('open-pdf', (event) => {
      if (event.payload) {
        void openPdfByPath(event.payload)
      }
    })
      .then((fn) => {
        unlisten = fn
      })
      .catch(() => {
        // Not in Tauri webview
      })

    return () => {
      unlisten?.()
    }
  }, [openPdfByPath])

  const openPdfFile = useCallback(
    async (file: File | undefined) => {
      if (!file) {
        return
      }

      const nativePath = (file as File & { path?: string }).path
      if (typeof nativePath === 'string' && nativePath) {
        if (openPdfInputRef.current) {
          openPdfInputRef.current.value = ''
        }
        return openPdfByPath(nativePath)
      }

      if (!(await confirmDiscardDirty())) {
        if (openPdfInputRef.current) {
          openPdfInputRef.current.value = ''
        }
        return
      }

      setIsBusy(true)
      setLastCommand('open_pdf')
      setBridgeStatus('connecting')
      setStatusMessage(`กำลังเปิด PDF: ${file.name}`)
      try {
        await getBridgeHealth()
        const uploaded = await uploadLocalPdf(file)
        const response = await callWorker({
          command: 'batch',
          commands: [
            { command: 'open_pdf', payload: { path: uploaded.path } },
            { command: 'render_page', payload: { page_index: 0, zoom: defaultZoomPercent / 100 } },
          ],
        })
        applyResponse(response)
        setSearchQuery('')
        setSearchResults([])
        setActiveSearchIndex(-1)
        setSelectedImagePath(null)
        setSelectedImageName('')
        setMetadataFields(emptyMetadata)
        setFormFields([])
        setBridgeStatus('ready')
        setStatusMessage(`เปิดไฟล์แล้ว: ${uploaded.file_name}`)
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : 'เปิดไฟล์ PDF ไม่สำเร็จ')
        setPreviewUrl(null)
      } finally {
        setIsBusy(false)
        if (openPdfInputRef.current) {
          openPdfInputRef.current.value = ''
        }
      }
    },
    [applyResponse, confirmDiscardDirty, openPdfByPath],
  )

  const renderPage = useCallback(
    async (pageIndex: number, zoom = zoomPercent) => {
      setIsBusy(true)
      setLastCommand('render_page')
      setStatusMessage('กำลัง render หน้าจาก Python worker...')
      try {
        const response = await callWorker({
          command: 'render_page',
          payload: { page_index: pageIndex, zoom: zoom / 100 },
        })
        applyResponse(response, response)
        setBridgeStatus('ready')
        setStatusMessage('render หน้าเสร็จแล้ว')
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : 'render หน้าไม่สำเร็จ')
      } finally {
        setIsBusy(false)
      }
    },
    [applyResponse, zoomPercent],
  )

  const fitPageToViewer = useCallback(
    async (mode: 'width' | 'height') => {
      if (!hasDocument) {
        setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนปรับพอดีหน้าจอ')
        return
      }
      if (!previewImageSize || !viewerStageRef.current) {
        await renderPage(selectedPageIndex, defaultZoomPercent)
        return
      }

      const stage = viewerStageRef.current
      const styles = window.getComputedStyle(stage)
      const horizontalPadding = Number.parseFloat(styles.paddingLeft) + Number.parseFloat(styles.paddingRight)
      const verticalPadding = Number.parseFloat(styles.paddingTop) + Number.parseFloat(styles.paddingBottom)
      const availableWidth = Math.max(120, stage.clientWidth - horizontalPadding - 24)
      const availableHeight = Math.max(120, stage.clientHeight - verticalPadding - 24)
      const baseWidth = previewImageSize.width / previewImageSize.zoom
      const baseHeight = previewImageSize.height / previewImageSize.zoom
      const nextZoom =
        mode === 'width'
          ? clampZoomPercent((availableWidth / baseWidth) * 100)
          : clampZoomPercent((availableHeight / baseHeight) * 100)
      await renderPage(selectedPageIndex, nextZoom)
      setStatusMessage(mode === 'width' ? 'ปรับพอดีกว้างตามหน้าต่างแล้ว' : 'ปรับพอดีบน-ล่างตามหน้าต่างแล้ว')
    },
    [hasDocument, previewImageSize, renderPage, selectedPageIndex],
  )

  const toggleViewerExpanded = useCallback(() => {
    setIsViewerExpanded((current) => {
      const next = !current
      setStatusMessage(next ? 'ขยายพื้นที่ดูเอกสารแล้ว' : 'กลับสู่หน้าจอปกติแล้ว')
      if (next) {
        void appShellRef.current?.requestFullscreen?.().catch(() => undefined)
      } else if (document.fullscreenElement) {
        void document.exitFullscreen().catch(() => undefined)
      }
      return next
    })
  }, [])

  const moveSelectedPage = useCallback(
    async (direction: -1 | 1) => {
      const targetIndex = selectedPageIndex + direction
      if (targetIndex < 0 || targetIndex >= totalPages) {
        return
      }

      setIsBusy(true)
      setLastCommand('move_page')
      setStatusMessage('กำลังย้ายหน้าผ่าน worker...')
      try {
        const response = await callWorker({
          command: 'batch',
          commands: [
            { command: 'move_page', payload: { selected_page_index: selectedPageIndex, delta: direction } },
            { command: 'render_page', payload: { page_index: targetIndex, zoom: zoomPercent / 100 } },
          ],
        })
        applyResponse(response)
        setSearchResults([])
        setActiveSearchIndex(-1)
        setBridgeStatus('ready')
        setStatusMessage('ย้ายหน้าแล้ว')
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : 'ย้ายหน้าไม่สำเร็จ')
      } finally {
        setIsBusy(false)
      }
    },
    [applyResponse, selectedPageIndex, totalPages, zoomPercent],
  )

  const rotateSelectedPage = useCallback(
    async (degrees: -90 | 90) => {
      if (!hasDocument) {
        setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนหมุนหน้า')
        return
      }

      setIsBusy(true)
      setLastCommand('rotate_page')
      setStatusMessage(`กำลังหมุนหน้า${degrees > 0 ? 'ขวา' : 'ซ้าย'}ผ่าน worker...`)
      try {
        const response = await callWorker({
          command: 'batch',
          commands: [
            { command: 'rotate_page', payload: { selected_page_index: selectedPageIndex, degrees } },
            { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
          ],
        })
        applyResponse(response)
        setSearchResults([])
        setActiveSearchIndex(-1)
        setBridgeStatus('ready')
        setStatusMessage(`หมุนหน้า${degrees > 0 ? 'ขวา' : 'ซ้าย'}แล้ว`)
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : 'หมุนหน้าไม่สำเร็จ')
      } finally {
        setIsBusy(false)
      }
    },
    [applyResponse, hasDocument, selectedPageIndex, zoomPercent],
  )

  const duplicateSelectedPage = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนทำซ้ำหน้า')
      return
    }

    const duplicatedPageIndex = selectedPageIndex + 1
    setIsBusy(true)
    setLastCommand('duplicate_page')
    setStatusMessage('กำลังทำซ้ำหน้าผ่าน worker...')
    try {
      const response = await callWorker({
        command: 'batch',
        commands: [
          { command: 'duplicate_page', payload: { selected_page_index: selectedPageIndex } },
          { command: 'render_page', payload: { page_index: duplicatedPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('ready')
      setStatusMessage('ทำซ้ำหน้าแล้ว')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'ทำซ้ำหน้าไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, selectedPageIndex, zoomPercent])

  const extractSelectedPage = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนแยกหน้านี้')
      return
    }

    setIsBusy(true)
    setLastCommand('extract_page')
    setStatusMessage('กำลังแยกหน้านี้ผ่าน worker...')
    try {
      const response = await callWorker({
        command: 'extract_page',
        payload: { selected_page_index: selectedPageIndex },
      })
      applyResponse(response)
      setBridgeStatus('ready')
      const extractedPath = response.payload.destination_path
      const extractedName = typeof extractedPath === 'string' ? fileNameFromPath(extractedPath) : 'ไฟล์แยกหน้า'
      setStatusMessage(`แยกหน้านี้แล้ว: ${extractedName}`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'แยกหน้านี้ไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, selectedPageIndex])

  const deleteSelectedPage = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนลบหน้า')
      return
    }
    if (totalPages <= 1) {
      setStatusMessage('ไม่สามารถลบหน้าสุดท้ายของเอกสารได้')
      return
    }

    const nextPageIndex = Math.min(selectedPageIndex, totalPages - 2)
    setIsBusy(true)
    setLastCommand('delete_page')
    setStatusMessage('กำลังลบหน้าผ่าน worker...')
    try {
      const response = await callWorker({
        command: 'batch',
        commands: [
          { command: 'delete_page', payload: { selected_page_index: selectedPageIndex } },
          { command: 'render_page', payload: { page_index: nextPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('ready')
      setStatusMessage('ลบหน้าแล้ว')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'ลบหน้าไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, selectedPageIndex, totalPages, zoomPercent])

  const saveCopy = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนบันทึก')
      return
    }

    setIsBusy(true)
    setLastCommand('save_copy')
    setStatusMessage('กำลังบันทึกสำเนา local...')
    try {
      const response = await callWorker({
        command: 'batch',
        commands: [
          { command: 'save_copy' },
          { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      setBridgeStatus('ready')
      const savedPath = responseFor(response, 'save_copy')?.payload.destination_path
      const savedName = typeof savedPath === 'string' ? fileNameFromPath(savedPath) : 'ไฟล์สำเนา'
      setStatusMessage(`บันทึกสำเนาแล้ว: ${savedName}`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'บันทึกสำเนาไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, selectedPageIndex, zoomPercent])

  const runPendingHistory = useCallback(
    async (command: 'undo_pending' | 'redo_pending') => {
      const isUndo = command === 'undo_pending'
      if (!hasDocument) {
        setStatusMessage('ยังไม่ได้เปิดไฟล์ PDF')
        return
      }
      if (isUndo ? !canUndo : !canRedo) {
        setStatusMessage(isUndo ? 'ไม่มีคำสั่งให้ย้อนกลับ' : 'ไม่มีคำสั่งให้ทำซ้ำ')
        return
      }

      setIsBusy(true)
      setLastCommand(command)
      setStatusMessage(isUndo ? 'กำลังย้อนกลับคำสั่งล่าสุดผ่าน worker...' : 'กำลังทำซ้ำคำสั่งล่าสุดผ่าน worker...')
      try {
        const response = await callWorker({
          command: 'batch',
          commands: [
            { command },
            { command: 'render_page', payload: { zoom: zoomPercent / 100 } },
          ],
        })
        applyResponse(response)
        setSearchResults([])
        setActiveSearchIndex(-1)
        setBridgeStatus('ready')
        setStatusMessage(isUndo ? 'ย้อนกลับคำสั่งล่าสุดแล้ว' : 'ทำซ้ำคำสั่งล่าสุดแล้ว')
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : isUndo ? 'ย้อนกลับไม่สำเร็จ' : 'ทำซ้ำไม่สำเร็จ')
      } finally {
        setIsBusy(false)
      }
    },
    [applyResponse, canRedo, canUndo, hasDocument, zoomPercent],
  )

  const closeDocument = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('ยังไม่ได้เปิดไฟล์ PDF')
      return
    }
    if (!(await confirmDiscardDirty())) {
      return
    }

    setIsBusy(true)
    setLastCommand('close_document')
    setStatusMessage('กำลังล้างจอผ่าน worker...')
    try {
      const response = await callWorker({ command: 'close_document' })
      applyResponse(response, response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setSelectedImagePath(null)
      setSelectedImageName('')
      setBridgeStatus('ready')
      setStatusMessage('ล้างจอแล้ว')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'ล้างจอไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, confirmDiscardDirty, hasDocument])

  const goToSearchResult = useCallback(
    async (resultIndex: number) => {
      if (!searchResults.length) {
        return
      }
      const nextIndex = (resultIndex + searchResults.length) % searchResults.length
      const result = searchResults[nextIndex]

      setIsBusy(true)
      setLastCommand('search_text')
      setStatusMessage('กำลังเปิดผลค้นหา...')
      try {
        const response = await callWorker({
          command: 'render_page',
          payload: { page_index: result.page_index, zoom: zoomPercent / 100 },
        })
        applyResponse(response, response)
        setBridgeStatus('ready')
        setActiveSearchIndex(nextIndex)
        setStatusMessage(`ผลค้นหา ${nextIndex + 1}/${searchResults.length}: ${result.label}`)
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : 'เปิดผลค้นหาไม่สำเร็จ')
      } finally {
        setIsBusy(false)
      }
    },
    [applyResponse, searchResults, zoomPercent],
  )

  const runSearch = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนค้นหา')
      return
    }

    const query = searchQuery.trim()
    if (!query) {
      setStatusMessage('กรุณากรอกคำค้นหา')
      return
    }

    setIsBusy(true)
    setLastCommand('search_text')
    setStatusMessage('กำลังค้นหาใน text layer...')
    try {
      const searchResponse = await callWorker({ command: 'search_text', payload: { query } })
      const results = searchResultsFrom(searchResponse)
      if (!results.length) {
        throw new Error('ไม่พบผลค้นหา')
      }

      const firstResult = results[0]
      const renderResponse = await callWorker({
        command: 'render_page',
        payload: { page_index: firstResult.page_index, zoom: zoomPercent / 100 },
      })
      applyResponse(renderResponse, renderResponse)
      setSearchResults(results)
      setActiveSearchIndex(0)
      setBridgeStatus('ready')
      setStatusMessage(`ค้นหา "${query}" พบ ${results.length} รายการ`)
    } catch (error) {
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'ค้นหาไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, searchQuery, zoomPercent])

  const addTextOverlay = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนวางข้อความ')
      return
    }

    const text = textOverlayValue.trim()
    if (!text) {
      setStatusMessage('กรุณากรอกข้อความก่อนวางลง PDF')
      return
    }

    const parsedFontSize = Number.parseInt(textOverlayFontSize, 10)
    const fontSize = Number.isFinite(parsedFontSize) ? Math.max(6, Math.min(96, parsedFontSize)) : 16

    setIsBusy(true)
    setLastCommand('add_text_overlay')
    setStatusMessage('กำลังวางข้อความผ่าน worker...')
    try {
      const response = await callWorker({
        command: 'batch',
        commands: [
          {
            command: 'add_text_overlay',
            payload: {
              selected_page_index: selectedPageIndex,
              text,
              font_size: fontSize,
              color: '#111111',
            },
          },
          { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('ready')
      setStatusMessage(`วางข้อความแล้ว: ${text}`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'วางข้อความไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, selectedPageIndex, textOverlayFontSize, textOverlayValue, zoomPercent])

  const addShapeOverlay = useCallback(
    async (command: 'draw_rectangle_overlay' | 'add_highlight_overlay') => {
      if (!hasDocument) {
        setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนวางรูปร่าง')
        return
      }

      const isHighlight = command === 'add_highlight_overlay'
      setIsBusy(true)
      setLastCommand(command)
      setStatusMessage(isHighlight ? 'กำลังวาง Highlight ผ่าน worker...' : 'กำลังวาดกล่องผ่าน worker...')
      try {
        const response = await callWorker({
          command: 'batch',
          commands: [
            {
              command,
              payload: {
                selected_page_index: selectedPageIndex,
                color: isHighlight ? '#fff176' : '#d32f2f',
                line_width: 2,
              },
            },
            { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
          ],
        })
        applyResponse(response)
        setSearchResults([])
        setActiveSearchIndex(-1)
        setBridgeStatus('ready')
        setStatusMessage(isHighlight ? 'วาง Highlight แล้ว' : 'วาดกล่องแล้ว')
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : isHighlight ? 'วาง Highlight ไม่สำเร็จ' : 'วาดกล่องไม่สำเร็จ')
      } finally {
        setIsBusy(false)
      }
    },
    [applyResponse, hasDocument, selectedPageIndex, zoomPercent],
  )

  const addRedactionOverlay = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนวาง Redaction')
      return
    }

    setIsBusy(true)
    setLastCommand('add_redaction_overlay')
    setStatusMessage('กำลังวาง Redaction ผ่าน worker...')
    try {
      const response = await callWorker({
        command: 'batch',
        commands: [
          { command: 'add_redaction_overlay', payload: { selected_page_index: selectedPageIndex } },
          { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('ready')
      setStatusMessage('วาง Redaction แล้ว ตรวจพื้นที่ก่อนบันทึก')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'วาง Redaction ไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, selectedPageIndex, zoomPercent])

  const replaceExistingText = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนแก้ข้อความเดิม')
      return
    }
    const searchText = replaceSearchText.trim()
    if (!searchText) {
      setStatusMessage('กรุณากรอกข้อความเดิมที่ต้องการค้นหา')
      return
    }

    const parsedFontSize = Number.parseInt(textOverlayFontSize, 10)
    const fontSize = Number.isFinite(parsedFontSize) ? Math.max(6, Math.min(96, parsedFontSize)) : 16
    setIsBusy(true)
    setLastCommand('replace_text')
    setStatusMessage('กำลังแก้ข้อความเดิมแบบ pending ผ่าน worker...')
    try {
      const response = await callWorker({
        command: 'batch',
        commands: [
          {
            command: 'replace_text',
            payload: {
              selected_page_index: selectedPageIndex,
              search_text: searchText,
              replacement_text: replaceTextValue,
              page_scope: replacePageScope,
              font_size: fontSize,
              color: '#111111',
            },
          },
          { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('ready')
      const replaced = responseFor(response, 'replace_text')
      const count = typeof replaced?.payload.operation_count === 'number' ? replaced.payload.operation_count : 0
      setStatusMessage(`เตรียมแก้ข้อความเดิมแล้ว ${count} รายการ`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'แก้ข้อความเดิมไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [
    applyResponse,
    hasDocument,
    replacePageScope,
    replaceSearchText,
    replaceTextValue,
    selectedPageIndex,
    textOverlayFontSize,
    zoomPercent,
  ])

  const chooseImageFile = useCallback(async (file: File | undefined) => {
    if (!file) {
      return
    }

    setIsBusy(true)
    setStatusMessage('กำลังนำรูปภาพเข้า local bridge...')
    try {
      const uploaded = await uploadLocalImage(file)
      setSelectedImagePath(uploaded.path)
      setSelectedImageName(uploaded.file_name)
      setBridgeStatus('ready')
      setStatusMessage(`เลือกรูปภาพแล้ว: ${uploaded.file_name}`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'เลือกรูปภาพไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [])

  const mergePdfFiles = useCallback(
    async (fileList: FileList | null) => {
      const files = Array.from(fileList ?? [])
      if (files.length === 0) {
        return
      }
      if (files.length < 2) {
        setStatusMessage('กรุณาเลือก PDF อย่างน้อย 2 ไฟล์สำหรับรวม')
        if (mergePdfInputRef.current) {
          mergePdfInputRef.current.value = ''
        }
        return
      }
      if (!(await confirmDiscardDirty())) {
        if (mergePdfInputRef.current) {
          mergePdfInputRef.current.value = ''
        }
        return
      }

      setIsBusy(true)
      setLastCommand('merge_pdfs')
      setStatusMessage(`กำลังรวม PDF ${files.length} ไฟล์ผ่าน worker...`)
      try {
        const uploadedFiles = await Promise.all(files.map((file) => uploadLocalPdf(file)))
        const response = await callWorker({
          command: 'batch',
          commands: [
            { command: 'merge_pdfs', payload: { source_paths: uploadedFiles.map((file) => file.path) } },
            { command: 'render_page', payload: { page_index: 0, zoom: zoomPercent / 100 } },
          ],
        })
        applyResponse(response)
        setSearchResults([])
        setActiveSearchIndex(-1)
        setBridgeStatus('ready')
        setStatusMessage(`รวม PDF แล้ว: ${uploadedFiles.length} ไฟล์`)
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : 'รวม PDF ไม่สำเร็จ')
      } finally {
        setIsBusy(false)
        if (mergePdfInputRef.current) {
          mergePdfInputRef.current.value = ''
        }
      }
    },
    [applyResponse, confirmDiscardDirty, zoomPercent],
  )

  const openPrintDialog = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนพิมพ์')
      return
    }

    setIsBusy(true)
    setLastCommand('list_printers')
    setStatusMessage('กำลังตรวจเครื่องพิมพ์ในเครื่อง...')
    try {
      const response = await callWorker({ command: 'list_printers' })
      const payloadPrinters = response.payload.printers
      const printerNames = Array.isArray(payloadPrinters)
        ? payloadPrinters.filter((name): name is string => typeof name === 'string' && name.trim().length > 0)
        : []
      const defaultPrinter = typeof response.payload.default_printer === 'string' ? response.payload.default_printer : ''
      setPrinters(printerNames)
      setSelectedPrinter(defaultPrinter && printerNames.includes(defaultPrinter) ? defaultPrinter : printerNames[0] || '')
      setPrintCopies('1')
      setIsPrintDialogOpen(true)
      setBridgeStatus('ready')
      setStatusMessage(printerNames.length > 0 ? 'เลือกเครื่องพิมพ์ก่อนส่งงานพิมพ์' : 'ไม่พบเครื่องพิมพ์ในเครื่องนี้')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'ตรวจเครื่องพิมพ์ไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [hasDocument])

  const closePrintDialog = useCallback(() => {
    setIsPrintDialogOpen(false)
    setStatusMessage('ปิดหน้าต่างพิมพ์')
  }, [])

  const submitPrintJob = useCallback(async () => {
    if (!selectedPrinter) {
      setStatusMessage('กรุณาเลือกเครื่องพิมพ์ก่อนพิมพ์')
      return
    }

    const parsedCopies = Number.parseInt(printCopies, 10)
    const copies = Number.isFinite(parsedCopies) ? Math.max(1, Math.min(99, parsedCopies)) : 1
    setIsBusy(true)
    setLastCommand('print_pdf')
    setStatusMessage(`กำลังส่งพิมพ์ → ${selectedPrinter}`)
    try {
      await callWorker({ command: 'print_pdf', payload: { printer_name: selectedPrinter, copies } })
      setBridgeStatus('ready')
      setIsPrintDialogOpen(false)
      setStatusMessage(`ส่งคำสั่งพิมพ์แล้ว → ${selectedPrinter}`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'ส่งพิมพ์ไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [printCopies, selectedPrinter])

  const clearConvertPoll = useCallback(() => {
    if (convertPollRef.current !== null) {
      clearInterval(convertPollRef.current)
      convertPollRef.current = null
    }
  }, [])

  useEffect(() => clearConvertPoll, [clearConvertPoll])

  const pollConvertJob = useCallback(
    (jobId: string) => {
      clearConvertPoll()
      const refreshJob = async () => {
        try {
          const job = await getConverterJob(jobId)
          setConvertJob(job)
          if (job.status === 'failed') {
            setConvertError(job.error || 'แปลงไฟล์ไม่สำเร็จ')
            clearConvertPoll()
          } else if (job.status === 'cancelled') {
            clearConvertPoll()
          } else if (job.status === 'succeeded') {
            clearConvertPoll()
          }
        } catch (error) {
          setConvertError(error instanceof Error ? error.message : 'ตรวจสถานะงานแปลงไม่สำเร็จ')
          clearConvertPoll()
        }
      }
      convertPollRef.current = setInterval(() => void refreshJob(), 1200)
      void refreshJob()
    },
    [clearConvertPoll],
  )

  const openConvertDialog = useCallback(() => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนแปลงเป็น Word/OCR')
      return
    }
    clearConvertPoll()
    setConvertJob(null)
    setConvertError(null)
    setConvertFormat('docx')
    setConvertPageScope('all')
    setIsConvertDialogOpen(true)
    setStatusMessage('เลือกรูปแบบไฟล์ที่ต้องการแปลง')
  }, [clearConvertPoll, hasDocument])

  const closeConvertDialog = useCallback(() => {
    clearConvertPoll()
    setIsConvertDialogOpen(false)
    setConvertJob(null)
    setConvertError(null)
    setStatusMessage('ปิดหน้าต่างแปลงไฟล์')
  }, [clearConvertPoll])

  const startConversion = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนแปลงเป็น Word/OCR')
      return
    }

    setIsConvertStarting(true)
    setConvertError(null)
    setConvertJob(null)
    setStatusMessage('กำลังเตรียมไฟล์ล่าสุดสำหรับแปลง...')
    try {
      // Staging save: convert must never read the live working copy directly,
      // and unsaved in-memory edits (rotate, overlays, etc.) would otherwise
      // be silently dropped. save_copy with no destination writes a fresh
      // temp snapshot that reflects everything currently in memory.
      const saveResponse = await callWorker({ command: 'save_copy' })
      const stagedPath = saveResponse.payload.destination_path
      if (typeof stagedPath !== 'string' || !stagedPath) {
        throw new Error('เตรียมไฟล์สำหรับแปลงไม่สำเร็จ')
      }

      const job = await startConverterJob(stagedPath, {
        output_format: convertFormat,
        start_page: convertPageScope === 'current' ? selectedPageIndex : 0,
        end_page: convertPageScope === 'current' ? selectedPageIndex + 1 : null,
      })
      setConvertJob(job)
      setStatusMessage('เริ่มแปลงไฟล์แล้ว กำลังประมวลผล...')
      pollConvertJob(job.id)
    } catch (error) {
      setConvertError(error instanceof Error ? error.message : 'เริ่มแปลงไฟล์ไม่สำเร็จ')
    } finally {
      setIsConvertStarting(false)
    }
  }, [convertFormat, convertPageScope, hasDocument, pollConvertJob, selectedPageIndex])

  const cancelConversion = useCallback(async () => {
    if (!convertJob) {
      return
    }
    clearConvertPoll()
    try {
      await cancelConverterJob(convertJob.id)
      const job = await getConverterJob(convertJob.id)
      setConvertJob(job)
      setStatusMessage('ยกเลิกงานแปลงไฟล์แล้ว')
    } catch (error) {
      setConvertError(error instanceof Error ? error.message : 'ยกเลิกงานแปลงไม่สำเร็จ')
    }
  }, [clearConvertPoll, convertJob])

  const retryConversion = useCallback(async () => {
    if (!convertJob) {
      return
    }
    setConvertError(null)
    try {
      const job = await retryConverterJob(convertJob.id)
      setConvertJob(job)
      setStatusMessage('กำลังลองแปลงไฟล์ใหม่...')
      pollConvertJob(job.id)
    } catch (error) {
      setConvertError(error instanceof Error ? error.message : 'ลองแปลงไฟล์ใหม่ไม่สำเร็จ')
    }
  }, [convertJob, pollConvertJob])

  const downloadConvertedFile = useCallback(async () => {
    if (!convertJob || convertJob.status !== 'succeeded') {
      return
    }
    try {
      const blob = await downloadConverterResult(convertJob)
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = converterResultFileName(convertJob)
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(objectUrl)
      setStatusMessage('ดาวน์โหลดไฟล์ที่แปลงแล้ว')
    } catch (error) {
      setConvertError(error instanceof Error ? error.message : 'ดาวน์โหลดไฟล์ไม่สำเร็จ')
    }
  }, [convertJob])

  const createSignatureImage = useCallback(async () => {
    const text = signatureText.trim()
    if (!text) {
      setStatusMessage('กรุณากรอกข้อความลายเซ็นภาพ')
      return
    }

    setIsBusy(true)
    setLastCommand('create_visual_signature')
    setStatusMessage('กำลังสร้างลายเซ็นภาพในเครื่อง...')
    try {
      const response = await callWorker({
        command: 'create_visual_signature',
        payload: { text, width_px: 720, color: '#1565c0' },
      })
      const imagePath = response.payload.image_path
      const fileName = response.payload.file_name
      if (typeof imagePath !== 'string') {
        throw new Error('สร้างลายเซ็นภาพไม่สำเร็จ')
      }
      setSelectedImagePath(imagePath)
      setSelectedImageName(typeof fileName === 'string' ? fileName : fileNameFromPath(imagePath))
      setBridgeStatus('ready')
      setStatusMessage(`สร้างลายเซ็นภาพแล้ว: ${typeof fileName === 'string' ? fileName : fileNameFromPath(imagePath)}`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'สร้างลายเซ็นภาพไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [signatureText])

  const addImageOverlay = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนวางรูปภาพ')
      return
    }
    if (!selectedImagePath) {
      setStatusMessage('กรุณาเลือกรูปภาพหรือสร้างลายเซ็นภาพก่อน')
      return
    }

    const parsedWidth = Number.parseInt(imageOverlayWidth, 10)
    const width = Number.isFinite(parsedWidth) ? Math.max(8, Math.min(500, parsedWidth)) : 140
    setIsBusy(true)
    setLastCommand('add_image_overlay')
    setStatusMessage('กำลังวางรูปภาพผ่าน worker...')
    try {
      const response = await callWorker({
        command: 'batch',
        commands: [
          {
            command: 'add_image_overlay',
            payload: {
              selected_page_index: selectedPageIndex,
              image_path: selectedImagePath,
              width,
            },
          },
          { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('ready')
      setStatusMessage(`วางรูปภาพแล้ว: ${selectedImageName || fileNameFromPath(selectedImagePath)}`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'วางรูปภาพไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, imageOverlayWidth, selectedImageName, selectedImagePath, selectedPageIndex, zoomPercent])

  const cropCurrentPage = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อน Crop หน้า')
      return
    }

    const parsedMargin = Number.parseFloat(cropMarginPercent)
    const marginPercent = Number.isFinite(parsedMargin) ? Math.max(0, Math.min(45, parsedMargin)) : 8
    setIsBusy(true)
    setLastCommand('crop_page')
    setStatusMessage('กำลัง Crop หน้าผ่าน worker...')
    try {
      const response = await callWorker({
        command: 'batch',
        commands: [
          {
            command: 'crop_page',
            payload: {
              selected_page_index: selectedPageIndex,
              margin_percent: marginPercent,
            },
          },
          { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('ready')
      setStatusMessage(`Crop หน้าแล้ว: ตัดขอบ ${marginPercent}%`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'Crop หน้าไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, cropMarginPercent, hasDocument, selectedPageIndex, zoomPercent])

  const loadMetadata = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนดูข้อมูลเอกสาร')
      return
    }

    setIsBusy(true)
    setLastCommand('list_metadata')
    setStatusMessage('กำลังโหลด metadata จาก worker...')
    try {
      const response = await callWorker({ command: 'list_metadata' })
      setMetadataFields(metadataFromPayload(response))
      setBridgeStatus('ready')
      setStatusMessage('โหลดข้อมูลเอกสารแล้ว')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'โหลดข้อมูลเอกสารไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [hasDocument])

  const saveMetadata = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนบันทึกข้อมูลเอกสาร')
      return
    }

    setIsBusy(true)
    setLastCommand('update_metadata')
    setStatusMessage('กำลังบันทึก metadata ลง working copy...')
    try {
      const response = await callWorker({
        command: 'update_metadata',
        payload: { updates: metadataFields },
      })
      applyResponse(response)
      setMetadataFields(metadataFromPayload(response))
      setBridgeStatus('ready')
      setStatusMessage('บันทึก metadata แล้ว กดบันทึกเพื่อสร้างไฟล์สำเนา')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'บันทึก metadata ไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, metadataFields])

  const loadFormFields = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนดูฟอร์ม')
      return
    }

    setIsBusy(true)
    setLastCommand('list_form_fields')
    setStatusMessage('กำลังโหลดฟอร์มจาก worker...')
    try {
      const response = await callWorker({ command: 'list_form_fields' })
      const fields = formFieldsFromPayload(response)
      setFormFields(fields)
      setBridgeStatus('ready')
      setStatusMessage(fields.length ? `โหลดฟอร์มแล้ว ${fields.length} ช่อง` : 'ไม่พบช่องฟอร์มที่แก้ไขได้')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'โหลดฟอร์มไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [hasDocument])

  const saveFormFields = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนบันทึกฟอร์ม')
      return
    }
    if (!formFields.length) {
      setStatusMessage('ยังไม่มีช่องฟอร์มให้บันทึก')
      return
    }

    setIsBusy(true)
    setLastCommand('update_form_fields')
    setStatusMessage('กำลังบันทึกฟอร์มลง working copy...')
    try {
      const updates = Object.fromEntries(formFields.map((field) => [String(field.xref), field.value]))
      const response = await callWorker({
        command: 'batch',
        commands: [
          { command: 'update_form_fields', payload: { updates } },
          { command: 'render_page', payload: { page_index: selectedPageIndex, zoom: zoomPercent / 100 } },
        ],
      })
      applyResponse(response)
      const updated = responseFor(response, 'update_form_fields')
      if (updated) {
        setFormFields(formFieldsFromPayload(updated))
      }
      setBridgeStatus('ready')
      setStatusMessage('บันทึกฟอร์มแล้ว กดบันทึกเพื่อสร้างไฟล์สำเนา')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'บันทึกฟอร์มไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, formFields, hasDocument, selectedPageIndex, zoomPercent])

  const updateFormFieldValue = useCallback((xref: number, value: string | boolean) => {
    setFormFields((current) => current.map((field) => (field.xref === xref ? { ...field, value } : field)))
  }, [])

  const exportJpg = useCallback(async () => {
    if (!hasDocument) {
      setStatusMessage('กรุณาเปิดไฟล์ PDF ก่อนส่งออก JPG')
      return
    }

    const dpi = Number.parseInt(jpgDpi, 10)
    const quality = Number.parseInt(jpgQuality, 10)
    setIsBusy(true)
    setLastCommand('export_jpg')
    setStatusMessage('กำลังส่งออก JPG ในเครื่อง...')
    try {
      const response = await callWorker({
        command: 'export_jpg',
        payload: {
          selected_page_index: selectedPageIndex,
          page_scope: jpgPageScope,
          dpi: Number.isFinite(dpi) ? dpi : 300,
          quality: Number.isFinite(quality) ? quality : 100,
          destination_dir: jpgOutputDir.trim(),
        },
      })
      applyResponse(response)
      setBridgeStatus('ready')
      const count = typeof response.payload.count === 'number' ? response.payload.count : 0
      const destDir = typeof response.payload.destination_dir === 'string' ? response.payload.destination_dir : jpgOutputDir
      const fileNames = Array.isArray(response.payload.file_names)
        ? response.payload.file_names.filter((name): name is string => typeof name === 'string')
        : []
      setStatusMessage(`ส่งออก JPG แล้ว ${count} ไฟล์ → ${destDir}${fileNames.length ? ` (${fileNames.slice(0, 2).join(', ')})` : ''}`)
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'ส่งออก JPG ไม่สำเร็จ')
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse, hasDocument, jpgDpi, jpgOutputDir, jpgPageScope, jpgQuality, selectedPageIndex])

  const batchExportJpgFiles = useCallback(
    async (fileList: FileList | null | undefined) => {
      const files = Array.from(fileList || []).filter((file) => file.name.toLowerCase().endsWith('.pdf'))
      if (!files.length) {
        setStatusMessage('กรุณาเลือก PDF อย่างน้อย 1 ไฟล์สำหรับ Batch JPG')
        return
      }

      const dpi = Number.parseInt(jpgDpi, 10)
      const quality = Number.parseInt(jpgQuality, 10)
      const fileNames = files.map((file) => file.name)
      setBatchJpgFileNames(fileNames)
      setActiveToolTab('export')
      setIsBusy(true)
      setLastCommand('batch_export_jpg')
      setStatusMessage(`กำลัง Batch JPG ${files.length} ไฟล์ในเครื่อง...`)
      try {
        const uploadedPdfs = await Promise.all(files.map((file) => uploadLocalPdf(file)))
        const response = await callWorker({
          command: 'batch_export_jpg',
          payload: {
            source_paths: uploadedPdfs.map((item) => item.path),
            dpi: Number.isFinite(dpi) ? dpi : 300,
            quality: Number.isFinite(quality) ? quality : 100,
            destination_dir: jpgOutputDir.trim(),
          },
        })
        applyResponse(response)
        setBridgeStatus('ready')
        const succeeded = typeof response.payload.succeeded === 'number' ? response.payload.succeeded : 0
        const failed = typeof response.payload.failed === 'number' ? response.payload.failed : 0
        const count = typeof response.payload.count === 'number' ? response.payload.count : 0
        const reportPath = typeof response.payload.report_path === 'string' ? response.payload.report_path : ''
        setStatusMessage(
          `Batch JPG เสร็จ: PDF สำเร็จ ${succeeded}/${files.length}, JPG ${count} ไฟล์${
            failed ? `, ล้มเหลว ${failed}` : ''
          }${reportPath ? ` | รายงาน: ${fileNameFromPath(reportPath)}` : ''}`,
        )
      } catch (error) {
        setBridgeStatus('error')
        setStatusMessage(error instanceof Error ? error.message : 'Batch JPG ไม่สำเร็จ')
      } finally {
        setIsBusy(false)
      }
    },
    [applyResponse, jpgDpi, jpgOutputDir, jpgQuality],
  )

  const openGuide = useCallback(() => {
    setIsGuideOpen(true)
    setStatusMessage('เปิดคู่มือการใช้งาน')
  }, [])

  const closeGuide = useCallback(() => {
    setIsGuideOpen(false)
    setStatusMessage('ปิดคู่มือการใช้งาน')
  }, [])

  const workerCommands = useMemo(
    () =>
      commandNames.map((name) => ({
        name,
        state: lastCommand === name ? 'active' : 'ready',
      })),
    [lastCommand],
  )

  return (
    <main ref={appShellRef} className={`app-shell ${isViewerExpanded ? 'is-viewer-expanded' : ''}`}>
      <Toolbar
        canRedo={canRedo}
        canUndo={canUndo}
        hasDocument={hasDocument}
        isViewerExpanded={isViewerExpanded}
        isBusy={isBusy}
        searchResultSummary={searchResultSummary}
        selectedPage={selectedPageNumber}
        totalPages={totalPages}
        zoom={zoomPercent}
        onFitHeight={() => void fitPageToViewer('height')}
        onFitWidth={() => void fitPageToViewer('width')}
        onCloseDocument={() => void closeDocument()}
        onNextPage={() => void renderPage(Math.min(totalPages - 1, selectedPageIndex + 1))}
        onOpenPdf={() => openPdfInputRef.current?.click()}
        onPreviousPage={() => void renderPage(Math.max(0, selectedPageIndex - 1))}
        onPrint={openPrintDialog}
        onRedo={() => void runPendingHistory('redo_pending')}
        onRunSearch={() => void runSearch()}
        onSaveCopy={() => void saveCopy()}
        onMergePdfs={() => mergePdfInputRef.current?.click()}
        onOpenGuide={openGuide}
        onToggleViewerExpanded={toggleViewerExpanded}
        onUndo={() => void runPendingHistory('undo_pending')}
        onZoomIn={() => void renderPage(selectedPageIndex, Math.min(maxZoomPercent, zoomPercent + 10))}
        onZoomOut={() => void renderPage(selectedPageIndex, Math.max(minZoomPercent, zoomPercent - 10))}
      />
      <section className="workspace">
        <PagePanel
          hasDocument={hasDocument}
          isBusy={isBusy}
          pages={pages}
          selectedPageIndex={selectedPageIndex}
          onDeleteSelectedPage={deleteSelectedPage}
          onDuplicateSelectedPage={duplicateSelectedPage}
          onExtractSelectedPage={extractSelectedPage}
          onMoveSelectedPage={moveSelectedPage}
          onRotateSelectedPage={rotateSelectedPage}
          onSelectPage={(pageIndex) => void renderPage(pageIndex)}
        />
        <Viewer
          bridgeStatus={bridgeStatus}
          isBusy={isBusy}
          previewUrl={previewUrl}
          stageRef={viewerStageRef}
          selectedPage={selectedPageNumber}
          statusMessage={statusMessage}
          zoom={zoomPercent}
        />
        <ToolPanel
          activeToolTab={activeToolTab}
          activeSearchIndex={activeSearchIndex}
          batchJpgFileNames={batchJpgFileNames}
          bridgeStatus={bridgeStatus}
          cropMarginPercent={cropMarginPercent}
          formFields={formFields}
          hasDocument={hasDocument}
          imageInputRef={imageInputRef}
          imageOverlayWidth={imageOverlayWidth}
          isBusy={isBusy}
          jpgDpi={jpgDpi}
          jpgOutputDir={jpgOutputDir}
          jpgPageScope={jpgPageScope}
          jpgQuality={jpgQuality}
          metadataFields={metadataFields}
          replacePageScope={replacePageScope}
          replaceSearchText={replaceSearchText}
          replaceTextValue={replaceTextValue}
          selectedImageName={selectedImageName}
          signatureText={signatureText}
          onAddHighlightOverlay={() => void addShapeOverlay('add_highlight_overlay')}
          onAddRedactionOverlay={() => void addRedactionOverlay()}
          onChooseBatchJpgFiles={() => batchJpgInputRef.current?.click()}
          onNextSearchResult={() => void goToSearchResult(activeSearchIndex + 1)}
          onPreviousSearchResult={() => void goToSearchResult(activeSearchIndex - 1)}
          onAddTextOverlay={() => void addTextOverlay()}
          onChooseImageFile={chooseImageFile}
          onCreateSignatureImage={() => void createSignatureImage()}
          onCropCurrentPage={() => void cropCurrentPage()}
          onDrawRectangleOverlay={() => void addShapeOverlay('draw_rectangle_overlay')}
          onExportJpg={() => void exportJpg()}
          onOpenConvertDialog={openConvertDialog}
          onFormFieldValueChange={updateFormFieldValue}
          onCropMarginPercentChange={setCropMarginPercent}
          onImageOverlayWidthChange={setImageOverlayWidth}
          onJpgDpiChange={setJpgDpi}
          onJpgOutputDirChange={setJpgOutputDir}
          onJpgPageScopeChange={setJpgPageScope}
          onJpgQualityChange={setJpgQuality}
          onLoadFormFields={() => void loadFormFields()}
          onLoadMetadata={() => void loadMetadata()}
          onMetadataChange={(field, value) => setMetadataFields((current) => ({ ...current, [field]: value }))}
          onPlaceImageOverlay={() => void addImageOverlay()}
          onReplaceExistingText={() => void replaceExistingText()}
          onRunSearch={() => void runSearch()}
          onSaveFormFields={() => void saveFormFields()}
          onSaveMetadata={() => void saveMetadata()}
          onSearchQueryChange={setSearchQuery}
          onSelectSearchResult={(resultIndex) => void goToSearchResult(resultIndex)}
          onReplacePageScopeChange={setReplacePageScope}
          onReplaceSearchTextChange={setReplaceSearchText}
          onReplaceTextValueChange={setReplaceTextValue}
          onSignatureTextChange={setSignatureText}
          onTextOverlayChange={setTextOverlayValue}
          onTextOverlayFontSizeChange={setTextOverlayFontSize}
          onToolTabChange={setActiveToolTab}
          searchQuery={searchQuery}
          searchResults={searchResults}
          textOverlayFontSize={textOverlayFontSize}
          textOverlayValue={textOverlayValue}
          workerCommands={workerCommands}
        />
      </section>
      <StatusBar
        dirty={dirty}
        documentPath={documentPath}
        selectedPage={selectedPageNumber}
        statusMessage={statusMessage}
        totalPages={totalPages}
        zoom={zoomPercent}
      />
      <input
        ref={openPdfInputRef}
        accept="application/pdf,.pdf"
        className="file-input"
        onChange={(event) => void openPdfFile(event.currentTarget.files?.[0])}
        type="file"
      />
      <input
        ref={mergePdfInputRef}
        accept="application/pdf,.pdf"
        className="file-input"
        multiple
        onChange={(event) => void mergePdfFiles(event.currentTarget.files)}
        type="file"
      />
      <input
        ref={batchJpgInputRef}
        accept="application/pdf,.pdf"
        className="file-input"
        multiple
        onChange={(event) => {
          void batchExportJpgFiles(event.currentTarget.files)
          event.currentTarget.value = ''
        }}
        type="file"
      />
      {isPrintDialogOpen ? (
        <PrintDialog
          copies={printCopies}
          isBusy={isBusy}
          printers={printers}
          selectedPrinter={selectedPrinter}
          onClose={closePrintDialog}
          onCopiesChange={setPrintCopies}
          onPrinterChange={setSelectedPrinter}
          onSubmit={() => void submitPrintJob()}
        />
      ) : null}
      {isGuideOpen ? <GuideDialog onClose={closeGuide} /> : null}
      {isDiscardDialogOpen ? <DiscardChangesDialog onCancel={() => answerDiscardPrompt(false)} onConfirm={() => answerDiscardPrompt(true)} /> : null}
      {isConvertDialogOpen ? (
        <ConvertDialog
          error={convertError}
          format={convertFormat}
          isStarting={isConvertStarting}
          job={convertJob}
          pageScope={convertPageScope}
          onCancel={() => void cancelConversion()}
          onClose={closeConvertDialog}
          onDownload={() => void downloadConvertedFile()}
          onFormatChange={setConvertFormat}
          onPageScopeChange={setConvertPageScope}
          onRetry={() => void retryConversion()}
          onStart={() => void startConversion()}
        />
      ) : null}
    </main>
  )
}

function Toolbar({
  canRedo,
  canUndo,
  hasDocument,
  isViewerExpanded,
  isBusy,
  searchResultSummary,
  selectedPage,
  totalPages,
  zoom,
  onFitHeight,
  onFitWidth,
  onCloseDocument,
  onNextPage,
  onOpenPdf,
  onPreviousPage,
  onPrint,
  onRedo,
  onRunSearch,
  onSaveCopy,
  onMergePdfs,
  onOpenGuide,
  onToggleViewerExpanded,
  onUndo,
  onZoomIn,
  onZoomOut,
}: {
  canRedo: boolean
  canUndo: boolean
  hasDocument: boolean
  isViewerExpanded: boolean
  isBusy: boolean
  searchResultSummary: string
  selectedPage: number
  totalPages: number
  zoom: number
  onFitHeight: () => void
  onFitWidth: () => void
  onCloseDocument: () => void
  onNextPage: () => void
  onOpenPdf: () => void
  onPreviousPage: () => void
  onPrint: () => void
  onRedo: () => void
  onRunSearch: () => void
  onSaveCopy: () => void
  onMergePdfs: () => void
  onOpenGuide: () => void
  onToggleViewerExpanded: () => void
  onUndo: () => void
  onZoomIn: () => void
  onZoomOut: () => void
}) {
  return (
    <header className="toolbar" aria-label="แถบเครื่องมือแก้ไข PDF">
      <ToolbarGroup label="ไฟล์">
        <ToolButton icon={<FolderOpen />} label="เปิดไฟล์" active disabled={isBusy} onClick={onOpenPdf} />
        <ToolButton icon={<X />} label="ล้างจอ" disabled={isBusy || !hasDocument} onClick={onCloseDocument} />
        <ToolButton icon={<Save />} label="บันทึก" disabled={isBusy || !hasDocument} onClick={onSaveCopy} />
        <ToolButton icon={<Printer />} label="พิมพ์" disabled={isBusy || !hasDocument} onClick={onPrint} />
      </ToolbarGroup>
      <ToolbarGroup label="แก้ไข">
        <ToolButton icon={<Undo2 />} label="ย้อนกลับ" disabled={isBusy || !canUndo} onClick={onUndo} />
        <ToolButton icon={<Redo2 />} label="ทำซ้ำ" disabled={isBusy || !canRedo} onClick={onRedo} />
        <ToolButton icon={<FileDown />} label="รวม PDF" disabled={isBusy} onClick={onMergePdfs} />
      </ToolbarGroup>
      <ToolbarGroup label="มุมมอง">
        <ToolButton icon={<ZoomOut />} label="ซูม-" disabled={isBusy || !hasDocument} onClick={onZoomOut} />
        <div className="zoom-readout" aria-live="polite">
          {zoom}%
        </div>
        <ToolButton icon={<ZoomIn />} label="ซูม+" disabled={isBusy || !hasDocument} onClick={onZoomIn} />
        <ToolButton icon={<Maximize2 />} label="พอดีกว้าง" wide disabled={isBusy || !hasDocument} onClick={onFitWidth} />
        <ToolButton icon={<Maximize2 />} label="พอดีบน-ล่าง" wide disabled={isBusy || !hasDocument} onClick={onFitHeight} />
        <ToolButton
          icon={<Maximize2 />}
          label={isViewerExpanded ? 'ย่อจอ' : 'เต็มจอ'}
          disabled={isBusy}
          onClick={onToggleViewerExpanded}
        />
      </ToolbarGroup>
      <ToolbarGroup label="ไปที่หน้า">
        <ToolButton
          icon={<ArrowLeft />}
          label="ก่อน"
          disabled={isBusy || !hasDocument || selectedPage <= 1}
          onClick={onPreviousPage}
        />
        <div className="page-control" aria-live="polite">
          <span>{selectedPage}</span>
          <small>/ {totalPages}</small>
        </div>
        <ToolButton
          icon={<ArrowRight />}
          label="ถัด"
          disabled={isBusy || !hasDocument || selectedPage >= totalPages}
          onClick={onNextPage}
        />
      </ToolbarGroup>
      <ToolbarGroup label="ช่วยเหลือ">
        <ToolButton icon={<Search />} label="ค้นหา" disabled={isBusy || !hasDocument} onClick={onRunSearch} />
        {searchResultSummary ? <div className="search-readout">{searchResultSummary}</div> : null}
        <ToolButton icon={<MousePointer2 />} label="คู่มือ" onClick={onOpenGuide} />
      </ToolbarGroup>
    </header>
  )
}

function PrintDialog({
  copies,
  isBusy,
  printers,
  selectedPrinter,
  onClose,
  onCopiesChange,
  onPrinterChange,
  onSubmit,
}: {
  copies: string
  isBusy: boolean
  printers: string[]
  selectedPrinter: string
  onClose: () => void
  onCopiesChange: (value: string) => void
  onPrinterChange: (value: string) => void
  onSubmit: () => void
}) {
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isBusy) {
          onClose()
        }
      }}
      role="presentation"
    >
      <section aria-labelledby="print-title" aria-modal="true" className="print-dialog" role="dialog">
        <div className="guide-heading">
          <div>
            <b id="print-title">พิมพ์เอกสาร</b>
            <span>เลือกเครื่องพิมพ์ในเครื่องก่อนส่งคำสั่ง</span>
          </div>
          <button aria-label="ปิดหน้าต่างพิมพ์" className="icon-action" disabled={isBusy} onClick={onClose} type="button">
            <X size={18} />
          </button>
        </div>
        <div className="print-content">
          <label className="print-field">
            <span>เครื่องพิมพ์</span>
            <select
              disabled={isBusy || printers.length === 0}
              onChange={(event) => onPrinterChange(event.currentTarget.value)}
              value={selectedPrinter}
            >
              {printers.length === 0 ? <option value="">ไม่พบเครื่องพิมพ์</option> : null}
              {printers.map((printer) => (
                <option key={printer} value={printer}>
                  {printer}
                </option>
              ))}
            </select>
          </label>
          <label className="print-field">
            <span>จำนวนชุด</span>
            <input
              disabled={isBusy}
              max="99"
              min="1"
              onChange={(event) => onCopiesChange(event.currentTarget.value)}
              type="number"
              value={copies}
            />
          </label>
          <div className="dialog-actions">
            <button className="secondary-action" disabled={isBusy} onClick={onClose} type="button">
              ยกเลิก
            </button>
            <button className="primary-action" disabled={isBusy || !selectedPrinter} onClick={onSubmit} type="button">
              พิมพ์
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

function ConvertDialog({
  error,
  format,
  isStarting,
  job,
  pageScope,
  onCancel,
  onClose,
  onDownload,
  onFormatChange,
  onPageScopeChange,
  onRetry,
  onStart,
}: {
  error: string | null
  format: ConverterOutputFormat
  isStarting: boolean
  job: ConverterJob | null
  pageScope: PageScope
  onCancel: () => void
  onClose: () => void
  onDownload: () => void
  onFormatChange: (value: ConverterOutputFormat) => void
  onPageScopeChange: (value: PageScope) => void
  onRetry: () => void
  onStart: () => void
}) {
  const isRunning = job?.status === 'queued' || job?.status === 'running'
  const isDone = job?.status === 'succeeded'
  const isFailed = job?.status === 'failed'
  const isCancelled = job?.status === 'cancelled'
  const canCloseNow = !isRunning
  const progressLabel = job ? `${Math.round(job.progress_percent)}%` : '0%'
  const statusLabel =
    job?.status === 'queued'
      ? 'อยู่ในคิว...'
      : job?.status === 'running'
        ? `กำลังแปลง... (${job.done_pages}/${job.total_pages || '?'} หน้า)`
        : isDone
          ? 'แปลงไฟล์เสร็จแล้ว'
          : isFailed
            ? 'แปลงไฟล์ไม่สำเร็จ'
            : isCancelled
              ? 'ยกเลิกงานแปลงแล้ว'
            : ''

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && canCloseNow) {
          onClose()
        }
      }}
      role="presentation"
    >
      <section aria-labelledby="convert-title" aria-modal="true" className="print-dialog convert-dialog" role="dialog">
        <div className="guide-heading">
          <div>
            <b id="convert-title">แปลงเป็น Word/OCR</b>
            <span>ประมวลผลในเครื่องนี้ทั้งหมด ไม่ส่งไฟล์ออกอินเทอร์เน็ต</span>
          </div>
          <button
            aria-label="ปิดหน้าต่างแปลงไฟล์"
            className="icon-action"
            disabled={!canCloseNow}
            onClick={onClose}
            type="button"
          >
            <X size={18} />
          </button>
        </div>
        <div className="print-content">
          {!job ? (
            <>
              <label className="print-field">
                <span>รูปแบบไฟล์ผลลัพธ์</span>
                <select
                  disabled={isStarting}
                  onChange={(event) => onFormatChange(event.currentTarget.value as ConverterOutputFormat)}
                  value={format}
                >
                  <option value="docx">Word (.docx)</option>
                  <option value="xlsx">Excel (.xlsx)</option>
                  <option value="pdf">PDF ค้นหาได้ (.pdf)</option>
                  <option value="jpg">รูปภาพ JPG (.zip)</option>
                </select>
              </label>
              <label className="print-field">
                <span>ขอบเขตหน้า</span>
                <select
                  disabled={isStarting}
                  onChange={(event) => onPageScopeChange(event.currentTarget.value as PageScope)}
                  value={pageScope}
                >
                  <option value="all">ทุกหน้าในไฟล์นี้</option>
                  <option value="current">เฉพาะหน้านี้</option>
                </select>
              </label>
              {error ? <p className="dialog-message convert-error">{error}</p> : null}
              <div className="dialog-actions">
                <button className="secondary-action" disabled={isStarting} onClick={onClose} type="button">
                  ยกเลิก
                </button>
                <button className="primary-action" disabled={isStarting} onClick={onStart} type="button">
                  {isStarting ? 'กำลังเตรียมไฟล์...' : 'เริ่มแปลง'}
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="dialog-message">{statusLabel}</p>
              {isRunning || isDone ? (
                <div className="convert-progress-track" role="progressbar" aria-valuenow={Math.round(job.progress_percent)} aria-valuemin={0} aria-valuemax={100}>
                  <div className="convert-progress-fill" style={{ width: isDone ? '100%' : progressLabel }} />
                </div>
              ) : null}
              {isFailed && job.error ? <p className="dialog-message convert-error">{job.error}</p> : null}
              {error ? <p className="dialog-message convert-error">{error}</p> : null}
              <div className="dialog-actions">
                {isRunning ? (
                  <>
                    <button className="secondary-action" onClick={onCancel} type="button">
                      <Ban size={15} />
                      ยกเลิกงาน
                    </button>
                    <button className="primary-action" disabled type="button">
                      {progressLabel}
                    </button>
                  </>
                ) : null}
                {isDone ? (
                  <>
                    <button className="secondary-action" onClick={onClose} type="button">
                      ปิด
                    </button>
                    <button className="primary-action" onClick={onDownload} type="button">
                      <FileDown size={15} />
                      ดาวน์โหลดไฟล์
                    </button>
                  </>
                ) : null}
                {isFailed ? (
                  <>
                    <button className="secondary-action" onClick={onClose} type="button">
                      ปิด
                    </button>
                    <button className="primary-action" onClick={onRetry} type="button">
                      <RefreshCw size={15} />
                      ลองใหม่
                    </button>
                  </>
                ) : null}
                {isCancelled ? (
                  <>
                    <button className="secondary-action" onClick={onClose} type="button">
                      ปิด
                    </button>
                    <button className="primary-action" onClick={onRetry} type="button">
                      <RefreshCw size={15} />
                      ลองใหม่
                    </button>
                  </>
                ) : null}
              </div>
            </>
          )}
        </div>
      </section>
    </div>
  )
}

function DiscardChangesDialog({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onCancel()
        }
      }}
      role="presentation"
    >
      <section aria-labelledby="discard-title" aria-modal="true" className="discard-dialog" role="dialog">
        <div className="guide-heading">
          <div>
            <b id="discard-title">มีงานที่ยังไม่ได้บันทึก</b>
            <span>เลือกทิ้งงานเฉพาะเมื่อแน่ใจว่าจะเปิดเอกสารใหม่หรือล้างจอ</span>
          </div>
          <button aria-label="ยกเลิกการทิ้งงาน" className="icon-action" onClick={onCancel} type="button">
            <X size={18} />
          </button>
        </div>
        <div className="print-content">
          <p className="dialog-message">{unsavedChangesMessage}</p>
          <div className="dialog-actions">
            <button className="secondary-action" onClick={onCancel} type="button">
              ยกเลิก
            </button>
            <button className="danger-action" onClick={onConfirm} type="button">
              ทิ้งงาน
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

function GuideDialog({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose()
        }
      }}
      role="presentation"
    >
      <section aria-labelledby="guide-title" aria-modal="true" className="guide-dialog" role="dialog">
        <div className="guide-heading">
          <div>
            <b id="guide-title">คู่มือการใช้งาน</b>
            <span>React shell ทำงานผ่าน worker ในเครื่อง</span>
          </div>
          <button aria-label="ปิดคู่มือ" className="icon-action" onClick={onClose} type="button">
            <X size={18} />
          </button>
        </div>
        <div className="guide-content">
          <section>
            <h2>เริ่มต้น</h2>
            <p>กด เปิดไฟล์ เพื่อโหลด PDF จากนั้นใช้ปุ่มหน้า ซูม พอดีกว้าง และพอดีบน-ล่างเพื่อจัดมุมมอง</p>
          </section>
          <section>
            <h2>จัดการหน้า</h2>
            <p>เลือกหน้าจากรายการด้านซ้ายเพื่อย้าย ทำซ้ำ ลบ Crop หรือแยกหน้า แล้วตรวจภาพ preview ก่อนบันทึก</p>
          </section>
          <section>
            <h2>วางข้อมูล</h2>
            <p>เพิ่มข้อความ รูปภาพ ลายเซ็นภาพ กล่อง และ Highlight ได้จากแผงเครื่องมือด้านขวา</p>
          </section>
          <section>
            <h2>ค้นหาและบันทึก</h2>
            <p>ค้นหาจาก text layer ของ PDF แล้วกด บันทึก เพื่อสร้างไฟล์สำเนา ทุกงานทำในเครื่องและไม่เขียนทับต้นฉบับ</p>
          </section>
        </div>
      </section>
    </div>
  )
}

function ToolbarGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="toolbar-group">
      <div className="toolbar-label">{label}</div>
      <div className="toolbar-actions">{children}</div>
    </div>
  )
}

function ToolButton({
  icon,
  label,
  active = false,
  disabled = false,
  muted = false,
  wide = false,
  onClick,
}: {
  icon: ReactNode
  label: string
  active?: boolean
  disabled?: boolean
  muted?: boolean
  wide?: boolean
  onClick?: () => void
}) {
  return (
    <button
      className={`tool-button ${active ? 'is-active' : ''} ${muted ? 'is-muted' : ''} ${wide ? 'is-wide' : ''}`}
      disabled={disabled || muted}
      onClick={onClick}
      type="button"
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

function PagePanel({
  hasDocument,
  isBusy,
  pages,
  selectedPageIndex,
  onDeleteSelectedPage,
  onDuplicateSelectedPage,
  onExtractSelectedPage,
  onMoveSelectedPage,
  onRotateSelectedPage,
  onSelectPage,
}: {
  hasDocument: boolean
  isBusy: boolean
  pages: number[]
  selectedPageIndex: number
  onDeleteSelectedPage: () => void
  onDuplicateSelectedPage: () => void
  onExtractSelectedPage: () => void
  onMoveSelectedPage: (direction: -1 | 1) => void
  onRotateSelectedPage: (degrees: -90 | 90) => void
  onSelectPage: (pageIndex: number) => void
}) {
  return (
    <aside className="page-panel" aria-label="รายการหน้า">
      <div className="panel-heading">
        <div>
          <b>รายการหน้า</b>
          <span>{pages.length} หน้า</span>
        </div>
        <Layers size={18} />
      </div>
      <div className="page-list">
        {pages.map((_pageMarker, pageIndex) => (
          <button
            key={pageIndex}
            className={`page-row ${pageIndex === selectedPageIndex ? 'is-selected' : ''}`}
            disabled={isBusy || !hasDocument}
            onClick={() => onSelectPage(pageIndex)}
            type="button"
          >
            <span>หน้า {pageIndex + 1}</span>
            {pageIndex === selectedPageIndex ? <small>ปัจจุบัน</small> : null}
          </button>
        ))}
      </div>
      <div className="page-actions-grid">
        <button
          disabled={isBusy || !hasDocument || selectedPageIndex <= 0}
          onClick={() => onMoveSelectedPage(-1)}
          type="button"
        >
          <ArrowUp size={16} />
          ขึ้น
        </button>
        <button
          disabled={isBusy || !hasDocument || selectedPageIndex >= pages.length - 1}
          onClick={() => onMoveSelectedPage(1)}
          type="button"
        >
          <ArrowDown size={16} />
          ลง
        </button>
      </div>
      <div className="page-actions-grid">
        <button disabled={isBusy || !hasDocument} onClick={() => onRotateSelectedPage(-90)} type="button">
          <RotateCcw size={16} />
          หมุนซ้าย
        </button>
        <button disabled={isBusy || !hasDocument} onClick={() => onRotateSelectedPage(90)} type="button">
          <RotateCw size={16} />
          หมุนขวา
        </button>
      </div>
      <button
        className="secondary-action"
        disabled={isBusy || !hasDocument}
        onClick={onDuplicateSelectedPage}
        type="button"
      >
        ทำซ้ำหน้า
      </button>
      <button
        className="secondary-action"
        disabled={isBusy || !hasDocument}
        onClick={onExtractSelectedPage}
        type="button"
      >
        แยกหน้านี้
      </button>
      <button
        className="danger-action"
        disabled={isBusy || !hasDocument || pages.length <= 1}
        onClick={onDeleteSelectedPage}
        type="button"
      >
        ลบหน้า
      </button>
    </aside>
  )
}

function Viewer({
  bridgeStatus,
  isBusy,
  previewUrl,
  stageRef,
  selectedPage,
  statusMessage,
  zoom,
}: {
  bridgeStatus: BridgeStatus
  isBusy: boolean
  previewUrl: string | null
  stageRef: RefObject<HTMLDivElement | null>
  selectedPage: number
  statusMessage: string
  zoom: number
}) {
  const bottomScrollRef = useRef<HTMLDivElement | null>(null)
  const [horizontalTrackWidth, setHorizontalTrackWidth] = useState(0)

  useEffect(() => {
    const stage = stageRef.current
    const bottomScroll = bottomScrollRef.current
    if (!stage || !bottomScroll) {
      return
    }

    let isSyncing = false
    let animationFrame = 0

    const syncMetrics = () => {
      setHorizontalTrackWidth(Math.max(stage.scrollWidth, stage.clientWidth))
      if (bottomScroll.scrollLeft !== stage.scrollLeft) {
        bottomScroll.scrollLeft = stage.scrollLeft
      }
    }

    const scheduleSyncMetrics = () => {
      window.cancelAnimationFrame(animationFrame)
      animationFrame = window.requestAnimationFrame(syncMetrics)
    }

    const syncFromStage = () => {
      if (isSyncing) {
        return
      }
      isSyncing = true
      bottomScroll.scrollLeft = stage.scrollLeft
      isSyncing = false
    }

    const previewImage = stage.querySelector('.pdf-preview-image')
    const documentPage = stage.querySelector('.document-page')
    const resizeObserver = new ResizeObserver(scheduleSyncMetrics)
    const metricTimers = [120, 400, 1000].map((delay) => window.setTimeout(syncMetrics, delay))
    resizeObserver.observe(stage)
    if (documentPage instanceof Element) {
      resizeObserver.observe(documentPage)
    }
    if (previewImage instanceof HTMLImageElement) {
      resizeObserver.observe(previewImage)
      previewImage.addEventListener('load', scheduleSyncMetrics)
      if (previewImage.complete) {
        scheduleSyncMetrics()
      }
    }

    stage.addEventListener('scroll', syncFromStage, { passive: true })
    window.addEventListener('resize', scheduleSyncMetrics)
    scheduleSyncMetrics()

    return () => {
      window.cancelAnimationFrame(animationFrame)
      metricTimers.forEach((timer) => window.clearTimeout(timer))
      resizeObserver.disconnect()
      if (previewImage instanceof HTMLImageElement) {
        previewImage.removeEventListener('load', scheduleSyncMetrics)
      }
      stage.removeEventListener('scroll', syncFromStage)
      window.removeEventListener('resize', scheduleSyncMetrics)
    }
  }, [previewUrl, stageRef, zoom])

  return (
    <section className="viewer" aria-label="พื้นที่แสดง PDF">
      <div ref={stageRef} className="viewer-stage" style={{ '--viewer-zoom': `${zoom / 100}` } as CSSProperties}>
        <div className={`document-page ${previewUrl ? 'is-worker-preview' : 'is-fallback'}`}>
          {previewUrl ? (
            <img className="pdf-preview-image" src={previewUrl} alt={`ตัวอย่าง PDF หน้า ${selectedPage}`} />
          ) : (
            <FallbackPage />
          )}
        </div>
        <div className={`viewer-toast is-${bridgeStatus}`} aria-live="polite">
          {isBusy ? 'กำลังทำงาน...' : statusMessage}
        </div>
      </div>
      <div
        ref={bottomScrollRef}
        className="bottom-scrollbar"
        aria-label="เลื่อน PDF แนวนอน"
        onScroll={(event) => {
          const stage = stageRef.current
          if (stage && Math.abs(stage.scrollLeft - event.currentTarget.scrollLeft) > 0.5) {
            stage.scrollLeft = event.currentTarget.scrollLeft
          }
        }}
        onWheel={(event) => {
          const delta = event.deltaX || event.deltaY
          if (delta === 0) {
            return
          }
          event.preventDefault()
          event.currentTarget.scrollLeft += delta
          const stage = stageRef.current
          if (stage) {
            stage.scrollLeft = event.currentTarget.scrollLeft
          }
        }}
        tabIndex={0}
      >
        <div className="bottom-scrollbar-track" style={{ width: `${horizontalTrackWidth}px` }}></div>
      </div>
    </section>
  )
}

function FallbackPage() {
  return (
    <>
      <div className="slide-visual" aria-hidden="true">
        <div className="solar-card large" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <FolderOpen style={{ width: 64, height: 64, color: 'var(--accent-color, #3b82f6)' }} />
        </div>
      </div>
      <h1>โปรแกรมแก้ไข PDF ภาษาไทย</h1>
      <p>
        กรุณากดปุ่ม "เปิดไฟล์" บนแถบเครื่องมือ เพื่อเลือกเอกสาร PDF ที่ต้องการดูหรือแก้ไข
        หรือดับเบิลคลิกไฟล์ .pdf ในเครื่องคอมพิวเตอร์เพื่อเปิดใช้งานทันที
      </p>
    </>
  )
}

function ToolPanel({
  activeToolTab,
  activeSearchIndex,
  batchJpgFileNames,
  bridgeStatus,
  cropMarginPercent,
  formFields,
  hasDocument,
  imageInputRef,
  imageOverlayWidth,
  isBusy,
  jpgDpi,
  jpgOutputDir,
  jpgPageScope,
  jpgQuality,
  metadataFields,
  replacePageScope,
  replaceSearchText,
  replaceTextValue,
  selectedImageName,
  signatureText,
  onAddHighlightOverlay,
  onAddRedactionOverlay,
  onAddTextOverlay,
  onChooseBatchJpgFiles,
  onChooseImageFile,
  onCreateSignatureImage,
  onCropCurrentPage,
  onCropMarginPercentChange,
  onDrawRectangleOverlay,
  onExportJpg,
  onOpenConvertDialog,
  onFormFieldValueChange,
  onImageOverlayWidthChange,
  onJpgDpiChange,
  onJpgOutputDirChange,
  onJpgPageScopeChange,
  onJpgQualityChange,
  onLoadFormFields,
  onLoadMetadata,
  onMetadataChange,
  onNextSearchResult,
  onPlaceImageOverlay,
  onPreviousSearchResult,
  onReplaceExistingText,
  onReplacePageScopeChange,
  onReplaceSearchTextChange,
  onReplaceTextValueChange,
  onRunSearch,
  onSaveFormFields,
  onSaveMetadata,
  onSearchQueryChange,
  onSelectSearchResult,
  onSignatureTextChange,
  onTextOverlayChange,
  onTextOverlayFontSizeChange,
  onToolTabChange,
  searchQuery,
  searchResults,
  textOverlayFontSize,
  textOverlayValue,
  workerCommands,
}: {
  activeToolTab: ToolTab
  activeSearchIndex: number
  batchJpgFileNames: string[]
  bridgeStatus: BridgeStatus
  cropMarginPercent: string
  formFields: WorkerFormField[]
  hasDocument: boolean
  imageInputRef: RefObject<HTMLInputElement | null>
  imageOverlayWidth: string
  isBusy: boolean
  jpgDpi: string
  jpgOutputDir: string
  jpgPageScope: PageScope
  jpgQuality: string
  metadataFields: MetadataFields
  replacePageScope: PageScope
  replaceSearchText: string
  replaceTextValue: string
  selectedImageName: string
  signatureText: string
  onAddHighlightOverlay: () => void
  onAddRedactionOverlay: () => void
  onAddTextOverlay: () => void
  onChooseBatchJpgFiles: () => void
  onChooseImageFile: (file: File | undefined) => Promise<void>
  onCreateSignatureImage: () => void
  onCropCurrentPage: () => void
  onCropMarginPercentChange: (value: string) => void
  onDrawRectangleOverlay: () => void
  onExportJpg: () => void
  onOpenConvertDialog: () => void
  onFormFieldValueChange: (xref: number, value: string | boolean) => void
  onImageOverlayWidthChange: (value: string) => void
  onJpgDpiChange: (value: string) => void
  onJpgOutputDirChange: (value: string) => void
  onJpgPageScopeChange: (value: PageScope) => void
  onJpgQualityChange: (value: string) => void
  onLoadFormFields: () => void
  onLoadMetadata: () => void
  onMetadataChange: (field: keyof MetadataFields, value: string) => void
  onNextSearchResult: () => void
  onPlaceImageOverlay: () => void
  onPreviousSearchResult: () => void
  onReplaceExistingText: () => void
  onReplacePageScopeChange: (value: PageScope) => void
  onReplaceSearchTextChange: (value: string) => void
  onReplaceTextValueChange: (value: string) => void
  onRunSearch: () => void
  onSaveFormFields: () => void
  onSaveMetadata: () => void
  onSearchQueryChange: (value: string) => void
  onSelectSearchResult: (resultIndex: number) => void
  onSignatureTextChange: (value: string) => void
  onTextOverlayChange: (value: string) => void
  onTextOverlayFontSizeChange: (value: string) => void
  onToolTabChange: (value: ToolTab) => void
  searchQuery: string
  searchResults: WorkerSearchResult[]
  textOverlayFontSize: string
  textOverlayValue: string
  workerCommands: Array<{ name: WorkerCommandName; state: string }>
}) {
  const batchJpgLabel = batchJpgFileNames.length
    ? `Batch: ${batchJpgFileNames.length} ไฟล์ (${batchJpgFileNames.slice(0, 2).join(', ')}${
        batchJpgFileNames.length > 2 ? ', ...' : ''
      })`
    : 'Batch: ยังไม่ได้เลือกไฟล์'

  return (
    <aside className="tool-panel" aria-label="เครื่องมือ">
      <div className="panel-heading">
        <div>
          <b>เครื่องมือ</b>
          <span>Bridge: {bridgeStatus}</span>
        </div>
        <FileText size={18} />
      </div>
      <div className="tool-tabs" role="tablist" aria-label="หมวดเครื่องมือ">
        <button
          className={activeToolTab === 'search' ? 'is-selected' : ''}
          onClick={() => onToolTabChange('search')}
          role="tab"
          type="button"
        >
          ค้นหา
        </button>
        <button
          className={activeToolTab === 'edit' ? 'is-selected' : ''}
          onClick={() => onToolTabChange('edit')}
          role="tab"
          type="button"
        >
          แก้ไข
        </button>
        <button
          className={activeToolTab === 'data' ? 'is-selected' : ''}
          onClick={() => onToolTabChange('data')}
          role="tab"
          type="button"
        >
          ข้อมูล
        </button>
        <button
          className={activeToolTab === 'export' ? 'is-selected' : ''}
          onClick={() => onToolTabChange('export')}
          role="tab"
          type="button"
        >
          ส่งออก
        </button>
        <button
          className={activeToolTab === 'status' ? 'is-selected' : ''}
          onClick={() => onToolTabChange('status')}
          role="tab"
          type="button"
        >
          สถานะ
        </button>
      </div>
      {activeToolTab === 'search' ? (
      <section className="tool-section search-section">
        <h2>
          <Search size={16} />
          ค้นหา
        </h2>
        <form
          className="search-form"
          onSubmit={(event) => {
            event.preventDefault()
            onRunSearch()
          }}
        >
          <input
            aria-label="คำค้นหา"
            disabled={isBusy || !hasDocument}
            onChange={(event) => onSearchQueryChange(event.target.value)}
            placeholder="คำค้นหา"
            value={searchQuery}
          />
          <button className="secondary-action compact-action" disabled={isBusy || !hasDocument} type="submit">
            ค้นหา
          </button>
        </form>
        {searchResults.length ? (
          <div className="search-results" aria-label="ผลค้นหา">
            <div className="search-result-toolbar">
              <span>
                ผลค้นหา {activeSearchIndex + 1}/{searchResults.length}
              </span>
              <div>
                <button disabled={isBusy} onClick={onPreviousSearchResult} type="button">
                  ก่อน
                </button>
                <button disabled={isBusy} onClick={onNextSearchResult} type="button">
                  ถัด
                </button>
              </div>
            </div>
            {searchResults.slice(0, 8).map((result, resultIndex) => (
              <button
                key={`${result.page_index}-${result.match_index}-${resultIndex}`}
                className={`search-result-row ${resultIndex === activeSearchIndex ? 'is-selected' : ''}`}
                disabled={isBusy}
                onClick={() => onSelectSearchResult(resultIndex)}
                type="button"
              >
                <span>{result.label}</span>
              </button>
            ))}
          </div>
        ) : null}
      </section>
      ) : null}
      {activeToolTab === 'edit' ? (
      <>
      <section className="tool-section">
        <h2>
          <Type size={16} />
          ข้อความ
        </h2>
        <input
          disabled={isBusy || !hasDocument}
          onChange={(event) => onTextOverlayChange(event.target.value)}
          placeholder="ข้อความ"
          value={textOverlayValue ?? ''}
        />
        <div className="inline-fields">
          <input
            aria-label="ขนาดข้อความ"
            disabled={isBusy || !hasDocument}
            max="96"
            min="6"
            onChange={(event) => onTextOverlayFontSizeChange(event.target.value)}
            type="number"
            value={textOverlayFontSize ?? '16'}
          />
          <button
            className="color-swatch"
            disabled={isBusy || !hasDocument}
            type="button"
            aria-label="สีข้อความ"
          ></button>
        </div>
        <button className="primary-action" disabled={isBusy || !hasDocument} onClick={onAddTextOverlay} type="button">
          วางข้อความ
        </button>
      </section>
      <section className="tool-section">
        <h2>
          <Type size={16} />
          แก้ข้อความเดิม
        </h2>
        <input
          disabled={isBusy || !hasDocument}
          onChange={(event) => onReplaceSearchTextChange(event.target.value)}
          placeholder="ข้อความเดิม"
          value={replaceSearchText}
        />
        <input
          disabled={isBusy || !hasDocument}
          onChange={(event) => onReplaceTextValueChange(event.target.value)}
          placeholder="ข้อความใหม่"
          value={replaceTextValue}
        />
        <select
          disabled={isBusy || !hasDocument}
          onChange={(event) => onReplacePageScopeChange(event.currentTarget.value as PageScope)}
          value={replacePageScope}
        >
          <option value="current">หน้านี้</option>
          <option value="all">ทุกหน้าในไฟล์นี้</option>
        </select>
        <button className="secondary-action" disabled={isBusy || !hasDocument} onClick={onReplaceExistingText} type="button">
          แก้ข้อความเดิม
        </button>
      </section>
      <section className="tool-section">
        <h2>
          <Image size={16} />
          รูปภาพ / ลายเซ็น
        </h2>
        <input
          ref={imageInputRef}
          accept="image/png,image/jpeg,image/webp"
          className="file-input"
          onChange={(event) => {
            void onChooseImageFile(event.currentTarget.files?.[0])
            event.currentTarget.value = ''
          }}
          type="file"
        />
        <p className="image-selection">รูป: {selectedImageName || 'ยังไม่ได้เลือก'}</p>
        <button
          className="primary-action"
          disabled={isBusy}
          onClick={() => imageInputRef.current?.click()}
          type="button"
        >
          เลือกรูป/ลายเซ็นภาพ
        </button>
        <input
          aria-label="ข้อความลายเซ็นภาพ"
          disabled={isBusy}
          onChange={(event) => onSignatureTextChange(event.target.value)}
          placeholder="ข้อความลายเซ็น"
          value={signatureText}
        />
        <button className="secondary-action" disabled={isBusy} onClick={onCreateSignatureImage} type="button">
          สร้างลายเซ็นภาพ
        </button>
        <div className="inline-fields image-place-fields">
          <input
            aria-label="ความกว้างรูปภาพ"
            disabled={isBusy || !hasDocument}
            max="500"
            min="8"
            onChange={(event) => onImageOverlayWidthChange(event.target.value)}
            type="number"
            value={imageOverlayWidth ?? '140'}
          />
          <button
            className="primary-action compact-place-action"
            disabled={isBusy || !hasDocument || !selectedImageName}
            onClick={onPlaceImageOverlay}
            type="button"
          >
            วางรูป
          </button>
        </div>
      </section>
      <section className="tool-section">
        <h2>
          <Square size={16} />
          รูปทรง
        </h2>
        <button className="primary-action" disabled={isBusy || !hasDocument} onClick={onDrawRectangleOverlay} type="button">
          <Minus size={16} />
          วาดกล่อง
        </button>
        <button className="highlight-action" disabled={isBusy || !hasDocument} onClick={onAddHighlightOverlay} type="button">
          Highlight
        </button>
        <button className="danger-action" disabled={isBusy || !hasDocument} onClick={onAddRedactionOverlay} type="button">
          Redaction
        </button>
        <div className="inline-fields crop-fields">
          <input
            aria-label="ระยะขอบ Crop หน้า"
            disabled={isBusy || !hasDocument}
            max="45"
            min="0"
            onChange={(event) => onCropMarginPercentChange(event.target.value)}
            type="number"
            value={cropMarginPercent ?? '8'}
          />
          <button
            className="secondary-action compact-place-action"
            disabled={isBusy || !hasDocument}
            onClick={onCropCurrentPage}
            type="button"
          >
            <Crop size={15} />
            Crop
          </button>
        </div>
      </section>
      </>
      ) : null}
      {activeToolTab === 'data' ? (
      <>
      <section className="tool-section">
        <h2>
          <FileText size={16} />
          ข้อมูลเอกสาร
        </h2>
        <div className="metadata-grid">
          {(['title', 'author', 'subject', 'keywords'] as Array<keyof MetadataFields>).map((field) => (
            <input
              key={field}
              disabled={isBusy || !hasDocument}
              onChange={(event) => onMetadataChange(field, event.currentTarget.value)}
              placeholder={field}
              value={metadataFields[field]}
            />
          ))}
        </div>
        <div className="inline-fields two-actions">
          <button className="secondary-action compact-place-action" disabled={isBusy || !hasDocument} onClick={onLoadMetadata} type="button">
            โหลดข้อมูล
          </button>
          <button className="primary-action compact-place-action" disabled={isBusy || !hasDocument} onClick={onSaveMetadata} type="button">
            บันทึกข้อมูล
          </button>
        </div>
      </section>
      <section className="tool-section">
        <h2>
          <FileText size={16} />
          ฟอร์ม PDF
        </h2>
        <div className="inline-fields two-actions">
          <button className="secondary-action compact-place-action" disabled={isBusy || !hasDocument} onClick={onLoadFormFields} type="button">
            โหลดฟอร์ม
          </button>
          <button
            className="primary-action compact-place-action"
            disabled={isBusy || !hasDocument || formFields.length === 0}
            onClick={onSaveFormFields}
            type="button"
          >
            บันทึกฟอร์ม
          </button>
        </div>
        <div className="form-field-list">
          {formFields.length ? (
            formFields.slice(0, 6).map((field) => (
              <label key={field.xref} className="form-field-row">
                <span>{field.name}</span>
                {field.is_checkbox ? (
                  <input
                    checked={Boolean(field.value)}
                    disabled={isBusy || !hasDocument}
                    onChange={(event) => onFormFieldValueChange(field.xref, event.currentTarget.checked)}
                    type="checkbox"
                  />
                ) : (
                  <input
                    disabled={isBusy || !hasDocument}
                    onChange={(event) => onFormFieldValueChange(field.xref, event.currentTarget.value)}
                    value={String(field.value)}
                  />
                )}
              </label>
            ))
          ) : (
            <p className="empty-tool-note">ยังไม่ได้โหลดฟอร์ม</p>
          )}
        </div>
      </section>
      </>
      ) : null}
      {activeToolTab === 'export' ? (
      <>
        <section className="tool-section">
          <h2>
            <FileDown size={16} />
            ส่งออก JPG
          </h2>
          <select
            disabled={isBusy || !hasDocument}
            onChange={(event) => onJpgPageScopeChange(event.currentTarget.value as PageScope)}
            value={jpgPageScope}
          >
            <option value="current">หน้านี้</option>
            <option value="all">ทุกหน้าในไฟล์นี้</option>
          </select>
          <div className="inline-fields two-actions">
            <input
              aria-label="DPI สำหรับ JPG"
              disabled={isBusy || !hasDocument}
              max="600"
              min="72"
              onChange={(event) => onJpgDpiChange(event.currentTarget.value)}
              type="number"
              value={jpgDpi}
            />
            <input
              aria-label="คุณภาพ JPG"
              disabled={isBusy || !hasDocument}
              max="100"
              min="1"
              onChange={(event) => onJpgQualityChange(event.currentTarget.value)}
              type="number"
              value={jpgQuality}
            />
          </div>
          <label className="field-label" htmlFor="jpg-output-dir">โฟลเดอร์ปลายทาง</label>
          <input
            id="jpg-output-dir"
            aria-label="โฟลเดอร์ปลายทาง JPG"
            disabled={isBusy}
            onChange={(event) => onJpgOutputDirChange(event.currentTarget.value)}
            placeholder="เว้นว่างเพื่อใช้โฟลเดอร์เริ่มต้น"
            style={{ fontFamily: 'monospace', fontSize: '11px' }}
            type="text"
            value={jpgOutputDir}
          />
          <button className="primary-action" disabled={isBusy || !hasDocument} onClick={onExportJpg} type="button">
            ส่งออก JPG
          </button>
        </section>
        <section className="tool-section">
          <h2>
            <Layers size={16} />
            Batch JPG
          </h2>
          <p className="image-selection">{batchJpgLabel}</p>
          <button className="secondary-action" disabled={isBusy} onClick={onChooseBatchJpgFiles} type="button">
            เลือก PDF หลายไฟล์
          </button>
        </section>
        <section className="tool-section">
          <h2>
            <Wand2 size={16} />
            แปลงเป็น Word/OCR
          </h2>
          <p className="empty-tool-note">แปลง PDF เป็น Word, Excel, PDF ที่ค้นหาได้ หรือ JPG ด้วย OCR ภาษาไทย</p>
          <button className="primary-action" disabled={isBusy || !hasDocument} onClick={onOpenConvertDialog} type="button">
            <Wand2 size={16} />
            แปลงเป็น Word/OCR
          </button>
        </section>
      </>
      ) : null}
      {activeToolTab === 'status' ? (
      <section className="worker-card">
        <h2>Worker Commands</h2>
        {workerCommands.map((command) => (
          <div key={command.name} className="command-row">
            <span>{command.name}</span>
            <small>{command.state}</small>
          </div>
        ))}
      </section>
      ) : null}
    </aside>
  )
}

function StatusBar({
  dirty,
  documentPath,
  selectedPage,
  statusMessage,
  totalPages,
  zoom,
}: {
  dirty: boolean
  documentPath: string | null
  selectedPage: number
  statusMessage: string
  totalPages: number
  zoom: number
}) {
  const fileName = documentPath ? documentPath.split(/[\\/]/).pop() : 'ยังไม่ได้เปิดไฟล์'

  return (
    <footer className="status-bar">
      <span>เปิดไฟล์แล้ว: {fileName}</span>
      <span>{statusMessage}</span>
      <b>
        หน้า {selectedPage} / {totalPages} | {zoom}%{dirty ? ' | มีการแก้ไข' : ''}
      </b>
    </footer>
  )
}

export default App
