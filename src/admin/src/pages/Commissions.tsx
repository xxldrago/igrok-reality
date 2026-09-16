import { useState, useEffect } from 'react'
import { Table, Button, Typography, message, Popconfirm } from 'antd'
import { DollarOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { getUsers, getUser, payoutCommission, UserListItem } from '../services/api'
import RoleGuard from '../components/RoleGuard'

const { Title } = Typography

export default function Commissions() {
  const [data, setData] = useState<UserListItem[]>([])
  const [loading, setLoading] = useState(true)

  const loadUsers = () => {
    setLoading(true)
    getUsers({ page_size: 100 })
      .then((res) => {
        setData(res.data.users)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const handlePayout = async (userId: string) => {
    const b = balances[userId]
    if (!b || b.pending === 0) {
      message.warning('Нет суммы для выплаты')
      return
    }
    try {
      await payoutCommission(userId, b.pending)
      message.success('Выплата выполнена')
      // Reload data
      getUsers().then((res) => setData(res.data.users))
    } catch {
      message.error('Ошибка выплаты')
    }
  }

  // Fetch per-user commission balance on row mount
  const [balances, setBalances] = useState<Record<string, { earned: number; pending: number; paid: number }>>({})

  useEffect(() => {
    if (data.length === 0) return
    const ids = data.map((u) => u.id)
    Promise.all(ids.map((id) => getUser(id).catch(() => null)))
      .then((results) => {
        const map: Record<string, { earned: number; pending: number; paid: number }> = {}
        results.forEach((res, i) => {
          if (res?.data.commission_balance) {
            const cb = res.data.commission_balance
            map[ids[i]] = { earned: cb.total_earned, pending: cb.total_pending, paid: cb.total_paid_out }
          }
        })
        setBalances(map)
      })
  }, [data])

  const columns: ColumnsType<UserListItem> = [
    { title: 'User ID', dataIndex: 'id', key: 'id', ellipsis: true },
    {
      title: 'Заработано',
      key: 'earned',
      render: (_, r) => {
        const b = balances[r.id]
        return b ? `${(b.earned / 100).toFixed(2)} ₽` : '—'
      },
    },
    {
      title: 'Ожидает',
      key: 'pending',
      render: (_, r) => {
        const b = balances[r.id]
        return b ? `${(b.pending / 100).toFixed(2)} ₽` : '—'
      },
    },
    {
      title: 'Выплачено',
      key: 'paid',
      render: (_, r) => {
        const b = balances[r.id]
        return b ? `${(b.paid / 100).toFixed(2)} ₽` : '—'
      },
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <RoleGuard roles={['master']}>
          <Popconfirm title="Выполнить выплату?" onConfirm={() => handlePayout(record.id)}>
            <Button size="small" icon={<DollarOutlined />}>
              Выплатить
            </Button>
          </Popconfirm>
        </RoleGuard>
      ),
    },
  ]

  return (
    <div>
      <Title level={4}>Комиссии</Title>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </div>
  )
}