import { useEffect, useRef } from 'react'
import { STUB_USER_KEY } from '@/shared/api/client'
import type { Task } from './api'

const IS_STUB = import.meta.env.VITE_AUTH_STUB === 'true'

export type TaskEventType = 'task.created' | 'task.updated' | 'task.status_changed' | 'task.deleted'

export interface TaskEvent {
  type: TaskEventType
  project_id: string
  task_id: string
  task?: Task
}

async function buildAuthHeaders(): Promise<Record<string, string>> {
  if (IS_STUB) {
    const email = typeof window !== 'undefined' ? window.localStorage.getItem(STUB_USER_KEY) : null
    return email ? { 'X-Stub-User': email } : {}
  }
  const { userManager } = await import('@/features/auth/oidc')
  const user = await userManager.getUser()
  return user?.access_token ? { Authorization: `Bearer ${user.access_token}` } : {}
}

interface SseLineState {
  eventName: string
  dataLines: string[]
}

function parseSseLine(
  line: string,
  state: SseLineState,
  onDispatch: (name: string, data: string) => void,
) {
  if (line === '') {
    if (state.dataLines.length > 0) {
      onDispatch(state.eventName, state.dataLines.join('\n'))
    }
    state.eventName = 'message'
    state.dataLines = []
  } else if (line.startsWith(':')) {
    // comment / keepalive — ignore
  } else if (line.startsWith('event:')) {
    state.eventName = line.slice(6).trim()
  } else if (line.startsWith('data:')) {
    state.dataLines.push(line.slice(5).trim())
  }
}

async function connectSse(
  projectId: string,
  onEvent: (evt: TaskEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const headers = await buildAuthHeaders()
  const response = await fetch(`/api/v1/projects/${projectId}/events`, { headers, signal })

  if (!response.ok || !response.body) {
    throw new Error(`SSE connect failed: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const state: SseLineState = { eventName: 'message', dataLines: [] }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      parseSseLine(line, state, (name, data) => {
        if (name === 'connected') return
        try {
          onEvent(JSON.parse(data) as TaskEvent)
        } catch {
          // malformed JSON — ignore
        }
      })
    }
  }
}

export function useProjectEvents(
  projectId: string | null | undefined,
  onEvent: (evt: TaskEvent) => void,
): void {
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    if (!projectId) return

    let disposed = false
    let retryDelay = 1000
    const controller = new AbortController()

    async function run() {
      while (!disposed) {
        try {
          await connectSse(projectId!, (evt) => onEventRef.current(evt), controller.signal)
          retryDelay = 1000 // clean close — reset backoff
        } catch (err) {
          if (controller.signal.aborted) break
          console.warn('[SSE] disconnected, retrying in', retryDelay, 'ms', err)
          await new Promise(r => setTimeout(r, retryDelay))
          retryDelay = Math.min(retryDelay * 2, 30_000)
        }
      }
    }

    run()

    return () => {
      disposed = true
      controller.abort()
    }
  }, [projectId])
}
