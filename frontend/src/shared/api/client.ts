import axios from 'axios'
import { toast } from 'sonner'

export const STUB_USER_KEY = 'tt_stub_user'

const ERROR_MESSAGES: Record<string, string> = {
  // task / assignment
  TASK_NOT_FOUND:                  'Задача не найдена',
  VERSION_CONFLICT:                'Данные изменились — обновите страницу',
  VERSION_REQUIRED:                'Не передан параметр version',
  WORKFLOW_TRANSITION_NOT_ALLOWED: 'Этот переход статуса недопустим',
  WORKFLOW_NO_DEFAULT_STATUS:      'В воркфлоу нет статуса по умолчанию',
  TASK_BLOCKED_BY_SUBTASKS:        'Задача заблокирована: не все подзадачи завершены',
  // result and review (ADR-021)
  NOT_ASSIGNEE:                    'Действие доступно только исполнителю задачи',
  UNKNOWN_CRITERION:               'Указан критерий, которого нет в задании',
  PROPOSAL_NOT_FOUND:              'Предложение результата не найдено',
  PROPOSAL_NOT_REVIEWABLE:         'Эта версия уже проверена или заменена',
  PROPOSAL_NOT_SUPERSEDABLE:       'Эту версию нельзя заменить',
  PROPOSAL_NOT_WITHDRAWABLE:       'Отозвать можно только непроверенную версию',
  SELF_REVIEW:                     'Нельзя проверять собственный результат или задачу, где вы исполнитель',
  NOT_REVIEWER:                    'Нужен профиль проверяющего в проекте',
  NOT_DESIGNATED_REVIEWER:         'Задачу проверяет назначенный проверяющий',
  CRITERIA_NOT_MET:                'Для принятия все обязательные критерии должны быть выполнены',
  RESULT_NOT_REVIEWED:             'Нельзя закрыть задачу без проверки результата',
  RESULT_NOT_ACCEPTED:             'Поставка возможна только после принятия результата',
  DELIVERY_NOT_PROPOSED:           'Сначала предложите поставку',
  // assignment (work package)
  WORK_PACKAGE_INCOMPLETE:         'Задание неполное: заполните цель, результат, критерии и специализацию',
  WORK_PACKAGE_UNCHANGED:          'Задание не изменилось с последней версии',
  WORK_PACKAGE_NOT_FOUND:          'Версия задания не найдена',
  // work sessions
  SESSION_ACTIVE:                  'Задача уже в работе в другой сессии',
  SESSION_NOT_ACTIVE:              'Сессия не активна или принадлежит другому',
  SESSION_NOT_FOUND:               'Сессия не найдена',
  // processes
  META_INVALID:                    'Поля задачи не соответствуют схеме её типа',
  TRANSITION_FIELDS_REQUIRED:      'Для этого перехода заполните обязательные поля',
  // idempotency
  IDEMPOTENCY_KEY_REUSED:          'Ключ повтора уже использован для другого запроса',
  IDEMPOTENCY_IN_PROGRESS:         'Запрос ещё выполняется — повторите позже',
  IDEMPOTENCY_OUTCOME_UNKNOWN:     'Команда выполнена, но ответ потерян — обновите данные',
  // project / workflow
  PROJECT_NOT_FOUND:               'Проект не найден',
  DUPLICATE_PROJECT_KEY:           'Проект с таким ключом уже существует',
  PROJECT_MEMBER_ALREADY_EXISTS:   'Участник уже добавлен в проект',
  PROJECT_MEMBER_NOT_FOUND:        'Участник не найден в проекте',
  WORKFLOW_NOT_FOUND:              'Воркфлоу не найден',
  WORKFLOW_HAS_TASKS:              'Нельзя удалить воркфлоу — есть активные задачи',
  WORKFLOW_IS_DEFAULT:             'Нельзя удалить воркфлоу по умолчанию',
  STATUS_NOT_FOUND:                'Статус не найден',
  STATUS_HAS_ACTIVE_ASSIGNMENTS:   'Статус используется — нельзя удалить',
  STATUS_DEFAULT_MUST_BE_INITIAL:  'Статус по умолчанию должен быть initial',
  STATUS_NOT_IN_WORKFLOW:          'Статус не принадлежит этому воркфлоу',
  STATUS_WORKFLOW_MISMATCH:        'Статус принадлежит другому воркфлоу',
  TRANSITION_NOT_FOUND:            'Переход не найден',
  TRANSITION_ROLE_REQUIRED:        'Для этого перехода нужна более высокая роль в проекте',
  // generic
  PERMISSION_DENIED:               'Нет прав для этого действия',
}

const IS_STUB = import.meta.env.VITE_AUTH_STUB === 'true'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(async config => {
  if (IS_STUB) {
    // Dev "View as" header
    if (typeof window !== 'undefined') {
      const email = window.localStorage.getItem(STUB_USER_KEY)
      if (email) config.headers.set('X-Stub-User', email)
    }
  } else {
    // OIDC: attach Bearer token
    const { userManager } = await import('@/features/auth/oidc')
    const user = await userManager.getUser()
    if (user?.access_token) {
      config.headers.set('Authorization', `Bearer ${user.access_token}`)
    }
  }
  return config
})

api.interceptors.response.use(
  res => res,
  async err => {
    if (!axios.isAxiosError(err)) {
      toast.error('Неизвестная ошибка')
      return Promise.reject(err)
    }
    if (err.response?.status === 401) {
      if (IS_STUB) {
        // Stale email in localStorage — clear it and reload so AuthProvider picks the default user
        window.localStorage.removeItem(STUB_USER_KEY)
        window.location.reload()
        return new Promise(() => {})
      }
      if (!IS_STUB) {
        const { userManager } = await import('@/features/auth/oidc')
        // Try silent token refresh before doing a full redirect.
        // A full redirect on every 401 creates an infinite loop when Keycloak
        // immediately issues a new token via SSO (user appears logged in but 401 repeats).
        try {
          await userManager.signinSilent()
          // Retry the original request with the new token
          const user = await userManager.getUser()
          if (user?.access_token && err.config) {
            err.config.headers = err.config.headers ?? {}
            err.config.headers['Authorization'] = `Bearer ${user.access_token}`
            return api(err.config)
          }
        } catch {
          // Silent refresh failed — the session is truly gone
          await userManager.signinRedirect()
          return new Promise(() => {})
        }
      }
      return Promise.reject(err)
    }

    const detail = err.response?.data?.detail
    const code = typeof detail === 'object' ? detail?.code : undefined
    const message =
      (code && ERROR_MESSAGES[code]) ??
      (typeof detail === 'string' ? detail : null) ??
      `Ошибка ${err.response?.status ?? 'сети'}`

    toast.error(message)
    return Promise.reject(err)
  },
)
