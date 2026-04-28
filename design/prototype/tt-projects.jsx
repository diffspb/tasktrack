
// ─── Mock extended project data ───────────────────────────────────────────────
const PROJECT_MEMBERS = {
  p1: [
    { userId: 'u5', role: 'manager', joinedAt: '2024-12-01' },
    { userId: 'u1', role: 'member',  joinedAt: '2024-12-05' },
    { userId: 'u2', role: 'member',  joinedAt: '2024-12-05' },
    { userId: 'u3', role: 'member',  joinedAt: '2024-12-05' },
    { userId: 'u4', role: 'member',  joinedAt: '2024-12-10' },
  ],
  p2: [
    { userId: 'u5', role: 'manager', joinedAt: '2024-11-01' },
    { userId: 'u3', role: 'member',  joinedAt: '2024-11-15' },
  ],
  p3: [
    { userId: 'u2', role: 'manager', joinedAt: '2024-10-01' },
    { userId: 'u4', role: 'member',  joinedAt: '2024-10-15' },
    { userId: 'u1', role: 'viewer',  joinedAt: '2024-11-01' },
  ],
};

const PROJECT_META = {
  p1: { visibility: 'restricted', createdAt: '2024-12-01', ownerId: 'u5' },
  p2: { visibility: 'private',    createdAt: '2024-11-01', ownerId: 'u5' },
  p3: { visibility: 'public',     createdAt: '2024-10-01', ownerId: 'u2' },
};

const VISIBILITY_META = {
  public:     { label: 'Public',     icon: 'eye',    color: 'oklch(0.45 0.14 150)', bg: 'oklch(0.93 0.06 150)', desc: 'All members of the instance can see this project' },
  restricted: { label: 'Restricted', icon: 'users',  color: 'oklch(0.50 0.14 55)',  bg: 'oklch(0.95 0.05 55)',  desc: 'Only invited users and groups can see this project' },
  private:    { label: 'Private',    icon: 'x',      color: 'oklch(0.50 0.15 25)',  bg: 'oklch(0.95 0.05 25)',  desc: 'Only project members can see this project' },
};

const PROJECT_ROLE_META = {
  manager: { label: 'Manager', color: 'oklch(0.48 0.14 252)', bg: 'oklch(0.93 0.05 252)' },
  member:  { label: 'Member',  color: 'oklch(0.45 0.01 240)', bg: 'oklch(0.92 0.01 240)' },
  viewer:  { label: 'Viewer',  color: 'oklch(0.50 0.08 240)', bg: 'oklch(0.93 0.03 240)' },
};

// ─── Visibility Badge ─────────────────────────────────────────────────────────
function VisibilityBadge({ visibility }) {
  const m = VISIBILITY_META[visibility] || {};
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 11, fontWeight: 500, color: m.color, background: m.bg,
      borderRadius: 4, padding: '2px 7px',
    }}>
      <Icon name={m.icon} size={11} stroke={m.color} />
      {m.label}
    </span>
  );
}

// ─── Project Card ─────────────────────────────────────────────────────────────
function ProjectCard({ project, currentUserId, onOpen, onSettings }) {
  const meta    = PROJECT_META[project.id] || {};
  const members = PROJECT_MEMBERS[project.id] || [];
  const taskCount = TASKS.filter(t => t.projectId === project.id).length;
  const activeCount = TASKS.filter(t => t.projectId === project.id && !['closed','decided'].includes(t.globalStatus)).length;
  const myRole  = members.find(m => m.userId === currentUserId)?.role;
  const [hovered, setHovered] = React.useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 12, overflow: 'hidden',
        boxShadow: hovered ? 'var(--shadow)' : 'var(--shadow-sm)',
        transition: 'box-shadow 0.15s, border-color 0.15s',
        borderColor: hovered ? 'var(--border-focus)' : 'var(--border)',
        display: 'flex', flexDirection: 'column',
      }}
    >
      {/* Colour bar */}
      <div style={{ height: 4, background: project.color }} />

      {/* Body */}
      <div style={{ padding: '16px 18px', flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 9, background: project.color,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 800, color: '#fff', flexShrink: 0, letterSpacing: '0.01em',
          }}>{project.key}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--fg)', marginBottom: 2 }}>{project.name}</div>
            <div style={{ fontSize: 12, color: 'var(--fg-subtle)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {project.description}
            </div>
          </div>
          {hovered && (
            <button onClick={e => { e.stopPropagation(); onSettings(project); }}
              style={{ background: 'none', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', color: 'var(--fg-muted)', display: 'flex', alignItems: 'center', flexShrink: 0 }}>
              <Icon name="settings" size={13} />
            </button>
          )}
        </div>

        {/* Stats row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--fg)' }}>{activeCount}</span>
            <span style={{ fontSize: 10, color: 'var(--fg-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Active</span>
          </div>
          <div style={{ width: 1, height: 28, background: 'var(--border)' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--fg)' }}>{taskCount}</span>
            <span style={{ fontSize: 10, color: 'var(--fg-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Total</span>
          </div>
          <div style={{ width: 1, height: 28, background: 'var(--border)' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--fg)' }}>{members.length}</span>
            <span style={{ fontSize: 10, color: 'var(--fg-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Members</span>
          </div>
        </div>

        {/* Members + visibility */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <AvatarStack userIds={members.map(m => m.userId)} size={22} max={5} />
          <div style={{ flex: 1 }} />
          <VisibilityBadge visibility={meta.visibility} />
          {myRole && (
            <span style={{
              fontSize: 10, fontWeight: 600, color: PROJECT_ROLE_META[myRole]?.color,
              background: PROJECT_ROLE_META[myRole]?.bg, borderRadius: 3, padding: '2px 6px',
              textTransform: 'uppercase', letterSpacing: '0.04em',
            }}>{PROJECT_ROLE_META[myRole]?.label}</span>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{
        display: 'flex', gap: 8, padding: '10px 18px',
        borderTop: '1px solid var(--border)', background: 'var(--bg-muted)',
      }}>
        <Btn variant="default" size="sm" style={{ flex: 1, justifyContent: 'center' }} onClick={() => onOpen(project)}>
          <Icon name="kanban" size={13} /> Open Board
        </Btn>
        <Btn variant="secondary" size="sm" onClick={() => onSettings(project)}>
          <Icon name="settings" size={13} />
        </Btn>
      </div>
    </div>
  );
}

// ─── Create Project Modal ─────────────────────────────────────────────────────
function CreateProjectModal({ onClose }) {
  const [name, setName]       = React.useState('');
  const [key, setKey]         = React.useState('');
  const [desc, setDesc]       = React.useState('');
  const [vis, setVis]         = React.useState('restricted');
  const [color, setColor]     = React.useState(PROJECTS[0].color);
  const colors = ['oklch(0.52 0.16 252)', 'oklch(0.52 0.16 160)', 'oklch(0.52 0.16 340)', 'oklch(0.52 0.16 30)', 'oklch(0.52 0.16 60)', 'oklch(0.45 0.01 240)'];

  // Auto-generate key from name
  React.useEffect(() => {
    if (name) setKey(name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 4));
  }, [name]);

  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 300, background: 'oklch(0 0 0 / 0.35)' }} />
      <div style={{
        position: 'fixed', zIndex: 301, top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
        width: 480, background: 'var(--bg-card)', borderRadius: 12,
        border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--fg)' }}>Create Project</span>
          <div style={{ flex: 1 }} />
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--fg-muted)', display: 'flex' }}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Color picker */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 44, height: 44, borderRadius: 10, background: color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 800, color: '#fff' }}>
              {key || '?'}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {colors.map(c => (
                <button key={c} onClick={() => setColor(c)} style={{
                  width: 22, height: 22, borderRadius: '50%', background: c, border: 'none', cursor: 'pointer',
                  outline: color === c ? `3px solid ${c}` : 'none', outlineOffset: 2,
                }} />
              ))}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 12 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)' }}>Project name <span style={{ color: 'oklch(0.50 0.15 25)' }}>*</span></label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Mobile App"
                style={{ padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7, background: 'var(--bg)', color: 'var(--fg)', fontSize: 13, fontFamily: 'inherit', outline: 'none' }} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)' }}>Key <span style={{ color: 'oklch(0.50 0.15 25)' }}>*</span></label>
              <input value={key} onChange={e => setKey(e.target.value.toUpperCase().slice(0, 4))} placeholder="MA"
                style={{ padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7, background: 'var(--bg)', color: 'var(--fg)', fontSize: 13, fontFamily: 'monospace', fontWeight: 700, outline: 'none' }} />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)' }}>Description</label>
            <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={3} placeholder="What is this project about?"
              style={{ padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7, background: 'var(--bg)', color: 'var(--fg)', fontSize: 13, fontFamily: 'inherit', resize: 'vertical', outline: 'none' }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)' }}>Visibility</label>
            {Object.entries(VISIBILITY_META).map(([k, m]) => (
              <div key={k} onClick={() => setVis(k)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
                  border: `1.5px solid ${vis === k ? m.color : 'var(--border)'}`,
                  borderRadius: 8, cursor: 'pointer', background: vis === k ? m.bg + '60' : 'transparent',
                  transition: 'all 0.15s',
                }}>
                <div style={{ width: 30, height: 30, borderRadius: 7, background: m.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon name={m.icon} size={14} stroke={m.color} />
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{m.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--fg-subtle)' }}>{m.desc}</div>
                </div>
                {vis === k && <Icon name="check" size={16} stroke={m.color} style={{ marginLeft: 'auto' }} />}
              </div>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', padding: '14px 20px', borderTop: '1px solid var(--border)', background: 'var(--bg)' }}>
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn variant="default" onClick={onClose} disabled={!name.trim() || !key.trim()}>
            <Icon name="check" size={13} /> Create Project
          </Btn>
        </div>
      </div>
    </>
  );
}

// ─── Projects Overview ────────────────────────────────────────────────────────
function ProjectsOverview({ currentUserId, onOpenProject, onOpenSettings }) {
  const [search, setSearch]     = React.useState('');
  const [createOpen, setCreate] = React.useState(false);

  const filtered = PROJECTS.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.key.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '28px 32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--fg)', marginBottom: 2 }}>Projects</h1>
          <p style={{ fontSize: 13, color: 'var(--fg-muted)' }}>{PROJECTS.length} projects in this instance</p>
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ display: 'flex', gap: 8 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'var(--bg-muted)', border: '1.5px solid var(--border)',
            borderRadius: 7, padding: '6px 10px', width: 200,
          }}>
            <Icon name="search" size={13} stroke="var(--fg-subtle)" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search projects…"
              style={{ border: 'none', background: 'none', outline: 'none', fontSize: 13, color: 'var(--fg)', width: '100%', fontFamily: 'inherit' }} />
          </div>
          <Btn variant="default" onClick={() => setCreate(true)}>
            <Icon name="plus" size={13} /> Create project
          </Btn>
        </div>
      </div>

      {/* Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
        {filtered.map(p => (
          <ProjectCard
            key={p.id} project={p} currentUserId={currentUserId}
            onOpen={onOpenProject}
            onSettings={onOpenSettings}
          />
        ))}
      </div>

      {createOpen && <CreateProjectModal onClose={() => setCreate(false)} />}
    </div>
  );
}

Object.assign(window, { ProjectsOverview, PROJECT_MEMBERS, PROJECT_META, PROJECT_ROLE_META, VISIBILITY_META, VisibilityBadge });
