
// ─── Sidebar ──────────────────────────────────────────────────────────────────
function Sidebar({ projects, currentProject, setCurrentProject, currentView, setCurrentView }) {
  const navItems = [
    { id: 'dashboard', icon: 'dashboard', label: 'My Dashboard' },
    { id: 'board',     icon: 'kanban',    label: 'Board' },
    { id: 'backlog',   icon: 'backlog',   label: 'Backlog' },
    { id: 'members',   icon: 'users',     label: 'Members' },
    { id: 'settings',  icon: 'settings',  label: 'Settings' },
  ];

  return (
    <div style={{
      width: 220, flexShrink: 0,
      background: 'var(--sidebar-bg)',
      borderRight: '1px solid var(--sidebar-border)',
      display: 'flex', flexDirection: 'column',
      height: '100%', overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{
        height: 52, display: 'flex', alignItems: 'center',
        padding: '0 16px', borderBottom: '1px solid var(--sidebar-border)',
        gap: 10, flexShrink: 0,
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 7,
          background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon name="zap" size={15} stroke="#fff" fill="none" />
        </div>
        <span style={{ fontSize: 15, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>
          TaskTrack
        </span>
      </div>

      {/* All Projects button */}
      <div style={{ padding: '10px 8px 0', flexShrink: 0 }}>
        <button onClick={() => setCurrentView('projects')}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '7px 9px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: currentView === 'projects' ? 'var(--sidebar-active)' : 'transparent',
            color: currentView === 'projects' ? 'var(--sidebar-fg-active)' : 'var(--sidebar-fg)',
            fontSize: 13, fontWeight: currentView === 'projects' ? 600 : 400,
            fontFamily: 'inherit', textAlign: 'left', transition: 'background 0.15s',
          }}
          onMouseEnter={e => { if (currentView !== 'projects') e.currentTarget.style.background = 'var(--sidebar-hover)'; }}
          onMouseLeave={e => { if (currentView !== 'projects') e.currentTarget.style.background = 'transparent'; }}
        >
          <Icon name="list" size={15} stroke={currentView === 'projects' ? 'var(--sidebar-fg-active)' : 'var(--sidebar-fg)'} />
          All Projects
        </button>
      </div>

      {/* Project selector */}
      <div style={{ padding: '12px 8px 4px', flexShrink: 0 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--sidebar-fg)', letterSpacing: '0.08em', textTransform: 'uppercase', padding: '0 8px 6px' }}>
          Projects
        </div>
        {projects.map(p => (
          <button key={p.id} onClick={() => setCurrentProject(p)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 8,
              padding: '7px 8px', borderRadius: 6, border: 'none', cursor: 'pointer',
              background: p.id === currentProject.id ? 'var(--sidebar-active)' : 'transparent',
              color: p.id === currentProject.id ? 'var(--sidebar-fg-active)' : 'var(--sidebar-fg)',
              fontSize: 13, fontWeight: p.id === currentProject.id ? 600 : 400,
              fontFamily: 'inherit', textAlign: 'left', transition: 'background 0.15s',
            }}
            onMouseEnter={e => { if (p.id !== currentProject.id) e.currentTarget.style.background = 'var(--sidebar-hover)'; }}
            onMouseLeave={e => { if (p.id !== currentProject.id) e.currentTarget.style.background = 'transparent'; }}
          >
            <div style={{
              width: 20, height: 20, borderRadius: 5, background: p.color,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 9, fontWeight: 700, color: '#fff', flexShrink: 0,
            }}>{p.key}</div>
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {p.name}
            </span>
          </button>
        ))}
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--sidebar-border)', margin: '8px 16px' }} />

      {/* Nav items */}
      <nav style={{ flex: 1, padding: '0 8px', display: 'flex', flexDirection: 'column', gap: 1 }}>
        {navItems.map(item => {
          const active = currentView === item.id;
          return (
            <button key={item.id} onClick={() => setCurrentView(item.id)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 9,
                padding: '7px 9px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: active ? 'var(--sidebar-active)' : 'transparent',
                color: active ? 'var(--sidebar-fg-active)' : 'var(--sidebar-fg)',
                fontSize: 13, fontWeight: active ? 600 : 400,
                fontFamily: 'inherit', textAlign: 'left', transition: 'background 0.15s',
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--sidebar-hover)'; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
            >
              <Icon name={item.icon} size={15} stroke={active ? 'var(--sidebar-fg-active)' : 'var(--sidebar-fg)'} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* User */}
      <div style={{
        padding: '12px 12px', borderTop: '1px solid var(--sidebar-border)',
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
      }}>
        <Avatar userId={window._appState?.currentUserId || 'u1'} size={28} />
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--sidebar-fg-active)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {getUserById(window._appState?.currentUserId || 'u1')?.name}
          </div>
          <div style={{ fontSize: 11, color: 'var(--sidebar-fg)' }}>
            {getUserById(window._appState?.currentUserId || 'u1')?.role}
          </div>
        </div>
        <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--sidebar-fg)', padding: 4, borderRadius: 4 }}>
          <Icon name="settings" size={13} stroke="var(--sidebar-fg)" />
        </button>
      </div>
    </div>
  );
}

// ─── Header ───────────────────────────────────────────────────────────────────
function Header({ project, view, theme, setTheme, unreadCount, notifOpen, setNotifOpen, currentUserId, onCreateTask }) {
  const viewLabels = { board: 'Board', backlog: 'Backlog', dashboard: 'My Dashboard', members: 'Members', settings: 'Settings' };
  return (
    <div style={{
      height: 52, display: 'flex', alignItems: 'center',
      padding: '0 20px', borderBottom: '1px solid var(--border)',
      background: 'var(--bg)', gap: 16, flexShrink: 0, zIndex: 10,
    }}>
      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{
          width: 18, height: 18, borderRadius: 4, background: project.color,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 8, fontWeight: 700, color: '#fff',
        }}>{project.key}</div>
        <span style={{ fontSize: 13, color: 'var(--fg-muted)' }}>{project.name}</span>
        <Icon name="chevronRight" size={13} stroke="var(--fg-subtle)" />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>{viewLabels[view] || view}</span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Create button */}
      <Btn variant="default" size="sm" onClick={onCreateTask}>
        <Icon name="plus" size={13} /> Create
      </Btn>

      {/* Search */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--bg-muted)', border: '1px solid var(--border)',
        borderRadius: 7, padding: '5px 12px', cursor: 'text', width: 200,
      }}
        onFocus={e => e.currentTarget.style.borderColor = 'var(--primary)'}
        onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
      >
        <Icon name="search" size={14} stroke="var(--fg-subtle)" />
        <span style={{ fontSize: 13, color: 'var(--fg-subtle)' }}>Search tasks…</span>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--fg-subtle)', background: 'var(--bg-hover)', borderRadius: 3, padding: '1px 5px', border: '1px solid var(--border)' }}>⌘K</span>
      </div>

      {/* Theme toggle */}
      <button onClick={() => setTheme(t => t === 'light' ? 'dark' : 'light')}
        title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        style={{
          background: 'none', border: '1px solid var(--border)', borderRadius: 7,
          padding: '5px 8px', cursor: 'pointer', color: 'var(--fg-muted)',
          display: 'flex', alignItems: 'center',
        }}>
        <Icon name={theme === 'light' ? 'moon' : 'sun'} size={15} stroke="var(--fg-muted)" />
      </button>

      {/* Notifications */}
      <div style={{ position: 'relative' }}>
        <button onClick={() => setNotifOpen(o => !o)}
          style={{
            background: notifOpen ? 'var(--bg-hover)' : 'none',
            border: '1px solid var(--border)', borderRadius: 7,
            padding: '5px 8px', cursor: 'pointer', color: 'var(--fg-muted)',
            display: 'flex', alignItems: 'center', position: 'relative',
          }}>
          <Icon name="bell" size={15} stroke="var(--fg-muted)" />
          {unreadCount > 0 && (
            <div style={{
              position: 'absolute', top: 3, right: 3,
              width: 8, height: 8, borderRadius: '50%',
              background: 'oklch(0.55 0.20 25)',
              border: '1.5px solid var(--bg)',
            }} />
          )}
        </button>

        {/* Notification panel */}
        {notifOpen && (
          <NotificationPanel
            notifications={window.NOTIFICATIONS}
            onClose={() => setNotifOpen(false)}
          />
        )}
      </div>
    </div>
  );
}

// ─── Notification Panel ───────────────────────────────────────────────────────
function NotificationPanel({ notifications, onClose }) {
  const typeIcon = { revision: 'arrowRight', decision: 'award', comment: 'message', mention: 'users', decided: 'check' };
  const typeColor = { revision: 'oklch(0.50 0.15 25)', decision: 'var(--primary)', comment: 'var(--fg-muted)', mention: 'oklch(0.52 0.14 160)', decided: 'oklch(0.45 0.14 150)' };

  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 49 }} />
      <div style={{
        position: 'absolute', top: 'calc(100% + 8px)', right: 0, zIndex: 50,
        width: 340, background: 'var(--bg-card)',
        border: '1px solid var(--border)', borderRadius: 10,
        boxShadow: 'var(--shadow-lg)', overflow: 'hidden',
      }}>
        <div style={{
          padding: '12px 16px', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--fg)' }}>Notifications</span>
          <div style={{ display: 'flex', gap: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--primary)', cursor: 'pointer', fontWeight: 500 }}>Mark all read</span>
          </div>
        </div>
        {notifications.map(n => (
          <div key={n.id} style={{
            display: 'flex', gap: 10, padding: '10px 16px',
            borderBottom: '1px solid var(--border-subtle)',
            background: n.read ? 'transparent' : 'var(--bg-muted)',
            cursor: 'pointer', transition: 'background 0.15s',
          }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = n.read ? 'transparent' : 'var(--bg-muted)'}
          >
            <div style={{
              width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
              background: 'var(--bg-muted)', border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Icon name={typeIcon[n.type] || 'bell'} size={12} stroke={typeColor[n.type] || 'var(--fg-muted)'} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, color: 'var(--fg)', lineHeight: 1.4 }}>{n.text}</div>
              <div style={{ fontSize: 11, color: 'var(--fg-subtle)', marginTop: 2 }}>{n.time}</div>
            </div>
            {!n.read && <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)', flexShrink: 0, marginTop: 6 }} />}
          </div>
        ))}
      </div>
    </>
  );
}

// ─── Placeholder View ─────────────────────────────────────────────────────────
function PlaceholderView({ view }) {
  const labels = { dashboard: 'My Dashboard', backlog: 'Backlog', members: 'Members', settings: 'Settings' };
  const icons =  { dashboard: 'dashboard', backlog: 'backlog', members: 'users', settings: 'settings' };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: 'var(--fg-muted)' }}>
      <div style={{ width: 48, height: 48, borderRadius: 12, background: 'var(--bg-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon name={icons[view] || 'dashboard'} size={22} stroke="var(--fg-subtle)" />
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--fg)' }}>{labels[view] || view}</div>
      <div style={{ fontSize: 13, color: 'var(--fg-subtle)' }}>This view is coming soon — prototyped in next iteration</div>
    </div>
  );
}

// ─── User Switcher (Tweaks) ───────────────────────────────────────────────────
function TweaksFloating({ currentUserId, setCurrentUserId, tweaksOpen, setTweaksOpen }) {
  return (
    <div style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 200 }}>
      <button onClick={() => setTweaksOpen(o => !o)}
        style={{
          width: 40, height: 40, borderRadius: '50%',
          background: 'var(--primary)', color: '#fff',
          border: 'none', cursor: 'pointer', fontSize: 18,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: 'var(--shadow-lg)',
        }} title="Tweaks">
        ✦
      </button>
      {tweaksOpen && (
        <div style={{
          position: 'absolute', bottom: 50, right: 0,
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 10, padding: 16, width: 220, boxShadow: 'var(--shadow-lg)',
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--fg)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Tweaks</div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--fg-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>View as user</div>
          {USERS.map(u => (
            <button key={u.id} onClick={() => { setCurrentUserId(u.id); window._appState = { currentUserId: u.id }; }}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 8px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: u.id === currentUserId ? 'var(--bg-muted)' : 'transparent',
                fontFamily: 'inherit', textAlign: 'left',
                outline: u.id === currentUserId ? '1.5px solid var(--primary)' : 'none',
              }}>
              <Avatar userId={u.id} size={22} />
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--fg)' }}>{u.name}</div>
                <div style={{ fontSize: 10, color: 'var(--fg-muted)' }}>{u.role}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────
function App() {
  const savedTheme = localStorage.getItem('tt-theme') || 'light';
  const [theme, setThemeState] = React.useState(savedTheme);
  const [currentProject, setCurrentProject] = React.useState(PROJECTS[0]);
  const [currentUserId, setCurrentUserId] = React.useState('u1');
  const [currentView, setCurrentView] = React.useState('dashboard');
  const [selectedTask, setSelectedTask] = React.useState(null);
  const [notifOpen, setNotifOpen] = React.useState(false);
  const [tweaksOpen, setTweaksOpen] = React.useState(false);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [settingsProject, setSettingsProject] = React.useState(null);

  window._appState = { currentUserId };

  function setTheme(fn) {
    setThemeState(prev => {
      const next = typeof fn === 'function' ? fn(prev) : fn;
      localStorage.setItem('tt-theme', next);
      return next;
    });
  }

  // Apply theme to root
  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const unread = NOTIFICATIONS.filter(n => !n.read).length;

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg)' }}>
      <Sidebar
        projects={PROJECTS}
        currentProject={currentProject}
        setCurrentProject={p => { setCurrentProject(p); setCurrentView('board'); }}
        currentView={currentView}
        setCurrentView={v => {
          if (v === 'settings') { setSettingsProject(currentProject); }
          setCurrentView(v);
        }}
      />

      {/* Main content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Header
          project={currentProject}
          view={currentView}
          theme={theme}
          setTheme={setTheme}
          unreadCount={unread}
          notifOpen={notifOpen}
          setNotifOpen={setNotifOpen}
          currentUserId={currentUserId}
          onCreateTask={() => setCreateOpen(true)}
        />

        <div style={{ flex: 1, overflow: 'hidden' }}>
          {currentView === 'board' && (
            <KanbanBoard project={currentProject} currentUserId={currentUserId} onTaskClick={setSelectedTask} onCreateTask={() => setCreateOpen(true)} />
          )}
          {currentView === 'dashboard' && (
            <Dashboard currentUserId={currentUserId} onTaskClick={setSelectedTask} onCreateTask={() => setCreateOpen(true)} />
          )}
          {currentView === 'backlog' && (
            <BacklogView project={currentProject} currentUserId={currentUserId} onTaskClick={setSelectedTask} onCreateTask={() => setCreateOpen(true)} />
          )}
          {currentView === 'projects' && (
            <ProjectsOverview
              currentUserId={currentUserId}
              onOpenProject={p => { setCurrentProject(p); setCurrentView('board'); }}
              onOpenSettings={p => { setSettingsProject(p); setCurrentView('settings'); }}
            />
          )}
          {currentView === 'settings' && settingsProject && (
            <ProjectSettings
              project={settingsProject}
              onBack={() => setCurrentView('projects')}
            />
          )}
          {currentView === 'settings' && !settingsProject && (
            <ProjectSettings
              project={currentProject}
              onBack={() => setCurrentView('board')}
            />
          )}
          {!['board','dashboard','backlog','projects','settings'].includes(currentView) && (
            <PlaceholderView view={currentView} />
          )}
        </div>
      </div>

      {/* Create task panel */}
      {createOpen && (
        <CreateTaskPanel
          project={currentProject}
          currentUserId={currentUserId}
          onClose={() => setCreateOpen(false)}
          onCreated={() => setCreateOpen(false)}
        />
      )}

      {/* Task detail panel */}
      {selectedTask && (
        <TaskDetailPanel
          task={selectedTask}
          currentUserId={currentUserId}
          onClose={() => setSelectedTask(null)}
        />
      )}

      {/* Tweaks */}
      <TweaksFloating
        currentUserId={currentUserId}
        setCurrentUserId={(id) => { setCurrentUserId(id); window._appState = { currentUserId: id }; }}
        tweaksOpen={tweaksOpen}
        setTweaksOpen={setTweaksOpen}
      />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
