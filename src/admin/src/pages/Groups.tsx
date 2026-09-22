import { useState, useEffect } from 'react'
import { Table, Tag, Select, Space, Button, Typography, Modal, Form, Input, InputNumber, Popconfirm, message } from 'antd'
import { PlusOutlined, DeleteOutlined, TeamOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getGroups,
  createGroup,
  deleteGroup,
  addGroupMember,
  getUsers,
  GroupItem,
  UserListItem,
} from '../services/api'
import RoleGuard from '../components/RoleGuard'

function userLabel(u: UserListItem): string {
  const name = `${u.first_name || ''} ${u.last_name || ''}`.trim() || 'Без имени'
  return u.username ? `@${u.username} — ${name}` : `${name} (tg ${u.telegram_id})`
}

const { Title } = Typography

const typeColors: Record<string, string> = {
  curator: 'blue',
  leader: 'green',
  specialist: 'purple',
  quest: 'gold',
}

const typeLabels: Record<string, string> = {
  curator: 'Куратор',
  leader: 'Лидер',
  specialist: 'Специалист',
  quest: 'Квест (автонабор)',
}

export default function Groups() {
  const [groups, setGroups] = useState<GroupItem[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [memberModalOpen, setMemberModalOpen] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<GroupItem | null>(null)
  const [newMemberId, setNewMemberId] = useState('')
  const [form] = Form.useForm()
  const [ownerOptions, setOwnerOptions] = useState<UserListItem[]>([])
  const [ownerLoading, setOwnerLoading] = useState(false)

  const loadGroups = () => {
    setLoading(true)
    getGroups(typeFilter ? { group_type: typeFilter } : undefined)
      .then((res) => setGroups(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadGroups()
  }, [typeFilter])

  const searchOwners = (query: string) => {
    setOwnerLoading(true)
    getUsers({ search: query || undefined, page_size: 20 })
      .then((res) => setOwnerOptions(res.data.users))
      .catch(console.error)
      .finally(() => setOwnerLoading(false))
  }

  useEffect(() => {
    if (createModalOpen && ownerOptions.length === 0) {
      searchOwners('')
    }
  }, [createModalOpen])

  const ownerName = (ownerId: string | null): string => {
    if (!ownerId) return '—'
    const found = ownerOptions.find((u) => u.id === ownerId)
    return found ? userLabel(found) : ownerId
  }

  const handleCreate = async (values: { name: string; type: string; owner_id: string; max_members?: number }) => {
    try {
      await createGroup(values)
      loadGroups()
      setCreateModalOpen(false)
      form.resetFields()
      message.success('Группа создана')
    } catch {
      message.error('Ошибка создания группы')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteGroup(id)
      loadGroups()
      message.success('Группа удалена')
    } catch {
      message.error('Ошибка удаления группы')
    }
  }

  const handleAddMember = async () => {
    if (!selectedGroup || !newMemberId.trim()) return
    try {
      await addGroupMember(selectedGroup.id, newMemberId.trim())
      setNewMemberId('')
      // Reload groups to get updated member_count
      loadGroups()
      message.success('Участник добавлен')
    } catch {
      message.error('Ошибка добавления участника')
    }
  }

  const columns: ColumnsType<GroupItem> = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    {
      title: 'Тип',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag color={typeColors[type] || 'default'}>{typeLabels[type] || type}</Tag>,
    },
    {
      title: 'Владелец',
      dataIndex: 'owner_id',
      key: 'owner_id',
      ellipsis: true,
      render: (ownerId: string) => <span title={ownerId}>{ownerName(ownerId)}</span>,
    },
    {
      title: 'Участники',
      key: 'members',
      render: (_, record) => `${record.member_count} / ${record.max_members}`,
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<TeamOutlined />}
            onClick={() => {
              setSelectedGroup(record)
              setMemberModalOpen(true)
            }}
          >
            Участники
          </Button>
          <RoleGuard roles={['master']}>
            <Popconfirm title="Удалить группу?" onConfirm={() => handleDelete(record.id)}>
              <Button size="small" danger icon={<DeleteOutlined />}>
                Удалить
              </Button>
            </Popconfirm>
          </RoleGuard>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={4}>Группы</Title>
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="Фильтр по типу"
          allowClear
          style={{ width: 200 }}
          value={typeFilter}
          onChange={setTypeFilter}
          options={[
            { value: 'curator', label: 'Куратор' },
            { value: 'leader', label: 'Лидер' },
            { value: 'specialist', label: 'Специалист' },
            { value: 'quest', label: 'Квест (автонабор)' },
          ]}
        />
        <RoleGuard roles={['master', 'leader']}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            Создать группу
          </Button>
        </RoleGuard>
      </Space>

      <Table
        columns={columns}
        dataSource={groups}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title="Создать группу"
        open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); form.resetFields() }}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="Название" rules={[{ required: true, message: 'Введите название' }]}>
            <Input placeholder="Название группы" />
          </Form.Item>
          <Form.Item name="type" label="Тип" rules={[{ required: true, message: 'Выберите тип' }]}>
            <Select
              placeholder="Тип группы"
              options={[
                { value: 'curator', label: 'Куратор' },
                { value: 'leader', label: 'Лидер' },
                { value: 'specialist', label: 'Специалист' },
                { value: 'quest', label: 'Квест (автонабор)' },
              ]}
            />
          </Form.Item>
          <Form.Item name="owner_id" label="Владелец (не нужен для квестов)">
            <Select
              showSearch
              placeholder="Выберите пользователя по username"
              filterOption={false}
              loading={ownerLoading}
              onSearch={searchOwners}
              notFoundContent={ownerLoading ? 'Загрузка...' : 'Ничего не найдено'}
              options={ownerOptions.map((u) => ({ value: u.id, label: userLabel(u) }))}
            />
          </Form.Item>
          <Form.Item name="max_members" label="Макс. участников">
            <InputNumber min={1} max={1000} placeholder="100" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Участники: ${selectedGroup?.name || ''}`}
        open={memberModalOpen}
        onCancel={() => { setMemberModalOpen(false); setSelectedGroup(null); setNewMemberId('') }}
        footer={null}
      >
        <Space style={{ marginBottom: 16 }}>
          <Input
            placeholder="Telegram ID пользователя"
            value={newMemberId}
            onChange={(e) => setNewMemberId(e.target.value)}
          />
          <Button type="primary" onClick={handleAddMember}>
            Добавить
          </Button>
        </Space>
        {selectedGroup && (
          <div style={{ color: '#666' }}>
            Участников: {selectedGroup.member_count} / {selectedGroup.max_members}
          </div>
        )}
      </Modal>
    </div>
  )
}
