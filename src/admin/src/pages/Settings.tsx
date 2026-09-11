import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Collapse, Card, message, Spin, Tag } from 'antd'
import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import {
  getSettings,
  updateSettings,
  getSettingsSchema,
  type SettingItem,
  type SettingsSchemaGroup,
} from '../services/api'
import RoleGuard from '../components/RoleGuard'

const DEFAULT_PRICE_RUB = 4900

function toRub(value: string): number {
  const kopecks = parseInt(value, 10)
  if (isNaN(kopecks) || kopecks <= 0) return DEFAULT_PRICE_RUB
  return kopecks / 100
}

export default function Settings() {
  const [settings, setSettings] = useState<SettingItem[]>([])
  const [groups, setGroups] = useState<SettingsSchemaGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [schemaLoading, setSchemaLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [form] = Form.useForm()
  const [schemaForm] = Form.useForm()
  const [saveLoading, setSaveLoading] = useState(false)
  const [groupSaving, setGroupSaving] = useState<string | null>(null)

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

  const fetchSchema = async () => {
    try {
      setSchemaLoading(true)
      const response = await getSettingsSchema()
      setGroups(response.data.groups)
      const values: Record<string, unknown> = {}
      response.data.groups.forEach((g) => {
        g.fields.forEach((f) => {
          if (f.type === 'price_rub') {
            values[f.key] = toRub(f.value)
          } else if (f.type === 'number') {
            values[f.key] = f.value ? Number(f.value) : undefined
          } else {
            values[f.key] = f.value
          }
        })
      })
      schemaForm.setFieldsValue(values)
    } catch {
      message.error('Ошибка загрузки схемы настроек')
    } finally {
      setSchemaLoading(false)
    }
  }

  useEffect(() => {
    fetchSettings()
    fetchSchema()
  }, [])

  const handleSaveGroup = async (groupKey: string) => {
    const group = groups.find((g) => g.group === groupKey)
    if (!group) return
    try {
      setGroupSaving(groupKey)
      const values = schemaForm.getFieldsValue()
      const toUpdate: { key: string; value: string }[] = []
      group.fields.forEach((f) => {
        const v = values[f.key]
        if (v === undefined || v === null || v === '') {
          if (f.type === 'password') return
          if (f.type === 'price_rub') return
          return
        }
        if (f.type === 'price_rub') {
          toUpdate.push({ key: f.key, value: String(Math.round(Number(v) * 100)) })
        } else {
          toUpdate.push({ key: f.key, value: String(v) })
        }
      })
      if (toUpdate.length === 0) {
        message.info('Нет изменений для сохранения')
        return
      }
      await updateSettings({ settings: toUpdate })
      message.success('Настройки сохранены')
      fetchSchema()
      fetchSettings()
    } catch {
      message.error('Ошибка сохранения')
    } finally {
      setGroupSaving(null)
    }
  }

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
      fetchSchema()
    } catch {
      message.error('Ошибка сохранения')
    } finally {
      setSaveLoading(false)
    }
  }

  const renderField = (f: SettingsSchemaGroup['fields'][number]) => {
    switch (f.type) {
      case 'password':
        return <Input.Password placeholder={f.is_default ? 'По умолчанию из окружения' : ''} autoComplete="new-password" />
      case 'number':
        return <InputNumber style={{ width: '100%' }} placeholder={f.is_default ? 'По умолчанию' : ''} />
      case 'price_rub':
        return <InputNumber style={{ width: '100%' }} min={0} addonAfter="₽" />
      case 'textarea':
        return <Input.TextArea rows={f.key === 'welcome_message' ? 8 : 4} />
      default:
        return <Input placeholder={f.is_default ? 'По умолчанию из окружения' : ''} />
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
      <h2 style={{ marginTop: 0 }}>Настройки платформы</h2>

      <Spin spinning={schemaLoading}>
        <Form form={schemaForm} layout="vertical">
          <Collapse
            defaultActiveKey={['telegram', 'platega', 'payments']}
            items={groups.map((g) => ({
              key: g.group,
              label: g.title,
              children: (
                <>
                  {g.fields.map((f) => (
                    <Form.Item
                      key={f.key}
                      name={f.key}
                      label={
                        <span>
                          {f.label}{' '}
                          {f.is_default ? <Tag>по умолчанию</Tag> : <Tag color="green">задано</Tag>}
                        </span>
                      }
                      help={f.hint || undefined}
                    >
                      {renderField(f)}
                    </Form.Item>
                  ))}
                  <RoleGuard roles={['master']}>
                    <Button
                      type="primary"
                      onClick={() => handleSaveGroup(g.group)}
                      loading={groupSaving === g.group}
                    >
                      Сохранить раздел
                    </Button>
                  </RoleGuard>
                </>
              ),
            }))}
          />
        </Form>
      </Spin>

      <Card title="Все настройки (сырые ключи)" style={{ marginTop: 24 }}>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
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
      </Card>

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
