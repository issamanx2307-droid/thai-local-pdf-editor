import { useCallback, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
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
  RotateCcw,
  RotateCw,
  Save,
  Search,
  Square,
  Type,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import {
  callWorker,
  getBridgeHealth,
  lastRenderResponse,
  openDemoDocument,
  previewUrlFrom,
  type WorkerCommandName,
  type WorkerResponse,
  type WorkerSearchResult,
  type WorkerState,
} from './workerApi'
import './App.css'

const fallbackPages = Array.from({ length: 3 }, (_, index) => index + 1)
const defaultZoomPercent = 100

const commandNames: WorkerCommandName[] = [
  'add_highlight_overlay',
  'add_text_overlay',
  'draw_rectangle_overlay',
  'open_pdf',
  'render_page',
  'go_to_page',
  'move_page',
  'duplicate_page',
  'delete_page',
  'search_text',
  'save_copy',
]
const demoCommandNames = new Set<WorkerCommandName>(['open_pdf', 'render_page'])
type BridgeStatus = 'idle' | 'connecting' | 'ready' | 'error'

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

function fileNameFromPath(path: string): string {
  return path.split(/[\\/]/).pop() || path
}

function App() {
  const [pages, setPages] = useState(fallbackPages)
  const [selectedPageIndex, setSelectedPageIndex] = useState(0)
  const [zoomPercent, setZoomPercent] = useState(defaultZoomPercent)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [documentPath, setDocumentPath] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [bridgeStatus, setBridgeStatus] = useState<BridgeStatus>('idle')
  const [statusMessage, setStatusMessage] = useState('กดเปิดไฟล์เพื่อโหลด PDF ตัวอย่างผ่าน worker')
  const [lastCommand, setLastCommand] = useState<WorkerCommandName | 'demo' | null>(null)
  const [isBusy, setIsBusy] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<WorkerSearchResult[]>([])
  const [activeSearchIndex, setActiveSearchIndex] = useState(-1)
  const [textOverlayValue, setTextOverlayValue] = useState('')
  const [textOverlayFontSize, setTextOverlayFontSize] = useState('16')

  const totalPages = pages.length
  const selectedPageNumber = selectedPageIndex + 1
  const hasDocument = Boolean(documentPath)
  const searchResultSummary =
    searchResults.length > 0 && activeSearchIndex >= 0 ? `${activeSearchIndex + 1}/${searchResults.length}` : ''

  const applyResponse = useCallback((response: WorkerResponse, renderResponse = lastRenderResponse(response)) => {
    const nextState: WorkerState = renderResponse?.state || response.state
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

    const nextPreviewUrl = previewUrlFrom(renderResponse)
    if (nextPreviewUrl) {
      setPreviewUrl(`${nextPreviewUrl}?v=${Date.now()}`)
    }
  }, [])

  const loadDemo = useCallback(async () => {
    setIsBusy(true)
    setLastCommand('demo')
    setBridgeStatus('connecting')
    setStatusMessage('กำลังเปิด PDF ตัวอย่างผ่าน worker...')
    try {
      await getBridgeHealth()
      const response = await openDemoDocument()
      applyResponse(response)
      setSearchResults([])
      setActiveSearchIndex(-1)
      setBridgeStatus('ready')
      setStatusMessage('เชื่อมต่อ Python worker แล้ว')
    } catch (error) {
      setBridgeStatus('error')
      setStatusMessage(error instanceof Error ? error.message : 'เชื่อมต่อ bridge ไม่สำเร็จ')
      setPreviewUrl(null)
    } finally {
      setIsBusy(false)
    }
  }, [applyResponse])

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

  const showPendingReactFeature = useCallback((featureName: string) => {
    setStatusMessage(`${featureName} ยังไม่ได้ต่อใน React shell ใช้ได้ในแอป desktop ตอนนี้`)
  }, [])

  const workerCommands = useMemo(
    () =>
      commandNames.map((name) => ({
        name,
        state: lastCommand === name || (lastCommand === 'demo' && demoCommandNames.has(name)) ? 'active' : 'ready',
      })),
    [lastCommand],
  )

  return (
    <main className="app-shell">
      <Toolbar
        hasDocument={hasDocument}
        isBusy={isBusy}
        searchResultSummary={searchResultSummary}
        selectedPage={selectedPageNumber}
        totalPages={totalPages}
        zoom={zoomPercent}
        onFitHeight={() => void renderPage(selectedPageIndex, 92)}
        onFitWidth={() => void renderPage(selectedPageIndex, 100)}
        onNextPage={() => void renderPage(Math.min(totalPages - 1, selectedPageIndex + 1))}
        onOpenDemo={loadDemo}
        onPreviousPage={() => void renderPage(Math.max(0, selectedPageIndex - 1))}
        onRunSearch={() => void runSearch()}
        onSaveCopy={() => void saveCopy()}
        onUnavailableAction={showPendingReactFeature}
        onZoomIn={() => void renderPage(selectedPageIndex, Math.min(240, zoomPercent + 10))}
        onZoomOut={() => void renderPage(selectedPageIndex, Math.max(50, zoomPercent - 10))}
      />
      <section className="workspace">
        <PagePanel
          hasDocument={hasDocument}
          isBusy={isBusy}
          pages={pages}
          selectedPageIndex={selectedPageIndex}
          onDeleteSelectedPage={deleteSelectedPage}
          onDuplicateSelectedPage={duplicateSelectedPage}
          onMoveSelectedPage={moveSelectedPage}
          onSelectPage={(pageIndex) => void renderPage(pageIndex)}
        />
        <Viewer
          bridgeStatus={bridgeStatus}
          isBusy={isBusy}
          previewUrl={previewUrl}
          selectedPage={selectedPageNumber}
          statusMessage={statusMessage}
          zoom={zoomPercent}
        />
        <ToolPanel
          activeSearchIndex={activeSearchIndex}
          bridgeStatus={bridgeStatus}
          hasDocument={hasDocument}
          isBusy={isBusy}
          onAddHighlightOverlay={() => void addShapeOverlay('add_highlight_overlay')}
          onNextSearchResult={() => void goToSearchResult(activeSearchIndex + 1)}
          onPreviousSearchResult={() => void goToSearchResult(activeSearchIndex - 1)}
          onAddTextOverlay={() => void addTextOverlay()}
          onDrawRectangleOverlay={() => void addShapeOverlay('draw_rectangle_overlay')}
          onRunSearch={() => void runSearch()}
          onSearchQueryChange={setSearchQuery}
          onSelectSearchResult={(resultIndex) => void goToSearchResult(resultIndex)}
          onTextOverlayChange={setTextOverlayValue}
          onTextOverlayFontSizeChange={setTextOverlayFontSize}
          onUnavailableAction={showPendingReactFeature}
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
    </main>
  )
}

function Toolbar({
  hasDocument,
  isBusy,
  searchResultSummary,
  selectedPage,
  totalPages,
  zoom,
  onFitHeight,
  onFitWidth,
  onNextPage,
  onOpenDemo,
  onPreviousPage,
  onRunSearch,
  onSaveCopy,
  onUnavailableAction,
  onZoomIn,
  onZoomOut,
}: {
  hasDocument: boolean
  isBusy: boolean
  searchResultSummary: string
  selectedPage: number
  totalPages: number
  zoom: number
  onFitHeight: () => void
  onFitWidth: () => void
  onNextPage: () => void
  onOpenDemo: () => void
  onPreviousPage: () => void
  onRunSearch: () => void
  onSaveCopy: () => void
  onUnavailableAction: (featureName: string) => void
  onZoomIn: () => void
  onZoomOut: () => void
}) {
  return (
    <header className="toolbar" aria-label="แถบเครื่องมือแก้ไข PDF">
      <ToolbarGroup label="ไฟล์">
        <ToolButton icon={<FolderOpen />} label="เปิดไฟล์" active disabled={isBusy} onClick={onOpenDemo} />
        <ToolButton icon={<Save />} label="บันทึก" disabled={isBusy || !hasDocument} onClick={onSaveCopy} />
        <ToolButton icon={<Printer />} label="พิมพ์" onClick={() => onUnavailableAction('พิมพ์')} />
      </ToolbarGroup>
      <ToolbarGroup label="แก้ไข">
        <ToolButton icon={<RotateCcw />} label="ย้อนกลับ" muted />
        <ToolButton icon={<RotateCw />} label="ทำซ้ำ" muted />
        <ToolButton icon={<FileDown />} label="รวม PDF" onClick={() => onUnavailableAction('รวม PDF')} />
      </ToolbarGroup>
      <ToolbarGroup label="มุมมอง">
        <ToolButton icon={<ZoomOut />} label="ซูม-" disabled={isBusy || !hasDocument} onClick={onZoomOut} />
        <div className="zoom-readout" aria-live="polite">
          {zoom}%
        </div>
        <ToolButton icon={<ZoomIn />} label="ซูม+" disabled={isBusy || !hasDocument} onClick={onZoomIn} />
        <ToolButton icon={<Maximize2 />} label="พอดีกว้าง" wide disabled={isBusy || !hasDocument} onClick={onFitWidth} />
        <ToolButton icon={<Maximize2 />} label="พอดีบน-ล่าง" wide disabled={isBusy || !hasDocument} onClick={onFitHeight} />
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
        <ToolButton icon={<MousePointer2 />} label="คู่มือ" onClick={() => onUnavailableAction('คู่มือ')} />
      </ToolbarGroup>
    </header>
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
  onMoveSelectedPage,
  onSelectPage,
}: {
  hasDocument: boolean
  isBusy: boolean
  pages: number[]
  selectedPageIndex: number
  onDeleteSelectedPage: () => void
  onDuplicateSelectedPage: () => void
  onMoveSelectedPage: (direction: -1 | 1) => void
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
      <button
        className="secondary-action"
        disabled={isBusy || !hasDocument}
        onClick={onDuplicateSelectedPage}
        type="button"
      >
        ทำซ้ำหน้า
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
  selectedPage,
  statusMessage,
  zoom,
}: {
  bridgeStatus: BridgeStatus
  isBusy: boolean
  previewUrl: string | null
  selectedPage: number
  statusMessage: string
  zoom: number
}) {
  return (
    <section className="viewer" aria-label="พื้นที่แสดง PDF">
      <div className="viewer-stage" style={{ '--viewer-zoom': `${zoom / 100}` } as CSSProperties}>
        <div className={`document-page ${previewUrl ? 'is-worker-preview' : 'is-fallback'}`}>
          {previewUrl ? (
            <img className="pdf-preview-image" src={previewUrl} alt={`ตัวอย่าง PDF หน้า ${selectedPage}`} />
          ) : (
            <FallbackPage selectedPage={selectedPage} />
          )}
        </div>
        <div className={`viewer-toast is-${bridgeStatus}`} aria-live="polite">
          {isBusy ? 'กำลังทำงาน...' : statusMessage}
        </div>
      </div>
      <div className="bottom-scrollbar" aria-hidden="true">
        <span style={{ width: `${Math.max(22, Math.min(70, zoom / 2))}%` }}></span>
      </div>
    </section>
  )
}

function FallbackPage({ selectedPage }: { selectedPage: number }) {
  return (
    <>
      <div className="slide-visual" aria-hidden="true">
        <div className="solar-card large">
          <div className="sun"></div>
          <div className="panel-grid"></div>
        </div>
        <div className="solar-card small">
          <div className="panel-grid compact"></div>
          <span>Load</span>
        </div>
      </div>
      <h1>หน้า {selectedPage}: ขั้นตอนการทำงาน</h1>
      <p>
        เมื่อมีแสงอาทิตย์ตกกระทบ แสงอาทิตย์จะถ่ายเทพลังงานให้กับอิเล็กตรอนและโฮล
        ทำให้เกิดการเคลื่อนไหว และเกิดกระแสไฟฟ้าจากแผงโซล่าเซลล์
      </p>
    </>
  )
}

function ToolPanel({
  activeSearchIndex,
  bridgeStatus,
  hasDocument,
  isBusy,
  onAddHighlightOverlay,
  onAddTextOverlay,
  onDrawRectangleOverlay,
  onNextSearchResult,
  onPreviousSearchResult,
  onRunSearch,
  onSearchQueryChange,
  onSelectSearchResult,
  onTextOverlayChange,
  onTextOverlayFontSizeChange,
  onUnavailableAction,
  searchQuery,
  searchResults,
  textOverlayFontSize,
  textOverlayValue,
  workerCommands,
}: {
  activeSearchIndex: number
  bridgeStatus: BridgeStatus
  hasDocument: boolean
  isBusy: boolean
  onAddHighlightOverlay: () => void
  onAddTextOverlay: () => void
  onDrawRectangleOverlay: () => void
  onNextSearchResult: () => void
  onPreviousSearchResult: () => void
  onRunSearch: () => void
  onSearchQueryChange: (value: string) => void
  onSelectSearchResult: (resultIndex: number) => void
  onTextOverlayChange: (value: string) => void
  onTextOverlayFontSizeChange: (value: string) => void
  onUnavailableAction: (featureName: string) => void
  searchQuery: string
  searchResults: WorkerSearchResult[]
  textOverlayFontSize: string
  textOverlayValue: string
  workerCommands: Array<{ name: WorkerCommandName; state: string }>
}) {
  return (
    <aside className="tool-panel" aria-label="เครื่องมือ">
      <div className="panel-heading">
        <div>
          <b>เครื่องมือ</b>
          <span>Bridge: {bridgeStatus}</span>
        </div>
        <FileText size={18} />
      </div>
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
          <Image size={16} />
          รูปภาพ / ลายเซ็น
        </h2>
        <button className="primary-action" onClick={() => onUnavailableAction('เลือกรูป/ลายเซ็นภาพ')} type="button">
          เลือกรูป/ลายเซ็นภาพ
        </button>
        <button className="secondary-action" onClick={() => onUnavailableAction('สร้างลายเซ็นภาพ')} type="button">
          สร้างลายเซ็นภาพ
        </button>
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
        <button className="secondary-action" onClick={() => onUnavailableAction('Crop หน้า')} type="button">
          <Crop size={15} />
          Crop หน้า
        </button>
      </section>
      <section className="worker-card">
        <h2>Worker Commands</h2>
        {workerCommands.map((command) => (
          <div key={command.name} className="command-row">
            <span>{command.name}</span>
            <small>{command.state}</small>
          </div>
        ))}
      </section>
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
