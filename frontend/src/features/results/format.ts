export const WAITING_LABEL: Record<string, string> = {
  no_work_package:      'No assignment',
  work_package_changed: 'Assignment changed',
  no_assignee:          'No assignee',
  blocked:              'Blocked',
  awaiting_review:      'Awaiting review',
  changes_requested:    'Changes requested',
  session_stale:        'Session silent',
  awaiting_recipient:   'Awaiting recipient',
  unverified_result:    'Unverified result',
}

export const fmtDateTime = (s: string) =>
  new Date(s).toLocaleString('en', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

export const inputCls =
  'w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:border-primary'
