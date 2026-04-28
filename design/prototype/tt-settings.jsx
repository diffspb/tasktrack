
// ─── Settings Tab Button ──────────────────────────────────────────────────────
function SettingsTab({ id, label, icon, active, onClick }) {
  return (
    <button onClick={() => onClick(id)}
      style={{
        display: 'flex', alignItems: 'center', gap: 8, width: '100%',
        padding: '8px 12px', borderRadius: 7, border: 'none', cursor: 'pointer',
        background: active ? 'var(--bg-muted)' : 'transparent',
        color: active ? 'var(--fg)' : 'var(--fg-muted)',
        fontFamily: 'inherit', fontSize: 13, fontWeight: active ? 600 : 400,
        textAlign: 'left', transition: 'background 0.12s, color 0.12s',
        borderLeft: active ? `3px solid var(--primary)` : '3px solid transparent',
      }}
      onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--bg-muted)'; }}
      onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
    >
      <Icon name={icon} size={14} stroke={active ? 'var(--primary)' : 'var(--fg-muted)'} />
      {label}
    </button>
  );
}

// ─── Settings Section Heading ─────────────────────────────────────────────────
function SettingSection({ title, desc, children }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 32, paddingBottom: 28, borderBottom: '1px solid var(--border)', marginBottom: 28 }}>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg)', marginBottom: 4 }}>{title}</div>
        {desc && <div style={{ fontSize: 12, color: 'var(--fg-muted)', lineHeight: 1.55 }}>{desc}</div>}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>{children}</div>
    </div>
  );
}

function SettingField({ label, hint, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg)' }}>{label}</span>
        {hint && <span style={{ fontSize: 11, color: 'var(--fg-subtle)' }}>{hint}</span>}
      </div>
      {children}
    </div>
  );
}

function SettingInput({ value, onChange, mono }) {
  return (
    <input value={value} onChange={e => onChange(e.target.value)}
      style={{
        padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7,
        background: 'var(--bg)', color: 'var(--fg)', fontSize: 13,
        fontFamily: mono ? 'monospace' : 'inherit', fontWeight: mono ? 700 : 400,
        outline: 'none', width: '100%', boxSizing: 'border-box', transition: 'border-color 0.15s',
      }}
      onFocus={e => e.target.style.borderColor = 'var(--primary)'}
      onBlur={e => e.target.style.borderColor = 'var(--border)'}
    />
  );
}

// ─── GENERAL TAB ─────────────────────────────────────────────────────────────
function GeneralTab({ project, meta }) {
  const [name, setName]   = React.useState(project.name);
  const [key, setKey]     = React.useState(project.key);
  const [desc, setDesc]   = React.useState(project.description);
  const [vis, setVis]     = React.useState(meta.visibility);
  const [saved, setSaved] = React.useState(false);

  function save() { setSaved(true); setTimeout(() => setSaved(false), 2000); }

  return (
    <div>
      <SettingSection title="Basic info" desc="Project name and key are visible across the instance.">
        <SettingField label="Project name">
          <SettingInput value={name} onChange={setName} />
        </SettingField>
        <SettingField label="Key" hint="— used as task prefix (e.g. TT-1). 2–4 chars.">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 140 }}>
              <SettingInput value={key} onChange={v => setKey(v.toUpperCase().slice(0, 4))} mono />
            </div>
            <div style={{
              padding: '6px 10px', background: 'var(--bg-muted)', border: '1px solid var(--border)',
              borderRadius: 7, fontSize: 12, color: 'var(--fg-muted)', fontFamily: 'monospace',
            }}>Preview: <strong style={{ color: 'var(--fg)' }}>{key}-42</strong></div>
          </div>
        </SettingField>
        <SettingField label="Description">
          <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={3}
            style={{
              padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7,
              background: 'var(--bg)', color: 'var(--fg)', fontSize: 13,
              fontFamily: 'inherit', resize: 'vertical', outline: 'none',
              width: '100%', boxSizing: 'border-box',
            }}
            onFocus={e => e.target.style.borderColor = 'var(--primary)'}
            onBlur={e => e.target.style.borderColor = 'var(--border)'}
          />
        </SettingField>
      </SettingSection>

      <SettingSection title="Visibility" desc="Controls who can see this project in the instance.">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {Object.entries(VISIBILITY_META).map(([k, m]) => (
            <div key={k} onClick={() => setVis(k)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
                border: `1.5px solid ${vis === k ? m.color : 'var(--border)'}`,
                borderRadius: 8, cursor: 'pointer',
                background: vis === k ? m.bg + '50' : 'var(--bg)',
                transition: 'all 0.15s',
              }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: m.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon name={m.icon} size={15} stroke={m.color} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{m.label}</div>
                <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{m.desc}</div>
              </div>
              <div style={{
                width: 18, height: 18, borderRadius: '50%',
                border: `2px solid ${vis === k ? m.color : 'var(--border)'}`,
                background: vis === k ? m.color : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                {vis === k && <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff' }} />}
              </div>
            </div>
          ))}
        </div>
      </SettingSection>

      <SettingSection title="Danger zone" desc="These actions are irreversible. Proceed with caution.">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', border: '1.5px solid oklch(0.86 0.08 25)', borderRadius: 8, background: 'oklch(0.97 0.02 25)' }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>Archive project</div>
            <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Hides the project from active lists. Tasks are preserved and searchable.</div>
          </div>
          <Btn variant="danger" size="sm">Archive</Btn>
        </div>
      </SettingSection>

      <div style={{ display: 'flex', gap: 8 }}>
        <Btn variant="default" onClick={save}>
          {saved ? <><Icon name="check" size={13} /> Saved!</> : 'Save changes'}
        </Btn>
        <Btn variant="ghost">Discard</Btn>
      </div>
    </div>
  );
}

// ─── MEMBERS TAB ─────────────────────────────────────────────────────────────
function MembersTab({ project }) {
  const members = PROJECT_MEMBERS[project.id] || [];
  const [inviteOpen, setInviteOpen] = React.useState(false);
  const roles = ['manager', 'member', 'viewer'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: 'var(--fg-muted)' }}>{members.length} members</span>
        <div style={{ flex: 1 }} />
        <Btn variant="default" size="sm" onClick={() => setInviteOpen(true)}>
          <Icon name="plus" size={13} /> Invite member
        </Btn>
      </div>

      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        {/* Table header */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 120px 140px 80px',
          padding: '8px 16px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-muted)',
        }}>
          {['Member', 'Role', 'Joined', ''].map(h => (
            <div key={h} style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</div>
          ))}
        </div>

        {members.map((m, i) => {
          const user = getUserById(m.userId);
          const rm = PROJECT_ROLE_META[m.role] || {};
          return (
            <div key={m.userId}
              style={{
                display: 'grid', gridTemplateColumns: '1fr 120px 140px 80px',
                padding: '12px 16px', alignItems: 'center',
                borderBottom: i < members.length - 1 ? '1px solid var(--border-subtle)' : 'none',
              }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Avatar userId={m.userId} size={28} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg)' }}>{user?.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--fg-subtle)' }}>{user?.role}</div>
                </div>
              </div>
              <div>
                <select value={m.role}
                  style={{
                    padding: '4px 8px', border: '1.5px solid var(--border)', borderRadius: 6,
                    background: 'var(--bg)', color: rm.color, fontSize: 12, fontWeight: 600,
                    fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
                  }}>
                  {roles.map(r => <option key={r} value={r} style={{ color: 'var(--fg)' }}>{PROJECT_ROLE_META[r]?.label}</option>)}
                </select>
              </div>
              <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>
                {new Date(m.joinedAt).toLocaleDateString('en', { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
              <div>
                <Btn variant="ghost" size="sm" style={{ fontSize: 11, color: 'oklch(0.50 0.15 25)' }}>Remove</Btn>
              </div>
            </div>
          );
        })}
      </div>

      {inviteOpen && (
        <>
          <div onClick={() => setInviteOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 300, background: 'oklch(0 0 0/0.3)' }} />
          <div style={{
            position: 'fixed', zIndex: 301, top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
            width: 400, background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--border)',
            boxShadow: 'var(--shadow-lg)', padding: 24,
          }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--fg)', marginBottom: 16 }}>Invite member</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)', display: 'block', marginBottom: 5 }}>User</label>
                <select style={{ width: '100%', padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7, background: 'var(--bg)', color: 'var(--fg)', fontSize: 13, fontFamily: 'inherit', outline: 'none' }}>
                  {USERS.filter(u => !(PROJECT_MEMBERS[project.id] || []).some(m => m.userId === u.id)).map(u => (
                    <option key={u.id} value={u.id}>{u.name} — {u.role}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)', display: 'block', marginBottom: 5 }}>Role</label>
                <select style={{ width: '100%', padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7, background: 'var(--bg)', color: 'var(--fg)', fontSize: 13, fontFamily: 'inherit', outline: 'none' }}>
                  {roles.map(r => <option key={r} value={r}>{PROJECT_ROLE_META[r]?.label}</option>)}
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Btn variant="ghost" onClick={() => setInviteOpen(false)}>Cancel</Btn>
              <Btn variant="default" onClick={() => setInviteOpen(false)}><Icon name="plus" size={13} /> Invite</Btn>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── WORKFLOW TAB ─────────────────────────────────────────────────────────────
function WorkflowTab() {
  const [statuses, setStatuses] = React.useState([
    { id: 'todo',        label: 'To Do',       category: 'todo',   color: 'var(--fg-subtle)' },
    { id: 'in_progress', label: 'In Progress',  category: 'active', color: 'oklch(0.48 0.14 200)' },
    { id: 'in_review',   label: 'In Review',    category: 'active', color: 'oklch(0.50 0.12 252)' },
    { id: 'done',        label: 'Done',         category: 'done',   color: 'oklch(0.45 0.14 150)' },
  ]);
  const [editId, setEditId] = React.useState(null);

  const catLabel = { todo: 'Not started', active: 'In progress', done: 'Done' };
  const catColor = { todo: 'var(--fg-subtle)', active: 'oklch(0.48 0.14 200)', done: 'oklch(0.45 0.14 150)' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ fontSize: 13, color: 'var(--fg-muted)', background: 'var(--bg-muted)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', lineHeight: 1.55 }}>
        Workflow statuses define the personal progression of each lead assignee. Each status belongs to a category that determines how it's interpreted globally.
      </div>

      {/* Status list */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '28px 1fr 120px 100px 60px', padding: '8px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg-muted)' }}>
          {['', 'Name', 'Category', 'Color', ''].map((h, i) => (
            <div key={i} style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</div>
          ))}
        </div>

        {statuses.map((s, i) => (
          <div key={s.id} style={{
            display: 'grid', gridTemplateColumns: '28px 1fr 120px 100px 60px',
            padding: '10px 16px', alignItems: 'center',
            borderBottom: i < statuses.length - 1 ? '1px solid var(--border-subtle)' : 'none',
          }}>
            {/* Drag handle */}
            <div style={{ cursor: 'grab', color: 'var(--fg-subtle)', display: 'flex', alignItems: 'center' }}>
              <svg width="12" height="16" viewBox="0 0 12 16" fill="currentColor">
                <circle cx="4" cy="4" r="1.5" /><circle cx="8" cy="4" r="1.5" />
                <circle cx="4" cy="8" r="1.5" /><circle cx="8" cy="8" r="1.5" />
                <circle cx="4" cy="12" r="1.5" /><circle cx="8" cy="12" r="1.5" />
              </svg>
            </div>

            {/* Name */}
            <div>
              {editId === s.id
                ? <input autoFocus value={s.label}
                    onChange={e => setStatuses(ss => ss.map(x => x.id === s.id ? { ...x, label: e.target.value } : x))}
                    onBlur={() => setEditId(null)}
                    onKeyDown={e => e.key === 'Enter' && setEditId(null)}
                    style={{ padding: '4px 8px', border: '1.5px solid var(--primary)', borderRadius: 5, background: 'var(--bg)', color: 'var(--fg)', fontSize: 13, fontFamily: 'inherit', outline: 'none', width: '100%' }}
                  />
                : <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'text' }} onClick={() => setEditId(s.id)}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
                    <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg)' }}>{s.label}</span>
                    <Icon name="more" size={13} stroke="var(--fg-subtle)" style={{ opacity: 0, transition: 'opacity 0.15s' }} />
                  </div>
              }
            </div>

            {/* Category */}
            <div>
              <span style={{ fontSize: 11, fontWeight: 600, color: catColor[s.category], background: catColor[s.category] + '18', borderRadius: 3, padding: '2px 6px' }}>
                {catLabel[s.category]}
              </span>
            </div>

            {/* Color swatch */}
            <div style={{ display: 'flex', gap: 4 }}>
              {['var(--fg-subtle)', 'oklch(0.48 0.14 200)', 'oklch(0.50 0.12 252)', 'oklch(0.45 0.14 150)', 'oklch(0.50 0.14 55)', 'oklch(0.50 0.15 25)'].map(c => (
                <button key={c} onClick={() => setStatuses(ss => ss.map(x => x.id === s.id ? { ...x, color: c } : x))}
                  style={{ width: 16, height: 16, borderRadius: '50%', background: c, border: 'none', cursor: 'pointer', outline: s.color === c ? '2px solid var(--fg)' : 'none', outlineOffset: 1 }} />
              ))}
            </div>

            {/* Delete */}
            <div>
              {statuses.length > 2 && (
                <button onClick={() => setStatuses(ss => ss.filter(x => x.id !== s.id))}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--fg-subtle)', padding: 4, borderRadius: 4, display: 'flex' }}>
                  <Icon name="x" size={14} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <Btn variant="secondary" size="sm" style={{ alignSelf: 'flex-start' }}>
        <Icon name="plus" size={13} /> Add status
      </Btn>

      <Btn variant="default" style={{ alignSelf: 'flex-start' }}>Save workflow</Btn>
    </div>
  );
}

// ─── LABELS TAB ──────────────────────────────────────────────────────────────
function LabelsTab({ project }) {
  const initLabels = {
    p1: ['design-system', 'frontend', 'auth', 'backend', 'ui', 'decision-process', 'api', 'performance', 'database', 'notifications', 'responsive'],
    p2: ['automation', 'scripts', 'ci'],
    p3: ['research', 'analysis', 'ux'],
  };
  const [labels, setLabels] = React.useState(initLabels[project.id] || []);
  const [newLabel, setNew]  = React.useState('');

  function addLabel() {
    const v = newLabel.trim().toLowerCase().replace(/\s+/g, '-');
    if (v && !labels.includes(v)) { setLabels(l => [...l, v]); setNew(''); }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Add label */}
      <div style={{ display: 'flex', gap: 8 }}>
        <input value={newLabel} onChange={e => setNew(e.target.value)}
          placeholder="New label name…"
          onKeyDown={e => e.key === 'Enter' && addLabel()}
          style={{
            flex: 1, padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7,
            background: 'var(--bg)', color: 'var(--fg)', fontSize: 13, fontFamily: 'inherit', outline: 'none',
          }}
          onFocus={e => e.target.style.borderColor = 'var(--primary)'}
          onBlur={e => e.target.style.borderColor = 'var(--border)'}
        />
        <Btn variant="default" size="sm" onClick={addLabel} disabled={!newLabel.trim()}>
          <Icon name="plus" size={13} /> Add
        </Btn>
      </div>

      {/* Labels grid */}
      <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
        {labels.length === 0
          ? <div style={{ fontSize: 13, color: 'var(--fg-subtle)', fontStyle: 'italic' }}>No labels yet. Add one above.</div>
          : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {labels.map(l => (
                <div key={l} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 5,
                  background: 'var(--bg-muted)', border: '1px solid var(--border)',
                  borderRadius: 5, padding: '4px 8px',
                }}>
                  <Icon name="tag" size={11} stroke="var(--fg-subtle)" />
                  <span style={{ fontSize: 12, color: 'var(--fg)', fontWeight: 500 }}>{l}</span>
                  <button onClick={() => setLabels(ll => ll.filter(x => x !== l))}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--fg-subtle)', padding: 0, display: 'flex', marginLeft: 2 }}>
                    <Icon name="x" size={11} />
                  </button>
                </div>
              ))}
            </div>
          )
        }
      </div>
    </div>
  );
}

// ─── Project Settings Page ────────────────────────────────────────────────────
function ProjectSettings({ project, onBack }) {
  const [tab, setTab] = React.useState('general');
  const meta = PROJECT_META[project.id] || {};

  const tabs = [
    { id: 'general',  label: 'General',  icon: 'settings' },
    { id: 'members',  label: 'Members',  icon: 'users'    },
    { id: 'workflow', label: 'Workflow',  icon: 'kanban'   },
    { id: 'labels',   label: 'Labels',   icon: 'tag'      },
  ];

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Left nav */}
      <div style={{
        width: 200, flexShrink: 0, borderRight: '1px solid var(--border)',
        padding: '20px 12px', display: 'flex', flexDirection: 'column', gap: 4,
        overflowY: 'auto',
      }}>
        {/* Back */}
        <button onClick={onBack}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, background: 'none',
            border: 'none', cursor: 'pointer', color: 'var(--fg-muted)',
            fontSize: 12, fontFamily: 'inherit', padding: '6px 8px', borderRadius: 6,
            marginBottom: 12, textAlign: 'left',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-muted)'}
          onMouseLeave={e => e.currentTarget.style.background = 'none'}
        >
          <Icon name="chevronLeft" size={13} /> All projects
        </button>

        {/* Project badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', marginBottom: 8 }}>
          <div style={{ width: 24, height: 24, borderRadius: 6, background: project.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, fontWeight: 800, color: '#fff' }}>{project.key}</div>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{project.name}</span>
        </div>

        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--fg-subtle)', letterSpacing: '0.06em', textTransform: 'uppercase', padding: '4px 12px', marginBottom: 4 }}>Settings</div>

        {tabs.map(t => <SettingsTab key={t.id} {...t} active={tab === t.id} onClick={setTab} />)}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 36px' }}>
        <div style={{ maxWidth: 680 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, color: 'var(--fg)', marginBottom: 24 }}>
            {tabs.find(t => t.id === tab)?.label}
          </h2>
          {tab === 'general'  && <GeneralTab  project={project} meta={meta} />}
          {tab === 'members'  && <MembersTab  project={project} />}
          {tab === 'workflow' && <WorkflowTab />}
          {tab === 'labels'   && <LabelsTab   project={project} />}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ProjectSettings });
