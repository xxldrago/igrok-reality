import { useState, useEffect } from 'react'
import { Table, Tag, Select, Space, Button, Typography, message } from 'antd'
import { CheckCircleOutlined, StopOutlined, WarningOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getModerationReports,
  resolveModerationReport,
  ModerationReportItem,
} from '../services/api'

const { Title } = Typography

const statusColors: Record<string, string> = {
  pending: 'orange',
  warned: 'gold',
  banned: 'red',
  excluded: 'purple',
}

const statusLabels: Record<string, string> = {
  pending: 'Ожидает',
  warned: 'Предупреждён',
  banned: 'Заблокирован',
  excluded: 'Исключён',
}

export default function Moderation() {
  const [reports, setReports] = useState<ModerationReportItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  const loadReports = (status?: string) => {
    setLoading(true)
    getModerationReports(status ? { status } : undefined)
      .then((res) => {
        setReports(res.data.reports)
        setTotal(res.data.total)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadReports(statusFilter)
  }, [statusFilter])

  const handleResolve = async (id: string, decision: string) => {
    try {
      await resolveModerationReport(id, decision)
      loadReports(statusFilter)
      message.success(`Решение: ${decision}`)
    } catch {
      message.error('Ошибка')
    }
  }

  const columns: ColumnsType<ModerationReportItem> = [
    { title: 'Username', dataIndex: 'username', key: 'username' },
    { title: 'Причина', dataIndex: 'reason', key: 'reason', ellipsis: true },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => (
        <Tag color={statusColors[v] || 'default'}>{statusLabels[v] || v}</Tag>
      ),
    },
    {
      title: '',
      key: 'actions',
      render: (_, record) =>
        record.status === 'pending' ? (
          <Space size="small">
            <Button
              size="small"
              icon={<WarningOutlined />}
              onClick={() => handleResolve(record.id, 'warn')}
            />
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleResolve(record.id, 'ban')}
            />
            <Button
              size="small"
              danger
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => handleResolve(record.id, 'exclude')}
            />
          </Space>
        ) : null,
    },
  ]

  return (
    <div>
      <Title level={4}>Модерация</Title>

      <Space style={{ marginBottom: 12 }}>
        <Select
          placeholder="Статус"
          allowClear
          style={{ width: 160 }}
          size="small"
          value={statusFilter}
          onChange={setStatusFilter}
          options={Object.entries(statusLabels).map(([value, label]) => ({
            value,
            label,
          }))}
        />
      </Space>

      <Table
        dataSource={reports}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={{ total, pageSize: 20 }}
      />
    </div>
  )
}
