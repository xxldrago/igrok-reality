import { useState, useEffect } from 'react'
import {
  Tabs,
  Table,
  Button,
  Space,
  Typography,
  Modal,
  Form,
  InputNumber,
  Input,
  message,
  Spin,
} from 'antd'
import { DownloadOutlined, PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getCommissions,
  getPrizeFunds,
  createPrizeFund,
  distributePrizeFund,
  exportPaymentsCsv,
  CommissionBalanceItem,
  PrizeFundItem,
} from '../services/api'

const { Title } = Typography

export default function Finance() {
  const [commissions, setCommissions] = useState<CommissionBalanceItem[]>([])
  const [funds, setFunds] = useState<PrizeFundItem[]>([])
  const [loading, setLoading] = useState(true)
  const [fundModalOpen, setFundModalOpen] = useState(false)
  const [distributeModalOpen, setDistributeModalOpen] = useState(false)
  const [selectedFund, setSelectedFund] = useState<PrizeFundItem | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    Promise.all([
      getCommissions().then((res) => setCommissions(res.data.balances)),
      getPrizeFunds().then((res) => setFunds(res.data.funds)),
    ])
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleCreateFund = async (values: { name: string; percent_rule: number }) => {
    try {
      await createPrizeFund(values)
      const res = await getPrizeFunds()
      setFunds(res.data.funds)
      setFundModalOpen(false)
      form.resetFields()
      message.success('Фонд создан')
    } catch {
      message.error('Ошибка создания фонда')
    }
  }

  const handleDistribute = async (topN: number) => {
    if (!selectedFund) return
    try {
      await distributePrizeFund({ fund_id: selectedFund.id, top_n: topN })
      const res = await getPrizeFunds()
      setFunds(res.data.funds)
      setDistributeModalOpen(false)
      message.success('Фонд распределён')
    } catch {
      message.error('Ошибка распределения')
    }
  }

  const handleExport = async () => {
    try {
      const res = await exportPaymentsCsv()
      const blob = new Blob([res.data.csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'payments_export.csv'
      a.click()
      URL.revokeObjectURL(url)
      message.success(`Экспортировано ${res.data.count} записей`)
    } catch {
      message.error('Ошибка экспорта')
    }
  }

  const commissionColumns: ColumnsType<CommissionBalanceItem> = [
    { title: 'Username', dataIndex: 'username', key: 'username' },
    {
      title: 'Ожидает',
      dataIndex: 'pending',
      key: 'pending',
      render: (v: number) => `${(v / 100).toFixed(2)} ₽`,
    },
    {
      title: 'Выплачено',
      dataIndex: 'paid_out',
      key: 'paid_out',
      render: (v: number) => `${(v / 100).toFixed(2)} ₽`,
    },
  ]

  const fundColumns: ColumnsType<PrizeFundItem> = [
    { title: 'Название', dataIndex: 'name', key: 'name' },
    {
      title: 'Сумма',
      dataIndex: 'total_amount',
      key: 'total_amount',
      render: (v: number) => `${(v / 100).toFixed(2)} ₽`,
    },
    { title: '%', dataIndex: 'percent_rule', key: 'percent_rule' },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => (
        <span style={{ color: v === 'open' ? 'green' : 'blue' }}>
          {v === 'open' ? 'Открыт' : 'Распределён'}
        </span>
      ),
    },
    {
      title: '',
      key: 'actions',
      render: (_, record) =>
        record.status === 'open' ? (
          <Button
            size="small"
            onClick={() => {
              setSelectedFund(record)
              setDistributeModalOpen(true)
            }}
          >
            Распределить
          </Button>
        ) : null,
    },
  ]

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  }

  return (
    <div>
      <Title level={4}>Финансы</Title>

      <Tabs
        items={[
          {
            key: 'commissions',
            label: 'Комиссии',
            children: (
              <Table
                dataSource={commissions}
                columns={commissionColumns}
                rowKey="user_id"
                pagination={false}
                size="small"
              />
            ),
          },
          {
            key: 'funds',
            label: 'Фонд',
            children: (
              <>
                <Space style={{ marginBottom: 12 }}>
                  <Button size="small" icon={<PlusOutlined />} onClick={() => setFundModalOpen(true)}>
                    Создать
                  </Button>
                </Space>
                <Table
                  dataSource={funds}
                  columns={fundColumns}
                  rowKey="id"
                  pagination={false}
                  size="small"
                />
              </>
            ),
          },
          {
            key: 'export',
            label: 'Экспорт',
            children: (
              <Button icon={<DownloadOutlined />} onClick={handleExport}>
                Скачать CSV
              </Button>
            ),
          },
        ]}
      />

      <Modal
        title="Новый фонд"
        open={fundModalOpen}
        onCancel={() => setFundModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleCreateFund} layout="vertical">
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input placeholder="Фонд January 2026" />
          </Form.Item>
          <Form.Item name="percent_rule" label="%" rules={[{ required: true }]}>
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Распределить"
        open={distributeModalOpen}
        onCancel={() => setDistributeModalOpen(false)}
        onOk={() => handleDistribute(form.getFieldValue('top_n') || 10)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="top_n" label="Топ N" initialValue={10}>
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
