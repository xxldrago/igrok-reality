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
  role?: string
  group_id?: string
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

export interface QuizAnswerItem {
  question: number
  key: string
  text: string
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
  quiz_answers: QuizAnswerItem[]
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

export interface UserCreateData {
  telegram_id: number
  first_name: string
  last_name?: string | null
  username?: string | null
  archetype?: string | null
  xp?: number
  streak?: number
  is_active?: boolean
  timezone?: string
  role?: string
}

export interface UserUpdateData {
  first_name?: string
  last_name?: string | null
  username?: string | null
  archetype?: string | null
  xp?: number
  streak?: number
  is_active?: boolean
  timezone?: string
  role?: string
  has_paid?: boolean | null
}

export function createUser(data: UserCreateData) {
  return api.post<UserListItem>('/admin/users', data)
}

export function updateUser(id: string, data: UserUpdateData) {
  return api.put<UserListItem>(`/admin/users/${id}`, data)
}

export function deleteUser(id: string) {
  return api.delete<{ user_id: string; deleted: boolean }>(`/admin/users/${id}`)
}

// --- Admin profile ---

export interface AdminProfile {
  username: string
  telegram: string
  has_custom_password: boolean
}

export interface AdminProfileUpdate {
  username?: string
  telegram?: string
  password?: string
}

export function getProfile() {
  return api.get<AdminProfile>('/admin/auth/profile')
}

export function updateProfile(data: AdminProfileUpdate) {
  return api.put<AdminProfile>('/admin/auth/profile', data)
}

// --- Settings schema (grouped editor) ---

export interface SettingsSchemaField {
  key: string
  label: string
  type: string
  hint: string
  value: string
  is_default: boolean
}

export interface SettingsSchemaGroup {
  group: string
  title: string
  fields: SettingsSchemaField[]
}

export function getSettingsSchema() {
  return api.get<{ groups: SettingsSchemaGroup[] }>('/admin/settings-schema')
}

// --- Quiz (entrance test) ---

export interface QuizOption {
  text: string
  key: string
}

export interface QuizQuestion {
  text: string
  options: QuizOption[]
}

export interface QuizConfig {
  intro: string
  questions: QuizQuestion[]
  results: Record<string, string>
}

export function getQuiz() {
  return api.get<QuizConfig>('/admin/quiz')
}

export function updateQuiz(data: { intro: string; questions: QuizQuestion[] }) {
  return api.put('/admin/quiz', data)
}

export function getQuizResults() {
  return api.get<Record<string, string>>('/admin/quiz/results')
}

export function updateQuizResults(data: Record<string, string>) {
  return api.put('/admin/quiz/results', data)
}

export type ArchetypeScores = Record<string, Record<string, Record<string, number>>>

export function getQuizScores() {
  return api.get<ArchetypeScores>('/admin/quiz/scores')
}

export function updateQuizScores(scores: ArchetypeScores) {
  return api.put('/admin/quiz/scores', { scores })
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

export interface ModerationReplyData {
  text?: string
  media_url?: string | null
  media_type?: string | null
}

export function replyModerationReport(id: string, data: ModerationReplyData) {
  return api.post<{ report_id: string; sent: boolean }>(`/admin/moderation/${id}/reply`, data)
}

export function deleteModerationReport(id: string) {
  return api.delete<{ id: string; deleted: boolean }>(`/admin/moderation/${id}`)
}

// --- Role change ---

export function changeUserRole(userId: string, role: string) {
  return api.post(`/admin/users/${userId}/role`, { role })
}

// --- Scroll Types interfaces ---

export interface ScrollTypeItem {
  id: string
  code: string
  name: string
  command: string
  hour: number
  minute: number
  xp_reward: number
  description: string
  requires_meditation: boolean
  is_breathing_day_only: boolean
  is_awareness_day_only: boolean
  sort_order: number
}

export interface ScrollTypeListResponse {
  scroll_types: ScrollTypeItem[]
}

export function getScrollTypes() {
  return api.get<ScrollTypeListResponse>('/admin/scroll-types')
}

export interface ScrollTypeUpdateData {
  name?: string
  description?: string
  hour?: number
  minute?: number
  xp_reward?: number
  sort_order?: number
}

export function updateScrollType(id: string, data: ScrollTypeUpdateData) {
  return api.put<ScrollTypeItem>(`/admin/scroll-types/${id}`, data)
}

// --- Daily Scrolls interfaces ---

export interface DailyScrollItem {
  id: string
  day_number: number
  scroll_type_id: string
  scroll_type_code: string | null
  title: string
  content: string
  media_file_id: string | null
  requires_report: boolean
  xp_reward: number | null
  published_at: string | null
  created_at: string
}

export interface DailyScrollCreateData {
  day_number: number
  scroll_type_id: string
  title: string
  content: string
  media_file_id?: string | null
  requires_report?: boolean
  xp_reward?: number | null
}

export function createDailyScroll(data: DailyScrollCreateData) {
  return api.post<DailyScrollItem>('/admin/daily-scrolls', data)
}

// --- User reports ---

export interface ReportItem {
  id: string
  source: 'scroll' | 'daily'
  user_id: string
  username: string | null
  first_name: string
  archetype: string | null
  quest_day: number | null
  command: string | null
  text: string | null
  media_url: string | null
  media_type: string | null
  xp_awarded: number
  created_at: string
}

export interface ReportListResponse {
  reports: ReportItem[]
  total: number
  page: number
  page_size: number
}

export interface GetReportsParams {
  quest_day?: number
  archetype?: string
  search?: string
  source?: string
  page?: number
  page_size?: number
}

export function getReports(params: GetReportsParams = {}) {
  return api.get<ReportListResponse>('/admin/reports', { params })
}

export interface DailyScrollListResponse {
  scrolls: DailyScrollItem[]
  total: number
  page: number
  page_size: number
}

export interface GetDailyScrollsParams {
  day_number?: number
  scroll_type_id?: string
  page?: number
  page_size?: number
}

export function getDailyScrolls(params: GetDailyScrollsParams = {}) {
  return api.get<DailyScrollListResponse>('/admin/daily-scrolls', { params })
}

export interface DayCoverageItem {
  day: number
  day_type: string
  expected: string[]
  actual: string[]
  missing: string[]
}

export interface ScrollCoverage {
  total_expected: number
  total_actual: number
  complete: boolean
  missing_days: DayCoverageItem[]
  day_types: Record<number, string>
}

export function getScrollCoverage() {
  return api.get<ScrollCoverage>('/admin/daily-scrolls/coverage')
}

export function updateDailyScroll(
  id: string,
  data: { title?: string; content?: string; media_file_id?: string; requires_report?: boolean; xp_reward?: number | null },
) {
  return api.put(`/admin/daily-scrolls/${id}`, data)
}

export function deleteDailyScroll(id: string) {
  return api.delete<{ id: string; deleted: boolean }>(`/admin/daily-scrolls/${id}`)
}

export function deleteReport(id: string, source: string) {
  return api.delete<{ id: string; deleted: boolean }>(`/admin/reports/${id}`, {
    params: { source },
  })
}

// --- User Commands interfaces ---

export interface UserCommandItem {
  id: string
  user_id: string
  quest_day: number
  command: string
  xp_awarded: number
  completed_at: string
  report_text: string | null
}

export interface UserCommandListResponse {
  commands: UserCommandItem[]
  total: number
}

export function getUserCommands(userId: string, params?: { quest_day?: number }) {
  return api.get<UserCommandListResponse>(`/admin/users/${userId}/commands`, { params })
}

// --- User progress (90-day expected vs done) ---

export interface ProgressDoneItem {
  command: string
  slot: string
  xp_awarded: number
  completed_at: string
  report_text: string | null
  report_media_url: string | null
  report_media_type: string | null
}

export interface ProgressExpectedItem {
  code: string
  command: string
  label: string
  xp: number
  time: string
}

export interface ProgressDayItem {
  quest_day: number
  day_type: string
  expected: ProgressExpectedItem[]
  done: ProgressDoneItem[]
  earned_xp: number
  max_xp: number
}

export interface UserProgressResponse {
  user_id: string
  quest_days_active: number
  total_commands: number
  total_xp_earned: number
  days: ProgressDayItem[]
}

export function getUserProgress(userId: string) {
  return api.get<UserProgressResponse>(`/admin/users/${userId}/progress`)
}

// --- Broadcast interfaces ---

export interface BroadcastRequest {
  text: string
  archetype?: string | null
  group_id?: string | null
  parse_mode?: string
  media_url?: string | null
  media_type?: string | null
  scheduled_at?: string | null
}

export interface BroadcastResponse {
  sent: number
  failed: number
  total: number
  scheduled: boolean
}

export function sendBroadcast(data: BroadcastRequest) {
  return api.post<BroadcastResponse>('/admin/broadcast', data)
}

export interface ScheduledBroadcastItem {
  scheduled_at: string
  audience: string
  text_preview: string
  total: number
  media_type: string | null
}

export function getScheduledBroadcasts() {
  return api.get<{ items: ScheduledBroadcastItem[] }>('/admin/broadcasts/scheduled')
}

export function cancelScheduledBroadcast(scheduled_at: string, audience: string) {
  return api.delete<{ cancelled: number }>('/admin/broadcasts/scheduled', {
    data: { scheduled_at, audience },
  })
}

// --- Media upload ---

export interface MediaUploadResponse {
  url: string
  media_type: string
  filename: string
  size: number
}

export function uploadMedia(file: File) {
  const form = new FormData()
  form.append('file', file)
  return api.post<MediaUploadResponse>('/admin/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** Direct URL for http(s) attachments, backend proxy path for Telegram file_ids. */
export function attachmentSrc(url: string | null): string | null {
  if (!url) return null
  if (/^https?:\/\//i.test(url)) return url
  return `/api/admin/media/telegram/${encodeURIComponent(url)}`
}

/** Download Telegram file_id bytes (admin JWT attached by interceptor). */
export function fetchTelegramMedia(fileId: string) {
  return api.get<Blob>(`/admin/media/telegram/${encodeURIComponent(fileId)}`, {
    responseType: 'blob',
  })
}

export interface ArchetypeStatsResponse {
  total: number
  by_archetype: Record<string, number>
}

export function getArchetypeStats() {
  return api.get<ArchetypeStatsResponse>('/admin/users/archetype-stats')
}

// --- Groups API ---
export interface GroupItem {
  id: string
  name: string
  type: string
  owner_id: string | null
  max_members: number
  member_count: number
}
export function getGroups(params?: { group_type?: string }) {
  return api.get<GroupItem[]>('/admin/groups', { params })
}
export function createGroup(data: { name: string; type: string; owner_id?: string | null; max_members?: number }) {
  return api.post<GroupItem>('/admin/groups', data)
}
export function deleteGroup(id: string) {
  return api.delete(`/admin/groups/${id}`)
}
export function addGroupMember(groupId: string, userId: string) {
  return api.post(`/admin/groups/${groupId}/members`, { user_id: userId })
}
export function removeGroupMember(groupId: string, userId: string) {
  return api.delete(`/admin/groups/${groupId}/members/${userId}`)
}
export function getGroupMembers(groupId: string) {
  return api.get(`/admin/groups/${groupId}`)
}

// --- Specialist Quests API ---
export interface SpecialistQuestItem {
  id: string
  group_id: string
  specialist_id: string
  title: string
  content: string
  day_number: number
  media_file_id: string | null
  xp_reward: number
  published_at: string | null
}
export function getSpecialistQuests(params?: { group_id?: string; day_number?: number }) {
  return api.get<SpecialistQuestItem[]>('/admin/specialist-quests', { params })
}
export function createSpecialistQuest(data: { group_id: string; title: string; content: string; day_number: number; xp_reward?: number; media_file_id?: string | null }) {
  return api.post<SpecialistQuestItem>('/admin/specialist-quests', data)
}
export function deleteSpecialistQuest(id: string) {
  return api.delete(`/admin/specialist-quests/${id}`)
}

// --- Commissions API ---
export function payoutCommission(userId: string, amount: number) {
  return api.post('/admin/payout', { user_id: userId, amount })
}

export default api
