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
  type WorkerState,
} from './workerApi'
import './App.css'

const fallbackPages = Array.from({ length: 3 }, (_, index) => index + 1)
const defaultZoomPercent = 100

const commandNames: WorkerCommandName[] = ['open_pdf', 'render_page', 'go_to_page', 'move_page']
type BridgeStatus = 'idle' | 'connecting' | 'ready' | 'error'

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

  const totalPages = pages.length
  const selectedPageNumber = selectedPageIndex + 1

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

  const workerCommands = useMemo(
    () =>
      commandNames.map((name) => ({
        name,
        state: lastCommand === name || (lastCommand === 'demo' && name !== 'move_page') ? 'active' : 'ready',
      })),
    [lastCommand],
  )

  return (
    <main className="app-shell">
      <Toolbar
        isBusy={isBusy}
        selectedPage={selectedPageNumber}
        totalPages={totalPages}
        zoom={zoomPercent}
        onFitHeight={() => void renderPage(selectedPageIndex, 92)}
        onFitWidth={() => void renderPage(selectedPageIndex, 100)}
        onNextPage={() => void renderPage(Math.min(totalPages - 1, selectedPageIndex + 1))}
        onOpenDemo={loadDemo}
        onPreviousPage={() => void renderPage(Math.max(0, selectedPageIndex - 1))}
        onZoomIn={() => void renderPage(selectedPageIndex, Math.min(240, zoomPercent + 10))}
        onZoomOut={() => void renderPage(selectedPageIndex, Math.max(50, zoomPercent - 10))}
      />
      <section className="workspace">
        <PagePanel
          isBusy={isBusy}
          pages={pages}
          selectedPageIndex={selectedPageIndex}
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
        <ToolPanel bridgeStatus={bridgeStatus} workerCommands={workerCommands} />
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
  isBusy,
  selectedPage,
  totalPages,
  zoom,
  onFitHeight,
  onFitWidth,
  onNextPage,
  onOpenDemo,
  onPreviousPage,
  onZoomIn,
  onZoomOut,
}: {
  isBusy: boolean
  selectedPage: number
  totalPages: number
  zoom: number
  onFitHeight: () => void
  onFitWidth: () => void
  onNextPage: () => void
  onOpenDemo: () => void
  onPreviousPage: () => void
  onZoomIn: () => void
  onZoomOut: () => void
}) {
  return (
    <header className="toolbar" aria-label="แถบเครื่องมือแก้ไข PDF">
      <ToolbarGroup label="ไฟล์">
        <ToolButton icon={<FolderOpen />} label="เปิดไฟล์" active disabled={isBusy} onClick={onOpenDemo} />
        <ToolButton icon={<Save />} label="บันทึก" />
        <ToolButton icon={<Printer />} label="พิมพ์" />
      </ToolbarGroup>
      <ToolbarGroup label="แก้ไข">
        <ToolButton icon={<RotateCcw />} label="ย้อนกลับ" muted />
        <ToolButton icon={<RotateCw />} label="ทำซ้ำ" muted />
        <ToolButton icon={<FileDown />} label="รวม PDF" />
      </ToolbarGroup>
      <ToolbarGroup label="มุมมอง">
        <ToolButton icon={<ZoomOut />} label="ซูม-" disabled={isBusy} onClick={onZoomOut} />
        <div className="zoom-readout" aria-live="polite">
          {zoom}%
        </div>
        <ToolButton icon={<ZoomIn />} label="ซูม+" disabled={isBusy} onClick={onZoomIn} />
        <ToolButton icon={<Maximize2 />} label="พอดีกว้าง" wide disabled={isBusy} onClick={onFitWidth} />
        <ToolButton icon={<Maximize2 />} label="พอดีบน-ล่าง" wide disabled={isBusy} onClick={onFitHeight} />
      </ToolbarGroup>
      <ToolbarGroup label="ไปที่หน้า">
        <ToolButton icon={<ArrowLeft />} label="ก่อน" disabled={isBusy || selectedPage <= 1} onClick={onPreviousPage} />
        <div className="page-control" aria-live="polite">
          <span>{selectedPage}</span>
          <small>/ {totalPages}</small>
        </div>
        <ToolButton icon={<ArrowRight />} label="ถัด" disabled={isBusy || selectedPage >= totalPages} onClick={onNextPage} />
      </ToolbarGroup>
      <ToolbarGroup label="ช่วยเหลือ">
        <ToolButton icon={<Search />} label="ค้นหา" />
        <ToolButton icon={<MousePointer2 />} label="คู่มือ" />
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
  isBusy,
  pages,
  selectedPageIndex,
  onMoveSelectedPage,
  onSelectPage,
}: {
  isBusy: boolean
  pages: number[]
  selectedPageIndex: number
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
            disabled={isBusy}
            onClick={() => onSelectPage(pageIndex)}
            type="button"
          >
            <span>หน้า {pageIndex + 1}</span>
            {pageIndex === selectedPageIndex ? <small>ปัจจุบัน</small> : null}
          </button>
        ))}
      </div>
      <div className="page-actions-grid">
        <button disabled={isBusy || selectedPageIndex <= 0} onClick={() => onMoveSelectedPage(-1)} type="button">
          <ArrowUp size={16} />
          ขึ้น
        </button>
        <button
          disabled={isBusy || selectedPageIndex >= pages.length - 1}
          onClick={() => onMoveSelectedPage(1)}
          type="button"
        >
          <ArrowDown size={16} />
          ลง
        </button>
      </div>
      <button className="secondary-action" type="button">
        ทำซ้ำหน้า
      </button>
      <button className="danger-action" type="button">
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
  bridgeStatus,
  workerCommands,
}: {
  bridgeStatus: BridgeStatus
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
      <section className="tool-section">
        <h2>
          <Type size={16} />
          ข้อความ
        </h2>
        <input placeholder="ข้อความ" />
        <div className="inline-fields">
          <input defaultValue="16" />
          <button className="color-swatch" type="button" aria-label="สีข้อความ"></button>
        </div>
        <button className="primary-action" type="button">
          วางข้อความ
        </button>
      </section>
      <section className="tool-section">
        <h2>
          <Image size={16} />
          รูปภาพ / ลายเซ็น
        </h2>
        <button className="primary-action" type="button">
          เลือกรูป/ลายเซ็นภาพ
        </button>
        <button className="secondary-action" type="button">
          สร้างลายเซ็นภาพ
        </button>
      </section>
      <section className="tool-section">
        <h2>
          <Square size={16} />
          รูปทรง
        </h2>
        <button className="primary-action" type="button">
          <Minus size={16} />
          วาดกล่อง
        </button>
        <button className="highlight-action" type="button">
          Highlight
        </button>
        <button className="secondary-action" type="button">
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
