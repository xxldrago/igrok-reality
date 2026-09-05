import { useState, useEffect, useCallback } from 'react'
import { Table, Input, Select, Space, Tag, Spin, Typography } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import { getUsers, UserListItem, UserListResponse } from '../services/api'
import UserDetail from './UserDetail'

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
  ]

  return (
    <div>
      <Title level={4}>Пользователи</Title>

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
    </div>
  )
}
