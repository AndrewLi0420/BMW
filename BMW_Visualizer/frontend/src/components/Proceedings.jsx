import React, { useEffect, useState } from 'react'
import { getProceedings, uploadDocument } from '../api/client'

const SOURCE_LABELS = {
  press_release: 'PR',
  conference_paper: 'Paper',
  presentation: 'Slides',
  pamphlet: 'Doc',
  audio_transcript: 'Audio',
}

export default function Proceedings() {
  const [proceedings, setProceedings] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [technology, setTechnology] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)

  function loadData() {
    setLoading(true)
    const params = {}
    if (search) params.search = search
    if (technology) params.technology = technology
    getProceedings(params)
      .then(({ data }) => setProceedings(data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadData() }, [search, technology])

  async function handleFileUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setUploadMsg(null)
    try {
      const { data } = await uploadDocument(file)
      setUploadMsg(`Upload started (Job #${data.job_id}) — check Research Panel for status`)
      setTimeout(loadData, 8000)
    } catch (err) {
      setUploadMsg(`Upload failed: ${err.message}`)
    }
    setUploading(false)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="bg-white border-b border-[#B8CAD1] p-4 flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Search proceedings…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-[#B8CAD1] rounded px-3 py-2 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-[#4599FE]"
        />
        <input
          type="text"
          placeholder="Filter by technology…"
          value={technology}
          onChange={(e) => setTechnology(e.target.value)}
          className="border border-[#B8CAD1] rounded px-3 py-2 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-[#4599FE]"
        />
        <span className="text-sm text-gray-500">{proceedings.length} records</span>
        <label className="ml-auto cursor-pointer">
          <span className="bg-[#4599FE] hover:bg-[#4599FE] text-white text-sm px-4 py-2 rounded inline-block">
            {uploading ? 'Uploading…' : '+ Upload Document'}
          </span>
          <input
            type="file"
            accept=".pdf,.txt,.md"
            className="hidden"
            onChange={handleFileUpload}
          />
        </label>
      </div>
      {uploadMsg && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 text-sm text-blue-700">
          {uploadMsg}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-full text-gray-500">Loading…</div>
        ) : proceedings.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <div className="text-5xl mb-3"></div>
            <div className="text-lg font-medium">No proceedings found</div>
            <div className="text-sm mt-1">Upload PDF documents to extract proceedings automatically</div>
          </div>
        ) : (
          <div className="grid gap-4">
            {proceedings.map((p) => (
              <ProceedingCard key={p.id} proc={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ProceedingCard({ proc }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-lg border border-[#B8CAD1] p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        <span className="text-xs font-semibold bg-[#F0F4F8] border border-[#B8CAD1] text-[#031E49] px-2 py-1 rounded flex-shrink-0 mt-0.5">
          {SOURCE_LABELS[proc.source_type] || 'Doc'}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-[#031E49] text-sm leading-snug">{proc.title}</h3>
          <div className="flex items-center gap-3 mt-1 flex-wrap text-xs text-gray-500">
            {proc.event_name && <span className="font-medium text-gray-700">{proc.event_name}</span>}
            {proc.event_date && <span>{proc.event_date}</span>}
            {proc.location && <span> {proc.location}</span>}
            {proc.company_name && (
              <span className="text-[#4599FE]">{proc.company_name}</span>
            )}
          </div>

          {/* Technologies */}
          {proc.technologies?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {proc.technologies.map((t) => (
                <span
                  key={t}
                  className="bg-[#E8F1FF] text-[#4599FE] text-xs px-2 py-0.5 rounded-full"
                >
                  {t}
                </span>
              ))}
            </div>
          )}

          {/* Results summary */}
          {proc.results_summary && (
            <p
              className={`text-sm text-gray-600 mt-2 leading-relaxed ${
                expanded ? '' : 'line-clamp-2'
              }`}
            >
              {proc.results_summary}
            </p>
          )}
          {proc.results_summary && proc.results_summary.length > 150 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-[#4599FE] mt-1 hover:underline"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}

          {/* Authors & Partners */}
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-500">
            {proc.authors?.length > 0 && (
              <span>Authors: {proc.authors.join(', ')}</span>
            )}
            {proc.partners_mentioned?.length > 0 && (
              <span>Partners: {proc.partners_mentioned.join(', ')}</span>
            )}
          </div>

          {/* Topics */}
          {proc.topics?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {proc.topics.map((t) => (
                <span key={t} className="bg-[#F0F4F8] text-gray-600 text-xs px-2 py-0.5 rounded">
                  {t}
                </span>
              ))}
            </div>
          )}

          {/* Source link */}
          {proc.source_url && (
            <a
              href={proc.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-block mt-2 text-xs text-[#4599FE] hover:underline"
            >
              View source →
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
