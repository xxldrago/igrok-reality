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
      <Title level={3}>Дашборд</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Активные игроки"
              value={data.active_players}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Оплатившие"
              value={data.paid_players}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Конверсия"
              value={data.conversion_rate}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Общий доход"
              value={formatKopecks(data.total_income)}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="Призовой фонд"
              value={formatKopecks(data.prize_fund_total)}
              prefix={<TrophyOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Удержание по дням">
            <Table
              dataSource={Object.entries(data.retention_by_day).map(([day, count]) => ({
                key: day,
                day: Number(day),
                count,
              }))}
              columns={[
                { title: 'День', dataIndex: 'day', key: 'day' },
                { title: 'Завершений', dataIndex: 'count', key: 'count' },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Последняя активность">
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
        </Col>
      </Row>
    </div>
  )
}
