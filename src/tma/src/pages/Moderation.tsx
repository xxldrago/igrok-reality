import { useState, useEffect } from 'react'
import { Table, Tag, Select, Space, Button, Typography, Modal, Form, Input, message, Popconfirm } from 'antd'
import { CheckCircleOutlined, StopOutlined, WarningOutlined, MessageOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getModerationReports,
  resolveModerationReport,
  replyModerationReport,
  deleteModerationReport,
  ModerationReportItem,
} from '../services/api'
import MediaUpload from '../components/MediaUpload'

const { Title } = Typography

const statusColors: Record<string, string> = {
  pending: 'orange',
  warned: 'gold',
  banned: 'red',
  excluded: 'purple',
}

const statusLabels: Record<string, string> = {
  pending: 'Ожидает',
  warned: 'Предупреждён',
  banned: 'Заблокирован',
  excluded: 'Исключён',
}

export default function Moderation() {
  const [reports, setReports] = useState<ModerationReportItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [replyModalOpen, setReplyModalOpen] = useState(false)
  const [replyingReport, setReplyingReport] = useState<ModerationReportItem | null>(null)
  const [replySending, setReplySending] = useState(false)
  const [replyMediaUrl, setReplyMediaUrl] = useState<string | null>(null)
  const [replyMediaType, setReplyMediaType] = useState<string | null>(null)
  const [replyForm] = Form.useForm()

  const loadReports = (status?: string) => {
    setLoading(true)
    getModerationReports(status ? { status } : undefined)
      .then((res) => {
        setReports(res.data.reports)
        setTotal(res.data.total)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadReports(statusFilter)
  }, [statusFilter])

  const handleResolve = async (id: string, decision: string) => {
    try {
      await resolveModerationReport(id, decision)
      loadReports(statusFilter)
      message.success(`Решение: ${decision}`)
    } catch {
      message.error('Ошибка')
    }
  }

  const openReply = (record: ModerationReportItem) => {
    setReplyingReport(record)
    replyForm.resetFields()
    setReplyMediaUrl(null)
    setReplyMediaType(null)
    setReplyModalOpen(true)
  }

  const handleReply = async () => {
    if (!replyingReport) return
    try {
      const values = await replyForm.validateFields()
      const text = (values.text || '').trim()
      if (!text && !replyMediaUrl) {
        message.warning('Введите текст или прикрепите файл')
        return
      }
      setReplySending(true)
      await replyModerationReport(replyingReport.id, {
        text: text || undefined,
        media_url: replyMediaUrl,
        media_type: replyMediaType,
      })
      message.success('Ответ отправлен')
      setReplyModalOpen(false)
      setReplyingReport(null)
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error('Ошибка отправки')
    } finally {
      setReplySending(false)
    }
  }

  const columns: ColumnsType<ModerationReportItem> = [
    { title: 'Логин', dataIndex: 'username', key: 'username' },
    { title: 'Причина', dataIndex: 'reason', key: 'reason', ellipsis: true },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => (
        <Tag color={statusColors[v] || 'default'}>{statusLabels[v] || v}</Tag>
      ),
    },
    {
      title: '',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          {record.status === 'pending' ? (
            <>
              <Button
                size="small"
                icon={<MessageOutlined />}
                onClick={() => openReply(record)}
              />
              <Button
                size="small"
                icon={<WarningOutlined />}
                onClick={() => handleResolve(record.id, 'warn')}
              />
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => handleResolve(record.id, 'ban')}
              />
              <Button
                size="small"
                danger
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => handleResolve(record.id, 'exclude')}
              />
            </>
          ) : null}
          <Popconfirm
            title="Удалить жалобу?"
            okText="Удалить"
            cancelText="Отмена"
            okType="danger"
            onConfirm={async () => {
              try {
                await deleteModerationReport(record.id)
                message.success('Жалоба удалена')
                loadReports(statusFilter)
              } catch {
                message.error('Ошибка удаления')
              }
            }}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={4}>Модерация</Title>

      <Space style={{ marginBottom: 12 }}>
        <Select
          placeholder="Статус"
          allowClear
          style={{ width: 160 }}
          size="small"
          value={statusFilter}
          onChange={setStatusFilter}
          options={Object.entries(statusLabels).map(([value, label]) => ({
            value,
            label,
          }))}
        />
      </Space>

      <Table
        dataSource={reports}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={{ total, pageSize: 20 }}
      />

      <Modal
        title="Ответ пользователю"
        open={replyModalOpen}
        onCancel={() => setReplyModalOpen(false)}
        onOk={handleReply}
        confirmLoading={replySending}
        okText="Отправить"
        cancelText="Отмена"
      >
        <Form form={replyForm} layout="vertical">
          <Form.Item name="text" label="Текст ответа">
            <Input.TextArea rows={4} placeholder="Сообщение пользователю в боте" />
          </Form.Item>
          <Form.Item label="Вложение">
            <MediaUpload
              value={replyMediaUrl}
              mediaType={replyMediaType}
              onChange={(url, type) => {
                setReplyMediaUrl(url)
                setReplyMediaType(type)
              }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
