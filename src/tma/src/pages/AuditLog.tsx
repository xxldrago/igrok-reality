import { useState, useEffect, useCallback } from 'react'
import { Card, Tag, Select, Empty, Spin, Button } from 'antd'
import { AuditOutlined } from '@ant-design/icons'
import {
  getAuditLog,
  type AuditEntry,
  type GetAuditParams,
} from '../services/api'
import { useTmaAuth } from '../contexts/TmaAuthContext'

const actionColors: Record<string, string> = {
  create: 'green',
  update: 'blue',
  delete: 'red',
  login: 'cyan',
}

export default function AuditLog() {
  const { user } = useTmaAuth()
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [actionFilter, setActionFilter] = useState<string | undefined>()
  const pageSize = 20

  const fetchEntries = useCallback(
    async (p: number, reset: boolean = false) => {
      setLoading(true)
      try {
        const params: GetAuditParams = { page: p, page_size: pageSize }
        if (actionFilter) params.action = actionFilter

        const res = await getAuditLog(params)
        setEntries((prev) =>
          reset ? res.data.entries : [...prev, ...res.data.entries],
        )
        setTotal(res.data.total)
      } catch {
        // Error handled by API interceptor
      } finally {
        setLoading(false)
      }
    },
    [actionFilter],
  )

  useEffect(() => {
    setPage(1)
    fetchEntries(1, true)
  }, [fetchEntries])

  const loadMore = () => {
    const nextPage = page + 1
    setPage(nextPage)
    fetchEntries(nextPage)
  }

  if (user?.role !== 'master' && user?.role !== 'leader') {
    return <Empty description="Нет доступа" />
  }

  // Extract unique actions from loaded entries for filter
  const uniqueActions = [...new Set(entries.map((e) => e.action))]

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Select
          placeholder="Фильтр по действию"
          allowClear
          style={{ width: '100%' }}
          value={actionFilter}
          onChange={(val) => setActionFilter(val)}
          options={uniqueActions.map((a) => ({ label: a, value: a }))}
        />
      </div>

      {entries.length === 0 && !loading ? (
        <Empty description="Нет записей" />
      ) : (
        <>
          {entries.map((entry) => (
            <Card key={entry.id} size="small" style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 500 }}>
                    <AuditOutlined style={{ marginRight: 6 }} />
                    {entry.action}
                  </div>
                  <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                    {entry.admin_name || 'System'}
                  </div>
                </div>
                <Tag color={actionColors[entry.action.split('_')[0]] || 'default'}>
                  {entry.action}
                </Tag>
              </div>
              {entry.details && (
                <div
                  style={{
                    marginTop: 8,
                    fontSize: 12,
                    color: '#333',
                    background: '#f5f5f5',
                    padding: 8,
                    borderRadius: 6,
                    fontFamily: 'monospace',
                    wordBreak: 'break-all',
                  }}
                >
                  {entry.details}
                </div>
              )}
              <div style={{ marginTop: 6, fontSize: 11, color: '#999' }}>
                {new Date(entry.created_at).toLocaleString('ru-RU')}
              </div>
            </Card>
          ))}

          {entries.length < total && (
            <Button block onClick={loadMore} loading={loading} style={{ marginTop: 8 }}>
              Загрузить ещё
            </Button>
          )}
        </>
      )}

      {loading && entries.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      )}
    </div>
  )
}
