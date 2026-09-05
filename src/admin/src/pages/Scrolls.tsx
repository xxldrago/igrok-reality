import { useState, useEffect, useCallback } from 'react'
import {
  Table,
  Button,
  Space,
  Tag,
  Spin,
  Typography,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Popconfirm,
  message,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, FileOutlined } from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import {
  getScrolls,
  createScroll,
  updateScroll,
  deleteScroll,
  ScrollItem,
  ScrollListResponse,
} from '../services/api'

const { Title } = Typography
const { TextArea } = Input

const archetypeColors: Record<string, string> = {
  head: 'blue',
  shell: 'green',
  whirlwind: 'orange',
  ghost: 'purple',
}

const archetypeLabels: Record<string, string> = {
  head: 'Голова',
  shell: 'Панцирь',
  whirlwind: 'Вихрь',
  ghost: 'Призрак',
}

export default function Scrolls() {
  const [data, setData] = useState<ScrollListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [archetypeFilter, setArchetypeFilter] = useState<string | undefined>(undefined)
  const [dayFilter, setDayFilter] = useState<number | undefined>(undefined)
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 20,
    showSizeChanger: true,
    pageSizeOptions: ['10', '20', '50'],
  })
  const [modalOpen, setModalOpen] = useState(false)
  const [editingScroll, setEditingScroll] = useState<ScrollItem | null>(null)
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getScrolls({
        archetype: archetypeFilter,
        day_number: dayFilter,
        page: pagination.current || 1,
        page_size: pagination.pageSize || 20,
      })
      setData(response.data)
    } catch (error) {
      console.error('Failed to fetch scrolls:', error)
    } finally {
      setLoading(false)
    }
  }, [archetypeFilter, dayFilter, pagination.current, pagination.pageSize])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleCreate = () => {
    setEditingScroll(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (record: ScrollItem, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingScroll(record)
    form.setFieldsValue({
      day_number: record.day_number,
      archetype: record.archetype,
      text: record.text,
      media_file_id: record.media_file_id,
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteScroll(id)
      message.success('Свиток удалён')
      fetchData()
    } catch {
      message.error('Не удалось удалить свиток')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)

      if (editingScroll) {
        await updateScroll(editingScroll.id, {
          text: values.text,
          media_file_id: values.media_file_id || null,
        })
        message.success('Свиток обновлён')
      } else {
        await createScroll({
          day_number: values.day_number,
          archetype: values.archetype,
          text: values.text,
          media_file_id: values.media_file_id || null,
        })
        message.success('Свиток создан')
      }

      setModalOpen(false)
      fetchData()
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) {
        // Form validation error — do nothing, form shows errors
        return
      }
      message.error('Не удалось сохранить свиток')
    } finally {
      setSubmitting(false)
    }
  }

  const handleTableChange = (pag: TablePaginationConfig) => {
    setPagination((prev) => ({
      ...prev,
      current: pag.current,
      pageSize: pag.pageSize,
    }))
  }

  const columns: ColumnsType<ScrollItem> = [
    {
      title: 'День',
      dataIndex: 'day_number',
      key: 'day_number',
      width: 80,
      sorter: (a, b) => a.day_number - b.day_number,
    },
    {
      title: 'Архетип',
      dataIndex: 'archetype',
      key: 'archetype',
      width: 120,
      render: (archetype: string) => (
        <Tag color={archetypeColors[archetype] || 'default'}>
          {archetypeLabels[archetype] || archetype}
        </Tag>
      ),
    },
    {
      title: 'Текст',
      dataIndex: 'text',
      key: 'text',
      ellipsis: true,
      render: (text: string) => text.length > 80 ? text.slice(0, 80) + '...' : text,
    },
    {
      title: 'Медиа',
      dataIndex: 'media_file_id',
      key: 'media_file_id',
      width: 80,
      align: 'center',
      render: (val: string | null) =>
        val ? <FileOutlined style={{ color: '#1890ff' }} /> : '—',
    },
    {
      title: 'Дата создания',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      render: (date: string) => new Date(date).toLocaleDateString('ru-RU'),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={(e) => handleEdit(record, e)}
          />
          <Popconfirm
            title="Удалить свиток?"
            onConfirm={() => handleDelete(record.id)}
            okText="Да"
            cancelText="Нет"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={4}>Свитки</Title>

      <Space style={{ marginBottom: 16 }} wrap>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          Добавить свиток
        </Button>
        <Select
          placeholder="Архетип"
          value={archetypeFilter}
          onChange={(val) => {
            setArchetypeFilter(val)
            setPagination((prev) => ({ ...prev, current: 1 }))
          }}
          allowClear
          style={{ width: 150 }}
          options={[
            { value: 'head', label: 'Голова' },
            { value: 'shell', label: 'Панцирь' },
            { value: 'whirlwind', label: 'Вихрь' },
            { value: 'ghost', label: 'Призрак' },
          ]}
        />
        <InputNumber
          placeholder="День"
          min={1}
          max={90}
          value={dayFilter}
          onChange={(val) => {
            setDayFilter(val ?? undefined)
            setPagination((prev) => ({ ...prev, current: 1 }))
          }}
          style={{ width: 100 }}
        />
      </Space>

      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={data?.scrolls || []}
          rowKey="id"
          pagination={{
            ...pagination,
            total: data?.total || 0,
          }}
          onChange={handleTableChange}
          locale={{ emptyText: 'Свитки не найдены' }}
        />
      </Spin>

      <Modal
        title={editingScroll ? 'Редактировать свиток' : 'Новый свиток'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        okText={editingScroll ? 'Сохранить' : 'Создать'}
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="day_number"
            label="День"
            rules={[{ required: true, message: 'Укажите номер дня' }]}
          >
            <InputNumber
              min={1}
              max={90}
              disabled={!!editingScroll}
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item
            name="archetype"
            label="Архетип"
            rules={[{ required: true, message: 'Выберите архетип' }]}
          >
            <Select
              disabled={!!editingScroll}
              options={[
                { value: 'head', label: 'Голова' },
                { value: 'shell', label: 'Панцирь' },
                { value: 'whirlwind', label: 'Вихрь' },
                { value: 'ghost', label: 'Призрак' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="text"
            label="Текст"
            rules={[{ required: true, message: 'Введите текст свитка' }]}
          >
            <TextArea rows={6} />
          </Form.Item>
          <Form.Item name="media_file_id" label="Media File ID">
            <Input placeholder="Telegram file_id (необязательно)" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
