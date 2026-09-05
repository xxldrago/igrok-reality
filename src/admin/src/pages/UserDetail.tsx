import { useState, useEffect } from 'react'
import { Drawer, Descriptions, Table, Spin, Typography, Space, Tag } from 'antd'
import { getUser, UserDetailResponse } from '../services/api'

const { Title } = Typography

const archetypeLabels: Record<string, string> = {
  head: 'Голова',
  shell: 'Панцирь',
  whirlwind: 'Вихрь',
  ghost: 'Призрак',
}

interface UserDetailProps {
  userId: string | null
  open: boolean
  onClose: () => void
}

export default function UserDetail({ userId, open, onClose }: UserDetailProps) {
  const [loading, setLoading] = useState(false)
  const [user, setUser] = useState<UserDetailResponse | null>(null)

  useEffect(() => {
    if (open && userId) {
      setLoading(true)
      getUser(userId)
        .then((res) => setUser(res.data))
        .catch((err) => {
          console.error('Failed to fetch user detail:', err)
        })
        .finally(() => setLoading(false))
    } else {
      setUser(null)
    }
  }, [open, userId])

  const paymentColumns = [
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString('ru-RU'),
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => `${(amount / 100).toFixed(2)} ₽`,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          succeeded: 'green',
          pending: 'orange',
          canceled: 'red',
          refunded: 'blue',
        }
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>
      },
    },
  ]

  return (
    <Drawer
      title={user ? `${user.first_name} ${user.last_name || ''}` : 'Пользователь'}
      width={600}
      open={open}
      onClose={onClose}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" />
        </div>
      ) : user ? (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Profile */}
          <div>
            <Title level={5}>Профиль</Title>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Полное имя">
                {user.first_name} {user.last_name || ''}
              </Descriptions.Item>
              <Descriptions.Item label="Username">
                {user.username ? `@${user.username}` : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Telegram ID">
                {user.telegram_id}
              </Descriptions.Item>
              <Descriptions.Item label="Архетип">
                {user.archetype
                  ? archetypeLabels[user.archetype] || user.archetype
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Часовой пояс">
                {user.timezone}
              </Descriptions.Item>
            </Descriptions>
          </div>

          {/* Progress */}
          <div>
            <Title level={5}>Прогресс</Title>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="XP">{user.xp}</Descriptions.Item>
              <Descriptions.Item label="Streak">{user.streak} дн.</Descriptions.Item>
              <Descriptions.Item label="Дата начала">
                {user.started_at
                  ? new Date(user.started_at).toLocaleDateString('ru-RU')
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Статус оплаты">
                {user.paid_at ? (
                  <Tag color="green">Оплачено</Tag>
                ) : (
                  <Tag color="red">Не оплачено</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Выполнено">
                {user.completions_count} свитков
              </Descriptions.Item>
              <Descriptions.Item label="Рефералы">
                {user.referrals_count}
              </Descriptions.Item>
            </Descriptions>
          </div>

          {/* Commission */}
          {user.commission_balance && (
            <div>
              <Title level={5}>Комиссия</Title>
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Заработано">
                  {(user.commission_balance.total_earned / 100).toFixed(2)} ₽
                </Descriptions.Item>
                <Descriptions.Item label="Ожидает">
                  {(user.commission_balance.total_pending / 100).toFixed(2)} ₽
                </Descriptions.Item>
                <Descriptions.Item label="Выплачено">
                  {(user.commission_balance.total_paid_out / 100).toFixed(2)} ₽
                </Descriptions.Item>
              </Descriptions>
            </div>
          )}

          {/* Payments */}
          <div>
            <Title level={5}>Платежи</Title>
            <Table
              columns={paymentColumns}
              dataSource={user.payments}
              rowKey="id"
              pagination={false}
              size="small"
              locale={{ emptyText: 'Нет платежей' }}
            />
          </div>
        </Space>
      ) : null}
    </Drawer>
  )
}
