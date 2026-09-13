import { useState } from 'react'
import { Button, Card, Form, Input, Spin, Alert, Typography } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { tmaLogin } from '../services/api'

const { Title } = Typography

/** Fallback login form shown when the app is opened outside Telegram Mini Apps.
 *  Inside Telegram, TmaAuthContext silently exchanges initData → JWT and this
 *  component never renders. */
export default function AdminLoginFallback() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onFinish = async (values: { username: string; password: string }) => {
    setError(null)
    setLoading(true)
    try {
      const res = await tmaLogin(values.username, values.password)
      localStorage.setItem('tma_access_token', res.data.access_token)
      window.location.reload()
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Неверное имя пользователя или пароль'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#f0f2f5',
      }}
    >
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: 'center' }}>
          Игрок.Реальность
        </Title>
        <Title level={5} style={{ textAlign: 'center', marginTop: 0 }}>
          Админ-панель (веб-режим)
        </Title>
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="Вы открыли админ-панель не через Telegram. Войдите паролем."
        />
        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}
        <Form name="admin-login" onFinish={onFinish} autoComplete="off">
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Введите имя пользователя' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Имя пользователя" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Введите пароль' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Пароль" />
          </Form.Item>
          <Form.Item shouldUpdate>
            <Button type="primary" htmlType="submit" block loading={loading}>
              {loading ? <Spin size="small" /> : 'Войти'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
