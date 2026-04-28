
// ─── Filter Chip ──────────────────────────────────────────────────────────────
function FilterChip({ label, value, options, onChange }) {
  const [open, setOpen] = React.useState(false);
  const active = value !== 'all';
  return (
    <div style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px',
        border: `1.5px solid ${active ? 'var(--primary)' : 'var(--border)'}`,
        borderRadius: 20, background: active ? 'oklch(0.94 0.05 252)' : 'var(--bg)',
        color: active ? 'var(--primary)' : 'var(--fg-muted)',
        fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
        transition: 'all 0.15s',
      }}>
        {label}{active && `: ${options.find(o => o.value === value)?.label || value}`}
        <Icon name="chevronDown" size={11} stroke="currentColor" />
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 50 }} />
          <div style={{
            position: 'absolute', top: 'calc(100% + 4px)', left: 0, zIndex: 51,
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 8, boxShadow: 'var(--shadow)', minWidth: 160, overflow: 'hidden',
          }}>
            {options.map(opt => (
              <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  width: '100%', padding: '7px 12px', border: 'none', background: 'none',
                  cursor: 'pointer', fontFamily: 'inherit', fontSize: 12,
                  color: value === opt.value ? 'var(--primary)' : 'var(--fg)',
                  fontWeight: value === opt.value ? 600 : 400,
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-muted)'}
                onMouseLeave={e => e.currentTarget.style.background = 'none'}
              >
                {opt.label}
                {value === opt.value && <Icon name="check" size={12} stroke="var(--primary)" />}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Sortable Column Header ───────────────────────────────────────────────────
function SortableHeader({ label, field, sortField, sortDir, onSort, style = {} }) {
  const active = sortField === field;
  return (
    <th onClick={() => onSort(field)}
      style={{
        padding: '9px 12px', textAlign: 'left', fontSize: 11, fontWeight: 600,
        color: active ? 'var(--primary)' : 'var(--fg-muted)',
        letterSpacing: '0.04em', textTransform: 'uppercase', cursor: 'pointer',
        userSelect: 'none', whiteSpace: 'nowrap', ...style,
      }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {label}
        {active && <Icon name={sortDir === 'asc' ? 'chevronDown' : 'chevronRight'} size={11} stroke="var(--primary)" style={{ transform: sortDir === 'asc' ? 'rotate(0deg)' : 'rotate(-90deg)' }} />}
      </div>
    </th>
  );
}

// ─── Backlog Row ──────────────────────────────────────────────────────────────
function BacklogRow({ task, currentUserId, onTaskClick }) {
  const [hovered, setHovered] = React.useState(false);
  const leadIds = task.assignees.filter(a => a.role === 'lead').map(a => a.userId);
  const myAssignee = task.assignees.find(a => a.userId === currentUserId);

  return (
    <tr
      onClick={() => onTaskClick(task)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? 'var(--bg-muted)' : 'transparent',
        cursor: 'pointer', transition: 'background 0.1s',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      {/* Priority */}
      <td style={{ padding: '7px 12px', width: 32 }}>
        <PriorityDot priority={task.priority} size={9} />
      </td>

      {/* Key */}
      <td style={{ padding: '7px 12px', whiteSpace: 'nowrap' }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-subtle)', fontFamily: 'monospace' }}>
          {task.key}
        </span>
      </td>

      {/* Title + labels — single line */}
      <td style={{ padding: '7px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
          <TypeBadge type={task.type} />
          <span style={{
            fontSize: 13, color: 'var(--fg)', fontWeight: 500,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            flex: '1 1 0', minWidth: 0,
          }}>{task.title}</span>
          {task.labels.slice(0, 3).map(l => <LabelTag key={l} label={l} />)}
        </div>
      </td>

      {/* Global status */}
      <td style={{ padding: '7px 12px', whiteSpace: 'nowrap' }}>
        <GlobalStatusBadge status={task.globalStatus} />
      </td>

      {/* My status (if assigned) */}
      <td style={{ padding: '7px 12px', whiteSpace: 'nowrap' }}>
        {myAssignee?.personalStatus
          ? <PersonalStatusBadge status={myAssignee.personalStatus} />
          : <span style={{ fontSize: 12, color: 'var(--fg-subtle)' }}>—</span>
        }
      </td>

      {/* Assignees */}
      <td style={{ padding: '7px 12px' }}>
        <AvatarStack userIds={leadIds} size={22} max={3} />
      </td>

      {/* Due date */}
      <td style={{ padding: '7px 12px', whiteSpace: 'nowrap' }}>
        {task.dueDate
          ? <span style={{ fontSize: 12, color: 'var(--fg-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Icon name="clock" size={12} stroke="var(--fg-subtle)" />
              {new Date(task.dueDate).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
            </span>
          : <span style={{ fontSize: 12, color: 'var(--fg-subtle)' }}>—</span>
        }
      </td>

      {/* Comments */}
      <td style={{ padding: '7px 12px', whiteSpace: 'nowrap' }}>
        {task.comments.length > 0
          ? <span style={{ fontSize: 12, color: 'var(--fg-subtle)', display: 'flex', alignItems: 'center', gap: 3 }}>
              <Icon name="message" size={12} stroke="var(--fg-subtle)" />
              {task.comments.length}
            </span>
          : null
        }
      </td>
    </tr>
  );
}

// ─── Backlog View ─────────────────────────────────────────────────────────────
function BacklogView({ project, currentUserId, onTaskClick, onCreateTask }) {
  const allTasks = TASKS.filter(t => t.projectId === project.id);

  const [search, setSearch]         = React.useState('');
  const [filterStatus, setFStatus]  = React.useState('all');
  const [filterPriority, setFPrio]  = React.useState('all');
  const [filterType, setFType]      = React.useState('all');
  const [filterAssignee, setFUser]  = React.useState('all');
  const [sortField, setSortField]   = React.useState('key');
  const [sortDir, setSortDir]       = React.useState('asc');

  function handleSort(field) {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('asc'); }
  }

  const statusOptions = [
    { value: 'all', label: 'All statuses' },
    ...Object.entries(GLOBAL_STATUS_META).map(([k, m]) => ({ value: k, label: m.label })),
  ];
  const priorityOptions = [
    { value: 'all', label: 'All priorities' },
    ...Object.entries(PRIORITY_META).map(([k, m]) => ({ value: k, label: m.label })),
  ];
  const typeOptions = [
    { value: 'all', label: 'All types' },
    ...Object.entries(TYPE_META).map(([k, m]) => ({ value: k, label: m.label })),
  ];
  const assigneeOptions = [
    { value: 'all', label: 'All assignees' },
    { value: 'me', label: 'Assigned to me' },
    ...USERS.map(u => ({ value: u.id, label: u.name })),
  ];

  const activeFilterCount = [filterStatus, filterPriority, filterType, filterAssignee].filter(f => f !== 'all').length;

  // Filter
  let filtered = allTasks.filter(t => {
    if (search && !t.title.toLowerCase().includes(search.toLowerCase()) && !t.key.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterStatus !== 'all' && t.globalStatus !== filterStatus) return false;
    if (filterPriority !== 'all' && t.priority !== filterPriority) return false;
    if (filterType !== 'all' && t.type !== filterType) return false;
    if (filterAssignee === 'me' && !t.assignees.some(a => a.userId === currentUserId)) return false;
    if (filterAssignee !== 'all' && filterAssignee !== 'me' && !t.assignees.some(a => a.userId === filterAssignee)) return false;
    return true;
  });

  // Sort
  filtered = [...filtered].sort((a, b) => {
    let va, vb;
    if (sortField === 'key') { va = parseInt(a.key.split('-')[1]); vb = parseInt(b.key.split('-')[1]); }
    else if (sortField === 'priority') { const o = { critical: 0, high: 1, medium: 2, low: 3 }; va = o[a.priority]; vb = o[b.priority]; }
    else if (sortField === 'status') { va = a.globalStatus; vb = b.globalStatus; }
    else if (sortField === 'due') { va = a.dueDate || 'z'; vb = b.dueDate || 'z'; }
    else { va = a[sortField] || ''; vb = b[sortField] || ''; }
    if (va < vb) return sortDir === 'asc' ? -1 : 1;
    if (va > vb) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  function clearFilters() {
    setSearch(''); setFStatus('all'); setFPrio('all'); setFType('all'); setFUser('all');
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
        padding: '12px 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg)',
        flexShrink: 0,
      }}>
        {/* Search */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--bg-muted)', border: '1.5px solid var(--border)',
          borderRadius: 7, padding: '5px 10px', width: 220,
          transition: 'border-color 0.15s',
        }}>
          <Icon name="search" size={13} stroke="var(--fg-subtle)" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search tasks…"
            style={{
              border: 'none', background: 'none', outline: 'none',
              fontSize: 13, color: 'var(--fg)', width: '100%', fontFamily: 'inherit',
            }} />
          {search && (
            <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--fg-subtle)', display: 'flex', padding: 0 }}>
              <Icon name="x" size={13} />
            </button>
          )}
        </div>

        <FilterChip label="Status"   value={filterStatus}   options={statusOptions}   onChange={setFStatus} />
        <FilterChip label="Priority" value={filterPriority} options={priorityOptions} onChange={setFPrio} />
        <FilterChip label="Type"     value={filterType}     options={typeOptions}     onChange={setFType} />
        <FilterChip label="Assignee" value={filterAssignee} options={assigneeOptions} onChange={setFUser} />

        {activeFilterCount > 0 && (
          <button onClick={clearFilters} style={{
            background: 'none', border: 'none', cursor: 'pointer', fontSize: 12,
            color: 'var(--fg-subtle)', fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <Icon name="x" size={12} /> Clear {activeFilterCount} filter{activeFilterCount > 1 ? 's' : ''}
          </button>
        )}

        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: 'var(--fg-subtle)' }}>{filtered.length} task{filtered.length !== 1 ? 's' : ''}</span>
        <Btn variant="default" size="sm" onClick={onCreateTask}>
          <Icon name="plus" size={13} /> Create task
        </Btn>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {filtered.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 10, color: 'var(--fg-muted)' }}>
            <Icon name="filter" size={28} stroke="var(--border)" />
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg)' }}>No tasks match your filters</div>
            <button onClick={clearFilters} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--primary)', fontSize: 13, fontFamily: 'inherit' }}>Clear filters</button>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ position: 'sticky', top: 0, zIndex: 5, background: 'var(--bg)', borderBottom: '1px solid var(--border)' }}>
              <tr>
                <th style={{ width: 32, padding: '9px 12px' }} />
                <SortableHeader label="Key"      field="key"      sortField={sortField} sortDir={sortDir} onSort={handleSort} style={{ width: 70 }} />
                <SortableHeader label="Title"    field="title"    sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                <SortableHeader label="Status"   field="status"   sortField={sortField} sortDir={sortDir} onSort={handleSort} style={{ width: 160 }} />
                <th style={{ padding: '9px 12px', fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', width: 120, textAlign: 'left' }}>My Status</th>
                <th style={{ padding: '9px 12px', fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', width: 100, textAlign: 'left' }}>Assignees</th>
                <SortableHeader label="Due"      field="due"      sortField={sortField} sortDir={sortDir} onSort={handleSort} style={{ width: 100 }} />
                <th style={{ width: 60, padding: '9px 12px' }} />
              </tr>
            </thead>
            <tbody>
              {filtered.map(task => (
                <BacklogRow
                  key={task.id}
                  task={task}
                  currentUserId={currentUserId}
                  onTaskClick={onTaskClick}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { BacklogView });
