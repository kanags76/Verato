// Verato — Mobile responsive primitives
// useViewport hook, MobileTopBar, MobileDrawer, MobileBottomNav,
// MobileCommitmentCard, SwipeReviewCard, light theme tokens.

const MOBILE_BREAKPOINT = 768;

const useViewport = () => {
  const [vw, setVw] = React.useState(typeof window !== 'undefined' ? window.innerWidth : 1280);
  React.useEffect(() => {
    const onResize = () => setVw(window.innerWidth);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);
  return { vw, isMobile: vw < MOBILE_BREAKPOINT, isTablet: vw >= MOBILE_BREAKPOINT && vw < 1024 };
};

// ── Theme tokens ─────────────────────────────────────────────────────────────

const LIGHT_THEME = {
  bg:       '#f5f5f9',
  surface:  '#ffffff',
  panel:    '#ffffff',
  border:   '#e2e2ec',
  borderFaint: '#eef0f4',
  text:     '#1a1a24',
  textMid:  '#5a5a72',
  textFaint:'#8a8a9e',
  accent:   '#7c6af7',
  accentDim:'#cfc8fb',
  overdue:  '#d8434a',
  overdueDim:'#fce8e9',
  risk:     '#b8741f',
  riskDim:  '#fbf0dc',
  onTrack:  '#3d8a63',
  onTrackDim:'#dff0e7',
  delivered:'#3d8a63',
  deliveredDim:'#dff0e7',
  deferred: '#7c7caa',
  deferredDim:'#eaeaf2',
  pending:  '#6a6a82',
  pendingDim:'#eaeaf2',
};

// Snapshot dark theme on first load so we can restore it.
if (!window.__DARK_THEME_SNAPSHOT) {
  window.__DARK_THEME_SNAPSHOT = { ...T };
}

const applyTheme = (mode) => {
  const src = mode === 'light' ? LIGHT_THEME : window.__DARK_THEME_SNAPSHOT;
  Object.keys(src).forEach(k => { T[k] = src[k]; });
  document.body.style.background = T.bg;
};

// ── Hamburger icon ────────────────────────────────────────────────────────────

const HamburgerIcon = ({ size = 22 }) =>
  React.createElement('svg', {
    width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
    stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round',
  },
    React.createElement('line', { x1: 3, y1: 6, x2: 21, y2: 6 }),
    React.createElement('line', { x1: 3, y1: 12, x2: 21, y2: 12 }),
    React.createElement('line', { x1: 3, y1: 18, x2: 21, y2: 18 }),
  );

// ── Mobile top bar ────────────────────────────────────────────────────────────

const MobileTopBar = ({ title, subtitle, onMenuClick, actions, onBack }) =>
  React.createElement('div', {
    style: {
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '11px 14px', borderBottom: `1px solid ${T.borderFaint}`,
      background: T.bg, position: 'sticky', top: 0, zIndex: 50,
      minHeight: 56,
    }
  },
    onBack
      ? React.createElement('button', {
          onClick: onBack,
          style: { background: 'none', border: 'none', color: T.text, cursor: 'pointer', padding: 8, marginLeft: -6, display: 'flex', borderRadius: 6 },
          'aria-label': 'Back',
        }, React.createElement(Icons.ArrowLeft, { size: 20 }))
      : React.createElement('button', {
          onClick: onMenuClick,
          style: { background: 'none', border: 'none', color: T.text, cursor: 'pointer', padding: 8, marginLeft: -6, display: 'flex', borderRadius: 6 },
          'aria-label': 'Open menu',
        }, React.createElement(HamburgerIcon, {})),
    React.createElement('div', { style: { flex: 1, minWidth: 0 } },
      React.createElement('div', { style: { fontSize: 15, fontWeight: 700, color: T.text, letterSpacing: '-0.01em', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, title),
      subtitle && React.createElement('div', { style: { fontSize: 11, color: T.textFaint, marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, subtitle),
    ),
    actions && React.createElement('div', { style: { display: 'flex', gap: 6, flexShrink: 0 } }, ...actions),
  );

// ── Mobile drawer (nav) ───────────────────────────────────────────────────────

const MobileDrawer = ({ open, onClose, activeScreen, onNavigate, onThemeToggle, theme }) => {
  return React.createElement(React.Fragment, {},
    open && React.createElement('div', {
      onClick: onClose,
      style: {
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 99,
        animation: 'fadeIn 0.18s ease',
        backdropFilter: 'blur(2px)',
      }
    }),
    React.createElement('div', {
      style: {
        position: 'fixed', top: 0, left: 0, bottom: 0, width: 280, maxWidth: '85vw',
        background: T.surface, borderRight: `1px solid ${T.borderFaint}`,
        zIndex: 100, transform: `translateX(${open ? '0' : '-100%'})`,
        transition: 'transform 0.22s cubic-bezier(.32,.72,0,1)',
        display: 'flex', flexDirection: 'column',
        boxShadow: open ? '4px 0 32px rgba(0,0,0,0.3)' : 'none',
      }
    },
      React.createElement('div', {
        style: { padding: '18px 20px', borderBottom: `1px solid ${T.borderFaint}`, display: 'flex', alignItems: 'center', gap: 9 }
      },
        React.createElement('div', { style: { width: 28, height: 28, borderRadius: 6, background: T.accent, display: 'flex', alignItems: 'center', justifyContent: 'center' } },
          React.createElement('span', { style: { color: '#fff', fontWeight: 800, fontSize: 13 } }, 'V')),
        React.createElement('span', { style: { color: T.text, fontWeight: 700, fontSize: 15, flex: 1, letterSpacing: '-0.02em' } }, 'Verato'),
        React.createElement('button', {
          onClick: onClose,
          style: { background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', padding: 6, marginRight: -6, display: 'flex' },
          'aria-label': 'Close menu',
        }, React.createElement(Icons.X, {})),
      ),
      React.createElement('nav', { style: { padding: '12px 10px', flex: 1 } },
        NAV_ITEMS.map(({ id, label, Icon: NavIcon }) => {
          const active = activeScreen === id ||
            (id === 'meetings' && ['upload', 'review', 'import'].includes(activeScreen)) ||
            (id === 'commitments' && activeScreen === 'commitment_detail');
          return React.createElement('div', {
            key: id,
            style: {
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '12px 14px', borderRadius: 8, marginBottom: 2,
              cursor: 'pointer',
              background: active ? `${T.accent}15` : 'transparent',
              color: active ? T.accent : T.textMid,
              fontWeight: active ? 600 : 500, fontSize: 14,
            },
            onClick: () => { onNavigate(id); onClose(); },
          },
            React.createElement(NavIcon, {}),
            label,
          );
        })
      ),
      onThemeToggle && React.createElement('button', {
        onClick: onThemeToggle,
        style: {
          margin: '0 14px 10px', padding: '10px 14px',
          background: T.surface, border: `1px solid ${T.borderFaint}`,
          color: T.textMid, fontSize: 12, fontWeight: 600,
          borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', gap: 8,
        }
      },
        React.createElement('span', { style: { fontSize: 14 } }, theme === 'dark' ? '☾' : '☀'),
        theme === 'dark' ? 'Switch to light' : 'Switch to dark',
      ),
      React.createElement('div', {
        style: { padding: '14px 18px', borderTop: `1px solid ${T.borderFaint}`, display: 'flex', alignItems: 'center', gap: 10 }
      },
        React.createElement(Avatar, { name: 'Sarah K.', size: 32 }),
        React.createElement('div', { style: { flex: 1, minWidth: 0 } },
          React.createElement('div', { style: { fontSize: 13, fontWeight: 600, color: T.text } }, 'Sarah K.'),
          React.createElement('div', { style: { fontSize: 11, color: T.textFaint } }, 'Acme Corp'),
        ),
      ),
    ),
  );
};

// ── Mobile bottom nav (alt nav style) ─────────────────────────────────────────

const MobileBottomNav = ({ activeScreen, onNavigate }) => {
  const items = NAV_ITEMS.slice(0, 5);
  return React.createElement('div', {
    style: {
      position: 'sticky', bottom: 0, left: 0, right: 0,
      background: T.surface, borderTop: `1px solid ${T.borderFaint}`,
      display: 'flex', justifyContent: 'space-around',
      padding: '6px 4px',
      paddingBottom: 'max(6px, env(safe-area-inset-bottom))',
      zIndex: 40, flexShrink: 0,
    }
  },
    items.map(({ id, label, Icon: NavIcon }) => {
      const active = activeScreen === id ||
        (id === 'meetings' && ['upload', 'review', 'import'].includes(activeScreen)) ||
        (id === 'commitments' && activeScreen === 'commitment_detail');
      return React.createElement('button', {
        key: id,
        onClick: () => onNavigate(id),
        style: {
          background: 'none', border: 'none', cursor: 'pointer',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
          padding: '7px 6px', flex: 1, minWidth: 0,
          color: active ? T.accent : T.textFaint,
          fontFamily: 'inherit', transition: 'color 0.15s',
        }
      },
        React.createElement(NavIcon, {}),
        React.createElement('span', { style: { fontSize: 10, fontWeight: active ? 600 : 500, letterSpacing: '0.01em' } }, label),
      );
    })
  );
};

// ── Mobile commitment card ────────────────────────────────────────────────────

const MobileCommitmentCard = ({ commitment, onClick }) => {
  const { normalised_text, status, risk_score, owner, deadline, meeting, priority, tags } = commitment;
  const isOverdue = deadline && new Date(deadline) < new Date() && !['delivered', 'cancelled', 'deferred'].includes(status);
  const effectiveStatus = isOverdue ? 'overdue' : status;

  const daysText = () => {
    if (!deadline) return null;
    const diff = Math.round((new Date(deadline) - new Date()) / 86400000);
    if (diff < 0) return `${Math.abs(diff)}d late`;
    if (diff === 0) return 'today';
    if (diff === 1) return 'tomorrow';
    if (diff < 7) return `in ${diff}d`;
    return new Date(deadline).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  };

  const priColor = priority === 'high' ? PRIORITY_META.high.color
    : priority === 'medium' ? PRIORITY_META.medium.color : 'transparent';

  return React.createElement('div', {
    onClick,
    style: {
      background: T.panel, border: `1px solid ${T.borderFaint}`,
      borderLeft: `3px solid ${priColor}`,
      borderRadius: 10, padding: '14px 14px 12px 13px',
      cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 10,
    }
  },
    React.createElement('div', { style: { display: 'flex', gap: 9, alignItems: 'flex-start' } },
      React.createElement(RiskDot, { score: risk_score }),
      React.createElement('div', { style: { flex: 1, minWidth: 0 } },
        React.createElement('div', { style: { fontSize: 14, fontWeight: 600, color: T.text, lineHeight: 1.35 } }, normalised_text),
        React.createElement('div', { style: { fontSize: 11, color: T.textFaint, marginTop: 5, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' } },
          React.createElement('span', {}, meeting?.title),
          tags?.length > 0 && React.createElement('span', { style: { color: T.textFaint } }, '·'),
          tags?.length > 0 && React.createElement('span', {
            style: { background: T.surface, border: `1px solid ${T.borderFaint}`, borderRadius: 3, padding: '0 5px', fontSize: 10 }
          }, typeof tags[0] === 'string' ? tags[0] : tags[0].label),
        ),
      ),
    ),
    React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' } },
      owner && React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6 } },
        React.createElement(Avatar, { name: owner.name, size: 20 }),
        React.createElement('span', { style: { fontSize: 12, color: T.textMid, fontWeight: 500 } }, owner.name.split(' ')[0]),
      ),
      deadline && React.createElement('span', {
        style: { fontSize: 11, color: isOverdue ? T.overdue : T.textFaint, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }
      }, daysText()),
      React.createElement('div', { style: { flex: 1 } }),
      React.createElement(StatusBadge, { status: effectiveStatus }),
    ),
  );
};

// ── Swipe review card stack ───────────────────────────────────────────────────

const SwipeReviewCard = ({ items: initialItems, meetingTitle, onBack, onDone }) => {
  const [items] = React.useState(initialItems);
  const [actions, setActions] = React.useState({}); // id -> 'confirmed' | 'rejected'
  const [idx, setIdx] = React.useState(0);
  const [dragX, setDragX] = React.useState(0);
  const [dragging, setDragging] = React.useState(false);
  const [exitDir, setExitDir] = React.useState(0); // 1 confirm, -1 reject, 0 idle
  const startX = React.useRef(0);
  const startY = React.useRef(0);
  const SWIPE_THRESHOLD = 90;

  const current = items[idx];
  const next = items[idx + 1];
  const remaining = items.length - idx;
  const confirmedCount = Object.values(actions).filter(a => a === 'confirmed').length;

  const finishSwipe = (action) => {
    const dir = action === 'confirm' ? 1 : action === 'reject' ? -1 : 0;
    if (dir === 0) {
      setDragX(0);
      setIdx(i => Math.min(i + 1, items.length));
      return;
    }
    setExitDir(dir);
    setActions(a => ({ ...a, [current.id]: dir === 1 ? 'confirmed' : 'rejected' }));
    setTimeout(() => {
      setExitDir(0);
      setDragX(0);
      setIdx(i => i + 1);
    }, 220);
  };

  const onDown = (e) => {
    const t = e.touches?.[0] || e;
    setDragging(true);
    startX.current = t.clientX;
    startY.current = t.clientY;
  };
  const onMove = (e) => {
    if (!dragging) return;
    const t = e.touches?.[0] || e;
    setDragX(t.clientX - startX.current);
  };
  const onUp = () => {
    if (!dragging) return;
    setDragging(false);
    if (Math.abs(dragX) > SWIPE_THRESHOLD) {
      finishSwipe(dragX > 0 ? 'confirm' : 'reject');
    } else {
      setDragX(0);
    }
  };

  if (idx >= items.length) {
    return React.createElement('div', {
      style: { padding: '32px 20px', fontFamily: "'Plus Jakarta Sans', sans-serif", textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, paddingTop: 80 }
    },
      React.createElement('div', {
        style: { width: 72, height: 72, borderRadius: '50%', background: T.onTrackDim, color: T.onTrack, display: 'flex', alignItems: 'center', justifyContent: 'center' }
      }, React.createElement(Icons.Check, { size: 32 })),
      React.createElement('h3', { style: { margin: 0, fontSize: 20, fontWeight: 700, color: T.text } }, 'All reviewed'),
      React.createElement('p', { style: { margin: 0, fontSize: 14, color: T.textFaint, maxWidth: 280 } },
        `${confirmedCount} commitment${confirmedCount !== 1 ? 's' : ''} confirmed and added to your tracker.`
      ),
      React.createElement('button', {
        onClick: onDone,
        style: {
          marginTop: 12, padding: '13px 28px', borderRadius: 8,
          background: T.accent, color: '#fff', border: 'none',
          fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
        }
      }, 'Go to dashboard →'),
    );
  }

  const rotate = (dragX + exitDir * 320) * 0.05;
  const translateX = dragX + exitDir * 360;
  const opacity = Math.max(0.1, 1 - Math.abs(translateX) / 360);
  const confColor = current.confidence >= 0.80 ? T.onTrack : current.confidence >= 0.65 ? T.risk : T.overdue;

  return React.createElement('div', {
    style: { padding: '16px 16px 24px', fontFamily: "'Plus Jakarta Sans', sans-serif", display: 'flex', flexDirection: 'column', gap: 14 }
  },
    React.createElement('div', {},
      React.createElement('h2', { style: { margin: 0, fontSize: 17, fontWeight: 700, color: T.text, letterSpacing: '-0.01em' } }, meetingTitle),
      React.createElement('div', { style: { fontSize: 12, color: T.textFaint, marginTop: 4, display: 'flex', justifyContent: 'space-between' } },
        React.createElement('span', {}, `${idx + 1} of ${items.length}`),
        React.createElement('span', { style: { color: T.onTrack, fontWeight: 600 } }, `${confirmedCount} confirmed`),
      ),
    ),
    React.createElement('div', { style: { height: 3, background: T.border, borderRadius: 2, overflow: 'hidden' } },
      React.createElement('div', { style: { width: `${(idx / items.length) * 100}%`, height: '100%', background: T.accent, transition: 'width 0.3s' } }),
    ),
    React.createElement('div', { style: { position: 'relative', height: 360, marginTop: 4 } },
      next && React.createElement('div', {
        style: {
          position: 'absolute', inset: 0, background: T.panel, border: `1px solid ${T.borderFaint}`,
          borderRadius: 14, padding: 18,
          transform: 'scale(0.95) translateY(10px)', opacity: 0.6, pointerEvents: 'none',
        }
      },
        React.createElement('div', { style: { fontSize: 14, fontWeight: 600, color: T.textFaint, lineHeight: 1.35 } }, next.normalised_text),
      ),
      React.createElement('div', {
        onMouseDown: onDown, onMouseMove: onMove, onMouseUp: onUp, onMouseLeave: onUp,
        onTouchStart: onDown, onTouchMove: onMove, onTouchEnd: onUp,
        style: {
          position: 'absolute', inset: 0, background: T.panel,
          border: `1.5px solid ${T.border}`, borderRadius: 14, padding: 20,
          transform: `translateX(${translateX}px) rotate(${rotate}deg)`,
          opacity, transition: dragging ? 'none' : 'transform 0.22s, opacity 0.22s',
          cursor: dragging ? 'grabbing' : 'grab', userSelect: 'none', touchAction: 'pan-y',
          display: 'flex', flexDirection: 'column', gap: 16,
          boxShadow: dragging || exitDir ? '0 14px 32px rgba(0,0,0,0.35)' : '0 4px 14px rgba(0,0,0,0.18)',
        }
      },
        (dragX > 30 || exitDir > 0) && React.createElement('div', {
          style: {
            position: 'absolute', top: 16, right: 16, padding: '5px 11px',
            border: `2px solid ${T.onTrack}`, color: T.onTrack, background: 'transparent',
            borderRadius: 6, fontSize: 12, fontWeight: 800, letterSpacing: '0.12em',
            transform: 'rotate(8deg)', opacity: exitDir ? 1 : Math.min(1, dragX / 80),
            fontFamily: "'JetBrains Mono', monospace",
          }
        }, 'CONFIRM'),
        (dragX < -30 || exitDir < 0) && React.createElement('div', {
          style: {
            position: 'absolute', top: 16, left: 16, padding: '5px 11px',
            border: `2px solid ${T.overdue}`, color: T.overdue, background: 'transparent',
            borderRadius: 6, fontSize: 12, fontWeight: 800, letterSpacing: '0.12em',
            transform: 'rotate(-8deg)', opacity: exitDir ? 1 : Math.min(1, -dragX / 80),
            fontFamily: "'JetBrains Mono', monospace",
          }
        }, 'REJECT'),

        React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' } },
          React.createElement('span', {
            style: { fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 700, color: confColor,
              background: confColor + '22', padding: '3px 8px', borderRadius: 4 }
          }, `${current.confidence.toFixed(2)} confidence`),
          current.confidence < 0.80 && React.createElement('span', { style: { fontSize: 10, color: T.risk, fontWeight: 600 } }, '⚠ review'),
        ),

        React.createElement('div', { style: { fontSize: 18, fontWeight: 600, color: T.text, lineHeight: 1.4, flex: 1 } },
          current.normalised_text
        ),

        React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 12 } },
          React.createElement(Avatar, { name: current.owner_name, size: 32 }),
          React.createElement('div', { style: { flex: 1, minWidth: 0 } },
            React.createElement('div', { style: { fontSize: 13, fontWeight: 600, color: T.text } }, current.owner_name),
            current.deadline_resolved && React.createElement('div', {
              style: { fontSize: 11, color: T.textFaint, marginTop: 2, fontFamily: "'JetBrains Mono', monospace" }
            }, new Date(current.deadline_resolved).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })),
          ),
          React.createElement(PriorityBadge, { priority: current.priority || 'medium' }),
        ),

        (current.tags?.length > 0) && React.createElement('div', { style: { display: 'flex', gap: 5, flexWrap: 'wrap' } },
          current.tags.slice(0, 4).map((t, i) =>
            React.createElement('span', {
              key: i,
              style: { background: T.surface, border: `1px solid ${T.borderFaint}`, borderRadius: 3, padding: '2px 7px', fontSize: 11, color: T.textMid }
            }, typeof t === 'string' ? t : t.label)
          )
        ),
      ),
    ),
    React.createElement('div', { style: { display: 'flex', gap: 14, justifyContent: 'center', paddingTop: 8 } },
      React.createElement('button', {
        onClick: () => finishSwipe('reject'),
        'aria-label': 'Reject',
        style: { width: 56, height: 56, borderRadius: '50%', border: `1.5px solid ${T.overdue}55`, background: T.overdueDim, color: T.overdue, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
      }, React.createElement(Icons.X, { size: 22 })),
      React.createElement('button', {
        onClick: () => finishSwipe('skip'),
        style: { width: 48, height: 48, alignSelf: 'center', borderRadius: '50%', border: `1.5px solid ${T.border}`, background: T.surface, color: T.textMid, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 600, fontFamily: 'inherit' },
      }, 'skip'),
      React.createElement('button', {
        onClick: () => finishSwipe('confirm'),
        'aria-label': 'Confirm',
        style: { width: 56, height: 56, borderRadius: '50%', border: `1.5px solid ${T.onTrack}55`, background: T.onTrackDim, color: T.onTrack, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
      }, React.createElement(Icons.Check, { size: 24 })),
    ),
  );
};

Object.assign(window, {
  useViewport, MOBILE_BREAKPOINT,
  MobileTopBar, MobileDrawer, MobileBottomNav,
  MobileCommitmentCard, SwipeReviewCard,
  LIGHT_THEME, applyTheme, HamburgerIcon,
});
