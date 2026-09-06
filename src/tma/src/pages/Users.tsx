import { useState, useEffect, useCallback } from 'react'
import { Card, Input, Tag, Button, Space, Empty, Spin } from 'antd'
import { SearchOutlined, UserOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import {
  getUsers,
  type UserListItem,
  type GetUsersParams,
} from '../services/api'

const archetypeColors: Record<string, string> = {
  Голова: 'blue',
  Панцирь: 'green',
  Вихрь: 'orange',
  Призрак: 'purple',
}

export default function Users() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<UserListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [archetypeFilter, setArchetypeFilter] = useState<string | undefined>()
  const pageSize = 20

  const fetchUsers = useCallback(
    async (p: number, reset: boolean = false) => {
      setLoading(true)
      try {
        const params: GetUsersParams = {
          page: p,
          page_size: pageSize,
        }
        if (search) params.search = search
        if (archetypeFilter) params.archetype = archetypeFilter

        const res = await getUsers(params)
        const data = res.data
        setUsers((prev) => (reset ? data.users : [...prev, ...data.users]))
        setTotal(data.total)
      } catch {
        // Error handled by API interceptor
      } finally {
        setLoading(false)
      }
    },
    [search, archetypeFilter],
  )

  useEffect(() => {
    setPage(1)
    fetchUsers(1, true)
  }, [fetchUsers])

  const loadMore = () => {
    const nextPage = page + 1
    setPage(nextPage)
    fetchUsers(nextPage)
  }

  const archetypes = ['Голова', 'Панцирь', 'Вихрь', 'Призрак']

  return (
    <div>
      <Input
        placeholder="Поиск по имени или username"
        prefix={<SearchOutlined />}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        allowClear
        style={{ marginBottom: 12 }}
      />

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

      {users.length === 0 && !loading ? (
        <Empty description="Нет пользователей" />
      ) : (
        <>
          {users.map((u) => (
            <Card
              key={u.id}
              size="small"
              style={{ marginBottom: 8 }}
              onClick={() => navigate(`/app/users/${u.id}`)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 500 }}>
                    <UserOutlined style={{ marginRight: 6 }} />
                    {u.first_name} {u.last_name || ''}
                  </div>
                  {u.username && (
                    <div style={{ fontSize: 12, color: '#999' }}>
                      @{u.username}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: 'right' }}>
                  {u.archetype && (
                    <Tag color={archetypeColors[u.archetype] || 'default'}>
                      {u.archetype}
                    </Tag>
                  )}
                  <div style={{ fontSize: 12, color: '#666' }}>
                    XP: {u.xp} | 🔥 {u.streak}
                  </div>
                </div>
              </div>
              <div style={{ marginTop: 4, fontSize: 11, color: '#999' }}>
                {u.is_active ? (
                  <Tag color="green">Активен</Tag>
                ) : (
                  <Tag color="default">Неактивен</Tag>
                )}
                {u.paid_at && <Tag color="blue">Оплачен</Tag>}
              </div>
            </Card>
          ))}

          {users.length < total && (
            <Button
              block
              onClick={loadMore}
              loading={loading}
              style={{ marginTop: 8 }}
            >
              Загрузить ещё
            </Button>
          )}
        </>
      )}

      {loading && users.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      )}
    </div>
  )
}
