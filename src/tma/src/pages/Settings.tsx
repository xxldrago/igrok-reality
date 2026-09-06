import { useState, useEffect } from 'react'
import { Card, List, Button, Input, message, Empty, Spin } from 'antd'
import { EditOutlined, SaveOutlined } from '@ant-design/icons'
import {
  getSettings,
  updateSettings,
  type SettingItem,
} from '../services/api'
import { useTmaAuth } from '../contexts/TmaAuthContext'

export default function Settings() {
  const { user } = useTmaAuth()
  const [settings, setSettings] = useState<SettingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setLoading(true)
    getSettings()
      .then((res) => setSettings(res.data.settings))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (user?.role !== 'master') {
    return <Empty description="Нет доступа" />
  }

  const startEdit = (item: SettingItem) => {
    setEditingKey(item.key)
    setEditValue(item.value)
  }

  const saveEdit = async (key: string) => {
    setSaving(true)
    try {
      await updateSettings({ settings: [{ key, value: editValue }] })
      setSettings((prev) =>
        prev.map((s) => (s.key === key ? { ...s, value: editValue } : s)),
      )
      setEditingKey(null)
      message.success('Настройка сохранена')
    } catch {
      message.error('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin />
      </div>
    )
  }

  return (
    <div>
      <Card size="small" title="Настройки платформы">
        {settings.length === 0 ? (
          <Empty description="Нет настроек" />
        ) : (
          <List
            dataSource={settings}
            renderItem={(item) => (
              <List.Item
                actions={[
                  editingKey === item.key ? (
                    <Button
                      key="save"
                      type="link"
                      icon={<SaveOutlined />}
                      loading={saving}
                      onClick={() => saveEdit(item.key)}
                    />
                  ) : (
                    <Button
                      key="edit"
                      type="link"
                      icon={<EditOutlined />}
                      onClick={() => startEdit(item)}
                    />
                  ),
                ]}
              >
                <List.Item.Meta
                  title={item.key}
                  description={
                    editingKey === item.key ? (
                      <Input
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onPressEnter={() => saveEdit(item.key)}
                        size="small"
                        autoFocus
                      />
                    ) : (
                      <span style={{ fontFamily: 'monospace' }}>
                        {item.value}
                      </span>
                    )
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}
