import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, message, Spin, Typography, Tabs, Divider } from 'antd'
import { getQuiz, updateQuiz, updateQuizResults, type QuizConfig } from '../services/api'
import RoleGuard from '../components/RoleGuard'

const { Title } = Typography

const ARCHETYPES = [
  { key: 'head', label: 'Голова (A)' },
  { key: 'shell', label: 'Панцирь (B)' },
  { key: 'whirlwind', label: 'Вихрь (C)' },
  { key: 'ghost', label: 'Призрак (D)' },
]

const OPTION_KEYS = ['a', 'b', 'c', 'd']

export default function Quiz() {
  const [quiz, setQuiz] = useState<QuizConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [savingQuiz, setSavingQuiz] = useState(false)
  const [savingResults, setSavingResults] = useState(false)
  const [quizForm] = Form.useForm()
  const [resultsForm] = Form.useForm()

  const fetchQuiz = async () => {
    try {
      setLoading(true)
      const response = await getQuiz()
      setQuiz(response.data)
      const qValues: Record<string, string> = {}
      response.data.questions.forEach((q, qi) => {
        qValues[`q${qi}_text`] = q.text
        q.options.forEach((opt) => {
          qValues[`q${qi}_opt_${opt.key}`] = opt.text
        })
      })
      quizForm.setFieldsValue({ intro: response.data.intro, ...qValues })
      resultsForm.setFieldsValue(response.data.results)
    } catch {
      message.error('Ошибка загрузки теста')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQuiz()
  }, [])

  const handleSaveQuiz = async () => {
    try {
      const values = await quizForm.validateFields()
      setSavingQuiz(true)
      const questions = (quiz?.questions || []).map((_q, qi) => ({
        text: values[`q${qi}_text`],
        options: OPTION_KEYS.map((key) => ({
          key,
          text: values[`q${qi}_opt_${key}`] || '',
        })),
      }))
      await updateQuiz({ intro: values.intro, questions })
      message.success('Тест сохранён')
      fetchQuiz()
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error('Ошибка сохранения теста')
    } finally {
      setSavingQuiz(false)
    }
  }

  const handleSaveResults = async () => {
    try {
      const values = await resultsForm.validateFields()
      setSavingResults(true)
      await updateQuizResults({
        head: values.head,
        shell: values.shell,
        whirlwind: values.whirlwind,
        ghost: values.ghost,
      })
      message.success('Результаты сохранены')
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error('Ошибка сохранения результатов')
    } finally {
      setSavingResults(false)
    }
  }

  if (loading) {
    return <Spin />
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <Title level={4}>Входной тест — 4 вопроса на архетип</Title>

      <Card title="Вступление и вопросы" style={{ marginBottom: 24 }}>
        <Form form={quizForm} layout="vertical">
          <Form.Item
            name="intro"
            label="Вступление (показывается перед тестом)"
            rules={[{ required: true, message: 'Введите вступление' }]}
          >
            <Input.TextArea rows={5} />
          </Form.Item>
          {(quiz?.questions || []).map((_q, qi) => (
            <div key={qi}>
              <Divider orientation="left">Вопрос {qi + 1}</Divider>
              <Form.Item
                name={`q${qi}_text`}
                label="Текст вопроса"
                rules={[{ required: true, message: 'Введите текст вопроса' }]}
              >
                <Input.TextArea rows={3} />
              </Form.Item>
              {OPTION_KEYS.map((key) => (
                <Form.Item
                  key={key}
                  name={`q${qi}_opt_${key}`}
                  label={`Вариант ${key.toUpperCase()}`}
                  rules={[{ required: true, message: 'Введите текст варианта' }]}
                >
                  <Input />
                </Form.Item>
              ))}
            </div>
          ))}
          <RoleGuard roles={['master']}>
            <Button type="primary" onClick={handleSaveQuiz} loading={savingQuiz}>
              Сохранить тест
            </Button>
          </RoleGuard>
        </Form>
      </Card>

      <Card title="Результаты — персонализированные приветствия">
        <Form form={resultsForm} layout="vertical">
          <Tabs
            defaultActiveKey="head"
            items={ARCHETYPES.map((a) => ({
              key: a.key,
              label: a.label,
              children: (
                <Form.Item
                  name={a.key}
                  rules={[{ required: true, message: 'Введите текст результата' }]}
                >
                  <Input.TextArea rows={12} />
                </Form.Item>
              ),
            }))}
          />
          <RoleGuard roles={['master']}>
            <Button type="primary" onClick={handleSaveResults} loading={savingResults}>
              Сохранить результаты
            </Button>
          </RoleGuard>
        </Form>
      </Card>
    </div>
  )
}
