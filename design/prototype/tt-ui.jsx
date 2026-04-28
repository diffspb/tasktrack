
// ─── Icons ───────────────────────────────────────────────────────────────────
const ICON_PATHS = {
  dashboard:    'M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z',
  kanban:       'M3 3h5v18H3zm7 0h5v12h-5zm7 0h5v15h-5z',
  list:         'M3 6h18M3 12h18M3 18h18',
  bell:         'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 00-5-5.917V4a1 1 0 10-2 0v1.083A6 6 0 006 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9',
  search:       'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
  settings:     'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z',
  users:        'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z',
  plus:         'M12 4v16m-8-8h16',
  x:            'M18 6L6 18M6 6l12 12',
  check:        'M5 13l4 4L19 7',
  chevronDown:  'M6 9l6 6 6-6',
  chevronRight: 'M9 18l6-6-6-6',
  chevronLeft:  'M15 18l-6-6 6-6',
  more:         'M5 12h.01M12 12h.01M19 12h.01',
  flag:         'M3 21V5l9-2 9 2v10l-9 2-9-2',
  tag:          'M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z',
  clock:        'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
  paperclip:    'M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13',
  message:      'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
  arrowRight:   'M13 7l5 5m0 0l-5 5m5-5H6',
  zap:          'M13 10V3L4 14h7v7l9-11h-7z',
  award:        'M12 15l-2 5-3-3-5 2 2-5M12 15l2 5 3-3 5 2-2-5M12 15V3m0 0l3 3m-3-3L9 6',
  link:         'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1',
  filter:       'M3 4h18M7 8h10M11 12h2M13 16h-2',
  backlog:      'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 5h6',
  eye:          'M15 12a3 3 0 11-6 0 3 3 0 016 0zm-3-9c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9-4.03-9-9-9z',
  sun:          'M12 3v1m0 16v1m8.66-13l-.87.5m-15.58 9l-.87.5M20.66 17l-.87-.5m-15.58-9l-.87-.5M21 12h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 7a5 5 0 110 10A5 5 0 0112 7z',
  moon:         'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z',
  history:      'M12 8v4l3 3M3.05 11a9 9 0 101.8-4.9L3 12M3 7v4h4',
};

function Icon({ name, size = 16, stroke = 'currentColor', fill = 'none', strokeWidth = 1.8, style = {} }) {
  const d = ICON_PATHS[name] || '';
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke}
      strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
      style={{ flexShrink: 0, ...style }}>
      <path d={d} />
    </svg>
  );
}

// ─── Avatar ───────────────────────────────────────────────────────────────────
function Avatar({ userId, size = 24, showTooltip = false }) {
  const user = getUserById(userId);
  if (!user) return null;
  const fs = Math.round(size * 0.38);
  return (
    <div title={showTooltip ? user.name : undefined}
      style={{
        width: size, height: size, borderRadius: '50%',
        background: user.color, color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: fs, fontWeight: 600, flexShrink: 0, letterSpacing: '-0.02em',
        border: '1.5px solid var(--bg-card)',
      }}>
      {user.initials}
    </div>
  );
}

function AvatarStack({ userIds, size = 22, max = 3 }) {
  const shown = userIds.slice(0, max);
  const rest = userIds.length - max;
  return (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      {shown.map((uid, i) => (
        <div key={uid} style={{ marginLeft: i === 0 ? 0 : -6, zIndex: shown.length - i }}>
          <Avatar userId={uid} size={size} showTooltip />
        </div>
      ))}
      {rest > 0 && (
        <div style={{
          width: size, height: size, borderRadius: '50%',
          background: 'var(--bg-muted)', color: 'var(--fg-muted)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: Math.round(size * 0.36), fontWeight: 600,
          marginLeft: -6, border: '1.5px solid var(--bg-card)',
        }}>+{rest}</div>
      )}
    </div>
  );
}

// ─── Priority ────────────────────────────────────────────────────────────────
const PRIORITY_META = {
  critical: { label: 'Critical', color: 'oklch(0.50 0.20 25)'  },
  high:     { label: 'High',     color: 'oklch(0.58 0.17 35)'  },
  medium:   { label: 'Medium',   color: 'oklch(0.62 0.14 60)'  },
  low:      { label: 'Low',      color: 'oklch(0.55 0.10 240)' },
};

function PriorityDot({ priority, size = 8 }) {
  const m = PRIORITY_META[priority] || PRIORITY_META.low;
  return <div style={{ width: size, height: size, borderRadius: '50%', background: m.color, flexShrink: 0 }} title={m.label} />;
}

function PriorityBadge({ priority }) {
  const m = PRIORITY_META[priority] || PRIORITY_META.low;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 11, fontWeight: 500, color: m.color,
      background: m.color + '18', borderRadius: 3, padding: '2px 6px',
    }}>
      <PriorityDot priority={priority} size={6} />
      {m.label}
    </span>
  );
}

// ─── Type Badge ──────────────────────────────────────────────────────────────
const TYPE_META = {
  feature: { label: 'Feature', color: 'oklch(0.50 0.14 252)', bg: 'oklch(0.93 0.05 252)' },
  task:    { label: 'Task',    color: 'oklch(0.45 0.01 240)', bg: 'oklch(0.92 0.01 240)' },
  bug:     { label: 'Bug',     color: 'oklch(0.50 0.18 25)',  bg: 'oklch(0.94 0.05 25)'  },
};

function TypeBadge({ type }) {
  const m = TYPE_META[type] || TYPE_META.task;
  return (
    <span style={{
      fontSize: 11, fontWeight: 500, color: m.color, background: m.bg,
      borderRadius: 3, padding: '2px 6px',
    }}>{m.label}</span>
  );
}

// ─── Global Status Badge ─────────────────────────────────────────────────────
function GlobalStatusBadge({ status, size = 'md' }) {
  const m = GLOBAL_STATUS_META[status] || {};
  const pad = size === 'lg' ? '4px 10px' : '2px 8px';
  const fs = size === 'lg' ? 12 : 11;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: fs, fontWeight: 600, color: m.color, background: m.bg,
      borderRadius: 4, padding: pad, letterSpacing: '0.01em',
    }}>
      <div style={{ width: 6, height: 6, borderRadius: '50%', background: m.color }} />
      {m.label}
    </span>
  );
}

// ─── Role Badge ──────────────────────────────────────────────────────────────
const ROLE_META = {
  lead:       { label: 'Lead',       color: 'oklch(0.48 0.14 252)', bg: 'oklch(0.93 0.05 252)' },
  reviewer:   { label: 'Reviewer',   color: 'oklch(0.48 0.10 200)', bg: 'oklch(0.93 0.04 200)' },
  consultant: { label: 'Consultant', color: 'oklch(0.50 0.08 150)', bg: 'oklch(0.94 0.03 150)' },
};

function RoleBadge({ role }) {
  const m = ROLE_META[role] || {};
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, color: m.color, background: m.bg,
      borderRadius: 3, padding: '1px 5px', letterSpacing: '0.03em', textTransform: 'uppercase',
    }}>{m.label}</span>
  );
}

// ─── Personal Status Badge ───────────────────────────────────────────────────
const PS_META = {
  todo:        { label: 'To Do',      color: 'var(--fg-muted)',       bg: 'var(--bg-muted)' },
  in_progress: { label: 'In Progress', color: 'oklch(0.48 0.14 200)', bg: 'oklch(0.93 0.04 200)' },
  in_review:   { label: 'In Review',  color: 'oklch(0.50 0.12 252)', bg: 'oklch(0.93 0.05 252)' },
  done:        { label: 'Done',       color: 'oklch(0.45 0.14 150)', bg: 'oklch(0.93 0.06 150)' },
};

function PersonalStatusBadge({ status }) {
  const m = PS_META[status] || {};
  return (
    <span style={{
      fontSize: 11, fontWeight: 500, color: m.color, background: m.bg,
      borderRadius: 3, padding: '2px 7px',
    }}>{m.label || status}</span>
  );
}

// ─── Solution Status Badge ───────────────────────────────────────────────────
const SS_META = {
  draft:              { label: 'Draft',      color: 'var(--fg-muted)', bg: 'var(--bg-muted)' },
  submitted:          { label: 'Submitted',  color: 'oklch(0.48 0.14 252)', bg: 'oklch(0.93 0.05 252)' },
  accepted:           { label: 'Accepted',   color: 'oklch(0.45 0.14 150)', bg: 'oklch(0.93 0.06 150)' },
  revision_requested: { label: 'Needs Revision', color: 'oklch(0.50 0.15 25)',  bg: 'oklch(0.94 0.05 25)'  },
  rejected:           { label: 'Rejected',   color: 'oklch(0.45 0.01 240)', bg: 'oklch(0.92 0.01 240)' },
};

function SolutionStatusBadge({ status }) {
  const m = SS_META[status] || {};
  return (
    <span style={{
      fontSize: 11, fontWeight: 500, color: m.color, background: m.bg,
      borderRadius: 3, padding: '2px 7px',
    }}>{m.label}</span>
  );
}

// ─── Label Tag ───────────────────────────────────────────────────────────────
function LabelTag({ label }) {
  return (
    <span style={{
      fontSize: 11, color: 'var(--fg-muted)', background: 'var(--bg-muted)',
      borderRadius: 3, padding: '1px 6px', border: '1px solid var(--border)',
    }}>{label}</span>
  );
}

// ─── Button ──────────────────────────────────────────────────────────────────
function Btn({ children, variant = 'default', size = 'md', onClick, disabled, style = {}, title }) {
  const base = {
    display: 'inline-flex', alignItems: 'center', gap: 6, cursor: disabled ? 'not-allowed' : 'pointer',
    border: 'none', borderRadius: 6, fontFamily: 'inherit', fontWeight: 500,
    transition: 'background 0.15s, opacity 0.15s', opacity: disabled ? 0.5 : 1,
    fontSize: size === 'sm' ? 12 : size === 'lg' ? 14 : 13,
    padding: size === 'sm' ? '4px 10px' : size === 'lg' ? '8px 16px' : '6px 12px',
  };
  const variants = {
    default:    { background: 'var(--primary)', color: 'var(--primary-fg)' },
    secondary:  { background: 'var(--bg-muted)', color: 'var(--fg)', border: '1px solid var(--border)' },
    ghost:      { background: 'transparent', color: 'var(--fg-muted)' },
    danger:     { background: 'oklch(0.95 0.04 25)', color: 'oklch(0.45 0.18 25)', border: '1px solid oklch(0.88 0.06 25)' },
    success:    { background: 'oklch(0.94 0.06 150)', color: 'oklch(0.40 0.14 150)', border: '1px solid oklch(0.86 0.08 150)' },
  };
  return (
    <button onClick={onClick} disabled={disabled} title={title}
      style={{ ...base, ...variants[variant], ...style }}>
      {children}
    </button>
  );
}

// ─── Divider ─────────────────────────────────────────────────────────────────
function Divider({ style = {} }) {
  return <div style={{ height: 1, background: 'var(--border)', ...style }} />;
}

// ─── Empty State ─────────────────────────────────────────────────────────────
function EmptyCol({ label }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
      padding: '32px 16px', color: 'var(--fg-subtle)', fontSize: 12,
    }}>
      <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--bg-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon name="kanban" size={16} stroke="var(--fg-subtle)" />
      </div>
      No tasks
    </div>
  );
}

Object.assign(window, {
  Icon, Avatar, AvatarStack,
  PriorityDot, PriorityBadge, TypeBadge,
  GlobalStatusBadge, RoleBadge, PersonalStatusBadge,
  SolutionStatusBadge, LabelTag, Btn, Divider, EmptyCol,
  PRIORITY_META, TYPE_META, ROLE_META, PS_META, SS_META,
});
