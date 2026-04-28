
// ─── Task Card ────────────────────────────────────────────────────────────────
function TaskCard({ task, currentUserId, onClick, isDragging, onDragStart, onDragEnd }) {
  const leadIds = task.assignees.filter(a => a.role === 'lead').map(a => a.userId);
  const isMulti = leadIds.length > 1;
  const prioMeta = PRIORITY_META[task.priority] || {};

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={() => onClick(task)}
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: '10px 12px',
        cursor: isDragging ? 'grabbing' : 'grab',
        transition: isDragging ? 'none' : 'box-shadow 0.15s, border-color 0.15s, opacity 0.15s',
        position: 'relative',
        overflow: 'hidden',
        opacity: isDragging ? 0.45 : 1,
        userSelect: 'none',
      }}
      onMouseEnter={e => {
        if (!isDragging) {
          e.currentTarget.style.boxShadow = 'var(--shadow)';
          e.currentTarget.style.borderColor = 'var(--border-focus)';
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.borderColor = 'var(--border)';
      }}
    >
      {/* Priority strip */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0, width: 3,
        background: prioMeta.color, borderRadius: '8px 0 0 8px',
      }} />

      {/* Top row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, paddingLeft: 4 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-subtle)', letterSpacing: '0.02em', fontFamily: 'monospace' }}>
          {task.key}
        </span>
        <TypeBadge type={task.type} />
        <div style={{ flex: 1 }} />
        <GlobalStatusBadge status={task.globalStatus} />
      </div>

      {/* Title */}
      <div style={{
        fontSize: 13, fontWeight: 500, color: 'var(--fg)',
        lineHeight: 1.4, marginBottom: 8, paddingLeft: 4,
        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
      }}>
        {task.title}
      </div>

      {/* Labels */}
      {task.labels.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8, paddingLeft: 4 }}>
          {task.labels.slice(0, 3).map(l => <LabelTag key={l} label={l} />)}
        </div>
      )}

      {/* Multi-assignee progress */}
      {isMulti && (() => {
        const leads = task.assignees.filter(a => a.role === 'lead');
        const submitted = leads.filter(a => ['submitted','accepted'].includes(a.solutionStatus)).length;
        const pct = Math.round((submitted / leads.length) * 100);
        return (
          <div style={{ marginBottom: 8, paddingLeft: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--fg-subtle)', marginBottom: 3 }}>
              <span>Solutions</span><span>{submitted}/{leads.length}</span>
            </div>
            <div style={{ height: 3, background: 'var(--bg-muted)', borderRadius: 2 }}>
              <div style={{ height: 3, background: 'var(--primary)', borderRadius: 2, width: pct + '%' }} />
            </div>
          </div>
        );
      })()}

      {/* Bottom row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 4 }}>
        <AvatarStack userIds={leadIds} size={20} max={4} />
        {task.assignees.some(a => a.role !== 'lead') && (
          <span style={{ fontSize: 10, color: 'var(--fg-subtle)' }}>
            +{task.assignees.filter(a => a.role !== 'lead').length} reviewer
          </span>
        )}
        <div style={{ flex: 1 }} />
        {task.dueDate && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: 'var(--fg-subtle)' }}>
            <Icon name="clock" size={11} stroke="var(--fg-subtle)" />
            {new Date(task.dueDate).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
          </span>
        )}
        {task.comments.length > 0 && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: 'var(--fg-subtle)' }}>
            <Icon name="message" size={11} stroke="var(--fg-subtle)" />
            {task.comments.length}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Drop Placeholder ─────────────────────────────────────────────────────────
function DropPlaceholder() {
  return (
    <div style={{
      border: '2px dashed var(--primary)',
      borderRadius: 8, height: 80,
      background: 'oklch(0.94 0.05 252 / 0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 500, opacity: 0.8 }}>Drop here</span>
    </div>
  );
}

// ─── Kanban Column ────────────────────────────────────────────────────────────
function KanbanColumn({ status, tasks, currentUserId, onTaskClick, onCreateTask,
  draggedId, dragOverCol, onDragStart, onDragEnd, onDragOver, onDragLeave, onDrop }) {

  const catColors = { todo: 'var(--fg-subtle)', active: 'var(--primary)', done: 'oklch(0.45 0.14 150)' };
  const dotColor = catColors[status.category] || 'var(--fg-subtle)';
  const isOver = dragOverCol === status.id;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: 280, minWidth: 280, flexShrink: 0 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 4px 10px' }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: dotColor }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
          {status.label}
        </span>
        <span style={{
          fontSize: 11, fontWeight: 600, color: 'var(--fg-subtle)',
          background: 'var(--bg-muted)', borderRadius: 10, padding: '1px 7px',
        }}>{tasks.length}</span>
        <div style={{ flex: 1 }} />
        <button onClick={onCreateTask}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--fg-subtle)', padding: 2, borderRadius: 4, display: 'flex', alignItems: 'center' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-hover)'; e.currentTarget.style.color = 'var(--fg)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = 'var(--fg-subtle)'; }}
        >
          <Icon name="plus" size={14} />
        </button>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        style={{
          flex: 1, background: isOver ? 'oklch(0.94 0.05 252 / 0.3)' : 'var(--bg-muted)',
          borderRadius: 10, padding: 8, minHeight: 120,
          display: 'flex', flexDirection: 'column', gap: 8,
          border: isOver ? '2px solid oklch(0.75 0.10 252)' : '2px solid transparent',
          transition: 'background 0.15s, border-color 0.15s',
        }}
      >
        {tasks.length === 0 && !isOver && <EmptyCol />}
        {tasks.map(task => (
          <TaskCard
            key={task.id}
            task={task}
            currentUserId={currentUserId}
            onClick={onTaskClick}
            isDragging={draggedId === task.id}
            onDragStart={() => onDragStart(task.id)}
            onDragEnd={onDragEnd}
          />
        ))}
        {isOver && draggedId && !tasks.find(t => t.id === draggedId) && (
          <DropPlaceholder />
        )}
      </div>
    </div>
  );
}

// ─── Kanban Board ─────────────────────────────────────────────────────────────
function KanbanBoard({ project, currentUserId, onTaskClick, onCreateTask }) {
  const baseTasks = React.useMemo(
    () => getTasksForUser(currentUserId, project.id),
    [currentUserId, project.id]
  );

  // Mutable personal status map (taskId → statusId)
  const [statusMap, setStatusMap] = React.useState(() => {
    const m = {};
    baseTasks.forEach(t => {
      const a = t.assignees.find(a => a.userId === currentUserId);
      if (a?.personalStatus) m[t.id] = a.personalStatus;
    });
    return m;
  });

  // Reset when user/project changes
  React.useEffect(() => {
    const m = {};
    baseTasks.forEach(t => {
      const a = t.assignees.find(a => a.userId === currentUserId);
      if (a?.personalStatus) m[t.id] = a.personalStatus;
    });
    setStatusMap(m);
  }, [currentUserId, project.id]);

  // DnD state
  const [draggedId, setDraggedId]   = React.useState(null);
  const [dragOverCol, setDragOverCol] = React.useState(null);

  function handleDragStart(taskId) {
    setDraggedId(taskId);
  }
  function handleDragEnd() {
    setDraggedId(null);
    setDragOverCol(null);
  }
  function handleDragOver(e, statusId) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverCol(statusId);
  }
  function handleDragLeave(e, statusId) {
    // Only clear if leaving the column entirely (not moving between child elements)
    const rect = e.currentTarget.getBoundingClientRect();
    const { clientX: x, clientY: y } = e;
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      setDragOverCol(null);
    }
  }
  function handleDrop(statusId) {
    if (draggedId) {
      setStatusMap(m => ({ ...m, [draggedId]: statusId }));
    }
    setDraggedId(null);
    setDragOverCol(null);
  }

  const columns = WORKFLOW_STATUSES.map(status => ({
    status,
    tasks: baseTasks.filter(t => statusMap[t.id] === status.id),
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '12px 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg)',
      }}>
        <span style={{ fontSize: 13, color: 'var(--fg-muted)' }}>
          Showing <strong style={{ color: 'var(--fg)' }}>my tasks</strong> — personal workflow view
        </span>
        {draggedId && (
          <span style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 5 }}>
            <Icon name="arrowRight" size={13} stroke="var(--primary)" /> Drag to move between columns
          </span>
        )}
        <div style={{ flex: 1 }} />
        <Btn variant="ghost" size="sm"><Icon name="filter" size={13} /> Filter</Btn>
        <Btn variant="default" size="sm" onClick={onCreateTask}><Icon name="plus" size={13} /> Create task</Btn>
      </div>

      {/* Columns */}
      <div style={{
        flex: 1, overflowX: 'auto', overflowY: 'hidden',
        padding: '20px', display: 'flex', gap: 16, alignItems: 'flex-start',
      }}>
        {columns.map(({ status, tasks }) => (
          <KanbanColumn
            key={status.id}
            status={status}
            tasks={tasks}
            currentUserId={currentUserId}
            onTaskClick={onTaskClick}
            onCreateTask={onCreateTask}
            draggedId={draggedId}
            dragOverCol={dragOverCol}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragOver={e => handleDragOver(e, status.id)}
            onDragLeave={e => handleDragLeave(e, status.id)}
            onDrop={() => handleDrop(status.id)}
          />
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { KanbanBoard, TaskCard, KanbanColumn });
