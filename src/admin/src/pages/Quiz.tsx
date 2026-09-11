import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, message, Spin, Typography, Tabs, Divider, Select, Space } from 'antd'
import {
  getQuiz,
  updateQuiz,
  updateQuizResults,
  getQuizScores,
  updateQuizScores,
  type QuizConfig,
  type ArchetypeScores,
} from '../services/api'
import RoleGuard from '../components/RoleGuard'

const { Title } = Typography

const ARCHETYPES = [
  { key: 'head', label: 'Голова (A)' },
  { key: 'shell', label: 'Панцирь (B)' },
  { key: 'whirlwind', label: 'Вихрь (C)' },
  { key: 'ghost', label: 'Призрак (D)' },
]

const OPTION_KEYS = ['a', 'b', 'c', 'd']

const DEFAULT_SCORE_MAP: Record<string, string> = { a: 'head', b: 'shell', c: 'whirlwind', d: 'ghost' }

function winnerOf(points: Record<string, number> | undefined, letter: string): string {
  if (!points || Object.keys(points).length === 0) return DEFAULT_SCORE_MAP[letter]
  return Object.entries(points).sort((x, y) => y[1] - x[1])[0][0]
}

export default function Quiz() {
  const [quiz, setQuiz] = useState<QuizConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [savingQuiz, setSavingQuiz] = useState(false)
  const [savingResults, setSavingResults] = useState(false)
  const [savingScores, setSavingScores] = useState(false)
  const [quizForm] = Form.useForm()
  const [resultsForm] = Form.useForm()
  const [scoresForm] = Form.useForm()

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
      try {
        const scoresRes = await getQuizScores()
        const scores: ArchetypeScores = scoresRes.data || {}
        const sValues: Record<string, string> = {}
        for (let qi = 1; qi <= 4; qi++) {
          const qScores = scores[String(qi)] || scores[qi]
          OPTION_KEYS.forEach((letter) => {
            sValues[`score_q${qi}_${letter}`] = winnerOf(qScores?.[letter], letter)
          })
        }
        scoresForm.setFieldsValue(sValues)
      } catch {
        console.error('Failed to load scores')
      }
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

  const handleSaveScores = async () => {
    try {
      const values = await scoresForm.validateFields()
      setSavingScores(true)
      const scores: ArchetypeScores = {}
      for (let qi = 1; qi <= 4; qi++) {
        const q: Record<string, Record<string, number>> = {}
        OPTION_KEYS.forEach((letter) => {
          const arch = values[`score_q${qi}_${letter}`]
          q[letter] = { [arch]: 2 }
        })
        scores[String(qi)] = q
      }
      await updateQuizScores(scores)
      message.success('Скоринг сохранён')
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) return
      message.error('Ошибка сохранения скоринга')
    } finally {
      setSavingScores(false)
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

      <Card title="Скоринг — какой вариант за какой архетип" style={{ marginBottom: 24 }}>
        <Form form={scoresForm} layout="vertical">
          {[1, 2, 3, 4].map((qi) => (
            <div key={qi}>
              <Divider orientation="left">Вопрос {qi}</Divider>
              <Space wrap>
                {OPTION_KEYS.map((letter) => (
                  <Form.Item
                    key={letter}
                    name={`score_q${qi}_${letter}`}
                    label={`Вариант ${letter.toUpperCase()}`}
                    style={{ marginBottom: 8, minWidth: 140 }}
                  >
                    <Select
                      options={ARCHETYPES.map((a) => ({ value: a.key, label: a.label }))}
                    />
                  </Form.Item>
                ))}
              </Space>
            </div>
          ))}
          <RoleGuard roles={['master']}>
            <Button type="primary" onClick={handleSaveScores} loading={savingScores}>
              Сохранить скоринг
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
