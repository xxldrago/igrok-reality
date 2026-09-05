import { useState, useEffect, useCallback } from 'react'
import { Table, Select, Space, Tag, Spin, Typography } from 'antd'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import { getPayments, PaymentItem, PaymentListResponse } from '../services/api'

const { Title } = Typography

const statusColors: Record<string, string> = {
  succeeded: 'green',
  pending: 'gold',
  canceled: 'red',
  chargebacked: 'volcano',
  refunded: 'blue',
}

const statusLabels: Record<string, string> = {
  succeeded: 'Успешно',
  pending: 'Ожидание',
  canceled: 'Отменён',
  chargebacked: 'Чарджбэк',
  refunded: 'Возврат',
}

function formatAmount(kopecks: number): string {
  const rubles = kopecks / 100
  return rubles.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' })
}

export default function Payments() {
  const [data, setData] = useState<PaymentListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 20,
    showSizeChanger: true,
    pageSizeOptions: ['10', '20', '50'],
  })

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getPayments({
        status: statusFilter,
        page: pagination.current || 1,
        page_size: pagination.pageSize || 20,
      })
      setData(response.data)
    } catch (error) {
      console.error('Failed to fetch payments:', error)
    } finally {
      setLoading(false)
    }
  }, [statusFilter, pagination.current, pagination.pageSize])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleTableChange = (pag: TablePaginationConfig) => {
    setPagination((prev) => ({
      ...prev,
      current: pag.current,
      pageSize: pag.pageSize,
    }))
  }

  const columns: ColumnsType<PaymentItem> = [
    {
      title: 'Пользователь',
      key: 'user',
      render: (_, record) => (
        <span>
          {record.user_name}
          {record.user_username && (
            <span style={{ color: '#999', marginLeft: 6 }}>
              @{record.user_username}
            </span>
          )}
        </span>
      ),
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      key: 'amount',
      width: 150,
      render: (amount: number) => formatAmount(amount),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={statusColors[status] || 'default'}>
          {statusLabels[status] || status}
        </Tag>
      ),
    },
    {
      title: 'Метод оплаты',
      dataIndex: 'payment_method',
      key: 'payment_method',
      width: 130,
      render: (method: string | null) => method || '—',
    },
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      render: (date: string) => new Date(date).toLocaleDateString('ru-RU'),
    },
  ]

  return (
    <div>
      <Title level={4}>Платежи</Title>

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="Статус"
          value={statusFilter}
          onChange={(val) => {
            setStatusFilter(val)
            setPagination((prev) => ({ ...prev, current: 1 }))
          }}
          allowClear
          style={{ width: 170 }}
          options={[
            { value: 'succeeded', label: 'Успешно' },
            { value: 'pending', label: 'Ожидание' },
            { value: 'canceled', label: 'Отменён' },
            { value: 'chargebacked', label: 'Чарджбэк' },
            { value: 'refunded', label: 'Возврат' },
          ]}
        />
      </Space>

      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={data?.payments || []}
          rowKey="id"
          pagination={{
            ...pagination,
            total: data?.total || 0,
          }}
          onChange={handleTableChange}
          locale={{ emptyText: 'Платежи не найдены' }}
        />
      </Spin>
    </div>
  )
}
