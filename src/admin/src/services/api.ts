import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  },
)

// --- TypeScript interfaces ---

export interface UserListItem {
  id: string
  telegram_id: number
  first_name: string
  last_name: string | null
  username: string | null
  archetype: string | null
  xp: number
  streak: number
  is_active: boolean
  paid_at: string | null
  started_at: string | null
  created_at: string
}

export interface UserListResponse {
  users: UserListItem[]
  total: number
  page: number
  page_size: number
}

export interface UserPaymentItem {
  id: string
  amount: number
  status: string
  created_at: string
}

export interface UserDetailResponse extends UserListItem {
  timezone: string
  completions_count: number
  payments: UserPaymentItem[]
  referrals_count: number
  commission_balance: {
    total_earned: number
    total_pending: number
    total_paid_out: number
  } | null
}

// --- User API methods ---

export interface GetUsersParams {
  search?: string
  archetype?: string
  is_active?: boolean
  has_paid?: boolean
  page?: number
  page_size?: number
}

export function getUsers(params: GetUsersParams = {}) {
  return api.get<UserListResponse>('/admin/users', { params })
}

export function getUser(id: string) {
  return api.get<UserDetailResponse>(`/admin/users/${id}`)
}

export default api
