import { useState, useEffect } from 'react'
import { Table, Space, Button, Typography, Modal, Form, Input, InputNumber, Tag, Select, message } from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getSpecialistQuests,
  createSpecialistQuest,
  deleteSpecialistQuest,
  getGroups,
  GroupItem,
  SpecialistQuestItem,
} from '../services/api'
import RoleGuard from '../components/RoleGuard'
import MediaUpload from '../components/MediaUpload'
import MediaPreview from '../components/MediaPreview'

function guessMediaType(url: string): string | null {
  const clean = url.split('?')[0].toLowerCase()
  if (/\.(jpg|jpeg|png|gif|webp)$/.test(clean)) return 'photo'
  if (/\.(mp4|mov|m4v|avi|mkv)$/.test(clean)) return 'video'
  return 'document'
}

const { Title } = Typography

const { TextArea } = Input

export default function SpecialistQuests() {
  const [quests, setQuests] = useState<SpecialistQuestItem[]>([])
  const [loading, setLoading] = useState(true)
  const [groupFilter, setGroupFilter] = useState<string | undefined>(undefined)
  const [dayFilter, setDayFilter] = useState<number | undefined>(undefined)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [form] = Form.useForm()
  const [mediaUrl, setMediaUrl] = useState<string | null>(null)
  const [mediaType, setMediaType] = useState<string | null>(null)
  const [groups, setGroups] = useState<GroupItem[]>([])

  useEffect(() => {
    getGroups().then((res) => setGroups(res.data)).catch(console.error)
  }, [])

  const groupName = (groupId: string): string => {
    const found = groups.find((g) => g.id === groupId)
    return found ? found.name : groupId
  }

  const loadQuests = () => {
    setLoading(true)
    const params: { group_id?: string; day_number?: number } = {}
    if (groupFilter) params.group_id = groupFilter
    if (dayFilter) params.day_number = dayFilter
    getSpecialistQuests(Object.keys(params).length ? params : undefined)
      .then((res) => setQuests(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadQuests()
  }, [groupFilter, dayFilter])

  const openCreate = () => {
    form.resetFields()
    setMediaUrl(null)
    setMediaType(null)
    setCreateModalOpen(true)
  }

  const handleCreate = async (values: { group_id: string; title: string; content: string; day_number: number; xp_reward?: number }) => {
    try {
      await createSpecialistQuest({ ...values, media_file_id: mediaUrl })
      loadQuests()
      setCreateModalOpen(false)
      form.resetFields()
      setMediaUrl(null)
      setMediaType(null)
      message.success('Квест создан')
    } catch {
      message.error('Ошибка создания квеста')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteSpecialistQuest(id)
      loadQuests()
      message.success('Квест удалён')
    } catch {
      message.error('Ошибка удаления квеста')
    }
  }

  const columns: ColumnsType<SpecialistQuestItem> = [
    {
      title: 'Группа',
      dataIndex: 'group_id',
      key: 'group_id',
      ellipsis: true,
      render: (groupId: string) => <span title={groupId}>{groupName(groupId)}</span>,
    },
    { title: 'Заголовок', dataIndex: 'title', key: 'title' },
    {
      title: 'День',
      dataIndex: 'day_number',
      key: 'day_number',
      render: (d: number) => <Tag>{d}</Tag>,
    },
    {
      title: 'XP',
      dataIndex: 'xp_reward',
      key: 'xp_reward',
      render: (xp: number) => `+${xp}`,
    },
    {
      title: '📎',
      dataIndex: 'media_file_id',
      key: 'media_file_id',
      width: 50,
      render: (media: string | null) => (media ? <Tag color="blue">есть</Tag> : '—'),
    },
    {
      title: 'Дата публикации',
      dataIndex: 'published_at',
      key: 'published_at',
      render: (d: string | null) => d ? new Date(d).toLocaleDateString('ru-RU') : '—',
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <RoleGuard roles={['master']}>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            Удалить
          </Button>
        </RoleGuard>
      ),
    },
  ]

  return (
    <div>
      <Title level={4}>Квесты специалистов</Title>
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="Фильтр по группе"
          allowClear
          style={{ width: 220 }}
          value={groupFilter}
          onChange={setGroupFilter}
          options={groups.map((g) => ({ value: g.id, label: g.name }))}
        />
        <InputNumber
          placeholder="День"
          min={1}
          max={90}
          style={{ width: 100 }}
          value={dayFilter}
          onChange={(v) => setDayFilter(v ?? undefined)}
        />
        <RoleGuard roles={['master', 'specialist']}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Создать квест
          </Button>
        </RoleGuard>
      </Space>

      <Table
        columns={columns}
        dataSource={quests}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
        expandable={{
          expandedRowRender: (record) => (
            <div>
              <div style={{ whiteSpace: 'pre-wrap', color: '#555', marginBottom: 8 }}>{record.content}</div>
              {record.media_file_id ? (
                <MediaPreview
                  url={record.media_file_id}
                  mediaType={
                    record.media_file_id.startsWith('http')
                      ? guessMediaType(record.media_file_id)
                      : null
                  }
                  size="full"
                />
              ) : null}
            </div>
          ),
        }}
      />

      <Modal
        title="Создать квест"
        open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); form.resetFields() }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="group_id" label="Группа" rules={[{ required: true, message: 'Выберите группу' }]}>
            <Select
              placeholder="Выберите группу по названию"
              options={groups.map((g) => ({ value: g.id, label: g.name }))}
            />
          </Form.Item>
          <Form.Item name="title" label="Заголовок" rules={[{ required: true, message: 'Введите заголовок' }]}>
            <Input placeholder="Заголовок квеста" />
          </Form.Item>
          <Form.Item name="content" label="Содержание" rules={[{ required: true, message: 'Введите содержание' }]}>
            <TextArea rows={4} placeholder="Описание квеста" />
          </Form.Item>
          <Form.Item label="Вложение (фото / видео / файл)">
            <MediaUpload
              value={mediaUrl}
              mediaType={mediaType}
              onChange={(url, type) => {
                setMediaUrl(url)
                setMediaType(type)
              }}
            />
          </Form.Item>
          <Form.Item name="day_number" label="День (1-90)" rules={[{ required: true, message: 'Укажите день' }]}>
            <InputNumber min={1} max={90} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="xp_reward" label="Награда XP">
            <InputNumber min={0} placeholder="50" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
