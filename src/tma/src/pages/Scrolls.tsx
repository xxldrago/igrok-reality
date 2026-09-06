import { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Input,
  Tag,
  Button,
  Space,
  Empty,
  Spin,
  Modal,
  Form,
  Select,
  InputNumber,
  message,
  Popconfirm,
} from 'antd'
import {
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import {
  getScrolls,
  createScroll,
  updateScroll,
  deleteScroll,
  type ScrollItem,
  type GetScrollsParams,
  type ScrollCreateData,
  type ScrollUpdateData,
} from '../services/api'

const archetypeColors: Record<string, string> = {
  Голова: 'blue',
  Панцирь: 'green',
  Вихрь: 'orange',
  Призрак: 'purple',
}

export default function Scrolls() {
  const [scrolls, setScrolls] = useState<ScrollItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [searchDay, setSearchDay] = useState<string>('')
  const [archetypeFilter, setArchetypeFilter] = useState<string | undefined>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingScroll, setEditingScroll] = useState<ScrollItem | null>(null)
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const pageSize = 20

  const fetchScrolls = useCallback(
    async (p: number, reset: boolean = false) => {
      setLoading(true)
      try {
        const params: GetScrollsParams = { page: p, page_size: pageSize }
        if (archetypeFilter) params.archetype = archetypeFilter
        if (searchDay) params.day_number = Number(searchDay)

        const res = await getScrolls(params)
        setScrolls((prev) => (reset ? res.data.scrolls : [...prev, ...res.data.scrolls]))
        setTotal(res.data.total)
      } catch {
        // Error handled by API interceptor
      } finally {
        setLoading(false)
      }
    },
    [archetypeFilter, searchDay],
  )

  useEffect(() => {
    setPage(1)
    fetchScrolls(1, true)
  }, [fetchScrolls])

  const loadMore = () => {
    const nextPage = page + 1
    setPage(nextPage)
    fetchScrolls(nextPage)
  }

  const openCreate = () => {
    setEditingScroll(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (scroll: ScrollItem) => {
    setEditingScroll(scroll)
    form.setFieldsValue({
      day_number: scroll.day_number,
      archetype: scroll.archetype,
      text: scroll.text,
      media_file_id: scroll.media_file_id,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)

      if (editingScroll) {
        const data: ScrollUpdateData = {
          text: values.text,
          media_file_id: values.media_file_id || null,
        }
        await updateScroll(editingScroll.id, data)
        message.success('Свиток обновлён')
      } else {
        const data: ScrollCreateData = {
          day_number: values.day_number,
          archetype: values.archetype,
          text: values.text,
          media_file_id: values.media_file_id || null,
        }
        await createScroll(data)
        message.success('Свиток создан')
      }

      setModalOpen(false)
      setPage(1)
      fetchScrolls(1, true)
    } catch {
      // Validation or API error
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteScroll(id)
      message.success('Свиток удалён')
      setPage(1)
      fetchScrolls(1, true)
    } catch {
      // Error handled by API interceptor
    }
  }

  const archetypes = ['Голова', 'Панцирь', 'Вихрь', 'Призрак']

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <Input
          placeholder="День"
          prefix={<SearchOutlined />}
          value={searchDay}
          onChange={(e) => setSearchDay(e.target.value.replace(/\D/g, ''))}
          style={{ width: 100 }}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          Создать
        </Button>
      </div>

      <Space wrap style={{ marginBottom: 16 }}>
        <Tag
          color={!archetypeFilter ? 'blue' : undefined}
          style={{ cursor: 'pointer' }}
          onClick={() => setArchetypeFilter(undefined)}
        >
          Все
        </Tag>
        {archetypes.map((a) => (
          <Tag
            key={a}
            color={archetypeFilter === a ? archetypeColors[a] : undefined}
            style={{ cursor: 'pointer' }}
            onClick={() =>
              setArchetypeFilter(archetypeFilter === a ? undefined : a)
            }
          >
            {a}
          </Tag>
        ))}
      </Space>

      {scrolls.length === 0 && !loading ? (
        <Empty description="Нет свитков" />
      ) : (
        <>
          {scrolls.map((s) => (
            <Card
              key={s.id}
              size="small"
              style={{ marginBottom: 8 }}
              title={
                <span>
                  День {s.day_number}{' '}
                  <Tag color={archetypeColors[s.archetype] || 'default'}>
                    {s.archetype}
                  </Tag>
                </span>
              }
              extra={
                <Space>
                  <EditOutlined
                    style={{ color: 'var(--tg-theme-link-color)' }}
                    onClick={() => openEdit(s)}
                  />
                  <Popconfirm
                    title="Удалить свиток?"
                    onConfirm={() => handleDelete(s.id)}
                    okText="Да"
                    cancelText="Нет"
                  >
                    <DeleteOutlined style={{ color: 'var(--tg-theme-destructive-text-color)' }} />
                  </Popconfirm>
                </Space>
              }
            >
              <div
                style={{
                  fontSize: 13,
                  color: '#333',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                }}
              >
                {s.text}
              </div>
            </Card>
          ))}

          {scrolls.length < total && (
            <Button block onClick={loadMore} loading={loading} style={{ marginTop: 8 }}>
              Загрузить ещё
            </Button>
          )}
        </>
      )}

      {loading && scrolls.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      )}

      <Modal
        title={editingScroll ? 'Редактировать свиток' : 'Новый свиток'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical">
          {!editingScroll && (
            <>
              <Form.Item
                name="day_number"
                label="День"
                rules={[{ required: true, message: 'Укажите номер дня' }]}
              >
                <InputNumber min={1} max={90} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="archetype"
                label="Архетип"
                rules={[{ required: true, message: 'Выберите архетип' }]}
              >
                <Select placeholder="Выберите архетип">
                  {archetypes.map((a) => (
                    <Select.Option key={a} value={a}>
                      {a}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </>
          )}
          <Form.Item
            name="text"
            label="Текст"
            rules={[{ required: true, message: 'Введите текст свитка' }]}
          >
            <Input.TextArea rows={6} />
          </Form.Item>
          <Form.Item name="media_file_id" label="Media file ID">
            <Input placeholder="Опционально" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
