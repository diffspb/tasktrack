
// ─── Comment ─────────────────────────────────────────────────────────────────
function CommentItem({ comment }) {
  const user = getUserById(comment.authorId);
  const date = new Date(comment.createdAt).toLocaleDateString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  return (
    <div style={{ display: 'flex', gap: 10 }}>
      <Avatar userId={comment.authorId} size={28} />
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{user?.name}</span>
          <span style={{ fontSize: 11, color: 'var(--fg-subtle)' }}>{date}</span>
        </div>
        <div style={{
          fontSize: 13, color: 'var(--fg)', lineHeight: 1.55,
          background: 'var(--bg-muted)', borderRadius: 8,
          padding: '8px 12px', border: '1px solid var(--border)',
        }}>
          {comment.text}
        </div>
      </div>
    </div>
  );
}

// ─── History Item ─────────────────────────────────────────────────────────────
function HistoryItem({ item }) {
  const user = item.authorId ? getUserById(item.authorId) : null;
  const date = new Date(item.date).toLocaleDateString('en', { month: 'short', day: 'numeric' });
  const iconMap = { status: 'arrowRight', assign: 'users', solution: 'zap', decision: 'award', revision: 'arrowRight', closed: 'check', global_status: 'flag' };
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
      <div style={{
        width: 24, height: 24, borderRadius: '50%',
        background: 'var(--bg-muted)', border: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <Icon name={iconMap[item.type] || 'arrowRight'} size={11} stroke="var(--fg-muted)" />
      </div>
      <div style={{ flex: 1, fontSize: 12, color: 'var(--fg-muted)', paddingTop: 4 }}>
        {user && <strong style={{ color: 'var(--fg)' }}>{user.name} </strong>}
        {item.text}
        <span style={{ color: 'var(--fg-subtle)', marginLeft: 6 }}>{date}</span>
      </div>
    </div>
  );
}

// ─── Solution Card ────────────────────────────────────────────────────────────
function SolutionCard({ solution, isDecisionMaker, isCurrentUser, onAccept, onRevision, isRevisionMode, revisionTarget, setRevisionTarget, revisionComment, setRevisionComment }) {
  const user = getUserById(solution.assigneeId);
  const date = new Date(solution.submittedAt).toLocaleDateString('en', { month: 'short', day: 'numeric', year: 'numeric' });
  const isSelected = revisionTarget === solution.id;

  return (
    <div style={{
      border: `1.5px solid ${solution.status === 'accepted' ? 'oklch(0.75 0.12 150)' : solution.status === 'revision_requested' ? 'oklch(0.78 0.10 25)' : 'var(--border)'}`,
      borderRadius: 10, overflow: 'hidden',
      background: solution.status === 'accepted' ? 'oklch(0.97 0.02 150)' : 'var(--bg-card)',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
        borderBottom: '1px solid var(--border)', background: 'var(--bg-muted)',
      }}>
        <Avatar userId={solution.assigneeId} size={26} />
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{user?.name}</div>
          <div style={{ fontSize: 11, color: 'var(--fg-subtle)' }}>Submitted {date}</div>
        </div>
        <div style={{ flex: 1 }} />
        <SolutionStatusBadge status={solution.status} />
        {isCurrentUser && solution.status === 'submitted' && (
          <Btn variant="ghost" size="sm" style={{ fontSize: 11, color: 'var(--fg-subtle)' }}>Withdraw</Btn>
        )}
      </div>

      {/* Revision feedback banner */}
      {solution.revisionComment && (
        <div style={{
          background: 'oklch(0.96 0.04 25)', borderBottom: '1px solid oklch(0.88 0.06 25)',
          padding: '8px 14px', display: 'flex', gap: 8, alignItems: 'flex-start',
        }}>
          <Icon name="arrowRight" size={14} stroke="oklch(0.50 0.15 25)" style={{ marginTop: 1, flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'oklch(0.45 0.15 25)', marginBottom: 2 }}>Revision requested</div>
            <div style={{ fontSize: 12, color: 'oklch(0.40 0.10 25)', lineHeight: 1.5 }}>{solution.revisionComment}</div>
          </div>
        </div>
      )}

      {/* Content */}
      <div style={{ padding: '12px 14px' }}>
        <div style={{ fontSize: 13, color: 'var(--fg)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
          {solution.content}
        </div>

        {/* Attachments */}
        {solution.attachments && solution.attachments.length > 0 && (
          <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {solution.attachments.map(a => (
              <span key={a} style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                fontSize: 11, color: 'var(--primary)', background: 'var(--bg-muted)',
                border: '1px solid var(--border)', borderRadius: 4, padding: '2px 8px',
                cursor: 'pointer',
              }}>
                <Icon name="paperclip" size={11} stroke="var(--primary)" />
                {a}
              </span>
            ))}
          </div>
        )}

        {/* Decision-maker actions */}
        {isDecisionMaker && solution.status === 'submitted' && (
          <div style={{ marginTop: 12, display: 'flex', gap: 8, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <Btn variant="success" size="sm" onClick={() => onAccept(solution.id)}>
              <Icon name="check" size={13} /> Accept
            </Btn>
            <Btn variant="danger" size="sm" onClick={() => onRevision(solution.id)}>
              <Icon name="arrowRight" size={13} /> Request Revision
            </Btn>
          </div>
        )}

        {/* Resubmit for current user when revision requested */}
        {isCurrentUser && solution.status === 'revision_requested' && (
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: 12, color: 'var(--fg-muted)', marginBottom: 8 }}>Edit your solution and resubmit:</div>
            <Btn variant="default" size="sm">
              <Icon name="arrowRight" size={13} /> Resubmit Solution
            </Btn>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Revision Modal ───────────────────────────────────────────────────────────
function RevisionModal({ solutionId, onConfirm, onCancel }) {
  const [comment, setComment] = React.useState('');
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'oklch(0 0 0 / 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onCancel}>
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 12,
        padding: 24, width: 460, boxShadow: 'var(--shadow-lg)',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--fg)', marginBottom: 4 }}>Request Revision</div>
        <div style={{ fontSize: 13, color: 'var(--fg-muted)', marginBottom: 16 }}>
          Provide feedback so the assignee knows what to improve.
        </div>
        <textarea
          autoFocus
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="e.g. SSE reconnection logic is missing. Please add exponential backoff…"
          style={{
            width: '100%', minHeight: 100, padding: '10px 12px',
            border: '1.5px solid var(--border)', borderRadius: 8,
            background: 'var(--bg)', color: 'var(--fg)',
            fontSize: 13, fontFamily: 'inherit', resize: 'vertical',
            outline: 'none', boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <Btn variant="secondary" onClick={onCancel}>Cancel</Btn>
          <Btn variant="danger" onClick={() => comment.trim() && onConfirm(comment)} disabled={!comment.trim()}>
            Send for Revision
          </Btn>
        </div>
      </div>
    </div>
  );
}

// ─── Task Detail Panel ────────────────────────────────────────────────────────
function TaskDetailPanel({ task: initialTask, currentUserId, onClose }) {
  const [task, setTask] = React.useState(initialTask);
  const [activeTab, setActiveTab] = React.useState('overview');
  const [revisionModalFor, setRevisionModalFor] = React.useState(null);

  React.useEffect(() => { setTask(initialTask); }, [initialTask]);

  const myAssignee = task.assignees.find(a => a.userId === currentUserId);
  const isDecisionMaker = task.decisionMakerId === currentUserId;
  const hasDecisionProcess = task.assignees.filter(a => a.role === 'lead').length > 1 || task.solutions.length > 0;
  const leads = task.assignees.filter(a => a.role === 'lead');
  const submittedCount = leads.filter(a => a.solutionStatus === 'submitted' || a.solutionStatus === 'accepted').length;

  function handleAccept(solutionId) {
    setTask(t => ({
      ...t,
      globalStatus: 'decided',
      solutions: t.solutions.map(s => s.id === solutionId ? { ...s, status: 'accepted' } : s),
    }));
  }

  function handleRevision(solutionId, comment) {
    setRevisionModalFor(null);
    setTask(t => ({
      ...t,
      globalStatus: 'in_revision',
      solutions: t.solutions.map(s => s.id === solutionId
        ? { ...s, status: 'revision_requested', revisionComment: comment }
        : s),
      assignees: t.assignees.map(a =>
        t.solutions.find(s => s.id === solutionId)?.assigneeId === a.userId
          ? { ...a, solutionStatus: 'revision_requested' }
          : a),
    }));
  }

  const tabs = [
    { id: 'overview', label: 'Overview' },
    ...(hasDecisionProcess ? [{ id: 'solutions', label: `Solutions (${task.solutions.length})` }] : []),
    { id: 'comments', label: `Comments (${task.comments.length})` },
    { id: 'history', label: 'History' },
  ];

  const tabStyle = (id) => ({
    padding: '8px 14px', fontSize: 13, fontWeight: 500,
    cursor: 'pointer', border: 'none', background: 'none',
    color: activeTab === id ? 'var(--primary)' : 'var(--fg-muted)',
    borderBottom: activeTab === id ? '2px solid var(--primary)' : '2px solid transparent',
    fontFamily: 'inherit', transition: 'color 0.15s',
  });

  return (
    <>
      {/* Backdrop */}
      <div onClick={onClose} style={{
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'oklch(0 0 0 / 0.25)',
      }} />

      {/* Panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 101,
        width: 620, background: 'var(--bg)', boxShadow: '-4px 0 24px oklch(0 0 0 / 0.12)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
        borderLeft: '1px solid var(--border)',
      }}>

        {/* Panel Header */}
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-subtle)', fontFamily: 'monospace', letterSpacing: '0.03em' }}>
              {task.key}
            </span>
            <TypeBadge type={task.type} />
            <PriorityBadge priority={task.priority} />
            <div style={{ flex: 1 }} />
            <Btn variant="ghost" size="sm" style={{ padding: '4px 8px' }}>
              <Icon name="link" size={13} />
            </Btn>
            <Btn variant="ghost" size="sm" style={{ padding: '4px 8px' }}>
              <Icon name="more" size={13} />
            </Btn>
            <Btn variant="ghost" size="sm" onClick={onClose} style={{ padding: '4px 8px' }}>
              <Icon name="x" size={14} />
            </Btn>
          </div>
          <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--fg)', lineHeight: 1.35 }}>
            {task.title}
          </div>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0,
          padding: '0 8px',
        }}>
          {tabs.map(t => (
            <button key={t.id} style={tabStyle(t.id)} onClick={() => setActiveTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>

          {/* ── OVERVIEW TAB ── */}
          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

              {/* Global Status + Workflow */}
              <div style={{
                background: 'var(--bg-card)', border: '1px solid var(--border)',
                borderRadius: 10, padding: '14px 16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', width: 90 }}>Global status</div>
                  <GlobalStatusBadge status={task.globalStatus} size="lg" />
                </div>
                {hasDecisionProcess && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', width: 90 }}>Solutions</div>
                    <div style={{ flex: 1, height: 6, background: 'var(--bg-muted)', borderRadius: 3 }}>
                      <div style={{ height: 6, background: 'var(--primary)', borderRadius: 3, width: (submittedCount / leads.length * 100) + '%', transition: 'width 0.4s' }} />
                    </div>
                    <span style={{ fontSize: 12, color: 'var(--fg-muted)', whiteSpace: 'nowrap' }}>
                      {submittedCount} / {leads.length} submitted
                    </span>
                  </div>
                )}
                {/* My workflow transition */}
                {myAssignee && myAssignee.role === 'lead' && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', width: 90 }}>My status</div>
                    <PersonalStatusBadge status={myAssignee.personalStatus} />
                    <Icon name="arrowRight" size={13} stroke="var(--fg-subtle)" />
                    {/* Next status options */}
                    <div style={{ display: 'flex', gap: 6 }}>
                      {WORKFLOW_STATUSES
                        .filter(s => s.id !== myAssignee.personalStatus)
                        .slice(0, 2)
                        .map(s => (
                          <Btn key={s.id} variant="secondary" size="sm" style={{ fontSize: 11 }}>
                            {s.label}
                          </Btn>
                        ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Decision criteria */}
              {task.decisionCriteria.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                    Decision Criteria
                  </div>
                  <div style={{
                    background: 'var(--bg-card)', border: '1px solid var(--border)',
                    borderRadius: 10, overflow: 'hidden',
                  }}>
                    {task.decisionCriteria.map((dc, i) => (
                      <div key={dc.id} style={{
                        display: 'flex', alignItems: 'flex-start', gap: 10,
                        padding: '9px 14px',
                        borderBottom: i < task.decisionCriteria.length - 1 ? '1px solid var(--border)' : 'none',
                      }}>
                        <div style={{
                          width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
                          background: 'var(--bg-muted)', border: '1px solid var(--border)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 10, fontWeight: 700, color: 'var(--fg-muted)', marginTop: 1,
                        }}>{i + 1}</div>
                        <span style={{ fontSize: 13, color: 'var(--fg)', lineHeight: 1.45 }}>{dc.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Assignees */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                  Assignees
                </div>
                <div style={{
                  background: 'var(--bg-card)', border: '1px solid var(--border)',
                  borderRadius: 10, overflow: 'hidden',
                }}>
                  {task.assignees.map((a, i) => {
                    const user = getUserById(a.userId);
                    return (
                      <div key={a.userId} style={{
                        display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
                        borderBottom: i < task.assignees.length - 1 ? '1px solid var(--border)' : 'none',
                        background: a.userId === currentUserId ? 'var(--bg-muted)' : 'transparent',
                      }}>
                        <Avatar userId={a.userId} size={28} />
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{user?.name}</span>
                            {a.userId === currentUserId && <span style={{ fontSize: 10, color: 'var(--fg-subtle)' }}>(you)</span>}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--fg-subtle)' }}>{user?.role}</div>
                        </div>
                        <RoleBadge role={a.role} />
                        {a.personalStatus && <PersonalStatusBadge status={a.personalStatus} />}
                        {a.solutionStatus && <SolutionStatusBadge status={a.solutionStatus} />}
                      </div>
                    );
                  })}
                </div>
                {/* Decision maker */}
                <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, color: 'var(--fg-subtle)' }}>Decision maker:</span>
                  <Avatar userId={task.decisionMakerId} size={20} />
                  <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--fg)' }}>
                    {getUserById(task.decisionMakerId)?.name}
                    {task.decisionMakerId === currentUserId && ' (you)'}
                  </span>
                </div>
              </div>

              {/* Metadata */}
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12,
              }}>
                {[
                  { label: 'Due date', value: task.dueDate ? new Date(task.dueDate).toLocaleDateString('en', { month: 'long', day: 'numeric', year: 'numeric' }) : '—', icon: 'clock' },
                  { label: 'Reporter', value: getUserById(task.authorId)?.name || '—', icon: 'users' },
                  { label: 'Created', value: new Date(task.createdAt).toLocaleDateString('en', { month: 'short', day: 'numeric', year: 'numeric' }), icon: 'clock' },
                  { label: 'Labels', value: task.labels.join(', ') || '—', icon: 'tag' },
                ].map(({ label, value, icon }) => (
                  <div key={label} style={{
                    background: 'var(--bg-card)', border: '1px solid var(--border)',
                    borderRadius: 8, padding: '10px 12px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
                      <Icon name={icon} size={12} stroke="var(--fg-subtle)" />
                      <span style={{ fontSize: 11, color: 'var(--fg-subtle)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</span>
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--fg)', fontWeight: 500 }}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Description */}
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>Description</div>
                <div style={{
                  fontSize: 13, color: 'var(--fg)', lineHeight: 1.65,
                  background: 'var(--bg-card)', border: '1px solid var(--border)',
                  borderRadius: 10, padding: '14px 16px',
                }}>
                  {task.description}
                </div>
              </div>
            </div>
          )}

          {/* ── SOLUTIONS TAB ── */}
          {activeTab === 'solutions' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Decision criteria reminder */}
              {task.decisionCriteria.length > 0 && (
                <div style={{
                  background: 'oklch(0.96 0.03 252)', border: '1px solid oklch(0.88 0.06 252)',
                  borderRadius: 8, padding: '10px 14px',
                }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'oklch(0.45 0.14 252)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Decision Criteria
                  </div>
                  {task.decisionCriteria.map((dc, i) => (
                    <div key={dc.id} style={{ fontSize: 12, color: 'oklch(0.40 0.10 252)', marginBottom: 2 }}>
                      {i + 1}. {dc.description}
                    </div>
                  ))}
                </div>
              )}

              {task.solutions.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--fg-muted)', fontSize: 13 }}>
                  No solutions submitted yet.<br />
                  <span style={{ color: 'var(--fg-subtle)', fontSize: 12 }}>Lead assignees submit their solutions when they complete their workflow.</span>
                </div>
              ) : (
                task.solutions.map(sol => (
                  <SolutionCard
                    key={sol.id}
                    solution={sol}
                    isDecisionMaker={isDecisionMaker}
                    isCurrentUser={sol.assigneeId === currentUserId}
                    onAccept={handleAccept}
                    onRevision={(id) => setRevisionModalFor(id)}
                  />
                ))
              )}

              {/* Submit own solution (if current user is lead and in done status) */}
              {myAssignee?.role === 'lead' && !task.solutions.find(s => s.assigneeId === currentUserId) && (
                <div style={{
                  border: '2px dashed var(--border)', borderRadius: 10,
                  padding: '20px', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 13, color: 'var(--fg-muted)', marginBottom: 10 }}>
                    You haven't submitted your solution yet.
                  </div>
                  <Btn variant="default" size="sm">
                    <Icon name="zap" size={13} /> Submit Solution
                  </Btn>
                </div>
              )}
            </div>
          )}

          {/* ── COMMENTS TAB ── */}
          {activeTab === 'comments' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {task.comments.length === 0
                ? <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--fg-muted)', fontSize: 13 }}>No comments yet.</div>
                : task.comments.map(c => <CommentItem key={c.id} comment={c} />)
              }
              {/* Comment box */}
              <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <Avatar userId={currentUserId} size={28} />
                <div style={{ flex: 1 }}>
                  <textarea
                    placeholder="Add a comment… (@ to mention)"
                    style={{
                      width: '100%', minHeight: 72, padding: '8px 12px',
                      border: '1.5px solid var(--border)', borderRadius: 8,
                      background: 'var(--bg)', color: 'var(--fg)',
                      fontSize: 13, fontFamily: 'inherit', resize: 'vertical', outline: 'none',
                      boxSizing: 'border-box',
                    }}
                    onFocus={e => { e.target.style.borderColor = 'var(--primary)'; }}
                    onBlur={e => { e.target.style.borderColor = 'var(--border)'; }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 6 }}>
                    <Btn variant="default" size="sm">Save</Btn>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── HISTORY TAB ── */}
          {activeTab === 'history' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {task.history.length === 0
                ? <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--fg-muted)', fontSize: 13 }}>No history yet.</div>
                : [...task.history].reverse().map(h => <HistoryItem key={h.id} item={h} />)
              }
            </div>
          )}
        </div>
      </div>

      {/* Revision modal */}
      {revisionModalFor && (
        <RevisionModal
          solutionId={revisionModalFor}
          onConfirm={(comment) => handleRevision(revisionModalFor, comment)}
          onCancel={() => setRevisionModalFor(null)}
        />
      )}
    </>
  );
}

Object.assign(window, { TaskDetailPanel });
