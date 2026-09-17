import { useState, useEffect, useCallback } from 'react'
import { Table, Input, Select, Space, Tag, Spin, Typography } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import { getReports, ReportItem, ReportListResponse } from '../services/api'

const { Title } = Typography

const archetypeLabels: Record<string, string> = {
  head: 'Голова',
  shell: 'Панцирь',
  whirlwind: 'Вихрь',
  ghost: 'Призрак',
}

const sourceLabels: Record<string, string> = {
  scroll: 'Свиток',
  daily: 'Дневник',
}

const sourceColors: Record<string, string> = {
  scroll: 'blue',
  daily: 'purple',
}

export default function Reports() {
  const [data, setData] = useState<ReportListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [archetype, setArchetype] = useState<string | undefined>(undefined)
  const [source, setSource] = useState<string | undefined>(undefined)
  const [dayNumber, setDayNumber] = useState<number | undefined>(undefined)
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 20,
    showSizeChanger: true,
    pageSizeOptions: ['10', '20', '50'],
  })

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getReports({
        search: search || undefined,
        archetype,
        source,
        quest_day: dayNumber,
        page: pagination.current || 1,
        page_size: pagination.pageSize || 20,
      })
      setData(response.data)
    } catch (error) {
      console.error('Failed to fetch reports:', error)
    } finally {
      setLoading(false)
    }
  }, [search, archetype, source, dayNumber, pagination.current, pagination.pageSize])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const resetPage = () =>
    setPagination((prev) => ({ ...prev, current: 1 }))

  const columns: ColumnsType<ReportItem> = [
    {
      title: 'Игрок',
      key: 'user',
      render: (_, record) => (
        <span>
          {record.first_name}
          {record.username ? (
            <span style={{ color: '#999', marginLeft: 6 }}>@{record.username}</span>
          ) : null}
          {record.archetype ? (
            <div style={{ fontSize: 11, color: '#999' }}>
              {archetypeLabels[record.archetype] || record.archetype}
            </div>
          ) : null}
        </span>
      ),
    },
    {
      title: 'День',
      dataIndex: 'quest_day',
      key: 'quest_day',
      width: 70,
      render: (day: number | null) => day ?? '—',
    },
    {
      title: 'Источник',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (src: string, record) => (
        <span>
          <Tag color={sourceColors[src] || 'default'}>{sourceLabels[src] || src}</Tag>
          {record.command ? (
            <div style={{ fontSize: 11, color: '#999' }}>{record.command}</div>
          ) : null}
        </span>
      ),
    },
    {
      title: 'Отчёт',
      dataIndex: 'text',
      key: 'text',
      ellipsis: true,
      render: (text: string | null, record) => (
        <span>
          {text || <span style={{ color: '#bbb' }}>без текста</span>}
          {record.media_url ? (
            <div style={{ fontSize: 11 }}>
              📎{' '}
              <a href={record.media_url} target="_blank" rel="noreferrer">
                {record.media_type || 'файл'}
              </a>
            </div>
          ) : null}
        </span>
      ),
    },
    {
      title: 'XP',
      dataIndex: 'xp_awarded',
      key: 'xp_awarded',
      width: 70,
      render: (xp: number) => `+${xp}`,
    },
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => new Date(date).toLocaleString('ru-RU'),
    },
  ]

  return (
    <div>
      <Title level={4}>Отчёты пользователей</Title>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="Поиск по имени или username"
          prefix={<SearchOutlined />}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            resetPage()
          }}
          style={{ width: 280 }}
          allowClear
        />
        <Select
          placeholder="Архетип"
          value={archetype}
          onChange={(val) => {
            setArchetype(val)
            resetPage()
          }}
          allowClear
          style={{ width: 150 }}
          options={[
            { value: 'head', label: 'Голова' },
            { value: 'shell', label: 'Панцирь' },
            { value: 'whirlwind', label: 'Вихрь' },
            { value: 'ghost', label: 'Призрак' },
          ]}
        />
        <Select
          placeholder="Источник"
          value={source}
          onChange={(val) => {
            setSource(val)
            resetPage()
          }}
          allowClear
          style={{ width: 150 }}
          options={[
            { value: 'scroll', label: 'Свиток' },
            { value: 'daily', label: 'Дневник' },
          ]}
        />
        <Input
          placeholder="День"
          type="number"
          min={1}
          max={90}
          style={{ width: 100 }}
          value={dayNumber ?? ''}
          onChange={(e) => {
            const v = parseInt(e.target.value, 10)
            setDayNumber(Number.isNaN(v) ? undefined : v)
            resetPage()
          }}
        />
      </Space>

      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={data?.reports || []}
          rowKey="id"
          pagination={{
            ...pagination,
            total: data?.total || 0,
          }}
          onChange={(pag) =>
            setPagination((prev) => ({
              ...prev,
              current: pag.current,
              pageSize: pag.pageSize,
            }))
          }
          expandable={{
            expandedRowRender: (record) =>
              record.text ? (
                <div style={{ whiteSpace: 'pre-wrap' }}>{record.text}</div>
              ) : (
                <span style={{ color: '#999' }}>Только вложение</span>
              ),
          }}
          locale={{ emptyText: 'Отчёты не найдены' }}
        />
      </Spin>
    </div>
  )
}
