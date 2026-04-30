import axios from 'axios'

export const STUB_USER_KEY = 'tt_stub_user'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Dev "View as" — read the active stub-user email from localStorage and
// pass it on every request. Backend respects the header only when
// AUTH_STUB=true; in production it's a no-op.
api.interceptors.request.use(config => {
  if (typeof window !== 'undefined') {
    const email = window.localStorage.getItem(STUB_USER_KEY)
    if (email) {
      config.headers.set('X-Stub-User', email)
    }
  }
  return config
})
