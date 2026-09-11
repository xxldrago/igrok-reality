import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, message, Spin, Tag, Typography } from 'antd'
import { getProfile, updateProfile, type AdminProfile } from '../services/api'
import RoleGuard from '../components/RoleGuard'

const { Title, Text } = Typography

export default function Profile() {
  const [profile, setProfile] = useState<AdminProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const fetchProfile = async () => {
    try {
      setLoading(true)
      const response = await getProfile()
      setProfile(response.data)
      form.setFieldsValue({ username: response.data.username, telegram: response.data.telegram })
    } catch {
      message.error('Ошибка загрузки профиля')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProfile()
  }, [])

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (values.password && values.password !== values.password_confirm) {
        message.error('Пароли не совпадают')
        return
      }
      setSaving(true)
      const payload: { username?: string; telegram?: string; password?: string } = {}
      if (values.username) payload.username = values.username
      if (values.telegram !== undefined) payload.telegram = values.telegram
      if (values.password) payload.password = values.password
      const response = await updateProfile(payload)
      setProfile(response.data)
      form.setFieldsValue({ password: undefined, password_confirm: undefined })
      message.success('Профиль обновлён. После смены логина войдите заново.')
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error('Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <Spin />
  }

  return (
    <div style={{ maxWidth: 560 }}>
      <Title level={4}>Профиль администратора</Title>
      <Card>
        <Form form={form} layout="vertical">
          <Form.Item label="Текущий логин">
            <Text strong>{profile?.username}</Text>{' '}
            {profile?.has_custom_password ? (
              <Tag color="green">свой пароль</Tag>
            ) : (
              <Tag>пароль из окружения</Tag>
            )}
          </Form.Item>
          <RoleGuard roles={['master']}>
            <Form.Item name="username" label="Логин для входа">
              <Input placeholder="admin" />
            </Form.Item>
            <Form.Item name="telegram" label="Telegram для связи (@login)">
              <Input placeholder="@login" />
            </Form.Item>
            <Form.Item name="password" label="Новый пароль (пусто — не менять)">
              <Input.Password placeholder="Минимум 6 символов" />
            </Form.Item>
            <Form.Item name="password_confirm" label="Подтверждение пароля">
              <Input.Password placeholder="Повторите пароль" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" onClick={handleSave} loading={saving}>
                Сохранить
              </Button>
            </Form.Item>
          </RoleGuard>
        </Form>
      </Card>
    </div>
  )
}
