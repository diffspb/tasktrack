
// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, icon, color, sub }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '16px 18px', flex: 1, minWidth: 140,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: color + '18', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={icon} size={14} stroke={color} />
        </div>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--fg)', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--fg-subtle)', marginTop: 5 }}>{sub}</div>}
    </div>
  );
}

// ─── Dashboard Task Row ───────────────────────────────────────────────────────
function DashTaskRow({ task, currentUserId, onClick, showDecisionRole }) {
  const myAssignee = task.assignees.find(a => a.userId === currentUserId);
  const leadIds = task.assignees.filter(a => a.role === 'lead').map(a => a.userId);

  return (
    <div onClick={() => onClick(task)}
      style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
        borderRadius: 8, cursor: 'pointer', transition: 'background 0.12s',
        border: '1px solid transparent',
      }}
      onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-muted)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
      onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; }}
    >
      {/* Priority dot */}
      <PriorityDot priority={task.priority} size={8} />

      {/* Key */}
      <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-subtle)', fontFamily: 'monospace', width: 44, flexShrink: 0 }}>
        {task.key}
      </span>

      {/* Title */}
      <span style={{
        fontSize: 13, color: 'var(--fg)', flex: 1,
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }}>{task.title}</span>

      {/* My role + status */}
      {myAssignee && !showDecisionRole && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <RoleBadge role={myAssignee.role} />
          {myAssignee.personalStatus && <PersonalStatusBadge status={myAssignee.personalStatus} />}
          {myAssignee.solutionStatus && <SolutionStatusBadge status={myAssignee.solutionStatus} />}
        </div>
      )}
      {showDecisionRole && (
        <div style={{ flexShrink: 0 }}>
          <GlobalStatusBadge status={task.globalStatus} />
        </div>
      )}

      {/* Assignee avatars */}
      <AvatarStack userIds={leadIds} size={20} max={3} />

      {/* Due date */}
      {task.dueDate && (
        <span style={{ fontSize: 11, color: 'var(--fg-subtle)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 3 }}>
          <Icon name="clock" size={11} stroke="var(--fg-subtle)" />
          {new Date(task.dueDate).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
        </span>
      )}
    </div>
  );
}

// ─── Dashboard Section ────────────────────────────────────────────────────────
function DashSection({ title, icon, iconColor, tasks, currentUserId, onTaskClick, showDecisionRole, emptyText, accent }) {
  return (
    <div style={{
      background: 'var(--bg-card)', border: `1px solid ${accent || 'var(--border)'}`,
      borderRadius: 10, overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '12px 14px',
        borderBottom: '1px solid var(--border)',
        background: accent ? accent + '10' : 'transparent',
      }}>
        <Icon name={icon} size={14} stroke={iconColor || 'var(--fg-muted)'} />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{title}</span>
        <span style={{
          fontSize: 11, fontWeight: 600, color: iconColor || 'var(--fg-muted)',
          background: (iconColor || 'var(--fg-muted)') + '18',
          borderRadius: 10, padding: '1px 7px',
        }}>{tasks.length}</span>
      </div>

      {/* Rows */}
      <div style={{ padding: '6px 0' }}>
        {tasks.length === 0
          ? <div style={{ padding: '14px 16px', fontSize: 12, color: 'var(--fg-subtle)', fontStyle: 'italic' }}>{emptyText}</div>
          : tasks.map(t => (
              <DashTaskRow
                key={t.id} task={t}
                currentUserId={currentUserId}
                onClick={onTaskClick}
                showDecisionRole={showDecisionRole}
              />
            ))
        }
      </div>
    </div>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
function Dashboard({ currentUserId, onTaskClick, onCreateTask }) {
  const user = getUserById(currentUserId);

  // Compute sections
  const myAssigned = TASKS.filter(t =>
    t.assignees.some(a => a.userId === currentUserId && a.role === 'lead')
  );
  const active = myAssigned.filter(t =>
    ['in_progress', 'in_review'].includes(t.assignees.find(a => a.userId === currentUserId)?.personalStatus)
  );
  const todo = myAssigned.filter(t =>
    t.assignees.find(a => a.userId === currentUserId)?.personalStatus === 'todo'
  );
  const needsRevision = myAssigned.filter(t =>
    t.assignees.find(a => a.userId === currentUserId)?.solutionStatus === 'revision_requested'
  );
  const awaitingDecision = TASKS.filter(t =>
    t.decisionMakerId === currentUserId && t.globalStatus === 'awaiting_decision'
  );
  const watching = TASKS.filter(t =>
    !t.assignees.some(a => a.userId === currentUserId) && t.decisionMakerId !== currentUserId
  ).slice(0, 3);

  // Stats
  const stats = [
    { label: 'My Open Tasks', value: myAssigned.filter(t => !['closed','decided'].includes(t.globalStatus)).length, icon: 'backlog', color: 'var(--primary)', sub: `${active.length} in progress` },
    { label: 'Awaiting Decision', value: awaitingDecision.length, icon: 'award', color: 'oklch(0.50 0.14 55)', sub: awaitingDecision.length > 0 ? 'Action required' : 'All clear' },
    { label: 'Needs Revision', value: needsRevision.length, icon: 'arrowRight', color: 'oklch(0.50 0.15 25)', sub: needsRevision.length > 0 ? 'Feedback received' : 'All submitted' },
    { label: 'Decided This Week', value: TASKS.filter(t => t.globalStatus === 'decided' || t.globalStatus === 'closed').length, icon: 'check', color: 'oklch(0.45 0.14 150)', sub: 'across all projects' },
  ];

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '24px 28px' }}>
      {/* Greeting */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--fg)', marginBottom: 4 }}>
          Good morning, {user?.name.split(' ')[0]} 👋
        </h1>
        <p style={{ fontSize: 13, color: 'var(--fg-muted)' }}>
          Here's what needs your attention today.
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' }}>
        {stats.map(s => <StatCard key={s.label} {...s} />)}
      </div>

      {/* Revision alert */}
      {needsRevision.length > 0 && (
        <div style={{
          background: 'oklch(0.96 0.04 25)', border: '1px solid oklch(0.86 0.08 25)',
          borderRadius: 10, padding: '12px 16px', marginBottom: 20,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: 'oklch(0.50 0.15 25)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Icon name="arrowRight" size={16} stroke="#fff" />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'oklch(0.38 0.15 25)' }}>
              {needsRevision.length} solution{needsRevision.length > 1 ? 's' : ''} sent back for revision
            </div>
            <div style={{ fontSize: 12, color: 'oklch(0.48 0.10 25)' }}>
              Review the feedback and resubmit to continue the Decision Process.
            </div>
          </div>
          <div style={{ flex: 1 }} />
          <Btn variant="danger" size="sm" onClick={() => onTaskClick(needsRevision[0])}>View task</Btn>
        </div>
      )}

      {/* Decision-maker alert */}
      {awaitingDecision.length > 0 && (
        <div style={{
          background: 'oklch(0.96 0.05 55)', border: '1px solid oklch(0.86 0.08 55)',
          borderRadius: 10, padding: '12px 16px', marginBottom: 20,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: 'oklch(0.55 0.14 55)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Icon name="award" size={16} stroke="#fff" />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'oklch(0.38 0.14 55)' }}>
              {awaitingDecision.length} task{awaitingDecision.length > 1 ? 's' : ''} awaiting your Decision
            </div>
            <div style={{ fontSize: 12, color: 'oklch(0.48 0.10 55)' }}>
              All solutions have been submitted. Review and accept or send for revision.
            </div>
          </div>
          <div style={{ flex: 1 }} />
          <Btn variant="secondary" size="sm" onClick={() => onTaskClick(awaitingDecision[0])}>Review</Btn>
        </div>
      )}

      {/* 2-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <DashSection
          title="In Progress" icon="kanban" iconColor="oklch(0.45 0.14 200)"
          accent="oklch(0.45 0.14 200)"
          tasks={active} currentUserId={currentUserId} onTaskClick={onTaskClick}
          emptyText="Nothing in progress — pick something from To Do."
        />
        <DashSection
          title="To Do" icon="list" iconColor="var(--fg-muted)"
          tasks={todo} currentUserId={currentUserId} onTaskClick={onTaskClick}
          emptyText="No tasks queued up."
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <DashSection
          title="Awaiting My Decision" icon="award" iconColor="oklch(0.50 0.14 55)"
          accent="oklch(0.50 0.14 55)"
          tasks={awaitingDecision} currentUserId={currentUserId} onTaskClick={onTaskClick}
          showDecisionRole emptyText="No decisions pending — nice!"
        />
        <DashSection
          title="Needs Revision" icon="arrowRight" iconColor="oklch(0.50 0.15 25)"
          accent={needsRevision.length > 0 ? 'oklch(0.50 0.15 25)' : undefined}
          tasks={needsRevision} currentUserId={currentUserId} onTaskClick={onTaskClick}
          emptyText="All solutions accepted — no revisions needed."
        />
      </div>
    </div>
  );
}

Object.assign(window, { Dashboard });
