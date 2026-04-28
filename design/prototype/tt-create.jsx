
// ─── User Picker Dropdown ─────────────────────────────────────────────────────
function UserPicker({ value, onChange, exclude = [], placeholder = 'Choose user…' }) {
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState('');
  const available = USERS.filter(u =>
    !exclude.includes(u.id) &&
    (u.name.toLowerCase().includes(query.toLowerCase()) || u.role.toLowerCase().includes(query.toLowerCase()))
  );
  const selected = value ? getUserById(value) : null;
  const ref = React.useRef();

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px',
        border: '1.5px solid var(--border)', borderRadius: 7,
        background: 'var(--bg)', cursor: 'pointer', fontFamily: 'inherit',
        color: 'var(--fg)', fontSize: 13, width: '100%', textAlign: 'left',
        transition: 'border-color 0.15s',
      }}
        onFocus={e => e.currentTarget.style.borderColor = 'var(--primary)'}
        onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
      >
        {selected
          ? <><Avatar userId={selected.id} size={20} /><span style={{ flex: 1 }}>{selected.name}</span></>
          : <span style={{ color: 'var(--fg-subtle)', flex: 1 }}>{placeholder}</span>
        }
        <Icon name="chevronDown" size={13} stroke="var(--fg-subtle)" />
      </button>
      {open && (
        <>
          <div onClick={() => { setOpen(false); setQuery(''); }} style={{ position: 'fixed', inset: 0, zIndex: 200 }} />
          <div style={{
            position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 201,
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            borderRadius: 8, boxShadow: 'var(--shadow-lg)', overflow: 'hidden',
          }}>
            <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>
              <input autoFocus value={query} onChange={e => setQuery(e.target.value)}
                placeholder="Search…"
                style={{
                  width: '100%', border: 'none', background: 'none', outline: 'none',
                  fontSize: 13, color: 'var(--fg)', fontFamily: 'inherit',
                }} />
            </div>
            {available.length === 0
              ? <div style={{ padding: '10px 12px', fontSize: 12, color: 'var(--fg-subtle)' }}>No users found</div>
              : available.map(u => (
                <button key={u.id} onClick={() => { onChange(u.id); setOpen(false); setQuery(''); }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                    padding: '8px 12px', border: 'none', background: value === u.id ? 'var(--bg-muted)' : 'none',
                    cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-muted)'}
                  onMouseLeave={e => e.currentTarget.style.background = value === u.id ? 'var(--bg-muted)' : 'none'}
                >
                  <Avatar userId={u.id} size={22} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg)' }}>{u.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--fg-subtle)' }}>{u.role}</div>
                  </div>
                  {value === u.id && <Icon name="check" size={14} stroke="var(--primary)" style={{ marginLeft: 'auto' }} />}
                </button>
              ))
            }
          </div>
        </>
      )}
    </div>
  );
}

// ─── Form Field wrapper ───────────────────────────────────────────────────────
function Field({ label, required, hint, children, error }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)', letterSpacing: '0.01em' }}>
          {label}
        </span>
        {required && <span style={{ fontSize: 11, color: 'oklch(0.50 0.15 25)' }}>*</span>}
        {hint && <span style={{ fontSize: 11, color: 'var(--fg-subtle)', marginLeft: 4 }}>{hint}</span>}
      </div>
      {children}
      {error && <div style={{ fontSize: 11, color: 'oklch(0.50 0.15 25)' }}>{error}</div>}
    </div>
  );
}

function TextInput({ value, onChange, placeholder, multiline, rows = 4, error }) {
  const style = {
    padding: '8px 10px', border: `1.5px solid ${error ? 'oklch(0.75 0.12 25)' : 'var(--border)'}`,
    borderRadius: 7, background: 'var(--bg)', color: 'var(--fg)',
    fontSize: 13, fontFamily: 'inherit', outline: 'none', width: '100%',
    boxSizing: 'border-box', resize: multiline ? 'vertical' : 'none',
    transition: 'border-color 0.15s',
  };
  const focus = e => { e.target.style.borderColor = 'var(--primary)'; };
  const blur  = e => { e.target.style.borderColor = error ? 'oklch(0.75 0.12 25)' : 'var(--border)'; };
  if (multiline) return <textarea rows={rows} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={style} onFocus={focus} onBlur={blur} />;
  return <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={style} onFocus={focus} onBlur={blur} />;
}

// ─── Inline segment control ───────────────────────────────────────────────────
function SegControl({ options, value, onChange, getLabel, getColor }) {
  return (
    <div style={{ display: 'flex', border: '1.5px solid var(--border)', borderRadius: 7, overflow: 'hidden' }}>
      {options.map((opt, i) => {
        const active = opt === value;
        const color = getColor ? getColor(opt) : 'var(--primary)';
        return (
          <button key={opt} onClick={() => onChange(opt)}
            style={{
              flex: 1, padding: '7px 4px', border: 'none', cursor: 'pointer', fontFamily: 'inherit',
              fontSize: 12, fontWeight: 500, transition: 'all 0.15s',
              borderLeft: i > 0 ? '1px solid var(--border)' : 'none',
              background: active ? color + '18' : 'var(--bg)',
              color: active ? color : 'var(--fg-muted)',
              outline: active ? `1.5px solid ${color}` : 'none',
              outlineOffset: -1.5,
            }}>
            {getLabel ? getLabel(opt) : opt}
          </button>
        );
      })}
    </div>
  );
}

// ─── Divider with label ───────────────────────────────────────────────────────
function SectionDivider({ label, optional, expanded, onToggle }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '4px 0' }}>
      <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      <button onClick={onToggle}
        style={{
          display: 'flex', alignItems: 'center', gap: 5, border: '1px solid var(--border)',
          background: 'var(--bg-muted)', borderRadius: 20, padding: '3px 10px',
          cursor: onToggle ? 'pointer' : 'default', fontFamily: 'inherit',
          fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', letterSpacing: '0.03em',
        }}>
        {label}
        {optional && <span style={{ color: 'var(--fg-subtle)', fontWeight: 400 }}>optional</span>}
        {onToggle && <Icon name={expanded ? 'chevronDown' : 'chevronRight'} size={12} stroke="var(--fg-subtle)" />}
      </button>
      <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
    </div>
  );
}

// ─── Create Task Modal ────────────────────────────────────────────────────────
function CreateTaskPanel({ project: defaultProject, currentUserId, onClose }) {
  const [projectId, setProjectId]     = React.useState(defaultProject.id);
  const [type, setType]               = React.useState('task');
  const [title, setTitle]             = React.useState('');
  const [priority, setPriority]       = React.useState('medium');
  const [description, setDescription] = React.useState('');
  const [dueDate, setDueDate]         = React.useState('');
  const [labels, setLabels]           = React.useState('');
  const [assignees, setAssignees]     = React.useState([
    { uid: 1, userId: currentUserId, role: 'lead' },
  ]);
  const [decisionMakerId, setDM]      = React.useState(currentUserId);
  const [multiAccept, setMultiAccept] = React.useState(false);
  const [criteria, setCriteria]       = React.useState([]);
  const [criteriaExpanded, setCriteriaExpanded] = React.useState(false);
  const [errors, setErrors]           = React.useState({});
  const [submitting, setSubmitting]   = React.useState(false);

  const project = PROJECTS.find(p => p.id === projectId) || PROJECTS[0];
  const leadCount = assignees.filter(a => a.userId && a.role === 'lead').length;
  const isMulti = leadCount > 1;

  // Auto-expand criteria when multi-lead
  React.useEffect(() => {
    if (isMulti) setCriteriaExpanded(true);
  }, [isMulti]);

  function addAssignee() {
    setAssignees(a => [...a, { uid: Date.now(), userId: '', role: 'lead' }]);
  }
  function removeAssignee(uid) {
    setAssignees(a => a.filter(x => x.uid !== uid));
  }
  function updateAssignee(uid, key, val) {
    setAssignees(a => a.map(x => x.uid === uid ? { ...x, [key]: val } : x));
  }
  function addCriterion() {
    setCriteria(c => [...c, { uid: Date.now(), text: '' }]);
  }
  function removeCriterion(uid) {
    setCriteria(c => c.filter(x => x.uid !== uid));
  }
  function updateCriterion(uid, val) {
    setCriteria(c => c.map(x => x.uid === uid ? { ...x, text: val } : x));
  }

  function handleSubmit() {
    const e = {};
    if (!title.trim()) e.title = 'Title is required';
    if (assignees.some(a => !a.userId)) e.assignees = 'Select a user for each assignee row';
    setErrors(e);
    if (Object.keys(e).length > 0) return;
    setSubmitting(true);
    setTimeout(() => { setSubmitting(false); onClose(); }, 600);
  }

  const usedUserIds = assignees.map(a => a.userId).filter(Boolean);

  return (
    <>
      {/* Backdrop */}
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 300, background: 'oklch(0 0 0 / 0.35)' }} />

      {/* Modal */}
      <div style={{
        position: 'fixed', zIndex: 301,
        top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
        width: 580, maxHeight: '90vh',
        background: 'var(--bg-card)', borderRadius: 12,
        border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', padding: '16px 20px',
          borderBottom: '1px solid var(--border)', flexShrink: 0,
        }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--fg)' }}>Create Task</span>
          <div style={{ flex: 1 }} />
          <button onClick={onClose} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--fg-muted)', padding: 4, borderRadius: 4, display: 'flex',
          }}>
            <Icon name="x" size={16} />
          </button>
        </div>

        {/* Scrollable body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 20px 4px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Project */}
            <Field label="Project" required>
              <div style={{ display: 'flex', border: '1.5px solid var(--border)', borderRadius: 7, overflow: 'hidden' }}>
                {PROJECTS.map((p, i) => (
                  <button key={p.id} onClick={() => setProjectId(p.id)}
                    style={{
                      flex: 1, padding: '7px 8px', border: 'none', cursor: 'pointer',
                      fontFamily: 'inherit', fontSize: 12, fontWeight: 500,
                      borderLeft: i > 0 ? '1px solid var(--border)' : 'none',
                      background: projectId === p.id ? p.color + '18' : 'var(--bg)',
                      color: projectId === p.id ? p.color : 'var(--fg-muted)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                      outline: projectId === p.id ? `1.5px solid ${p.color}` : 'none',
                      outlineOffset: -1.5, transition: 'all 0.15s',
                    }}>
                    <div style={{
                      width: 16, height: 16, borderRadius: 4, background: p.color,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 7, fontWeight: 800, color: '#fff',
                    }}>{p.key}</div>
                    {p.name}
                  </button>
                ))}
              </div>
            </Field>

            {/* Type */}
            <Field label="Issue type" required>
              <SegControl
                options={['task', 'feature', 'bug']}
                value={type} onChange={setType}
                getLabel={t => TYPE_META[t]?.label}
                getColor={t => TYPE_META[t]?.color}
              />
            </Field>

            {/* Title */}
            <Field label="Title" required error={errors.title}>
              <TextInput
                value={title} onChange={v => { setTitle(v); if (v.trim()) setErrors(e => ({ ...e, title: undefined })); }}
                placeholder="Short, descriptive title for the task…"
                error={errors.title}
              />
            </Field>

            {/* Priority */}
            <Field label="Priority">
              <SegControl
                options={['low', 'medium', 'high', 'critical']}
                value={priority} onChange={setPriority}
                getLabel={p => PRIORITY_META[p]?.label}
                getColor={p => PRIORITY_META[p]?.color}
              />
            </Field>

            {/* Description */}
            <Field label="Description" hint="(optional)">
              <TextInput
                value={description} onChange={setDescription} multiline rows={4}
                placeholder="What needs to be done? Include context, acceptance criteria, relevant links…"
              />
            </Field>

            {/* Due date + Labels row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Field label="Due date">
                <input type="date" value={dueDate} onChange={e => setDueDate(e.target.value)}
                  style={{
                    padding: '7px 10px', border: '1.5px solid var(--border)', borderRadius: 7,
                    background: 'var(--bg)', color: dueDate ? 'var(--fg)' : 'var(--fg-subtle)',
                    fontSize: 13, fontFamily: 'inherit', outline: 'none', width: '100%', boxSizing: 'border-box',
                  }} />
              </Field>
              <Field label="Labels" hint="comma-separated">
                <TextInput value={labels} onChange={setLabels} placeholder="ui, auth, backend…" />
              </Field>
            </div>

            <SectionDivider label="ASSIGNEES" />

            {/* Assignees */}
            <Field label="Assignees" required error={errors.assignees}
              hint={isMulti ? '— multi-assignee task, Decision Process will be triggered' : ''}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {assignees.map((a, i) => (
                  <div key={a.uid} style={{
                    display: 'grid', gridTemplateColumns: '1fr 130px auto',
                    gap: 8, alignItems: 'center',
                  }}>
                    <UserPicker
                      value={a.userId}
                      onChange={val => updateAssignee(a.uid, 'userId', val)}
                      exclude={assignees.filter(x => x.uid !== a.uid).map(x => x.userId).filter(Boolean)}
                      placeholder="Choose assignee…"
                    />
                    <select value={a.role} onChange={e => updateAssignee(a.uid, 'role', e.target.value)}
                      style={{
                        padding: '7px 8px', border: '1.5px solid var(--border)', borderRadius: 7,
                        background: 'var(--bg)', color: ROLE_META[a.role]?.color,
                        fontSize: 12, fontWeight: 600, fontFamily: 'inherit', cursor: 'pointer', outline: 'none',
                      }}>
                      {['lead','reviewer','consultant'].map(r => (
                        <option key={r} value={r} style={{ color: 'var(--fg)' }}>{ROLE_META[r]?.label}</option>
                      ))}
                    </select>
                    <button onClick={() => removeAssignee(a.uid)}
                      disabled={assignees.length === 1}
                      style={{
                        background: 'none', border: 'none', cursor: assignees.length === 1 ? 'not-allowed' : 'pointer',
                        color: 'var(--fg-subtle)', padding: 6, borderRadius: 5, display: 'flex',
                        opacity: assignees.length === 1 ? 0.3 : 1,
                      }}>
                      <Icon name="x" size={14} />
                    </button>
                  </div>
                ))}
                <button onClick={addAssignee}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    background: 'none', border: '1.5px dashed var(--border)', borderRadius: 7,
                    padding: '6px 10px', cursor: 'pointer', color: 'var(--fg-muted)',
                    fontSize: 12, fontWeight: 500, fontFamily: 'inherit', transition: 'border-color 0.15s, color 0.15s',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.color = 'var(--primary)'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--fg-muted)'; }}
                >
                  <Icon name="plus" size={13} /> Add assignee
                </button>
              </div>
            </Field>

            {/* Decision Maker */}
            <Field label="Decision maker"
              hint={`— reviews all solutions and makes the final call${decisionMakerId === currentUserId ? ' (you)' : ''}`}>
              <UserPicker value={decisionMakerId} onChange={setDM} placeholder="Choose decision maker…" />
            </Field>

            {/* Multi-accept — only if multiple leads */}
            {isMulti && (
              <div style={{
                display: 'flex', alignItems: 'flex-start', gap: 12, padding: '10px 14px',
                background: multiAccept ? 'oklch(0.95 0.04 252)' : 'var(--bg-muted)',
                border: `1.5px solid ${multiAccept ? 'oklch(0.78 0.10 252)' : 'var(--border)'}`,
                borderRadius: 8, cursor: 'pointer', transition: 'all 0.2s',
              }} onClick={() => setMultiAccept(m => !m)}>
                <div style={{
                  width: 36, height: 20, borderRadius: 10, flexShrink: 0, marginTop: 2,
                  background: multiAccept ? 'var(--primary)' : 'var(--border)', position: 'relative', transition: 'background 0.2s',
                }}>
                  <div style={{
                    width: 16, height: 16, borderRadius: '50%', background: '#fff',
                    position: 'absolute', top: 2, transition: 'left 0.2s',
                    left: multiAccept ? 18 : 2, boxShadow: '0 1px 3px oklch(0 0 0/0.2)',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>Allow multiple accepted solutions</div>
                  <div style={{ fontSize: 11, color: 'var(--fg-subtle)', marginTop: 2 }}>
                    Decision maker can accept more than one solution — e.g. "take both approaches in parallel"
                  </div>
                </div>
              </div>
            )}

            {/* Decision criteria — optional, collapses when single assignee */}
            <SectionDivider
              label="DECISION CRITERIA"
              optional
              expanded={criteriaExpanded}
              onToggle={() => setCriteriaExpanded(e => !e)}
            />

            {criteriaExpanded && (
              <Field label="Criteria" hint="— how solutions will be evaluated">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {criteria.map((c, i) => (
                    <div key={c.uid} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{
                        width: 22, height: 22, borderRadius: '50%', background: 'var(--bg-muted)',
                        border: '1px solid var(--border)', display: 'flex', alignItems: 'center',
                        justifyContent: 'center', fontSize: 11, fontWeight: 700, color: 'var(--fg-muted)', flexShrink: 0,
                      }}>{i + 1}</div>
                      <TextInput
                        value={c.text}
                        onChange={val => updateCriterion(c.uid, val)}
                        placeholder={['Performance — smooth at 60fps with 100+ cards', 'Visual quality and design system compliance', 'Code review score ≥ 4/5'][i] || 'Describe the criterion…'}
                      />
                      <button onClick={() => removeCriterion(c.uid)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--fg-subtle)', padding: 4, borderRadius: 4, display: 'flex' }}>
                        <Icon name="x" size={14} />
                      </button>
                    </div>
                  ))}
                  <button onClick={addCriterion}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      background: 'none', border: '1.5px dashed var(--border)', borderRadius: 7,
                      padding: '6px 10px', cursor: 'pointer', color: 'var(--fg-muted)',
                      fontSize: 12, fontWeight: 500, fontFamily: 'inherit', transition: 'border-color 0.15s, color 0.15s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.color = 'var(--primary)'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--fg-muted)'; }}
                  >
                    <Icon name="plus" size={13} /> Add criterion
                  </button>
                </div>
              </Field>
            )}

            {/* bottom padding */}
            <div style={{ height: 8 }} />
          </div>
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '14px 20px', borderTop: '1px solid var(--border)', flexShrink: 0,
          background: 'var(--bg)',
        }}>
          <div style={{ flex: 1 }} />
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn variant="default" onClick={handleSubmit} disabled={submitting}>
            {submitting
              ? <><span style={{ opacity: 0.7 }}>Creating…</span></>
              : <><Icon name="check" size={13} /> Create Task</>
            }
          </Btn>
        </div>
      </div>
    </>
  );
}

Object.assign(window, { CreateTaskPanel });
