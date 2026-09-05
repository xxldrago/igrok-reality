import { useState, useEffect } from 'react'
import { Table, Select, message } from 'antd'
import { getAuditLog, type AuditEntry } from '../services/api'

const ACTION_OPTIONS = [
  { value: '', label: 'Все действия' },
  { value: 'scroll_created', label: 'Создан свиток' },
  { value: 'scroll_updated', label: 'Обновлён свиток' },
  { value: 'scroll_deleted', label: 'Удалён свиток' },
  { value: 'settings_updated', label: 'Настройки изменены' },
  { value: 'commission_payout', label: 'Выплата комиссии' },
  { value: 'user_viewed', label: 'Просмотр пользователя' },
]

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [actionFilter, setActionFilter] = useState<string>('')

  const fetchAuditLog = async () => {
    try {
      setLoading(true)
      const params: Record<string, string | number> = {
        page,
        page_size: pageSize,
      }
      if (actionFilter) {
        params.action = actionFilter
      }
      const response = await getAuditLog(params)
      setEntries(response.data.entries)
      setTotal(response.data.total)
    } catch {
      message.error('Ошибка загрузки журнала аудита')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAuditLog()
  }, [page, pageSize, actionFilter])

  const columns = [
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString('ru-RU'),
    },
    {
      title: 'Администратор',
      dataIndex: 'admin_name',
      key: 'admin_name',
      render: (text: string | null) => text || 'Система',
    },
    {
      title: 'Действие',
      dataIndex: 'action',
      key: 'action',
    },
    {
      title: 'Детали',
      dataIndex: 'details',
      key: 'details',
      render: (text: string | null) => text || '—',
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>Журнал аудита</h2>
        <Select
          style={{ width: 220 }}
          placeholder="Фильтр по действию"
          value={actionFilter || undefined}
          onChange={(value) => {
            setActionFilter(value || '')
            setPage(1)
          }}
          options={ACTION_OPTIONS}
          allowClear
        />
      </div>

      <Table
        columns={columns}
        dataSource={entries}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50'],
          showTotal: (total) => `Всего: ${total}`,
          onChange: (newPage, newPageSize) => {
            setPage(newPage)
            setPageSize(newPageSize)
          },
        }}
      />
    </div>
  )
}
