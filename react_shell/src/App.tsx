import { useState, type CSSProperties, type ReactNode } from 'react'
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
import './App.css'

const initialPages = Array.from({ length: 18 }, (_, index) => index + 1)
const documentTotalPages = 116

const workerCommands = [
  { name: 'open_pdf', state: 'ready' },
  { name: 'render_page', state: 'ready' },
  { name: 'go_to_page', state: 'ready' },
  { name: 'move_page', state: 'ready' },
]

function App() {
  const [pages, setPages] = useState(initialPages)
  const [selectedPage, setSelectedPage] = useState(7)
  const [zoom, setZoom] = useState(100)

  const selectPreviousPage = () => {
    setSelectedPage((current) => Math.max(1, current - 1))
  }

  const selectNextPage = () => {
    setSelectedPage((current) => Math.min(pages.length, current + 1))
  }

  const changeZoom = (delta: number) => {
    setZoom((current) => Math.min(240, Math.max(50, current + delta)))
  }

  const moveSelectedPage = (direction: -1 | 1) => {
    setPages((currentPages) => {
      const selectedIndex = currentPages.indexOf(selectedPage)
      const targetIndex = selectedIndex + direction

      if (selectedIndex < 0 || targetIndex < 0 || targetIndex >= currentPages.length) {
        return currentPages
      }

      const nextPages = [...currentPages]
      const selectedPageNumber = nextPages[selectedIndex]
      nextPages[selectedIndex] = nextPages[targetIndex]
      nextPages[targetIndex] = selectedPageNumber
      return nextPages
    })
  }

  return (
    <main className="app-shell">
      <Toolbar
        selectedPage={selectedPage}
        totalPages={documentTotalPages}
        zoom={zoom}
        onFitHeight={() => setZoom(92)}
        onFitWidth={() => setZoom(100)}
        onNextPage={selectNextPage}
        onPreviousPage={selectPreviousPage}
        onZoomIn={() => changeZoom(10)}
        onZoomOut={() => changeZoom(-10)}
      />
      <section className="workspace">
        <PagePanel
          pages={pages}
          selectedPage={selectedPage}
          onMoveSelectedPage={moveSelectedPage}
          onSelectPage={setSelectedPage}
        />
        <Viewer selectedPage={selectedPage} zoom={zoom} />
        <ToolPanel />
      </section>
      <StatusBar selectedPage={selectedPage} totalPages={documentTotalPages} zoom={zoom} />
    </main>
  )
}

function Toolbar({
  selectedPage,
  totalPages,
  zoom,
  onFitHeight,
  onFitWidth,
  onNextPage,
  onPreviousPage,
  onZoomIn,
  onZoomOut,
}: {
  selectedPage: number
  totalPages: number
  zoom: number
  onFitHeight: () => void
  onFitWidth: () => void
  onNextPage: () => void
  onPreviousPage: () => void
  onZoomIn: () => void
  onZoomOut: () => void
}) {
  return (
    <header className="toolbar" aria-label="แถบเครื่องมือแก้ไข PDF">
      <ToolbarGroup label="ไฟล์">
        <ToolButton icon={<FolderOpen />} label="เปิดไฟล์" active />
        <ToolButton icon={<Save />} label="บันทึก" />
        <ToolButton icon={<Printer />} label="พิมพ์" />
      </ToolbarGroup>
      <ToolbarGroup label="แก้ไข">
        <ToolButton icon={<RotateCcw />} label="ย้อนกลับ" muted />
        <ToolButton icon={<RotateCw />} label="ทำซ้ำ" muted />
        <ToolButton icon={<FileDown />} label="รวม PDF" />
      </ToolbarGroup>
      <ToolbarGroup label="มุมมอง">
        <ToolButton icon={<ZoomOut />} label="ซูม-" onClick={onZoomOut} />
        <div className="zoom-readout" aria-live="polite">
          {zoom}%
        </div>
        <ToolButton icon={<ZoomIn />} label="ซูม+" onClick={onZoomIn} />
        <ToolButton icon={<Maximize2 />} label="พอดีกว้าง" wide onClick={onFitWidth} />
        <ToolButton icon={<Maximize2 />} label="พอดีบน-ล่าง" wide onClick={onFitHeight} />
      </ToolbarGroup>
      <ToolbarGroup label="ไปที่หน้า">
        <ToolButton icon={<ArrowLeft />} label="ก่อน" onClick={onPreviousPage} />
        <div className="page-control" aria-live="polite">
          <span>{selectedPage}</span>
          <small>/ {totalPages}</small>
        </div>
        <ToolButton icon={<ArrowRight />} label="ถัด" onClick={onNextPage} />
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
  muted = false,
  wide = false,
  onClick,
}: {
  icon: ReactNode
  label: string
  active?: boolean
  muted?: boolean
  wide?: boolean
  onClick?: () => void
}) {
  return (
    <button
      className={`tool-button ${active ? 'is-active' : ''} ${muted ? 'is-muted' : ''} ${wide ? 'is-wide' : ''}`}
      disabled={muted}
      onClick={onClick}
      type="button"
    >
      {icon}
      <span>{label}</span>
    </button>
  )
}

function PagePanel({
  pages,
  selectedPage,
  onMoveSelectedPage,
  onSelectPage,
}: {
  pages: number[]
  selectedPage: number
  onMoveSelectedPage: (direction: -1 | 1) => void
  onSelectPage: (page: number) => void
}) {
  return (
    <aside className="page-panel" aria-label="รายการหน้า">
      <div className="panel-heading">
        <div>
          <b>รายการหน้า</b>
          <span>{documentTotalPages} หน้า</span>
        </div>
        <Layers size={18} />
      </div>
      <div className="page-list">
        {pages.map((page) => (
          <button
            key={page}
            className={`page-row ${page === selectedPage ? 'is-selected' : ''}`}
            onClick={() => onSelectPage(page)}
            type="button"
          >
            <span>หน้า {page}</span>
            {page === selectedPage ? <small>ปัจจุบัน</small> : null}
          </button>
        ))}
      </div>
      <div className="page-actions-grid">
        <button onClick={() => onMoveSelectedPage(-1)} type="button">
          <ArrowUp size={16} />
          ขึ้น
        </button>
        <button onClick={() => onMoveSelectedPage(1)} type="button">
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

function Viewer({ selectedPage, zoom }: { selectedPage: number; zoom: number }) {
  return (
    <section className="viewer" aria-label="พื้นที่แสดง PDF">
      <div className="viewer-stage" style={{ '--viewer-zoom': `${zoom / 100}` } as CSSProperties}>
        <div className="document-page">
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
        </div>
      </div>
      <div className="bottom-scrollbar" aria-hidden="true">
        <span style={{ width: `${Math.max(22, Math.min(70, zoom / 2))}%` }}></span>
      </div>
    </section>
  )
}

function ToolPanel() {
  return (
    <aside className="tool-panel" aria-label="เครื่องมือ">
      <div className="panel-heading">
        <div>
          <b>เครื่องมือ</b>
          <span>Worker contract: Phase 2</span>
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

function StatusBar({ selectedPage, totalPages, zoom }: { selectedPage: number; totalPages: number; zoom: number }) {
  return (
    <footer className="status-bar">
      <span>เปิดไฟล์แล้ว: คู่มือการติดตั้งระบบโซล่าเซลล์_1.pdf</span>
      <span>React shell preview - ยังไม่แทน exe เดิม</span>
      <b>
        หน้า {selectedPage} / {totalPages} | {zoom}%
      </b>
    </footer>
  )
}

export default App
