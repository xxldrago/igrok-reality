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
import type { ColumnsType } from 'antd/es/table'
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

export default function Scrolls() {
  const [scrollTypes, setScrollTypes] = useState<ScrollTypeItem[]>([])
  const [dailyData, setDailyData] = useState<DailyScrollListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [dayFilter, setDayFilter] = useState<number | undefined>(undefined)
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingScroll, setEditingScroll] = useState<DailyScrollItem | null>(null)
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    getScrollTypes()
      .then((res) => setScrollTypes(res.data.scroll_types))
      .catch(console.error)
  }, [])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = { page, page_size: 20 }
      if (dayFilter) params.day_number = dayFilter
      if (typeFilter) {
        const st = scrollTypes.find((s) => s.code === typeFilter)
        if (st) params.scroll_type_id = st.id
      }
      const res = await getDailyScrolls(params)
      setDailyData(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [dayFilter, typeFilter, page, scrollTypes])

  useEffect(() => { fetchData() }, [fetchData])

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
      fetchData()
      message.success('Обновлено')
    } catch {
      message.error('Ошибка')
    } finally {
      setSubmitting(false)
    }
  }

  const columns: ColumnsType<DailyScrollItem> = [
    { title: 'День', dataIndex: 'day_number', key: 'day', width: 50 },
    {
      title: 'Тип',
      dataIndex: 'scroll_type_code',
      key: 'type',
      render: (code: string | null) => {
        const st = scrollTypes.find((s) => s.code === code)
        return st ? <Tag color={timeSlotColors[st.hour] || 'default'}>{st.name}</Tag> : code
      },
    },
    {
      title: '',
      key: 'cmd',
      width: 50,
      render: (_, r) => {
        const st = scrollTypes.find((s) => s.id === r.scroll_type_code)
        return st?.command || ''
      },
    },
    { title: 'Заголовок', dataIndex: 'title', key: 'title', ellipsis: true },
    {
      title: '',
      key: 'edit',
      width: 40,
      render: (_, r) => <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />,
    },
  ]

  return (
    <div>
      <Title level={4}>Свитки</Title>
      <Space style={{ marginBottom: 12 }} size="small">
        <InputNumber
          placeholder="День"
          min={1}
          max={90}
          size="small"
          style={{ width: 80 }}
          value={dayFilter}
          onChange={(v) => setDayFilter(v ?? undefined)}
        />
        <Select
          placeholder="Тип"
          allowClear
          size="small"
          style={{ width: 140 }}
          value={typeFilter}
          onChange={setTypeFilter}
          options={scrollTypes.map((st) => ({ value: st.code, label: st.name }))}
        />
      </Space>

      <Table
        dataSource={dailyData?.scrolls || []}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={{
          current: page,
          total: dailyData?.total || 0,
          pageSize: 20,
          onChange: setPage,
        }}
      />

      <Modal
        title="Редактировать"
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={submitting}
      >
        <Form form={form} onFinish={handleSave} layout="vertical">
          <Form.Item name="title" label="Заголовок"><Input /></Form.Item>
          <Form.Item name="content" label="Контент"><TextArea rows={6} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
