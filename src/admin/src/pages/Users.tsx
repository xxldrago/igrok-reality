import { useState, useEffect, useCallback } from 'react'
import { Table, Input, InputNumber, Select, Space, Tag, Spin, Typography, Button, Modal, Form, Switch, message } from 'antd'
import { SearchOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import { getUsers, createUser, updateUser, UserListItem, UserListResponse, UserUpdateData } from '../services/api'
import UserDetail from './UserDetail'
import RoleGuard from '../components/RoleGuard'

const { Title } = Typography

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

export default function Users() {
  const [data, setData] = useState<UserListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [archetype, setArchetype] = useState<string | undefined>(undefined)
  const [isActive, setIsActive] = useState<boolean | undefined>(undefined)
  const [hasPaid, setHasPaid] = useState<boolean | undefined>(undefined)
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 20,
    showSizeChanger: true,
    pageSizeOptions: ['10', '20', '50'],
  })
  const [selectedUser, setSelectedUser] = useState<UserListItem | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getUsers({
        search,
        archetype,
        is_active: isActive,
        has_paid: hasPaid,
        page: pagination.current || 1,
        page_size: pagination.pageSize || 20,
      })
      setData(response.data)
    } catch (error) {
      console.error('Failed to fetch users:', error)
    } finally {
      setLoading(false)
    }
  }, [search, archetype, isActive, hasPaid, pagination.current, pagination.pageSize])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSearch = (value: string) => {
    setSearch(value)
    setPagination((prev) => ({ ...prev, current: 1 }))
  }

  const handleTableChange = (pag: TablePaginationConfig) => {
    setPagination((prev) => ({
      ...prev,
      current: pag.current,
      pageSize: pag.pageSize,
    }))
  }

  const handleRowClick = (record: UserListItem) => {
    setSelectedUser(record)
    setDrawerOpen(true)
  }

  const handleAdd = () => {
    setEditingUser(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true, role: 'player', timezone: 'Asia/Krasnoyarsk', xp: 0, streak: 0 })
    setModalOpen(true)
  }

  const handleEdit = (record: UserListItem) => {
    setEditingUser(record)
    form.setFieldsValue({
      first_name: record.first_name,
      last_name: record.last_name || '',
      username: record.username || '',
      archetype: record.archetype || undefined,
      xp: record.xp,
      streak: record.streak,
      is_active: record.is_active,
      role: record.role || 'player',
      has_paid: record.paid_at ? true : false,
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      const username = values.username ? String(values.username).replace(/^@/, '') : null
      if (editingUser) {
        const data: UserUpdateData = {
          first_name: values.first_name,
          last_name: values.last_name || null,
          username,
          archetype: values.archetype || null,
          xp: values.xp,
          streak: values.streak,
          is_active: values.is_active,
          role: values.role,
          has_paid: values.has_paid,
        }
        await updateUser(editingUser.id, data)
        message.success('Пользователь обновлён')
      } else {
        await createUser({
          telegram_id: Number(values.telegram_id),
          first_name: values.first_name,
          last_name: values.last_name || null,
          username,
          archetype: values.archetype || null,
          xp: values.xp ?? 0,
          streak: values.streak ?? 0,
          is_active: values.is_active ?? true,
          timezone: values.timezone || 'Asia/Krasnoyarsk',
          role: values.role || 'player',
        })
        message.success('Пользователь создан')
      }
      setModalOpen(false)
      fetchData()
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const columns: ColumnsType<UserListItem> = [
    {
      title: 'Имя',
      key: 'name',
      render: (_, record) => (
        <span>
          {record.first_name} {record.last_name || ''}
        </span>
      ),
    },
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      render: (username: string | null) =>
        username ? `@${username}` : '—',
    },
    {
      title: 'Telegram ID',
      dataIndex: 'telegram_id',
      key: 'telegram_id',
    },
    {
      title: 'Архетип',
      dataIndex: 'archetype',
      key: 'archetype',
      render: (archetype: string | null) =>
        archetype ? (
          <Tag color={archetypeColors[archetype] || 'default'}>
            {archetypeLabels[archetype] || archetype}
          </Tag>
        ) : (
          '—'
        ),
    },
    {
      title: 'XP',
      dataIndex: 'xp',
      key: 'xp',
      sorter: true,
    },
    {
      title: 'Streak',
      dataIndex: 'streak',
      key: 'streak',
      sorter: true,
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <span>
          <span
            style={{
              display: 'inline-block',
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: isActive ? '#52c41a' : '#d9d9d9',
              marginRight: 6,
            }}
          />
          {isActive ? 'Активен' : 'Неактивен'}
        </span>
      ),
    },
    {
      title: 'Дата регистрации',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString('ru-RU'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: unknown, record: UserListItem) => (
        <RoleGuard roles={['master', 'leader']}>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={(e) => {
              e.stopPropagation()
              handleEdit(record)
            }}
          >
            Изменить
          </Button>
        </RoleGuard>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Пользователи</Title>
        <RoleGuard roles={['master', 'leader']}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            Добавить пользователя
          </Button>
        </RoleGuard>
      </div>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="Поиск по имени, username или Telegram ID"
          prefix={<SearchOutlined />}
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          style={{ width: 350 }}
          allowClear
        />
        <Select
          placeholder="Архетип"
          value={archetype}
          onChange={(val) => {
            setArchetype(val)
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
        <Select
          placeholder="Статус"
          value={isActive}
          onChange={(val) => {
            setIsActive(val)
            setPagination((prev) => ({ ...prev, current: 1 }))
          }}
          allowClear
          style={{ width: 150 }}
          options={[
            { value: true, label: 'Активен' },
            { value: false, label: 'Неактивен' },
          ]}
        />
        <Select
          placeholder="Оплата"
          value={hasPaid}
          onChange={(val) => {
            setHasPaid(val)
            setPagination((prev) => ({ ...prev, current: 1 }))
          }}
          allowClear
          style={{ width: 150 }}
          options={[
            { value: true, label: 'Оплачено' },
            { value: false, label: 'Не оплачено' },
          ]}
        />
      </Space>

      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={data?.users || []}
          rowKey="id"
          pagination={{
            ...pagination,
            total: data?.total || 0,
          }}
          onChange={handleTableChange}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: { cursor: 'pointer' },
          })}
          locale={{ emptyText: 'Пользователи не найдены' }}
        />
      </Spin>

      <UserDetail
        userId={selectedUser?.id || null}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setSelectedUser(null)
        }}
      />

      <Modal
        title={editingUser ? 'Редактировать пользователя' : 'Новый пользователь'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="Сохранить"
        cancelText="Отмена"
        width={560}
      >
        <Form form={form} layout="vertical">
          {!editingUser && (
            <Form.Item
              name="telegram_id"
              label="Telegram ID"
              rules={[{ required: true, message: 'Введите Telegram ID' }]}
            >
              <InputNumber style={{ width: '100%' }} placeholder="123456789" />
            </Form.Item>
          )}
          <Form.Item
            name="first_name"
            label="Имя"
            rules={[{ required: true, message: 'Введите имя' }]}
          >
            <Input placeholder="Имя" />
          </Form.Item>
          <Form.Item name="last_name" label="Фамилия">
            <Input placeholder="Фамилия" />
          </Form.Item>
          <Form.Item name="username" label="Telegram (@login)">
            <Input placeholder="@login" prefix="@" />
          </Form.Item>
          <Form.Item name="archetype" label="Архетип">
            <Select
              allowClear
              placeholder="Не определён"
              options={[
                { value: 'head', label: 'Голова' },
                { value: 'shell', label: 'Панцирь' },
                { value: 'whirlwind', label: 'Вихрь' },
                { value: 'ghost', label: 'Призрак' },
              ]}
            />
          </Form.Item>
          <Form.Item name="role" label="Роль">
            <Select
              options={[
                { value: 'player', label: 'Игрок' },
                { value: 'specialist', label: 'Специалист' },
                { value: 'curator', label: 'Куратор' },
                { value: 'leader', label: 'Лидер' },
                { value: 'master', label: 'Мастер' },
              ]}
            />
          </Form.Item>
          <Space style={{ display: 'flex' }} size="large">
            <Form.Item name="xp" label="XP" style={{ marginBottom: 0 }}>
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item name="streak" label="Streak" style={{ marginBottom: 0 }}>
              <InputNumber min={0} />
            </Form.Item>
            <Form.Item name="is_active" label="Активен" valuePropName="checked" style={{ marginBottom: 0 }}>
              <Switch />
            </Form.Item>
          </Space>
          {editingUser ? (
            <Form.Item name="has_paid" label="Доступ оплачен" style={{ marginTop: 16 }}>
              <Select
                options={[
                  { value: true, label: 'Да — доступ открыт' },
                  { value: false, label: 'Нет — доступ закрыт' },
                ]}
              />
            </Form.Item>
          ) : (
            <Form.Item name="timezone" label="Часовой пояс" style={{ marginTop: 16 }}>
              <Input placeholder="Asia/Krasnoyarsk" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  )
}
