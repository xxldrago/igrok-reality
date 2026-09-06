import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, List, Spin, Empty, Statistic, Row, Col } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { getUser, type UserDetailResponse } from '../services/api'

const archetypeColors: Record<string, string> = {
  Голова: 'blue',
  Панцирь: 'green',
  Вихрь: 'orange',
  Призрак: 'purple',
}

export default function UserDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [user, setUser] = useState<UserDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getUser(id)
      .then((res) => setUser(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin />
      </div>
    )
  }

  if (!user) {
    return <Empty description="Пользователь не найден" />
  }

  return (
    <div>
      <div
        style={{ marginBottom: 16, cursor: 'pointer', color: 'var(--tg-theme-link-color)' }}
        onClick={() => navigate('/app/users')}
      >
        <ArrowLeftOutlined /> Назад к списку
      </div>

      <Card size="small" style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 600, fontSize: 16 }}>
          {user.first_name} {user.last_name || ''}
        </div>
        {user.username && (
          <div style={{ color: '#999' }}>@{user.username}</div>
        )}
        <div style={{ marginTop: 8 }}>
          {user.archetype && (
            <Tag color={archetypeColors[user.archetype] || 'default'}>
              {user.archetype}
            </Tag>
          )}
          {user.is_active ? (
            <Tag color="green">Активен</Tag>
          ) : (
            <Tag>Неактивен</Tag>
          )}
        </div>
      </Card>

      <Row gutter={8} style={{ marginBottom: 12 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="XP" value={user.xp} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="Стрик" value={user.streak} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="Завершений" value={user.completions_count} />
          </Card>
        </Col>
      </Row>

      <Card size="small" title="Основное" style={{ marginBottom: 12 }}>
        <Descriptions column={1} size="small">
          <Descriptions.Item label="Telegram ID">
            {user.telegram_id}
          </Descriptions.Item>
          <Descriptions.Item label="Часовой пояс">
            {user.timezone}
          </Descriptions.Item>
          <Descriptions.Item label="Регистрация">
            {new Date(user.created_at).toLocaleDateString('ru-RU')}
          </Descriptions.Item>
          {user.paid_at && (
            <Descriptions.Item label="Оплата">
              {new Date(user.paid_at).toLocaleDateString('ru-RU')}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card size="small" title="Рефералы" style={{ marginBottom: 12 }}>
        <Statistic title="Приглашено" value={user.referrals_count} />
      </Card>

      {user.commission_balance && (
        <Card size="small" title="Комиссия" style={{ marginBottom: 12 }}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="Заработано">
              {user.commission_balance.total_earned} ₽
            </Descriptions.Item>
            <Descriptions.Item label="Ожидает">
              {user.commission_balance.total_pending} ₽
            </Descriptions.Item>
            <Descriptions.Item label="Выплачено">
              {user.commission_balance.total_paid_out} ₽
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Card size="small" title="Платежи">
        {user.payments.length === 0 ? (
          <Empty description="Нет платежей" />
        ) : (
          <List
            dataSource={user.payments}
            renderItem={(p) => (
              <List.Item>
                <List.Item.Meta
                  title={`${p.amount} ₽`}
                  description={
                    <>
                      <Tag
                        color={
                          p.status === 'CONFIRMED'
                            ? 'green'
                            : p.status === 'CANCELED'
                            ? 'red'
                            : 'orange'
                        }
                      >
                        {p.status}
                      </Tag>
                      <span style={{ fontSize: 12, color: '#999' }}>
                        {new Date(p.created_at).toLocaleDateString('ru-RU')}
                      </span>
                    </>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}
