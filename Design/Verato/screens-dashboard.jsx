// Verato — Dashboard + Commitment Detail screens

// ── Stat card ────────────────────────────────────────────────────────────────

const StatCard = ({ value, label, color, onClick }) => {
  const [hov, setHov] = React.useState(false);
  return React.createElement('div', {
    style: {
      background: T.panel, border: `1px solid ${hov && onClick ? T.border : T.borderFaint}`,
      borderRadius: 8, padding: '18px 20px', cursor: onClick ? 'pointer' : 'default',
      transition: 'border-color 0.15s',
    },
    onClick, onMouseEnter: () => setHov(true), onMouseLeave: () => setHov(false),
  },
    React.createElement('div', {
      style: { fontSize: 32, fontWeight: 800, color: color || T.text, letterSpacing: '-0.04em', lineHeight: 1, fontFamily: "'JetBrains Mono', monospace" }
    }, value),
    React.createElement('div', {
      style: { fontSize: 11, color: T.textFaint, marginTop: 6, textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }
    }, label),
  );
};

// ── Commitment row ────────────────────────────────────────────────────────────

const CommitmentRow = ({ commitment, onClick, onTagClick }) => {
  const [hov, setHov] = React.useState(false);
  const { normalised_text, status, risk_score, owner, deadline, meeting, priority, tags } = commitment;

  const isOverdue = deadline && new Date(deadline) < new Date() && !['delivered','cancelled','deferred'].includes(status);
  const effectiveStatus = isOverdue ? 'overdue' : status;

  const daysText = () => {
    if (!deadline) return null;
    const d = new Date(deadline);
    const now = new Date();
    const diff = Math.round((d - now) / 86400000);
    if (diff < 0) return `${Math.abs(diff)}d overdue`;
    if (diff === 0) return 'due today';
    if (diff === 1) return 'due tomorrow';
    return `due in ${diff}d`;
  };

  const nudgeStatus = commitment.escalations?.length
    ? `Nudge sent ${commitment.escalations[commitment.escalations.length - 1].method === 'slack' ? '· ' : ''}${commitment.escalations.length} time${commitment.escalations.length > 1 ? 's' : ''}`
    : null;

  return React.createElement('div', {
    style: {
      display: 'flex', alignItems: 'center', gap: 14,
      padding: '14px 20px', cursor: 'pointer',
      borderBottom: `1px solid ${T.borderFaint}`,
      background: hov ? `${T.panel}88` : 'transparent',
      transition: 'background 0.1s',
      borderLeft: `3px solid ${priority === 'high' ? PRIORITY_META.high.color : priority === 'medium' ? PRIORITY_META.medium.color : 'transparent'}`,
      paddingLeft: 17,
    },
    onClick, onMouseEnter: () => setHov(true), onMouseLeave: () => setHov(false),
  },
    React.createElement(RiskDot, { score: risk_score }),
    React.createElement('div', { style: { flex: 1, minWidth: 0 } },
      React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 } },
        React.createElement('span', {
          style: { fontSize: 13, fontWeight: 600, color: T.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }
        }, normalised_text),
      ),
      React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: T.textFaint, flexWrap: 'wrap' } },
        React.createElement('span', {}, meeting?.title),
        tags?.length > 0 && React.createElement(React.Fragment, {},
          React.createElement('span', {}, '·'),
          tags.slice(0, 2).map((t, i) => {
            const label = typeof t === 'string' ? t : t.label;
            return React.createElement('span', {
              key: i,
              onClick: (e) => { e.stopPropagation(); onTagClick && onTagClick(label); },
              style: {
                background: T.surface, border: `1px solid ${T.borderFaint}`, borderRadius: 3,
                padding: '0 5px', fontSize: 10, color: T.textMid,
                cursor: onTagClick ? 'pointer' : 'default',
                transition: 'all 0.1s',
              },
              onMouseEnter: (e) => { if (onTagClick) { e.target.style.borderColor = T.accent; e.target.style.color = T.accent; } },
              onMouseLeave: (e) => { if (onTagClick) { e.target.style.borderColor = T.borderFaint; e.target.style.color = T.textMid; } },
            }, label);
          }),
          tags.length > 2 && React.createElement('span', { style: { fontSize: 10 } }, `+${tags.length - 2}`),
        ),
        nudgeStatus && React.createElement(React.Fragment, {},
          React.createElement('span', {}, '·'),
          React.createElement('span', {}, nudgeStatus),
        ),
      ),
    ),
    React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 } },
      priority && React.createElement(PriorityBadge, { priority }),
      owner && React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6 } },
        React.createElement(Avatar, { name: owner.name, size: 22 }),
        React.createElement('span', { style: { fontSize: 12, color: T.textMid } }, owner.name),
      ),
      deadline && React.createElement('span', {
        style: { fontSize: 11, color: T.textFaint, fontFamily: "'JetBrains Mono', monospace", minWidth: 80, textAlign: 'right' }
      }, new Date(deadline).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })),
      React.createElement(StatusBadge, { status: effectiveStatus }),
    ),
  );
};

// ── Dashboard ─────────────────────────────────────────────────────────────────

const Dashboard = ({ onNavigate, onViewCommitment, onUpload }) => {
  const { isMobile } = (window.useViewport ? window.useViewport() : { isMobile: false });
  const [filter, setFilter] = React.useState('all');
  const [priorityFilter, setPriorityFilter] = React.useState(null); // null | 'high' | 'medium' | 'low'
  const [tagFilter, setTagFilter] = React.useState(null);

  const stats = {
    overdue: MOCK_COMMITMENTS.filter(c => c.status === 'escalated' && new Date(c.deadline) < new Date()).length,
    at_risk: MOCK_COMMITMENTS.filter(c => c.status === 'at_risk').length,
    on_track: MOCK_COMMITMENTS.filter(c => c.status === 'active').length,
    total: MOCK_COMMITMENTS.filter(c => !['delivered','cancelled'].includes(c.status)).length,
  };

  const filters = [
    { id: 'all', label: 'All active' },
    { id: 'escalated', label: 'Needs attention' },
    { id: 'at_risk', label: 'At risk' },
    { id: 'active', label: 'On track' },
    { id: 'delivered', label: 'Delivered' },
  ];

  let filtered = filter === 'all'
    ? MOCK_COMMITMENTS.filter(c => !['cancelled'].includes(c.status))
    : MOCK_COMMITMENTS.filter(c => c.status === filter);
  if (priorityFilter) filtered = filtered.filter(c => c.priority === priorityFilter);
  if (tagFilter) filtered = filtered.filter(c => (c.tags || []).some(t => (typeof t === 'string' ? t : t.label) === tagFilter));

  // Sort: overdue first, then by risk score
  const sorted = [...filtered].sort((a, b) => {
    const aOver = new Date(a.deadline) < new Date() && !['delivered','cancelled','deferred'].includes(a.status);
    const bOver = new Date(b.deadline) < new Date() && !['delivered','cancelled','deferred'].includes(b.status);
    if (aOver && !bOver) return -1;
    if (!aOver && bOver) return 1;
    return b.risk_score - a.risk_score;
  });

  return React.createElement('div', {
    style: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', fontFamily: "'Plus Jakarta Sans', sans-serif" }
  },
    // Header
    !isMobile && React.createElement('div', {
      style: { padding: '24px 32px 20px', borderBottom: `1px solid ${T.borderFaint}` }
    },
      React.createElement('div', { style: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 } },
        React.createElement('div', {},
          React.createElement('h1', { style: { margin: 0, fontSize: 20, fontWeight: 700, color: T.text, letterSpacing: '-0.02em' } }, 'Dashboard'),
          React.createElement('p', { style: { margin: '3px 0 0', fontSize: 12, color: T.textFaint } }, 'Week of 28 Apr 2026'),
        ),
        React.createElement('div', { style: { display: 'flex', gap: 8 } },
          React.createElement(Btn, { variant: 'secondary', size: 'sm', icon: Icons.Import, onClick: () => onNavigate('import') }, 'Import'),
          React.createElement(Btn, { variant: 'primary', size: 'sm', icon: Icons.Upload, onClick: onUpload }, 'Upload transcript'),
        ),
      ),
      React.createElement('div', { style: { display: 'flex', gap: 12 } },
        React.createElement(StatCard, { value: stats.overdue, label: 'Overdue', color: T.overdue, onClick: () => setFilter('escalated') }),
        React.createElement(StatCard, { value: stats.at_risk, label: 'At risk', color: T.risk, onClick: () => setFilter('at_risk') }),
        React.createElement(StatCard, { value: stats.on_track, label: 'On track', color: T.onTrack, onClick: () => setFilter('active') }),
        React.createElement(StatCard, { value: stats.total, label: 'Total active', color: T.text }),
      ),
    ),

    // Mobile header — compact, 2x2 stat grid
    isMobile && React.createElement('div', {
      style: { padding: '14px 14px 16px', borderBottom: `1px solid ${T.borderFaint}` }
    },
      React.createElement('div', { style: { fontSize: 11, color: T.textFaint, marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 } }, 'Week of 28 Apr'),
      React.createElement('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 } },
        React.createElement(StatCard, { value: stats.overdue, label: 'Overdue', color: T.overdue, onClick: () => setFilter('escalated') }),
        React.createElement(StatCard, { value: stats.at_risk, label: 'At risk', color: T.risk, onClick: () => setFilter('at_risk') }),
        React.createElement(StatCard, { value: stats.on_track, label: 'On track', color: T.onTrack, onClick: () => setFilter('active') }),
        React.createElement(StatCard, { value: stats.total, label: 'Total', color: T.text }),
      ),
    ),

    // Filter tabs + priority filter
    React.createElement('div', {
      style: {
        padding: isMobile ? '0 14px' : '0 32px',
        borderBottom: `1px solid ${T.borderFaint}`,
        display: 'flex', alignItems: 'center', gap: 12,
        justifyContent: 'space-between',
        overflowX: isMobile ? 'auto' : 'visible',
        flexWrap: isMobile ? 'nowrap' : 'wrap',
      }
    },
      React.createElement('div', { style: { display: 'flex', gap: 0 } },
        filters.map(f =>
          React.createElement('button', {
            key: f.id,
            style: {
              padding: '12px 14px', background: 'none', border: 'none',
              borderBottom: `2px solid ${filter === f.id ? T.accent : 'transparent'}`,
              color: filter === f.id ? T.text : T.textFaint,
              fontSize: 12, fontWeight: filter === f.id ? 600 : 400,
              cursor: 'pointer', fontFamily: 'inherit', transition: 'color 0.15s',
            },
            onClick: () => setFilter(f.id),
          }, f.label)
        ),
      ),
      React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6, paddingRight: 0 } },
        React.createElement('span', { style: { fontSize: 11, color: T.textFaint, marginRight: 4 } }, 'Priority:'),
        ['high', 'medium', 'low'].map(p =>
          React.createElement('button', {
            key: p,
            onClick: () => setPriorityFilter(priorityFilter === p ? null : p),
            style: {
              background: priorityFilter === p ? `${PRIORITY_META[p].bg}` : 'transparent',
              border: `1px solid ${priorityFilter === p ? PRIORITY_META[p].color + '55' : T.border}`,
              borderRadius: 4, padding: '3px 7px', cursor: 'pointer',
              opacity: priorityFilter && priorityFilter !== p ? 0.4 : 1,
              fontFamily: 'inherit', transition: 'all 0.15s',
            }
          }, React.createElement(PriorityBadge, { priority: p }))
        ),
      ),
    ),

    // Active tag filter chip
    tagFilter && React.createElement('div', {
      style: { padding: '10px 32px', display: 'flex', alignItems: 'center', gap: 8, background: `${T.accent}10`, borderBottom: `1px solid ${T.borderFaint}` }
    },
      React.createElement('span', { style: { fontSize: 11, color: T.textFaint } }, 'Filtered by tag:'),
      React.createElement('span', {
        style: { fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600, color: T.accent, background: T.surface, padding: '2px 7px', borderRadius: 3, border: `1px solid ${T.accent}55` }
      }, '#' + tagFilter),
      React.createElement('button', {
        onClick: () => setTagFilter(null),
        style: { background: 'none', border: 'none', color: T.textFaint, fontSize: 11, cursor: 'pointer', fontFamily: 'inherit' }
      }, 'clear ×'),
    ),

    // Commitment list — mobile uses card layout, desktop uses dense rows
    React.createElement('div', {
      style: {
        flex: 1, overflow: 'auto',
        padding: isMobile ? '12px 14px' : 0,
        display: isMobile ? 'flex' : 'block',
        flexDirection: 'column', gap: isMobile ? 10 : 0,
      }
    },
      sorted.length === 0
        ? React.createElement('div', {
            style: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 200, color: T.textFaint, gap: 8 }
          },
            React.createElement(Icons.Check, {}),
            React.createElement('span', { style: { fontSize: 13 } }, 'Nothing here — all clear'),
          )
        : sorted.map(c =>
            isMobile
              ? React.createElement(MobileCommitmentCard, {
                  key: c.id, commitment: c,
                  onClick: () => onViewCommitment(c),
                })
              : React.createElement(CommitmentRow, {
                  key: c.id, commitment: c,
                  onClick: () => onViewCommitment(c),
                  onTagClick: (tag) => setTagFilter(tag),
                })
          )
    ),
  );
};

// ── Commitment Detail ─────────────────────────────────────────────────────────

const CommitmentDetail = ({ commitment, onBack, onAction }) => {
  const { isMobile } = (window.useViewport ? window.useViewport() : { isMobile: false });
  const [actionDone, setActionDone] = React.useState(null);
  const [deferDate, setDeferDate] = React.useState('');
  const [showDefer, setShowDefer] = React.useState(false);

  const { normalised_text, raw_text, status, risk_score, owner, deadline, meeting, confidence, history, escalations } = commitment;
  const [priority, setPriority] = React.useState(commitment.priority || 'medium');
  const [tags, setTags] = React.useState(commitment.tags || []);

  const isOverdue = deadline && new Date(deadline) < new Date() && !['delivered','cancelled','deferred'].includes(status);
  const effectiveStatus = isOverdue ? 'overdue' : status;

  const daysAgo = () => {
    if (!deadline) return null;
    const d = new Date(deadline);
    const now = new Date();
    const diff = Math.round((now - d) / 86400000);
    if (diff > 0) return `${diff} day${diff > 1 ? 's' : ''} overdue`;
    if (diff < 0) return `${Math.abs(diff)} day${Math.abs(diff) > 1 ? 's' : ''} remaining`;
    return 'due today';
  };

  const riskPct = Math.round(risk_score * 100);
  const riskColor = risk_score >= 0.9 ? T.overdue : risk_score >= 0.7 ? T.risk : T.onTrack;

  const doAction = (action) => {
    setActionDone(action);
    onAction && onAction(action, commitment);
  };

  return React.createElement('div', {
    style: {
      flex: 1, overflow: 'auto', fontFamily: "'Plus Jakarta Sans', sans-serif",
      padding: isMobile ? '16px 14px 32px' : '28px 32px',
    }
  },
    !isMobile && React.createElement('button', {
      onClick: onBack,
      style: { display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', fontSize: 12, padding: 0, marginBottom: 24, fontFamily: 'inherit' }
    }, React.createElement(Icons.ArrowLeft, {}), 'Back to dashboard'),

    React.createElement('div', { style: { display: 'flex', gap: isMobile ? 16 : 24, flexDirection: isMobile ? 'column' : 'row' } },
      // Main column
      React.createElement('div', { style: { flex: 1, minWidth: 0 } },
        // Title + status + priority
        React.createElement('div', { style: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: 12, flexDirection: isMobile ? 'column' : 'row' } },
          React.createElement('h2', {
            style: { margin: 0, fontSize: isMobile ? 18 : 20, fontWeight: 700, color: T.text, letterSpacing: '-0.02em', lineHeight: 1.3 }
          }, normalised_text),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, flexWrap: 'wrap' } },
            React.createElement(PriorityPicker, { value: priority, onChange: setPriority, size: 'lg' }),
            React.createElement(StatusBadge, { status: effectiveStatus, size: 'lg' }),
          ),
        ),

        // Tags row (editable)
        React.createElement('div', { style: { marginBottom: 24 } },
          React.createElement(TagsEditor, { tags, onChange: setTags }),
        ),

        // Meta grid
        React.createElement('div', {
          style: { display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 10, marginBottom: 24 }
        },
          [
            ['Owner', owner ? React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
              React.createElement(Avatar, { name: owner.name, size: 20 }),
              React.createElement('span', {}, `${owner.name}${owner.role ? ' — ' + owner.role : ''}`)
            ) : '—'],
            ['Deadline', deadline ? React.createElement('span', {},
              new Date(deadline).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short', year: 'numeric' }),
              React.createElement('span', { style: { color: isOverdue ? T.overdue : T.textFaint, marginLeft: 8, fontSize: 11 } }, `(${daysAgo()})`)
            ) : '—'],
            ['Source', `${meeting?.title || 'Unknown'} · ${meeting?.occurred_at ? new Date(meeting.occurred_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : ''}`],
            ['Confidence', React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
              React.createElement('div', {
                style: { width: 60, height: 4, background: T.border, borderRadius: 2, overflow: 'hidden' }
              }, React.createElement('div', { style: { width: `${(confidence || 0) * 100}%`, height: '100%', background: T.accent } })),
              React.createElement('span', { style: { fontFamily: "'JetBrains Mono', monospace", fontSize: 11 } }, confidence?.toFixed(2) || '—'),
            )],
          ].map(([label, val], i) =>
            React.createElement('div', {
              key: i, style: { background: T.panel, border: `1px solid ${T.borderFaint}`, borderRadius: 6, padding: '12px 14px' }
            },
              React.createElement('div', { style: { fontSize: 10, fontWeight: 600, color: T.textFaint, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 } }, label),
              React.createElement('div', { style: { fontSize: 13, color: T.text } }, val),
            )
          )
        ),

        // Risk score bar
        React.createElement('div', {
          style: { background: T.panel, border: `1px solid ${T.borderFaint}`, borderRadius: 6, padding: '14px 16px', marginBottom: 20 }
        },
          React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 } },
            React.createElement('span', { style: { fontSize: 11, fontWeight: 600, color: T.textFaint, textTransform: 'uppercase', letterSpacing: '0.08em' } }, 'Risk score'),
            React.createElement('span', { style: { fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: riskColor, fontWeight: 700 } }, `${riskPct}%`),
          ),
          React.createElement('div', {
            style: { width: '100%', height: 6, background: T.border, borderRadius: 3, overflow: 'hidden' }
          },
            React.createElement('div', {
              style: { width: `${riskPct}%`, height: '100%', background: riskColor, borderRadius: 3, transition: 'width 0.6s ease' }
            })
          ),
          React.createElement('div', {
            style: { display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 10, color: T.textFaint }
          },
            ['Deadline proximity 50%', 'Owner history 35%', 'Update recency 15%'].map((t, i) =>
              React.createElement('span', { key: i }, t)
            )
          ),
        ),

        // Original quote
        React.createElement('div', {
          style: { background: T.panel, border: `1px solid ${T.borderFaint}`, borderLeft: `3px solid ${T.accent}`, borderRadius: '0 6px 6px 0', padding: '16px 18px', marginBottom: 20 }
        },
          React.createElement('div', { style: { fontSize: 10, fontWeight: 600, color: T.accent, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 } }, 'Original quote'),
          React.createElement('p', { style: { margin: 0, fontSize: 13, color: T.textMid, fontStyle: 'italic', lineHeight: 1.6 } }, `"${raw_text}"`),
        ),

        // Tags moved up — old static block removed

        // Actions
        actionDone
          ? React.createElement('div', {
              style: { background: T.onTrackDim, border: `1px solid ${T.onTrack}33`, borderRadius: 6, padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 10 }
            },
              React.createElement(Icons.Check, {}),
              React.createElement('span', { style: { fontSize: 13, color: T.onTrack } },
                actionDone === 'nudge' ? 'Slack nudge sent to ' + owner?.name
                : actionDone === 'delivered' ? 'Marked as delivered'
                : actionDone === 'cancelled' ? 'Commitment cancelled'
                : 'Action recorded'
              ),
            )
          : React.createElement('div', {
              style: { background: T.panel, border: `1px solid ${T.borderFaint}`, borderRadius: 6, padding: '16px 18px' }
            },
              React.createElement('div', { style: { fontSize: 11, fontWeight: 600, color: T.textFaint, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 } }, 'Actions'),
              React.createElement('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } },
                React.createElement(Btn, { variant: 'secondary', size: 'sm', icon: Icons.Send, onClick: () => doAction('nudge') }, 'Send Slack nudge'),
                React.createElement(Btn, { variant: 'success', size: 'sm', icon: Icons.Check, onClick: () => doAction('delivered') }, 'Mark delivered'),
                React.createElement('button', {
                  style: { padding: '5px 10px', borderRadius: 6, background: T.surface, border: `1px solid ${T.border}`, color: T.textMid, fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', gap: 6 },
                  onClick: () => setShowDefer(v => !v),
                },
                  React.createElement(Icons.Repeat, {}), 'Defer',
                ),
                React.createElement(Btn, { variant: 'danger', size: 'sm', icon: Icons.X, onClick: () => doAction('cancelled') }, 'Cancel'),
              ),
              showDefer && React.createElement('div', {
                style: { marginTop: 14, display: 'flex', gap: 8, alignItems: 'center' }
              },
                React.createElement('input', {
                  type: 'date', value: deferDate, onChange: e => setDeferDate(e.target.value),
                  style: { background: T.surface, border: `1px solid ${T.border}`, borderRadius: 6, padding: '6px 10px', color: T.text, fontSize: 12, fontFamily: 'inherit', outline: 'none' }
                }),
                React.createElement(Btn, { variant: 'secondary', size: 'sm', onClick: () => { setShowDefer(false); doAction('deferred'); } }, 'Set new date'),
              ),
            ),
      ),

      // Timeline sidebar (becomes full-width on mobile)
      React.createElement('div', {
        style: { width: isMobile ? '100%' : 260, flexShrink: 0 }
      },
        React.createElement('div', {
          style: { background: T.panel, border: `1px solid ${T.borderFaint}`, borderRadius: 8, padding: '18px' }
        },
          React.createElement('div', { style: { fontSize: 11, fontWeight: 600, color: T.textFaint, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 16 } }, 'History'),
          React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 0 } },
            (history || []).map((h, i) =>
              React.createElement('div', {
                key: i,
                style: { display: 'flex', gap: 12, paddingBottom: i < history.length - 1 ? 16 : 0 }
              },
                React.createElement('div', { style: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 0 } },
                  React.createElement('div', {
                    style: { width: 8, height: 8, borderRadius: '50%', background: i === 0 ? T.accent : T.border, flexShrink: 0, marginTop: 3 }
                  }),
                  i < history.length - 1 && React.createElement('div', { style: { width: 1, flex: 1, background: T.borderFaint, marginTop: 4 } }),
                ),
                React.createElement('div', { style: { paddingBottom: i < history.length - 1 ? 12 : 0 } },
                  React.createElement('div', { style: { fontSize: 11, color: T.textFaint, marginBottom: 2, fontFamily: "'JetBrains Mono', monospace" } },
                    new Date(h.at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) + ' ' +
                    new Date(h.at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
                  ),
                  React.createElement('div', { style: { fontSize: 12, color: T.textMid, lineHeight: 1.4 } }, h.note),
                ),
              )
            )
          ),
        ),
        // Owner card
        owner && React.createElement('div', {
          style: { background: T.panel, border: `1px solid ${T.borderFaint}`, borderRadius: 8, padding: '18px', marginTop: 12 }
        },
          React.createElement('div', { style: { fontSize: 11, fontWeight: 600, color: T.textFaint, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 } }, 'Owner'),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 } },
            React.createElement(Avatar, { name: owner.name, size: 32 }),
            React.createElement('div', {},
              React.createElement('div', { style: { fontSize: 13, fontWeight: 600, color: T.text } }, owner.name),
              React.createElement('div', { style: { fontSize: 11, color: T.textFaint } }, owner.role),
            ),
          ),
          React.createElement('div', { style: { fontSize: 11, color: T.textFaint, marginBottom: 6 } }, 'Delivery rate'),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
            React.createElement('div', { style: { flex: 1, height: 4, background: T.border, borderRadius: 2, overflow: 'hidden' } },
              React.createElement('div', { style: { width: `${(owner.delivery_rate || 0) * 100}%`, height: '100%', background: owner.delivery_rate >= 0.8 ? T.onTrack : owner.delivery_rate >= 0.6 ? T.risk : T.overdue } })
            ),
            React.createElement('span', { style: { fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: T.textMid } },
              `${Math.round((owner.delivery_rate || 0) * 100)}%`
            ),
          ),
        ),
      ),
    ),
  );
};

Object.assign(window, { Dashboard, CommitmentDetail, StatCard, CommitmentRow });
