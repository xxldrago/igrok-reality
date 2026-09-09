import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tma_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('tma_access_token')
      // In TMA there's no login page — show error via auth context
      window.location.reload()
    }
    return Promise.reject(error)
  },
)

// --- TypeScript interfaces (shared with web admin) ---

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

// --- Scroll interfaces ---

export interface ScrollItem {
  id: string
  day_number: number
  archetype: string
  text: string
  media_file_id: string | null
  created_at: string
  updated_at: string | null
}

export interface ScrollListResponse {
  scrolls: ScrollItem[]
  total: number
  page: number
  page_size: number
}

export interface ScrollCreateData {
  day_number: number
  archetype: string
  text: string
  media_file_id?: string | null
}

export interface ScrollUpdateData {
  text: string
  media_file_id?: string | null
}

// --- Scroll API methods ---

export interface GetScrollsParams {
  archetype?: string
  day_number?: number
  page?: number
  page_size?: number
}

export function getScrolls(params: GetScrollsParams = {}) {
  return api.get<ScrollListResponse>('/admin/scrolls', { params })
}

export function getScroll(id: string) {
  return api.get<ScrollItem>(`/admin/scrolls/${id}`)
}

export function createScroll(data: ScrollCreateData) {
  return api.post<ScrollItem>('/admin/scrolls', data)
}

export function updateScroll(id: string, data: ScrollUpdateData) {
  return api.put<ScrollItem>(`/admin/scrolls/${id}`, data)
}

export function deleteScroll(id: string) {
  return api.delete(`/admin/scrolls/${id}`)
}

// --- Payment interfaces ---

export interface PaymentItem {
  id: string
  user_id: string
  user_name: string
  user_username: string | null
  amount: number
  currency: string
  status: string
  payment_method: string | null
  platega_transaction_id: string | null
  created_at: string
}

export interface PaymentListResponse {
  payments: PaymentItem[]
  total: number
  page: number
  page_size: number
}

// --- Payment API methods ---

export interface GetPaymentsParams {
  status?: string
  user_id?: string
  page?: number
  page_size?: number
}

export function getPayments(params: GetPaymentsParams = {}) {
  return api.get<PaymentListResponse>('/admin/payments', { params })
}

export function getPayment(id: string) {
  return api.get<PaymentItem>(`/admin/payments/${id}`)
}

// --- Settings interfaces ---

export interface SettingItem {
  key: string
  value: string
  created_at: string
  updated_at: string
}

export interface SettingListResponse {
  settings: SettingItem[]
}

export interface SettingUpdateData {
  settings: { key: string; value: string }[]
}

// --- Settings API methods ---

export function getSettings() {
  return api.get<SettingListResponse>('/admin/settings')
}

export function updateSettings(data: SettingUpdateData) {
  return api.put<SettingListResponse>('/admin/settings', data)
}

// --- Audit log interfaces ---

export interface AuditEntry {
  id: string
  admin_id: string | null
  admin_name: string | null
  action: string
  details: string | null
  created_at: string
}

export interface AuditListResponse {
  entries: AuditEntry[]
  total: number
  page: number
  page_size: number
}

// --- Audit log API methods ---

export interface GetAuditParams {
  action?: string
  admin_id?: string
  page?: number
  page_size?: number
}

export function getAuditLog(params: GetAuditParams = {}) {
  return api.get<AuditListResponse>('/admin/audit', { params })
}

// --- Dashboard interfaces ---

export interface DashboardResponse {
  active_players: number
  paid_players: number
  conversion_rate: number
  total_income: number
  prize_fund_total: number
  retention_by_day: Record<number, number>
  recent_activity: {
    user_name: string
    day_number: number
    xp_awarded: number
    created_at: string
  }[]
}

export function getDashboard() {
  return api.get<DashboardResponse>('/admin/dashboard')
}

// --- Finance interfaces ---

export interface CommissionBalanceItem {
  user_id: string
  username: string | null
  pending: number
  paid_out: number
  last_commission_at: string | null
}

export interface CommissionListResponse {
  balances: CommissionBalanceItem[]
}

export function getCommissions() {
  return api.get<CommissionListResponse>('/admin/commissions')
}

export interface PrizeFundItem {
  id: string
  name: string
  total_amount: number
  percent_rule: number
  status: string
  distributed_at: string | null
  created_at: string
}

export interface PrizeFundListResponse {
  funds: PrizeFundItem[]
}

export function getPrizeFunds() {
  return api.get<PrizeFundListResponse>('/admin/prize-funds')
}

export function createPrizeFund(data: { name: string; percent_rule: number }) {
  return api.post<PrizeFundItem>('/admin/prize-funds', data)
}

export function distributePrizeFund(data: { fund_id: string; top_n?: number }) {
  return api.post('/admin/prize-funds/distribute', data)
}

export function exportPaymentsCsv() {
  return api.get<{ csv: string; count: number }>('/admin/payments/export')
}

// --- Moderation interfaces ---

export interface ModerationReportItem {
  id: string
  user_id: string
  username: string | null
  reason: string
  status: string
  created_at: string
}

export interface ModerationListResponse {
  reports: ModerationReportItem[]
  total: number
}

export function getModerationReports(params?: { status?: string }) {
  return api.get<ModerationListResponse>('/admin/moderation', { params })
}

export function resolveModerationReport(id: string, decision: string) {
  return api.post(`/admin/moderation/${id}/resolve`, { decision })
}

// --- Role change ---

export function changeUserRole(userId: string, role: string) {
  return api.post(`/admin/users/${userId}/role`, { role })
}

export default api
