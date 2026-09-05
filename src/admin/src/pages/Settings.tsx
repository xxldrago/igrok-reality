import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message } from 'antd'
import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { getSettings, updateSettings, type SettingItem } from '../services/api'
import RoleGuard from '../components/RoleGuard'

export default function Settings() {
  const [settings, setSettings] = useState<SettingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [form] = Form.useForm()
  const [saveLoading, setSaveLoading] = useState(false)

  const fetchSettings = async () => {
    try {
      setLoading(true)
      const response = await getSettings()
      setSettings(response.data.settings)
    } catch {
      message.error('Ошибка загрузки настроек')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSettings()
  }, [])

  const handleAdd = () => {
    setEditingKey(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (record: SettingItem) => {
    setEditingKey(record.key)
    form.setFieldsValue({ key: record.key, value: record.value })
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaveLoading(true)

      const settingsToUpdate = [{ key: values.key, value: values.value }]
      await updateSettings({ settings: settingsToUpdate })

      message.success('Настройка сохранена')
      setModalOpen(false)
      fetchSettings()
    } catch {
      message.error('Ошибка сохранения')
    } finally {
      setSaveLoading(false)
    }
  }

  const columns = [
    {
      title: 'Ключ',
      dataIndex: 'key',
      key: 'key',
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: 'Значение',
      dataIndex: 'value',
      key: 'value',
    },
    {
      title: 'Дата обновления',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (text: string) => new Date(text).toLocaleString('ru-RU'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: unknown, record: SettingItem) => (
        <RoleGuard roles={['master']}>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Изменить
          </Button>
        </RoleGuard>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>Настройки платформы</h2>
        <RoleGuard roles={['master']}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            Добавить настройку
          </Button>
        </RoleGuard>
      </div>

      <Table
        columns={columns}
        dataSource={settings}
        rowKey="key"
        loading={loading}
        pagination={false}
      />

      <Modal
        title={editingKey ? 'Редактировать настройку' : 'Добавить настройку'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saveLoading}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="key"
            label="Ключ"
            rules={[{ required: true, message: 'Введите ключ настройки' }]}
          >
            <Input
              placeholder="напр. bot.welcome_text"
              disabled={editingKey !== null}
            />
          </Form.Item>
          <Form.Item
            name="value"
            label="Значение"
            rules={[{ required: true, message: 'Введите значение' }]}
          >
            <Input.TextArea rows={3} placeholder="Значение настройки" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
