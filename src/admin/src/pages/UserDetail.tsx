import { useState, useEffect } from 'react'
import { Drawer, Descriptions, Table, Spin, Typography, Space, Tag, Tooltip, Row, Col, Card } from 'antd'
import {
  getUser,
  getUserProgress,
  UserDetailResponse,
  UserProgressResponse,
  ProgressDayItem,
} from '../services/api'

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

const SLOT_BY_CODE: Record<string, string> = {
  vetr: 'morning',
  vetr_day: 'day',
  vetr_evening: 'evening',
}

const DAY_TYPE_LABELS: Record<string, string> = {
  standard: 'Обычный',
  meditation: '🧘 Медитация',
  breathing: '🌬️ Дыхание',
  awareness: '🔮 Осознание',
}

function currentQuestDay(startedAt: string | null): number {
  if (!startedAt) return 1
  const diff = Math.floor((Date.now() - new Date(startedAt).getTime()) / 86400000) + 1
  return Math.min(Math.max(diff, 1), 90)
}

function DayDetail({ day }: { day: ProgressDayItem | undefined }) {
  if (!day) return null
  const used = new Set<number>()
  const rows = day.expected.map((exp) => {
    const wantSlot = SLOT_BY_CODE[exp.code] ?? ''
    let idx = day.done.findIndex(
      (d, i) => !used.has(i) && d.command === exp.command && (d.slot || '') === wantSlot,
    )
    if (idx === -1 && wantSlot !== '') {
      idx = day.done.findIndex((d, i) => !used.has(i) && d.command === exp.command && !d.slot)
    }
    if (idx === -1 && wantSlot === '') {
      idx = day.done.findIndex((d, i) => !used.has(i) && d.command === exp.command)
    }
    const done = idx === -1 ? undefined : day.done[idx]
    if (idx !== -1) used.add(idx)
    return { exp, done }
  })

  return (
    <Card
      size="small"
      title={`День ${day.quest_day} — ${DAY_TYPE_LABELS[day.day_type] || day.day_type} (${day.earned_xp}/${day.max_xp} XP)`}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        {rows.map(({ exp, done }) => (
          <div key={exp.code} style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 6 }}>
            <div>
              {done ? '✅' : '⬜'} <strong>{exp.label}</strong>{' '}
              <Tag>{exp.command}</Tag>
              <span style={{ color: '#999', fontSize: 12 }}>
                {exp.time === 'any' ? 'когда удобно' : exp.time} · +{exp.xp} XP
              </span>
              {done && (
                <span style={{ color: '#999', fontSize: 12 }}>
                  {' '}
                  — {new Date(done.completed_at).toLocaleString('ru-RU')}
                </span>
              )}
            </div>
            {done?.report_text && (
              <div style={{ marginTop: 4, fontSize: 12, background: '#fafafa', padding: 6, borderRadius: 4 }}>
                📝 {done.report_text}
              </div>
            )}
            {done?.report_media_url && (
              <div style={{ fontSize: 12 }}>
                📎 <a href={done.report_media_url} target="_blank" rel="noreferrer">
                  {done.report_media_type || 'файл'}
                </a>
              </div>
            )}
          </div>
        ))}
        {rows.length === 0 && <span>Нет ожидаемых заданий</span>}
      </Space>
    </Card>
  )
}

export default function UserDetail({ userId, open, onClose }: UserDetailProps) {
  const [loading, setLoading] = useState(false)
  const [user, setUser] = useState<UserDetailResponse | null>(null)
  const [progress, setProgress] = useState<UserProgressResponse | null>(null)
  const [progressLoading, setProgressLoading] = useState(false)
  const [selectedDay, setSelectedDay] = useState<number | null>(null)

  useEffect(() => {
    if (open && userId) {
      setLoading(true)
      getUser(userId)
        .then((res) => {
          setUser(res.data)
          setSelectedDay(currentQuestDay(res.data.started_at))
        })
        .catch((err) => {
          console.error('Failed to fetch user detail:', err)
        })
        .finally(() => setLoading(false))
      setProgressLoading(true)
      getUserProgress(userId)
        .then((res) => setProgress(res.data))
        .catch((err) => {
          console.error('Failed to fetch user progress:', err)
        })
        .finally(() => setProgressLoading(false))
    } else {
      setUser(null)
      setProgress(null)
      setSelectedDay(null)
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

          {/* Completed tasks */}
          <div>
            <Title level={5}>Выполненные задания</Title>
            {progressLoading ? (
              <Spin size="small" />
            ) : progress ? (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                <Descriptions column={3} bordered size="small">
                  <Descriptions.Item label="Активных дней">
                    {progress.quest_days_active}/90
                  </Descriptions.Item>
                  <Descriptions.Item label="Команд">
                    {progress.total_commands}
                  </Descriptions.Item>
                  <Descriptions.Item label="XP из заданий">
                    {progress.total_xp_earned}
                  </Descriptions.Item>
                </Descriptions>
                <Row gutter={[4, 4]}>
                  {progress.days.map((d) => {
                    const frac = d.max_xp > 0 ? d.earned_xp / d.max_xp : d.done.length > 0 ? 1 : 0
                    const bg = frac >= 1 ? '#52c41a' : frac > 0 ? '#faad14' : '#f0f0f0'
                    const fg = frac > 0 ? '#fff' : '#999'
                    return (
                      <Col key={d.quest_day} span={2}>
                        <Tooltip
                          title={`День ${d.quest_day} (${DAY_TYPE_LABELS[d.day_type] || d.day_type}): ${d.earned_xp}/${d.max_xp} XP`}
                        >
                          <div
                            onClick={() => setSelectedDay(d.quest_day)}
                            style={{
                              background: bg,
                              color: fg,
                              borderRadius: 4,
                              textAlign: 'center',
                              padding: '4px 0',
                              fontSize: 11,
                              cursor: 'pointer',
                              border: selectedDay === d.quest_day ? '2px solid #1890ff' : '2px solid transparent',
                            }}
                          >
                            {d.quest_day}
                          </div>
                        </Tooltip>
                      </Col>
                    )
                  })}
                </Row>
                {selectedDay != null && <DayDetail day={progress.days[selectedDay - 1]} />}
              </Space>
            ) : (
              <span>Нет данных</span>
            )}
          </div>

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
