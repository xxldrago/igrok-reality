import { useEffect, useState } from 'react'
import { Image, Spin } from 'antd'
import { fetchTelegramMedia } from '../services/api'

interface MediaPreviewProps {
  url: string | null
  mediaType: string | null
  /** Thumbnail mode for table cells; full mode for expanded rows. */
  size?: 'thumb' | 'full'
}

/** Inline preview of a report attachment.
 *
 * http(s) URLs render directly; Telegram file_ids are fetched as a blob
 * (admin JWT can't go into <img src>) lazily on mount — i.e. when the
 * report row is expanded.
 */
export default function MediaPreview({ url, mediaType, size = 'full' }: MediaPreviewProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)

  const isDirect = !!url && /^https?:\/\//i.test(url)

  useEffect(() => {
    if (!url || isDirect) return
    let cancelled = false
    setLoading(true)
    setFailed(false)
    fetchTelegramMedia(url)
      .then((res) => {
        if (cancelled) return
        setBlobUrl(URL.createObjectURL(res.data))
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      if (blobUrl) URL.revokeObjectURL(blobUrl)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url])

  if (!url) return null
  if (loading) return <Spin size="small" />
  if (failed) return <span style={{ color: '#999' }}>Не удалось загрузить</span>

  const src = isDirect ? url : blobUrl
  if (!src) return <Spin size="small" />

  const thumbStyle = { maxWidth: 64, maxHeight: 64, objectFit: 'cover' as const, borderRadius: 4 }
  const fullStyle = { maxWidth: '100%', maxHeight: 420, borderRadius: 4 }

  if (mediaType === 'video') {
    return (
      <video
        src={src}
        controls
        preload="metadata"
        style={size === 'thumb' ? thumbStyle : fullStyle}
      />
    )
  }
  if (mediaType === 'document') {
    return (
      <a href={src} target="_blank" rel="noreferrer" download>
        📎 Скачать файл
      </a>
    )
  }
  // photo (default)
  if (size === 'thumb') {
    return <img src={src} alt="Вложение" style={thumbStyle} />
  }
  return <Image src={src} alt="Вложение" style={fullStyle} />
}
