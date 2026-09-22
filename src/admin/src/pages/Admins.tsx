import { useState, useEffect } from 'react'
import { Table, Button, Space, Typography, Modal, Form, Input, Select, Switch, Popconfirm, Tag, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  getAdmins,
  createAdmin,
  updateAdmin,
  deleteAdmin,
  AdminAccount,
} from '../services/api'
import RoleGuard from '../components/RoleGuard'

const { Title } = Typography

const roleLabels: Record<string, string> = {
  master: 'Мастер',
  leader: 'Лидер',
  curator: 'Куратор',
}

const roleColors: Record<string, string> = {
  master: 'red',
  leader: 'blue',
  curator: 'green',
}

export default function Admins() {
  const [admins, setAdmins] = useState<AdminAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AdminAccount | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const fetchAdmins = async () => {
    try {
      setLoading(true)
      const res = await getAdmins()
      setAdmins(res.data)
    } catch {
      message.error('Ошибка загрузки администраторов')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAdmins()
  }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ role: 'master', is_active: true })
    setModalOpen(true)
  }

  const openEdit = (record: AdminAccount) => {
    setEditing(record)
    form.setFieldsValue({
      role: record.role,
      telegram: record.telegram,
      is_active: record.is_active,
      password: undefined,
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      if (editing) {
        const payload: { password?: string; role?: string; telegram?: string; is_active?: boolean } = {
          role: values.role,
          telegram: values.telegram || '',
          is_active: values.is_active ?? true,
        }
        if (values.password) payload.password = values.password
        await updateAdmin(editing.id, payload)
        message.success('Администратор обновлён')
      } else {
        await createAdmin({
          username: values.username,
          password: values.password,
          role: values.role || 'master',
          telegram: values.telegram || '',
        })
        message.success('Администратор создан')
      }
      setModalOpen(false)
      fetchAdmins()
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) return
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteAdmin(id)
      message.success('Администратор удалён')
      fetchAdmins()
    } catch (error) {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || 'Ошибка удаления')
    }
  }

  const columns: ColumnsType<AdminAccount> = [
    {
      title: 'Логин',
      dataIndex: 'username',
      key: 'username',
      render: (v: string) => <strong>{v}</strong>,
    },
    {
      title: 'Роль',
      dataIndex: 'role',
      key: 'role',
      render: (v: string) => <Tag color={roleColors[v] || 'default'}>{roleLabels[v] || v}</Tag>,
    },
    {
      title: 'Telegram',
      dataIndex: 'telegram',
      key: 'telegram',
      render: (v: string) => v || '—',
    },
    {
      title: 'Активен',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (v: boolean) =>
        v ? <Tag color="green">Да</Tag> : <Tag color="default">Нет</Tag>,
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString('ru-RU'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            Изменить
          </Button>
          <Popconfirm
            title="Удалить администратора?"
            description={`${record.username} потеряет доступ к панели.`}
            okText="Удалить"
            cancelText="Отмена"
            okType="danger"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              Удалить
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Администраторы</Title>
        <RoleGuard roles={['master']}>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Добавить
          </Button>
        </RoleGuard>
      </div>

      <Table
        columns={columns}
        dataSource={admins}
        rowKey="id"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={editing ? `Редактировать: ${editing.username}` : 'Новый администратор'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical">
          {!editing && (
            <Form.Item
              name="username"
              label="Логин"
              rules={[{ required: true, message: 'Введите логин' }]}
            >
              <Input placeholder="login" />
            </Form.Item>
          )}
          <Form.Item
            name="password"
            label={editing ? 'Новый пароль (пусто — не менять)' : 'Пароль'}
            rules={editing ? [] : [{ required: true, message: 'Введите пароль' }]}
          >
            <Input.Password placeholder="Минимум 6 символов" />
          </Form.Item>
          <Form.Item name="role" label="Роль">
            <Select
              options={[
                { value: 'master', label: 'Мастер' },
                { value: 'leader', label: 'Лидер' },
                { value: 'curator', label: 'Куратор' },
              ]}
            />
          </Form.Item>
          <Form.Item name="telegram" label="Telegram (@login)">
            <Input placeholder="@login" />
          </Form.Item>
          {editing && (
            <Form.Item name="is_active" label="Активен" valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  )
}
