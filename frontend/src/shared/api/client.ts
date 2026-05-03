import axios from 'axios'
import { toast } from 'sonner'

export const STUB_USER_KEY = 'tt_stub_user'

const ERROR_MESSAGES: Record<string, string> = {
  // task / assignment
  TASK_NOT_FOUND:                  'Задача не найдена',
  ASSIGNMENT_NOT_FOUND:            'Назначение не найдено',
  RESOLUTION_REQUIRED:             'Укажите резолюцию перед закрытием задачи',
  VERSION_CONFLICT:                'Данные изменились — обновите страницу',
  VERSION_REQUIRED:                'Не передан параметр version',
  WORKFLOW_TRANSITION_NOT_ALLOWED: 'Этот переход статуса недопустим',
  WORKFLOW_NO_DEFAULT_STATUS:      'В воркфлоу нет статуса по умолчанию',
  TASK_BLOCKED_BY_SUBTASKS:        'Задача заблокирована: не все подзадачи завершены',
  // decision process
  SOLUTION_NOT_FOUND:              'Решение не найдено',
  SOLUTION_ALREADY_SUBMITTED:      'Решение уже отправлено',
  SOLUTION_ALREADY_EXISTS:         'Решение уже создано',
  SOLUTION_IN_REVISION:            'Решение находится на доработке',
  SOLUTION_NOT_SUBMITTED:          'Решение ещё не отправлено',
  SOLUTION_LOCKED:                 'Решение заблокировано для редактирования',
  MULTI_ACCEPT_NOT_ALLOWED:        'Нельзя принять несколько решений для этой задачи',
  ACCEPTED_SOLUTIONS_REQUIRED:     'Необходимо выбрать хотя бы одно решение',
  INVALID_SOLUTION_IDS:            'Неверные идентификаторы решений',
  DECISION_ALREADY_MADE:           'Итоговое решение уже принято',
  DECISION_NOT_FOUND:              'Решение decision-maker\'а не найдено',
  TASK_NOT_AWAITING_DECISION:      'Задача не ожидает решения',
  TASK_NOT_DECIDED:                'Задача ещё не имеет решения',
  CANNOT_MODIFY_DECIDED_TASK:      'Нельзя изменить задачу с принятым решением',
  CRITERIA_LOCKED:                 'Критерии решения заблокированы',
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
  RESOLUTION_NOT_FOUND:            'Резолюция не найдена',
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
      if (!IS_STUB) {
        // Redirect to Keycloak login on expired session
        const { userManager } = await import('@/features/auth/oidc')
        await userManager.signinRedirect()
        return new Promise(() => {}) // pending — redirect happening
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
