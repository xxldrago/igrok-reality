import { useState } from 'react'
import { Typography, Card, Button, Space, Select, Input, message, Spin, Descriptions } from 'antd'
import { SendOutlined, ReloadOutlined } from '@ant-design/icons'
import { sendBroadcast, getArchetypeStats, ArchetypeStatsResponse } from '../services/api'

const { Title, Text, Paragraph } = Typography

export default function Broadcast() {
  const [text, setText] = useState('')
  const [archetype, setArchetype] = useState<string | null>(null)
  const [stats, setStats] = useState<ArchetypeStatsResponse | null>(null)
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

  const handleSend = async () => {
    if (!text.trim()) {
      message.warning('Введите текст сообщения')
      return
    }
    setSending(true)
    try {
      const res = await sendBroadcast({ text: text.trim(), archetype })
      setLastResult(`Отправлено: ${res.data.sent}, всего: ${res.data.total}`)
      message.success(`Рассылка поставлена в очередь: ${res.data.sent} пользователей`)
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

      <Card title="Помощь" style={{ marginTop: 16 }}>
        <Paragraph>
          <Text><strong>Фильтр по архетипу:</strong> если пусто — сообщение уйдёт всем активным игрокам.</Text>
        </Paragraph>
        <Paragraph>
          <Text><strong>Markdown/HTML:</strong> сообщение отправляется как обычный текст. Parse mode можно расширить в API.</Text>
        </Paragraph>
        <Paragraph>
          <Text><strong>Очередь:</strong> сообщения кладутся в таблицу notifications и отправляются worker'ом <code>send_pending_notifications</code> (каждую минуту).</Text>
        </Paragraph>
      </Card>
    </div>
  )
}