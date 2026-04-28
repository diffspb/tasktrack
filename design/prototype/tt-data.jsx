
const USERS = [
  { id: 'u1', name: 'Alex K.',    initials: 'AK', color: 'oklch(0.52 0.16 252)', role: 'Frontend Developer' },
  { id: 'u2', name: 'Maria S.',   initials: 'MS', color: 'oklch(0.52 0.16 340)', role: 'Designer' },
  { id: 'u3', name: 'Ivan P.',    initials: 'IP', color: 'oklch(0.52 0.16 160)', role: 'Backend Developer' },
  { id: 'u4', name: 'Olga T.',    initials: 'OT', color: 'oklch(0.52 0.16 60)',  role: 'QA Engineer' },
  { id: 'u5', name: 'Dmitry R.',  initials: 'DR', color: 'oklch(0.52 0.16 30)',  role: 'Product Manager' },
];

const PROJECTS = [
  { id: 'p1', key: 'TT', name: 'TaskTrack MVP',   color: 'oklch(0.52 0.16 252)', description: 'Internal task tracker with multi-assignee support' },
  { id: 'p2', key: 'IT', name: 'Internal Tools',  color: 'oklch(0.52 0.16 160)', description: 'Internal tooling and automation' },
  { id: 'p3', key: 'RH', name: 'Research Hub',    color: 'oklch(0.52 0.16 340)', description: 'Research collaboration platform' },
];

const WORKFLOW_STATUSES = [
  { id: 'todo',        label: 'To Do',      category: 'todo' },
  { id: 'in_progress', label: 'In Progress', category: 'active' },
  { id: 'in_review',   label: 'In Review',   category: 'active' },
  { id: 'done',        label: 'Done',        category: 'done' },
];

const GLOBAL_STATUS_META = {
  open:               { label: 'Open',               color: 'oklch(0.52 0.12 240)', bg: 'oklch(0.94 0.04 240)' },
  in_progress:        { label: 'In Progress',         color: 'oklch(0.45 0.14 200)', bg: 'oklch(0.93 0.06 200)' },
  awaiting_decision:  { label: 'Awaiting Decision',   color: 'oklch(0.50 0.14 55)',  bg: 'oklch(0.95 0.06 55)'  },
  in_revision:        { label: 'In Revision',         color: 'oklch(0.50 0.15 25)',  bg: 'oklch(0.95 0.06 25)'  },
  decided:            { label: 'Decided',             color: 'oklch(0.45 0.14 150)', bg: 'oklch(0.93 0.06 150)' },
  closed:             { label: 'Closed',              color: 'oklch(0.45 0.02 240)', bg: 'oklch(0.92 0.01 240)' },
};

const TASKS = [
  {
    id: 't1', key: 'TT-1', projectId: 'p1',
    title: 'Design system setup — tokens, typography, base components',
    type: 'task', priority: 'high',
    globalStatus: 'closed',
    description: 'Establish CSS variable tokens for colors, spacing, and typography. Set up base component library with shadcn/ui. Covers color scales, border-radius, shadow tokens.',
    dueDate: '2024-12-15', createdAt: '2024-12-01',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['design-system', 'frontend'],
    assignees: [
      { userId: 'u1', role: 'lead', personalStatus: 'done', solutionStatus: null },
    ],
    decisionCriteria: [],
    solutions: [],
    comments: [
      { id: 'c1', authorId: 'u5', text: 'Great work! Token structure looks solid. Merged.', createdAt: '2024-12-16T10:30:00Z' },
    ],
    history: [
      { id: 'h1', type: 'status', authorId: 'u1', text: 'moved to In Progress', date: '2024-12-02T09:00:00Z' },
      { id: 'h2', type: 'status', authorId: 'u1', text: 'moved to Done', date: '2024-12-14T16:00:00Z' },
      { id: 'h3', type: 'closed', authorId: 'u5', text: 'closed the task', date: '2024-12-16T10:31:00Z' },
    ],
  },
  {
    id: 't2', key: 'TT-2', projectId: 'p1',
    title: 'Auth module — login, registration, OAuth, password recovery',
    type: 'feature', priority: 'critical',
    globalStatus: 'in_progress',
    description: 'Implement full authentication flow: email/password login, Google OAuth via Keycloak, password recovery. Frontend forms + API integration.',
    dueDate: '2025-01-10', createdAt: '2024-12-05',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['auth', 'backend', 'frontend'],
    assignees: [
      { userId: 'u1', role: 'lead', personalStatus: 'in_progress', solutionStatus: null },
      { userId: 'u3', role: 'lead', personalStatus: 'in_review',   solutionStatus: null },
    ],
    decisionCriteria: [
      { id: 'dc1', description: 'Security best practices — OWASP compliance, CSRF protection' },
      { id: 'dc2', description: 'Performance: login round-trip < 500ms at p95' },
    ],
    solutions: [],
    comments: [
      { id: 'c2', authorId: 'u3', text: 'Backend endpoints are ready, tokens are short-lived (15 min access + 7d refresh). Need frontend to wire up.', createdAt: '2024-12-20T14:00:00Z' },
      { id: 'c3', authorId: 'u1', text: 'On it — connecting OAuth tomorrow, forms are almost done.', createdAt: '2024-12-20T15:22:00Z' },
    ],
    history: [
      { id: 'h4', type: 'assign', authorId: 'u5', text: 'assigned Alex K. (lead) and Ivan P. (lead)', date: '2024-12-05T10:00:00Z' },
      { id: 'h5', type: 'status', authorId: 'u3', text: 'Ivan P. moved to In Review', date: '2024-12-19T11:00:00Z' },
    ],
  },
  {
    id: 't3', key: 'TT-3', projectId: 'p1',
    title: 'Kanban board UI — personal view with drag-and-drop',
    type: 'feature', priority: 'high',
    globalStatus: 'awaiting_decision',
    description: 'Design and implement the personal Kanban board. Each user sees tasks positioned in columns matching their personal_status. Cards show priority, type, multi-assignees.',
    dueDate: '2025-01-05', createdAt: '2024-12-10',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['ui', 'frontend'],
    assignees: [
      { userId: 'u1', role: 'lead',     personalStatus: 'done', solutionStatus: 'submitted' },
      { userId: 'u2', role: 'lead',     personalStatus: 'done', solutionStatus: 'submitted' },
      { userId: 'u4', role: 'reviewer', personalStatus: null,   solutionStatus: null },
    ],
    decisionCriteria: [
      { id: 'dc3', description: 'Performance — smooth drag-and-drop at 60fps with 50+ cards' },
      { id: 'dc4', description: 'Visual quality and adherence to the design system tokens' },
      { id: 'dc5', description: 'Code maintainability — reviewable, typed, tested' },
    ],
    solutions: [
      {
        id: 's1', assigneeId: 'u1', status: 'submitted', submittedAt: '2025-01-04T17:00:00Z',
        content: 'Used @hello-pangea/dnd for drag-and-drop (maintained fork of react-beautiful-dnd). Columns are virtualized with react-window to handle 200+ cards without jank. Card component is fully typed and has unit tests. DnD operations are optimistic — UI updates instantly, syncs in background.\n\nPerformance: measured 60fps on mid-range laptop with 80 cards. Bundle size impact: +18KB gzipped.',
        attachments: ['kanban-board.tsx', 'kanban-card.tsx', 'kanban.spec.ts'],
      },
      {
        id: 's2', assigneeId: 'u2', status: 'submitted', submittedAt: '2025-01-05T11:30:00Z',
        content: 'Took a design-first approach. Built custom drag implementation using the Pointer Events API — no external DnD library, full control over animations. Cards use a staggered entrance animation. Column headers show task count and a mini-progress bar.\n\nDesign improvements: added a "ghost" card preview while dragging, smooth spring-physics drop animation, color-coded priority strips on card left edge.',
        attachments: ['kanban-v2.tsx', 'kanban-design.fig'],
      },
    ],
    comments: [],
    history: [
      { id: 'h6', type: 'solution', authorId: 'u1', text: 'Alex K. submitted Solution', date: '2025-01-04T17:00:00Z' },
      { id: 'h7', type: 'solution', authorId: 'u2', text: 'Maria S. submitted Solution', date: '2025-01-05T11:30:00Z' },
      { id: 'h8', type: 'global_status', authorId: null, text: 'task moved to Awaiting Decision (all leads submitted)', date: '2025-01-05T11:30:00Z' },
    ],
  },
  {
    id: 't4', key: 'TT-4', projectId: 'p1',
    title: 'Decision Process UI — solution submission and review screen',
    type: 'feature', priority: 'critical',
    globalStatus: 'open',
    description: 'Design and implement the Decision Process screens: solution submission form for lead assignees, solution comparison view for decision-maker, revision request flow with feedback.',
    dueDate: '2025-01-20', createdAt: '2024-12-15',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['ui', 'decision-process', 'frontend'],
    assignees: [
      { userId: 'u1', role: 'lead', personalStatus: 'todo', solutionStatus: null },
      { userId: 'u2', role: 'lead', personalStatus: 'todo', solutionStatus: null },
    ],
    decisionCriteria: [
      { id: 'dc6', description: 'UX clarity — decision-maker must understand the process without reading docs' },
      { id: 'dc7', description: 'Handles 2–5 simultaneous solutions without layout issues' },
    ],
    solutions: [],
    comments: [],
    history: [
      { id: 'h9', type: 'assign', authorId: 'u5', text: 'assigned Alex K. (lead) and Maria S. (lead)', date: '2024-12-15T09:00:00Z' },
    ],
  },
  {
    id: 't5', key: 'TT-5', projectId: 'p1',
    title: 'REST API integration — TanStack Query setup and all endpoints',
    type: 'task', priority: 'high',
    globalStatus: 'in_progress',
    description: 'Wire up all frontend components to REST API. Configure TanStack Query with proper caching, optimistic updates, and error handling. Cover: tasks, projects, users, assignments, solutions.',
    dueDate: '2025-01-15', createdAt: '2024-12-12',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['api', 'frontend'],
    assignees: [
      { userId: 'u3', role: 'lead', personalStatus: 'in_progress', solutionStatus: null },
    ],
    decisionCriteria: [],
    solutions: [],
    comments: [],
    history: [],
  },
  {
    id: 't6', key: 'TT-6', projectId: 'p1',
    title: 'Performance audit — FCP, LCP, bundle size optimization',
    type: 'task', priority: 'medium',
    globalStatus: 'in_progress',
    description: 'Run Lighthouse audit on all main screens. Analyze bundle with rollup-plugin-visualizer. Targets: LCP < 2.0s, FCP < 1.0s, bundle < 150KB gzipped.',
    dueDate: '2025-01-25', createdAt: '2024-12-18',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['performance'],
    assignees: [
      { userId: 'u1', role: 'lead',       personalStatus: 'in_review', solutionStatus: null },
      { userId: 'u3', role: 'consultant', personalStatus: null,         solutionStatus: null },
    ],
    decisionCriteria: [],
    solutions: [],
    comments: [
      { id: 'c4', authorId: 'u1', text: 'Initial audit: LCP 3.2s — main offenders are unoptimized avatars and a 42KB moment.js dep we can replace.', createdAt: '2024-12-22T16:00:00Z' },
    ],
    history: [],
  },
  {
    id: 't7', key: 'TT-7', projectId: 'p1',
    title: 'Database schema review — ERD validation before implementation',
    type: 'task', priority: 'high',
    globalStatus: 'decided',
    description: 'Review ERD against all 47 user stories. Identify missing indexes, N+1 risks, constraint gaps. Output: annotated ERD + migration plan.',
    dueDate: '2024-12-20', createdAt: '2024-12-08',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['database', 'backend'],
    assignees: [
      { userId: 'u3', role: 'lead',     personalStatus: 'done', solutionStatus: 'accepted' },
      { userId: 'u4', role: 'reviewer', personalStatus: null,   solutionStatus: null },
    ],
    decisionCriteria: [
      { id: 'dc8', description: 'All MVP user stories covered by schema with no missing FK' },
      { id: 'dc9', description: 'No obvious N+1 join patterns on hot paths (task list, board)' },
    ],
    solutions: [
      {
        id: 's3', assigneeId: 'u3', status: 'accepted', submittedAt: '2024-12-19T15:00:00Z',
        content: 'Reviewed all 47 user stories against ERD. Findings:\n• 3 missing composite indexes added (task_assignees, notifications)\n• N+1 risk on task list — recommend eager-loading assignees via lateral join\n• Added unique constraint on (task_id, user_id) in task_assignees\n• solution_attachments table added (was missing)\n\nAll changes reflected in schema-v2.sql. Ready for implementation.',
        attachments: ['schema-v2.sql', 'review-notes.md'],
      },
    ],
    comments: [],
    history: [
      { id: 'h10', type: 'solution', authorId: 'u3', text: 'Ivan P. submitted Solution', date: '2024-12-19T15:00:00Z' },
      { id: 'h11', type: 'decision', authorId: 'u5', text: 'Dmitry R. accepted Ivan P.\'s Solution', date: '2024-12-20T09:00:00Z' },
    ],
  },
  {
    id: 't8', key: 'TT-8', projectId: 'p1',
    title: 'Mobile responsiveness — tablet and phone breakpoints',
    type: 'task', priority: 'low',
    globalStatus: 'open',
    description: 'Ensure all MVP screens work on tablet (768px) and phone (375px). Priority: task list, task detail, dashboard. Kanban → collapsed list on mobile.',
    dueDate: '2025-02-01', createdAt: '2024-12-20',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['frontend', 'responsive'],
    assignees: [
      { userId: 'u1', role: 'lead', personalStatus: 'todo', solutionStatus: null },
    ],
    decisionCriteria: [],
    solutions: [],
    comments: [],
    history: [],
  },
  {
    id: 't9', key: 'TT-9', projectId: 'p1',
    title: 'Notification system — in-app bell, unread counter, SSE',
    type: 'feature', priority: 'medium',
    globalStatus: 'in_revision',
    description: 'In-app notification system: badge counter in header, notification panel, mark as read. Real-time delivery via Server-Sent Events.',
    dueDate: '2025-01-18', createdAt: '2024-12-14',
    authorId: 'u5', decisionMakerId: 'u5',
    labels: ['notifications', 'frontend', 'backend'],
    assignees: [
      { userId: 'u1', role: 'lead', personalStatus: 'in_progress', solutionStatus: 'revision_requested',
        revisionComment: 'SSE connection drops are not handled gracefully. Need exponential backoff reconnection and a fallback polling mode for corporate proxies that strip keep-alive.' },
      { userId: 'u3', role: 'lead', personalStatus: 'in_progress', solutionStatus: 'submitted' },
    ],
    decisionCriteria: [
      { id: 'dc10', description: 'Real-time delivery < 2s end-to-end without page refresh' },
      { id: 'dc11', description: 'Handles graceful reconnection; works behind corporate proxies' },
    ],
    solutions: [
      {
        id: 's4', assigneeId: 'u1', status: 'revision_requested', submittedAt: '2025-01-15T14:00:00Z',
        content: 'Frontend SSE client. EventSource connects to /api/notifications/stream. Badge counter updates in real time. Panel fetches history on open.',
        revisionComment: 'SSE connection drops are not handled gracefully. Need exponential backoff reconnection and a fallback polling mode for corporate proxies that strip keep-alive.',
        attachments: ['notifications-client.tsx'],
      },
      {
        id: 's5', assigneeId: 'u3', status: 'submitted', submittedAt: '2025-01-14T11:00:00Z',
        content: 'Backend notification service. PostgreSQL LISTEN/NOTIFY → SSE fanout via Redis Pub/Sub. Auto-reconnect on server side, heartbeat every 30s. Handles 1000 concurrent connections per instance.',
        attachments: ['notification-service.ts', 'sse-handler.ts'],
      },
    ],
    comments: [
      { id: 'c5', authorId: 'u5', text: "Ivan's backend is solid. Alex, please address the reconnection issue — corporate proxies are a real concern for our target users.", createdAt: '2025-01-16T09:00:00Z' },
    ],
    history: [
      { id: 'h12', type: 'solution', authorId: 'u3', text: 'Ivan P. submitted Solution', date: '2025-01-14T11:00:00Z' },
      { id: 'h13', type: 'solution', authorId: 'u1', text: 'Alex K. submitted Solution', date: '2025-01-15T14:00:00Z' },
      { id: 'h14', type: 'revision', authorId: 'u5', text: 'Dmitry R. sent Alex K.\'s Solution for revision', date: '2025-01-16T09:05:00Z' },
    ],
  },
];

const NOTIFICATIONS = [
  { id: 'n1', taskId: 't9', type: 'revision',  text: 'Dmitry R. sent your Solution for TT-9 for revision', time: '2h ago',  read: false },
  { id: 'n2', taskId: 't3', type: 'decision',  text: 'TT-3 is awaiting your Decision',                       time: '5h ago',  read: false },
  { id: 'n3', taskId: 't9', type: 'comment',   text: 'Dmitry R. commented on TT-9',                          time: '1d ago',  read: false },
  { id: 'n4', taskId: 't2', type: 'mention',   text: 'Ivan P. mentioned you in TT-2',                        time: '2d ago',  read: true  },
  { id: 'n5', taskId: 't7', type: 'decided',   text: 'TT-7 has been decided',                                time: '3d ago',  read: true  },
];

function getUserById(id) { return USERS.find(u => u.id === id); }
function getTasksForUser(userId, projectId) {
  return TASKS.filter(t =>
    (!projectId || t.projectId === projectId) &&
    t.assignees.some(a => a.userId === userId)
  );
}
function getPersonalStatus(task, userId) {
  const a = task.assignees.find(a => a.userId === userId);
  return a ? a.personalStatus : null;
}
function getAssigneeData(task, userId) {
  return task.assignees.find(a => a.userId === userId) || null;
}

Object.assign(window, {
  USERS, PROJECTS, TASKS, WORKFLOW_STATUSES, GLOBAL_STATUS_META,
  NOTIFICATIONS, getUserById, getTasksForUser, getPersonalStatus, getAssigneeData,
});
