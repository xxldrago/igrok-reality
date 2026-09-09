import { useState, useEffect } from 'react'
import { Typography, Card, Button, Space, Select, Input, message, Spin, Descriptions } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { sendBroadcast, getArchetypeStats, ArchetypeStatsResponse } from '../services/api'

const { Title, Text, Paragraph } = Typography

export default function Broadcast() {
  const [text, setText] = useState('')
  const [archetype, setArchetype] = useState<string | null>(null)
  const [stats, setStats] = useState<ArchetypeStatsResponse | null>(null)
  const [sending, setSending] = useState(false)
  const [lastResult, setLastResult] = useState<string | null>(null)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const res = await getArchetypeStats()
      setStats(res.data)
    } catch (e) {
      console.error(e)
      message.error('Ошибка загрузки статистики')
    }
  }

  const handleSend = async () => {
    if (!text.trim()) {
      message.warning('Введите текст сообщения')
      return
    }
    setSending(true)
    try {
      const res = await sendBroadcast({ text: text.trim(), archetype })
      setLastResult(`Отправлено: ${res.data.sent}, всего: ${res.data.total}`)
      message.success(`Рассылка в очереди: ${res.data.sent} пользователей`)
      setText('')
    } catch (e) {
      console.error(e)
      message.error('Ошибка отправки')
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      <Title level={4}>Рассылка</Title>

      <Card size="small" title="Статистика" style={{ marginBottom: 16 }}>
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
          <Button size="small" icon={<SendOutlined />} onClick={loadStats}>Обновить</Button>
        </Space>
      </Card>

      <Card size="small" title="Новая рассылка">
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Select
            placeholder="Фильтр по архетипу (всем — пусто)"
            allowClear
            size="small"
            style={{ width: '100%' }}
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
            rows={5}
            maxLength={4000}
            placeholder="Текст сообщения"
            value={text}
            onChange={(e) => setText(e.target.value)}
            showCount
          />
          <Space>
            <Button
              type="primary"
              icon={<SendOutlined />}
              size="large"
              loading={sending}
              onClick={handleSend}
            >
              Отправить
            </Button>
            {lastResult && <Text type="success">{lastResult}</Text>}
          </Space>
        </Space>
      </Card>

      <Card size="small" title="Помощь">
        <Paragraph>
          <Text><strong>Фильтр:</strong> пусто = всем. Выберите архетип для таргетинга.</Text>
        </Paragraph>
        <Paragraph>
          <Text><strong>Очередь:</strong> сообщения идут в notifications, отправляет worker.</Text>
        </Paragraph>
      </Card>
    </div>
  )
}
