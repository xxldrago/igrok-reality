import { useState } from 'react'
import { Upload, Button, message, Image, Space } from 'antd'
import { UploadOutlined, DeleteOutlined, FileOutlined } from '@ant-design/icons'
import { uploadMedia } from '../services/api'

interface MediaUploadProps {
  value?: string | null
  mediaType?: string | null
  onChange?: (url: string | null, mediaType: string | null) => void
}

export function mediaTypeLabel(mediaType: string | null | undefined): string {
  if (mediaType === 'photo') return 'Фото'
  if (mediaType === 'video') return 'Видео'
  if (mediaType === 'document') return 'Файл'
  return 'Вложение'
}

export default function MediaUpload({ value, mediaType, onChange }: MediaUploadProps) {
  const [uploading, setUploading] = useState(false)

  const customRequest = async (options: unknown) => {
    const opts = options as { file: File; onSuccess?: (v: unknown) => void; onError?: (v: unknown) => void }
    setUploading(true)
    try {
      const res = await uploadMedia(opts.file)
      onChange?.(res.data.url, res.data.media_type)
      message.success('Файл загружен')
      opts.onSuccess?.(res.data)
    } catch {
      message.error('Ошибка загрузки файла')
      opts.onError?.(new Error('upload failed'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      {value ? (
        <Space direction="vertical" style={{ width: '100%' }}>
          {mediaType === 'photo' ? (
            <Image src={value} alt="Вложение" width={200} />
          ) : mediaType === 'video' ? (
            <video src={value} controls style={{ maxWidth: '100%', maxHeight: 240 }} />
          ) : (
            <a href={value} target="_blank" rel="noreferrer">
              <FileOutlined /> {mediaTypeLabel(mediaType)} — открыть
            </a>
          )}
          <Button
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => onChange?.(null, null)}
          >
            Убрать вложение
          </Button>
        </Space>
      ) : (
        <Upload
          customRequest={customRequest}
          showUploadList={false}
          accept="image/*,video/*,.pdf,.zip,.doc,.docx,.xls,.xlsx,.mp3,.ogg,.wav,.txt"
        >
          <Button icon={<UploadOutlined />} loading={uploading}>
            Загрузить фото / видео / файл
          </Button>
        </Upload>
      )}
    </Space>
  )
}
