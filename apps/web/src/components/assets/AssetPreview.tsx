import { useEffect, useMemo, useState } from 'react'

import { useMutation, useQuery } from '@tanstack/react-query'
import { Download, ExternalLink, Eye, FileQuestion, LoaderCircle } from 'lucide-react'

import {
  getAssetContentBlob,
  getAssetContentText,
  getAssetDownload,
  type AssetOut,
} from '../../lib/api'
import { getErrorMessage } from '../../lib/types'
import { MarkdownContent } from '../content/MarkdownContent'

function formatFileSize(fileSize: number): string {
  if (fileSize < 1024) {
    return `${fileSize} B`
  }
  if (fileSize < 1024 * 1024) {
    return `${(fileSize / 1024).toFixed(1)} KB`
  }
  return `${(fileSize / (1024 * 1024)).toFixed(1)} MB`
}

function detectPreviewKind(assetType: string): 'pdf' | 'markdown' | 'text' | 'subtitle' | 'unsupported' {
  if (assetType === 'pdf') {
    return 'pdf'
  }
  if (assetType === 'md') {
    return 'markdown'
  }
  if (assetType === 'txt') {
    return 'text'
  }
  if (assetType === 'vtt' || assetType === 'srt') {
    return 'subtitle'
  }
  return 'unsupported'
}

async function saveAsset(
  courseId: string,
  moduleId: string,
  asset: AssetOut,
): Promise<void> {
  const response = await getAssetContentBlob(courseId, moduleId, asset.id, 'attachment')
  const objectUrl = URL.createObjectURL(response.blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = response.fileName ?? asset.file_name
  anchor.click()
  URL.revokeObjectURL(objectUrl)
}

interface AssetPreviewProps {
  courseId: string
  moduleId: string
  asset: AssetOut | null
  emptyTitle?: string
  emptyDescription?: string
}

export function AssetPreview({
  courseId,
  moduleId,
  asset,
  emptyTitle = 'Select a learning material',
  emptyDescription = 'Choose a file to preview it here, open it in a separate tab, or download it.',
}: AssetPreviewProps) {
  const [textPreview, setTextPreview] = useState('')
  const accessQuery = useQuery({
    queryKey: ['asset-download', courseId, moduleId, asset?.id],
    queryFn: () => getAssetDownload(courseId, moduleId, asset?.id ?? ''),
    enabled: Boolean(asset),
  })
  const previewKind = useMemo(
    () => (asset ? detectPreviewKind(asset.asset_type) : 'unsupported'),
    [asset],
  )

  const downloadMutation = useMutation({
    mutationFn: async () => {
      if (!asset) {
        return
      }
      await saveAsset(courseId, moduleId, asset)
    },
  })

  useEffect(() => {
    let isActive = true

    async function loadTextPreview() {
      if (!asset || !['markdown', 'text', 'subtitle'].includes(previewKind)) {
        setTextPreview('')
        return
      }

      try {
        const content = await getAssetContentText(courseId, moduleId, asset.id)
        if (isActive) {
          setTextPreview(content)
        }
      } catch {
        if (isActive) {
          setTextPreview('')
        }
      }
    }

    void loadTextPreview()

    return () => {
      isActive = false
    }
  }, [asset, courseId, moduleId, previewKind])

  if (!asset) {
    return (
      <div className="asset-preview asset-preview--empty">
        <FileQuestion size={26} />
        <h3>{emptyTitle}</h3>
        <p>{emptyDescription}</p>
      </div>
    )
  }

  return (
    <section className="asset-preview">
      <div className="asset-preview__header">
        <div>
          <p className="asset-preview__eyebrow">Learning material</p>
          <h3 className="asset-preview__title">{asset.title || asset.file_name}</h3>
          <p className="asset-preview__meta">
            {asset.file_name} · {asset.mime_type} · {formatFileSize(asset.file_size)}
          </p>
        </div>
        <div className="asset-preview__actions">
          <button
            className="btn btn--sm btn--secondary"
            disabled={downloadMutation.isPending}
            onClick={() => downloadMutation.mutate()}
            type="button"
          >
            <Download size={14} />
            {downloadMutation.isPending ? 'Preparing...' : 'Download'}
          </button>
          <button
            className="btn btn--sm btn--ghost"
            disabled={!accessQuery.data?.view_url}
            onClick={() => {
              if (accessQuery.data?.view_url) {
                window.open(accessQuery.data.view_url, '_blank', 'noopener,noreferrer')
              }
            }}
            type="button"
          >
            <ExternalLink size={14} />
            Open tab
          </button>
        </div>
      </div>

      {downloadMutation.isError ? (
        <div className="message message--error">{getErrorMessage(downloadMutation.error)}</div>
      ) : null}
      {accessQuery.isError ? (
        <div className="message message--error">{getErrorMessage(accessQuery.error)}</div>
      ) : null}

      {accessQuery.isLoading ? (
        <div className="asset-preview__loading">
          <LoaderCircle className="spin" size={18} />
          <span>Loading preview…</span>
        </div>
      ) : null}

      {!accessQuery.isLoading && previewKind === 'pdf' && accessQuery.data?.view_url ? (
        <div className="asset-preview__frame-wrap">
          <iframe className="asset-preview__frame" src={accessQuery.data.view_url} title={asset.file_name} />
        </div>
      ) : null}

      {!accessQuery.isLoading && previewKind === 'markdown' && textPreview ? (
        <div className="asset-preview__rich-text">
          <MarkdownContent content={textPreview} />
        </div>
      ) : null}

      {!accessQuery.isLoading && (previewKind === 'text' || previewKind === 'subtitle') && textPreview ? (
        <pre className="asset-preview__text">{textPreview}</pre>
      ) : null}

      {!accessQuery.isLoading && previewKind === 'unsupported' ? (
        <div className="asset-preview__unsupported">
          <div className="asset-preview__unsupported-icon">
            <Eye size={18} />
          </div>
          <div>
            <h4>No inline renderer for this file type yet</h4>
            <p>
              You can still open the file in a new tab or download it directly. PDFs, markdown,
              plain text, and subtitle files render inline in the learning player.
            </p>
          </div>
        </div>
      ) : null}
    </section>
  )
}