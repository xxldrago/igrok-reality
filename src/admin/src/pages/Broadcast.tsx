import { useState, useEffect } from 'react'
import { Typography, Card, Button, Space, Select, Input, message, Spin, Descriptions, DatePicker, Table, Popconfirm } from 'antd'
import { SendOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import {
  sendBroadcast,
  getArchetypeStats,
  getScheduledBroadcasts,
  cancelScheduledBroadcast,
  ArchetypeStatsResponse,
  ScheduledBroadcastItem,
} from '../services/api'
import MediaUpload from '../components/MediaUpload'
import RoleGuard from '../components/RoleGuard'

const { Title, Text, Paragraph } = Typography

const audienceLabels: Record<string, string> = {
  all: 'Всем',
  head: '🧠 Голова',
  shell: '🛡️ Панцирь',
  whirlwind: '🌪️ Вихрь',
  ghost: '👻 Призрак',
}

export default function Broadcast() {
  const [text, setText] = useState('')
  const [archetype, setArchetype] = useState<string | null>(null)
  const [mediaUrl, setMediaUrl] = useState<string | null>(null)
  const [mediaType, setMediaType] = useState<string | null>(null)
  const [scheduledAt, setScheduledAt] = useState<Dayjs | null>(null)
  const [stats, setStats] = useState<ArchetypeStatsResponse | null>(null)
  const [scheduled, setScheduled] = useState<ScheduledBroadcastItem[]>([])
  const [scheduledLoading, setScheduledLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [lastResult, setLastResult] = useState<string | null>(null)

  const loadStats = async () => {
    try {
      const res = await getArchetypeStats()
      setStats(res.data)
    } catch (e) {
      console.error(e)
      message.error('Ошибка загрузки статистики')
    }
  }

  const loadScheduled = async () => {
    try {
      setScheduledLoading(true)
      const res = await getScheduledBroadcasts()
      setScheduled(res.data.items)
    } catch (e) {
      console.error(e)
    } finally {
      setScheduledLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
    loadScheduled()
  }, [])

  const handleSend = async () => {
    if (!text.trim()) {
      message.warning('Введите текст сообщения')
      return
    }
    setSending(true)
    try {
      const res = await sendBroadcast({
        text: text.trim(),
        archetype,
        media_url: mediaUrl,
        media_type: mediaType,
        scheduled_at: scheduledAt ? scheduledAt.toISOString() : null,
      })
      if (res.data.scheduled) {
        setLastResult(`Запланировано на ${scheduledAt?.format('DD.MM.YYYY HH:mm')}: ${res.data.total} пользователей`)
        message.success('Рассылка запланирована')
      } else {
        setLastResult(`Отправлено: ${res.data.sent}, всего: ${res.data.total}`)
        message.success(`Рассылка поставлена в очередь: ${res.data.sent} пользователей`)
      }
      setText('')
      setMediaUrl(null)
      setMediaType(null)
      setScheduledAt(null)
      loadScheduled()
    } catch (e) {
      console.error(e)
      message.error('Ошибка отправки')
    } finally {
      setSending(false)
    }
  }

  const handleCancel = async (item: ScheduledBroadcastItem) => {
    try {
      const res = await cancelScheduledBroadcast(item.scheduled_at, item.audience)
      message.success(`Отменено сообщений: ${res.data.cancelled}`)
      loadScheduled()
    } catch (e) {
      console.error(e)
      message.error('Ошибка отмены')
    }
  }

  return (
    <div>
      <Title level={3}>Рассылка</Title>

      <Card title="Статистика игроков" style={{ marginBottom: 16 }}>
        <Spin spinning={!stats}>
          <Descriptions column={5} size="small">
            <Descriptions.Item label="Всего">{stats?.total || 0}</Descriptions.Item>
            <Descriptions.Item label="Голова">{stats?.by_archetype?.head || 0}</Descriptions.Item>
            <Descriptions.Item label="Панцирь">{stats?.by_archetype?.shell || 0}</Descriptions.Item>
            <Descriptions.Item label="Вихрь">{stats?.by_archetype?.whirlwind || 0}</Descriptions.Item>
            <Descriptions.Item label="Призрак">{stats?.by_archetype?.ghost || 0}</Descriptions.Item>
          </Descriptions>
        </Spin>
        <Space>
          <Button size="small" icon={<ReloadOutlined />} onClick={loadStats}>Обновить</Button>
        </Space>
      </Card>

      <Card title="Новая рассылка">
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Select
            placeholder="Фильтр по архетипу (всем — пусто)"
            allowClear
            style={{ width: 280 }}
            value={archetype}
            onChange={setArchetype}
            options={[
              { value: 'head', label: '🧠 Голова' },
              { value: 'shell', label: '🛡️ Панцирь' },
              { value: 'whirlwind', label: '🌪️ Вихрь' },
              { value: 'ghost', label: '👻 Призрак' },
            ]}
          />
          <Input.TextArea
            rows={6}
            maxLength={4000}
            placeholder="Текст сообщения (поддерживается Markdown/HTML)"
            value={text}
            onChange={(e) => setText(e.target.value)}
            showCount
          />
          <div>
            <Text strong>Вложение (фото / видео / файл)</Text>
            <div style={{ marginTop: 8 }}>
              <MediaUpload
                value={mediaUrl}
                mediaType={mediaType}
                onChange={(url, type) => {
                  setMediaUrl(url)
                  setMediaType(type)
                }}
              />
            </div>
          </div>
          <div>
            <Text strong>Отложенная отправка</Text>
            <div style={{ marginTop: 8 }}>
              <DatePicker
                showTime={{ format: 'HH:mm' }}
                format="DD.MM.YYYY HH:mm"
                placeholder="Сразу (или выберите день и время)"
                value={scheduledAt}
                onChange={setScheduledAt}
                disabledDate={(d) => d.isBefore(dayjs().startOf('day'))}
                style={{ width: 280 }}
              />
            </div>
            <Text type="secondary">Пусто — сообщение уйдёт сразу. Время — ваше местное.</Text>
          </div>
          <Space>
            <RoleGuard roles={['master']}>
              <Button
                type="primary"
                icon={<SendOutlined />}
                size="large"
                loading={sending}
                onClick={handleSend}
              >
                {scheduledAt ? 'Запланировать' : 'Отправить'}
              </Button>
            </RoleGuard>
            {lastResult && <Text type="success">{lastResult}</Text>}
          </Space>
        </Space>
      </Card>

      <Card title="Запланированные рассылки" style={{ marginTop: 16 }}>
        <Table
          dataSource={scheduled}
          rowKey={(r) => `${r.scheduled_at}|${r.audience}|${r.text_preview}`}
          loading={scheduledLoading}
          pagination={false}
          locale={{ emptyText: 'Нет запланированных рассылок' }}
          columns={[
            {
              title: 'Отправка',
              dataIndex: 'scheduled_at',
              key: 'scheduled_at',
              render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm'),
            },
            {
              title: 'Кому',
              dataIndex: 'audience',
              key: 'audience',
              render: (v: string) => audienceLabels[v] || v,
            },
            {
              title: 'Текст',
              dataIndex: 'text_preview',
              key: 'text_preview',
              ellipsis: true,
            },
            {
              title: 'Медиа',
              dataIndex: 'media_type',
              key: 'media_type',
              render: (v: string | null) => v || '—',
            },
            {
              title: 'Получателей',
              dataIndex: 'total',
              key: 'total',
            },
            {
              title: 'Действия',
              key: 'actions',
              render: (_: unknown, record: ScheduledBroadcastItem) => (
                <RoleGuard roles={['master']}>
                  <Popconfirm
                    title="Отменить запланированную рассылку?"
                    onConfirm={() => handleCancel(record)}
                    okText="Да"
                    cancelText="Нет"
                  >
                    <Button type="link" danger>Отменить</Button>
                  </Popconfirm>
                </RoleGuard>
              ),
            },
          ]}
        />
      </Card>

      <Card title="Помощь" style={{ marginTop: 16 }}>
        <Paragraph>
          <Text><strong>Фильтр по архетипу:</strong> если пусто — сообщение уйдёт всем активным игрокам.</Text>
        </Paragraph>
        <Paragraph>
          <Text><strong>Очередь:</strong> сообщения кладутся в таблицу notifications и отправляются worker'ом <code>send_pending_notifications</code> каждую минуту (включая созревшие отложенные).</Text>
        </Paragraph>
        <Paragraph>
          <Text><strong>Вложения:</strong> фото до 10 МБ, видео и файлы до 50 МБ. Длинный текст (свыше 1024 символов) придёт вторым сообщением после фото/видео.</Text>
        </Paragraph>
      </Card>
    </div>
  )
}
