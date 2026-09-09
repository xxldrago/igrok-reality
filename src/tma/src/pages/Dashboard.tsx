import { useState, useEffect } from 'react'
import { Card, Col, Row, Statistic, Table, Spin, Typography } from 'antd'
import {
  UserOutlined,
  DollarOutlined,
  TrophyOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { getDashboard, DashboardResponse } from '../services/api'

const { Title } = Typography

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboard()
      .then((res) => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  }

  if (!data) {
    return <div>Ошибка загрузки дашборда</div>
  }

  const formatKopecks = (kopecks: number) => `${(kopecks / 100).toFixed(2)} ₽`

  return (
    <div>
      <Title level={4}>Дашборд</Title>

      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="Игроки"
              value={data.active_players}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="Оплатившие"
              value={data.paid_players}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card size="small">
            <Statistic title="Конверсия" value={data.conversion_rate} suffix="%" precision={1} />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small">
            <Statistic
              title="Доход"
              value={formatKopecks(data.total_income)}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card size="small" title="Призовой фонд" style={{ marginBottom: 16 }}>
        <Statistic
          value={formatKopecks(data.prize_fund_total)}
          prefix={<TrophyOutlined />}
        />
      </Card>

      <Card size="small" title="Последняя активность">
        <Table
          dataSource={data.recent_activity.map((item, i) => ({ ...item, key: i }))}
          columns={[
            { title: 'Игрок', dataIndex: 'user_name', key: 'user_name' },
            { title: 'День', dataIndex: 'day_number', key: 'day_number' },
            { title: 'XP', dataIndex: 'xp_awarded', key: 'xp_awarded' },
          ]}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  )
}
