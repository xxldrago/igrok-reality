import { useState, useEffect, useCallback } from 'react'
import {
  Table,
  Button,
  Space,
  Typography,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Tag,
  Alert,
  Collapse,
  message,
} from 'antd'
import { EditOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import {
  getScrollTypes,
  getDailyScrolls,
  getScrollCoverage,
  updateDailyScroll,
  ScrollTypeItem,
  DailyScrollItem,
  DailyScrollListResponse,
  ScrollCoverage,
} from '../services/api'
import MediaUpload from '../components/MediaUpload'

function guessMediaType(url: string): string | null {
  const clean = url.split('?')[0].toLowerCase()
  if (/\.(jpg|jpeg|png|gif|webp)$/.test(clean)) return 'photo'
  if (/\.(mp4|mov|m4v|avi|mkv)$/.test(clean)) return 'video'
  return 'document'
}

const { Title } = Typography
const { TextArea } = Input

const timeSlotColors: Record<number, string> = {
  5: 'blue',
  8: 'green',
  12: 'orange',
  16: 'purple',
  21: 'cyan',
  '-1': 'default',
}

const timeSlotLabels: Record<number, string> = {
  5: '05:00 Утро',
  8: '08:00 День',
  12: '12:00 Полдень',
  16: '16:00 Вечер',
  21: '21:00 Ночь',
  '-1': 'Любое время',
}

export default function Scrolls() {
  const [scrollTypes, setScrollTypes] = useState<ScrollTypeItem[]>([])
  const [dailyData, setDailyData] = useState<DailyScrollListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [dayFilter, setDayFilter] = useState<number | undefined>(undefined)
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined)
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 20,
  })
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingScroll, setEditingScroll] = useState<DailyScrollItem | null>(null)
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [mediaUrl, setMediaUrl] = useState<string | null>(null)
  const [mediaType, setMediaType] = useState<string | null>(null)
  const [coverage, setCoverage] = useState<ScrollCoverage | null>(null)
  const [coverageLoading, setCoverageLoading] = useState(false)

  const fetchCoverage = useCallback(async () => {
    setCoverageLoading(true)
    try {
      const res = await getScrollCoverage()
      setCoverage(res.data)
    } catch (error) {
      console.error('Failed to fetch coverage:', error)
    } finally {
      setCoverageLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCoverage()
  }, [fetchCoverage])

  useEffect(() => {
    getScrollTypes()
      .then((res) => setScrollTypes(res.data.scroll_types))
      .catch(console.error)
  }, [])

  const fetchDailyScrolls = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = {
        page: pagination.current || 1,
        page_size: pagination.pageSize || 20,
      }
      if (dayFilter) params.day_number = dayFilter
      if (typeFilter) {
        const st = scrollTypes.find((s) => s.code === typeFilter)
        if (st) params.scroll_type_id = st.id
      }
      const res = await getDailyScrolls(params)
      setDailyData(res.data)
    } catch (error) {
      console.error('Failed to fetch daily scrolls:', error)
    } finally {
      setLoading(false)
    }
  }, [dayFilter, typeFilter, pagination.current, pagination.pageSize, scrollTypes])

  useEffect(() => {
    fetchDailyScrolls()
  }, [fetchDailyScrolls])

  const handleEdit = (record: DailyScrollItem) => {
    setEditingScroll(record)
    form.setFieldsValue({ title: record.title, content: record.content })
    setMediaUrl(record.media_file_id || null)
    setMediaType(
      record.media_file_id && record.media_file_id.startsWith('http')
        ? guessMediaType(record.media_file_id)
        : null,
    )
    setEditModalOpen(true)
  }

  const handleSave = async (values: { title: string; content: string }) => {
    if (!editingScroll) return
    setSubmitting(true)
    try {
      await updateDailyScroll(editingScroll.id, { ...values, media_file_id: mediaUrl || '' })
      setEditModalOpen(false)
      fetchDailyScrolls()
      fetchCoverage()
      message.success('Свиток обновлён')
    } catch {
      message.error('Ошибка сохранения')
    } finally {
      setSubmitting(false)
    }
  }

  const columns: ColumnsType<DailyScrollItem> = [
    {
      title: 'День',
      dataIndex: 'day_number',
      key: 'day_number',
      width: 70,
    },
    {
      title: 'Тип дня',
      key: 'day_type',
      width: 170,
      render: (_, record) => {
        const kind = coverage?.day_types[record.day_number]
        if (!kind) return '—'
        const label = dayTypeLabels[kind] || { text: kind, color: 'default' }
        return <Tag color={label.color}>{label.text}</Tag>
      },
    },
    {
      title: 'Тип',
      dataIndex: 'scroll_type_code',
      key: 'scroll_type_code',
      width: 120,
      render: (code: string | null) => {
        const st = scrollTypes.find((s) => s.code === code)
        return st ? (
          <Tag color={timeSlotColors[st.hour] || 'default'}>
            {st.name}
          </Tag>
        ) : (
          code
        )
      },
    },
    {
      title: 'Команда',
      key: 'command',
      width: 100,
      render: (_, record) => {
        const st = scrollTypes.find((s) => s.id === record.scroll_type_code)
        return st?.command || '—'
      },
    },
    {
      title: 'Время',
      key: 'time',
      width: 120,
      render: (_, record) => {
        const st = scrollTypes.find((s) => s.id === record.scroll_type_code)
        return st ? (
          <Tag color={timeSlotColors[st.hour] || 'default'}>
            {timeSlotLabels[st.hour] || `${st.hour}:${String(st.minute).padStart(2, '0')}`}
          </Tag>
        ) : '—'
      },
    },
    {
      title: 'XP',
      key: 'xp',
      width: 60,
      render: (_, record) => {
        const st = scrollTypes.find((s) => s.id === record.scroll_type_code)
        return st ? `+${st.xp_reward}` : '—'
      },
    },
    {
      title: 'Заголовок',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '📎',
      dataIndex: 'media_file_id',
      key: 'media_file_id',
      width: 50,
      render: (media: string | null) => (media ? <Tag color="blue">есть</Tag> : '—'),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 60,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => handleEdit(record)}
        />
      ),
    },
  ]

  const dayTypeLabels: Record<string, { text: string; color: string }> = {
    standard: { text: 'Обычный', color: 'default' },
    meditation: { text: 'Медитация', color: 'green' },
    breathing: { text: 'Дыхание', color: 'blue' },
    awareness: { text: 'Осознание (2 свитка)', color: 'orange' },
  }

  return (
    <div>
      <Title level={3}>Свитки</Title>

      {coverage && (
        coverage.complete ? (
          <Alert
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
            message={`Покрытие полное: ${coverage.total_actual}/${coverage.total_expected}`}
            action={
              <Button size="small" icon={<ReloadOutlined />} onClick={fetchCoverage} loading={coverageLoading}>
                Обновить
              </Button>
            }
          />
        ) : (
          <Alert
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
            message={`Не хватает свитков: ${coverage.total_actual}/${coverage.total_expected}. Дней с пробелами: ${coverage.missing_days.length}`}
            action={
              <Button size="small" icon={<ReloadOutlined />} onClick={fetchCoverage} loading={coverageLoading}>
                Обновить
              </Button>
            }
            description={
              <Collapse
                size="small"
                items={[
                  {
                    key: 'gaps',
                    label: 'Показать дни с пробелами',
                    children: (
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {coverage.missing_days.map((d) => (
                          <li key={d.day}>
                            День {d.day} ({d.day_type}): нет {d.missing.join(', ')}
                          </li>
                        ))}
                      </ul>
                    ),
                  },
                ]}
              />
            }
          />
        )
      )}

      <Space style={{ marginBottom: 16 }}>
        <InputNumber
          placeholder="День"
          min={1}
          max={90}
          style={{ width: 100 }}
          value={dayFilter}
          onChange={(v) => setDayFilter(v ?? undefined)}
        />
        <Select
          placeholder="Тип свитка"
          allowClear
          style={{ width: 180 }}
          value={typeFilter}
          onChange={setTypeFilter}
          options={scrollTypes.map((st) => ({
            value: st.code,
            label: `${st.name} (${st.command})`,
          }))}
        />
      </Space>

      <Table
        dataSource={dailyData?.scrolls || []}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          ...pagination,
          total: dailyData?.total || 0,
          onChange: (page, pageSize) => setPagination({ current: page, pageSize }),
        }}
      />

      <Modal
        title="Редактировать свиток"
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={submitting}
      >
        <Form form={form} onFinish={handleSave} layout="vertical">
          <Form.Item name="title" label="Заголовок">
            <Input />
          </Form.Item>
          <Form.Item name="content" label="Контент">
            <TextArea rows={8} />
          </Form.Item>
          <Form.Item label="Вложение (фото / видео / файл)">
            {mediaUrl && !mediaUrl.startsWith('http') ? (
              <Space direction="vertical">
                <span>
                  Telegram file_id: <code>{mediaUrl}</code>
                </span>
                <Button size="small" danger onClick={() => setMediaUrl(null)}>
                  Убрать вложение
                </Button>
              </Space>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }}>
                <MediaUpload
                  value={mediaUrl}
                  mediaType={mediaType}
                  onChange={(url, type) => {
                    setMediaUrl(url)
                    setMediaType(type)
                  }}
                />
                <Input
                  placeholder="…или вставьте ссылку на файл"
                  value={mediaUrl || ''}
                  onChange={(e) => {
                    const v = e.target.value || null
                    setMediaUrl(v)
                    setMediaType(v && v.startsWith('http') ? guessMediaType(v) : null)
                  }}
                />
              </Space>
            )}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
