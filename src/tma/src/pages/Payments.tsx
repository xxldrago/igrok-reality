import { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Tag,
  Space,
  Empty,
  Spin,
  Drawer,
  Descriptions,
  Button,
} from 'antd'
import {
  DollarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import {
  getPayments,
  type PaymentItem,
  type GetPaymentsParams,
} from '../services/api'

const statusConfig: Record<string, { color: string; icon: React.ReactNode }> = {
  CONFIRMED: { color: 'green', icon: <CheckCircleOutlined /> },
  CANCELED: { color: 'red', icon: <CloseCircleOutlined /> },
  PENDING: { color: 'orange', icon: <ClockCircleOutlined /> },
}

const statusFilters = ['CONFIRMED', 'CANCELED', 'PENDING']

export default function Payments() {
  const [payments, setPayments] = useState<PaymentItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [drawerPayment, setDrawerPayment] = useState<PaymentItem | null>(null)
  const pageSize = 20

  const fetchPayments = useCallback(
    async (p: number, reset: boolean = false) => {
      setLoading(true)
      try {
        const params: GetPaymentsParams = { page: p, page_size: pageSize }
        if (statusFilter) params.status = statusFilter

        const res = await getPayments(params)
        setPayments((prev) =>
          reset ? res.data.payments : [...prev, ...res.data.payments],
        )
        setTotal(res.data.total)
      } catch {
        // Error handled by API interceptor
      } finally {
        setLoading(false)
      }
    },
    [statusFilter],
  )

  useEffect(() => {
    setPage(1)
    fetchPayments(1, true)
  }, [fetchPayments])

  const loadMore = () => {
    const nextPage = page + 1
    setPage(nextPage)
    fetchPayments(nextPage)
  }

  return (
    <div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Tag
          color={!statusFilter ? 'blue' : undefined}
          style={{ cursor: 'pointer' }}
          onClick={() => setStatusFilter(undefined)}
        >
          Все
        </Tag>
        {statusFilters.map((s) => (
          <Tag
            key={s}
            color={statusFilter === s ? statusConfig[s]?.color : undefined}
            style={{ cursor: 'pointer' }}
            onClick={() => setStatusFilter(statusFilter === s ? undefined : s)}
          >
            {statusConfig[s]?.icon} {s}
          </Tag>
        ))}
      </Space>

      {payments.length === 0 && !loading ? (
        <Empty description="Нет платежей" />
      ) : (
        <>
          {payments.map((p) => (
            <Card
              key={p.id}
              size="small"
              style={{ marginBottom: 8 }}
              onClick={() => setDrawerPayment(p)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 500 }}>
                    <DollarOutlined style={{ marginRight: 6 }} />
                    {p.user_name}
                  </div>
                  {p.user_username && (
                    <div style={{ fontSize: 12, color: '#999' }}>
                      @{p.user_username}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>
                    {p.amount} {p.currency}
                  </div>
                  <Tag color={statusConfig[p.status]?.color || 'default'}>
                    {p.status}
                  </Tag>
                </div>
              </div>
              <div style={{ marginTop: 4, fontSize: 11, color: '#999' }}>
                {new Date(p.created_at).toLocaleDateString('ru-RU')}
              </div>
            </Card>
          ))}

          {payments.length < total && (
            <Button block onClick={loadMore} loading={loading} style={{ marginTop: 8 }}>
              Загрузить ещё
            </Button>
          )}
        </>
      )}

      {loading && payments.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      )}

      <Drawer
        title="Детали платежа"
        open={!!drawerPayment}
        onClose={() => setDrawerPayment(null)}
        placement="bottom"
        height="60%"
      >
        {drawerPayment && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="ID">{drawerPayment.id}</Descriptions.Item>
            <Descriptions.Item label="Пользователь">
              {drawerPayment.user_name}
            </Descriptions.Item>
            <Descriptions.Item label="Username">
              {drawerPayment.user_username || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Сумма">
              {drawerPayment.amount} {drawerPayment.currency}
            </Descriptions.Item>
            <Descriptions.Item label="Статус">
              <Tag color={statusConfig[drawerPayment.status]?.color}>
                {drawerPayment.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Способ оплаты">
              {drawerPayment.payment_method || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Transaction ID">
              {drawerPayment.platega_transaction_id || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="Дата">
              {new Date(drawerPayment.created_at).toLocaleString('ru-RU')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  )
}
