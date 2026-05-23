import { useState } from 'react'
import { FileText, Download, Eye, Map as MapIcon } from 'lucide-react'

function ReportViewer({ project, reports, phaseState }) {
  const [activeTab, setActiveTab] = useState('preview')

  const latestReport = reports?.[reports.length - 1]
  const reportText = phaseState?.structured_data?.report_text || ''
  const extracts = phaseState?.structured_data?.extracts_for_report || []

  // Convert local file path to API download URL
  const getDownloadUrl = (filePath) => {
    if (!filePath) return null
    const filename = filePath.replace(/\\/g, '/').split('/').pop()
    return `/api/analysis/download/${filename}`
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex border-b border-accent/10">
        <button
          onClick={() => setActiveTab('preview')}
          className={`px-4 py-2 text-xs font-medium transition ${activeTab === 'preview' ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-text'}`}
        >
          <Eye size={12} className="inline mr-1" /> Preview
        </button>
        <button
          onClick={() => setActiveTab('extracts')}
          className={`px-4 py-2 text-xs font-medium transition ${activeTab === 'extracts' ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-text'}`}
        >
          <FileText size={12} className="inline mr-1" /> Extracts ({extracts.length})
        </button>
        <button
          onClick={() => setActiveTab('downloads')}
          className={`px-4 py-2 text-xs font-medium transition ${activeTab === 'downloads' ? 'text-accent border-b-2 border-accent' : 'text-muted hover:text-text'}`}
        >
          <Download size={12} className="inline mr-1" /> Downloads
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'preview' && (
          <div className="space-y-4">
            {!reportText ? (
              <div className="text-sm text-muted text-center py-8">
                <FileText size={32} className="mx-auto mb-2 text-accent/30" />
                <p>No report generated yet. Chat with the AI to produce the manuscript.</p>
              </div>
            ) : (
              <div className="prose prose-invert max-w-none">
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-text/90">
                  {reportText}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'extracts' && (
          <div className="space-y-3">
            {extracts.length === 0 ? (
              <div className="text-sm text-muted text-center py-8">No extracts selected for report yet.</div>
            ) : (
              extracts.map((ex, i) => (
                <div key={i} className="rounded-lg border border-accent/10 bg-bg p-3">
                  <div className="text-xs font-semibold text-accent mb-1">{ex.theme_name}</div>
                  <div className="rounded bg-bg2 border-l-2 border-accent/30 px-3 py-2 text-sm italic text-text/80 mb-2">
                    "{ex.extract_text}"
                  </div>
                  <div className="text-xs text-muted">
                    <span className="font-semibold text-accent/80">Commentary:</span> {ex.commentary}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'downloads' && (
          <div className="space-y-3">
            {reports.length === 0 ? (
              <div className="text-sm text-muted text-center py-8">
                <Download size={32} className="mx-auto mb-2 text-accent/30" />
                <p>No reports generated yet. Use the PDF or Word buttons above to generate.</p>
              </div>
            ) : (
              reports.map((report, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-accent/10 bg-bg p-3">
                  <div className="flex items-center gap-2">
                    <FileText size={16} className="text-accent" />
                    <div>
                      <div className="text-sm font-medium text-text">{report.format.toUpperCase()} Report</div>
                      <div className="text-xs text-muted">{new Date(report.generated_at).toLocaleString()}</div>
                    </div>
                  </div>
                  <a
                    href={getDownloadUrl(report.file_path)}
                    download
                    className="flex items-center gap-1 rounded-lg bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition hover:bg-accent/20"
                  >
                    <Download size={12} /> Download
                  </a>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ReportViewer
