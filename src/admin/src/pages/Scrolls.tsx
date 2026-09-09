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
  message,
} from 'antd'
import { EditOutlined } from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import {
  getScrollTypes,
  getDailyScrolls,
  updateDailyScroll,
  ScrollTypeItem,
  DailyScrollItem,
  DailyScrollListResponse,
} from '../services/api'

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
    setEditModalOpen(true)
  }

  const handleSave = async (values: { title: string; content: string }) => {
    if (!editingScroll) return
    setSubmitting(true)
    try {
      await updateDailyScroll(editingScroll.id, values)
      setEditModalOpen(false)
      fetchDailyScrolls()
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

  return (
    <div>
      <Title level={3}>Свитки</Title>

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
        </Form>
      </Modal>
    </div>
  )
}
