// Verato — Upload, Extraction Review, Settings/Team screens

// ── Upload transcript ─────────────────────────────────────────────────────────

const UploadTranscript = ({ onBack, onSubmit }) => {
  const { isMobile } = (window.useViewport ? window.useViewport() : { isMobile: false });
  const [form, setForm] = React.useState({
    title: '', occurred_at: '', participants: '', transcript: '',
  });
  const [fileName, setFileName] = React.useState('');
  const [dragging, setDragging] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [step, setStep] = React.useState('form'); // form | processing | done

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const canSubmit = (form.title && form.occurred_at && (form.transcript.trim() || fileName));

  const handleSubmit = () => {
    if (!canSubmit) return;
    setLoading(true);
    setStep('processing');
    setTimeout(() => { setStep('done'); setLoading(false); onSubmit && onSubmit(form); }, 2200);
  };

  if (step === 'processing') {
    return React.createElement('div', {
      style: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Plus Jakarta Sans', sans-serif" }
    },
      React.createElement('div', { style: { textAlign: 'center' } },
        React.createElement('div', {
          style: {
            width: 52, height: 52, borderRadius: '50%', border: `3px solid ${T.accent}`,
            borderTopColor: 'transparent', margin: '0 auto 20px',
            animation: 'spin 0.8s linear infinite',
          }
        }),
        React.createElement('h3', { style: { margin: '0 0 6px', fontSize: 16, fontWeight: 700, color: T.text } }, 'Extracting commitments…'),
        React.createElement('p', { style: { margin: 0, fontSize: 13, color: T.textFaint } }, 'Gemini is reading your transcript. This takes a few seconds.'),
      )
    );
  }

  return React.createElement('div', {
    style: { flex: 1, overflow: 'auto', padding: isMobile ? '16px 14px 24px' : '28px 32px', fontFamily: "'Plus Jakarta Sans', sans-serif" }
  },
    !isMobile && React.createElement('button', {
      onClick: onBack,
      style: { display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', fontSize: 12, padding: 0, marginBottom: 24, fontFamily: 'inherit' }
    }, React.createElement(Icons.ArrowLeft, {}), 'Back'),

    React.createElement('div', { style: { maxWidth: 600 } },
      React.createElement('h2', { style: { margin: '0 0 4px', fontSize: isMobile ? 18 : 20, fontWeight: 700, color: T.text, letterSpacing: '-0.02em' } }, 'Upload transcript'),
      React.createElement('p', { style: { margin: '0 0 24px', fontSize: 13, color: T.textFaint } }, 'Paste or upload a meeting transcript. Verato will extract all commitments automatically.'),

      React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 14 } },
        React.createElement('div', { style: { display: 'flex', gap: 10, flexDirection: isMobile ? 'column' : 'row' } },
          React.createElement('div', { style: { flex: 2 } },
            React.createElement(Input, {
              label: 'Meeting title',
              value: form.title,
              onChange: e => set('title', e.target.value),
              placeholder: 'Q2 Planning · April 22',
            })
          ),
          React.createElement('div', { style: { flex: 1 } },
            React.createElement(Input, {
              label: 'Date',
              type: 'date',
              value: form.occurred_at,
              onChange: e => set('occurred_at', e.target.value),
            })
          ),
        ),
        React.createElement(Input, {
          label: 'Participants (optional)',
          value: form.participants,
          onChange: e => set('participants', e.target.value),
          placeholder: 'Sarah K., Tom R., Maya L.',
          hint: 'Comma-separated — helps with attribution',
        }),

        // Transcript input
        React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } },
          React.createElement('label', { style: { fontSize: 12, fontWeight: 600, color: T.textMid, letterSpacing: '0.04em' } }, 'Transcript'),
          React.createElement('div', {
            style: {
              border: `1.5px dashed ${dragging ? T.accent : T.border}`,
              borderRadius: 8, padding: '20px',
              background: dragging ? `${T.accent}08` : T.surface,
              transition: 'all 0.15s', marginBottom: 4,
              cursor: 'pointer',
            },
            onDragOver: e => { e.preventDefault(); setDragging(true); },
            onDragLeave: () => setDragging(false),
            onDrop: e => {
              e.preventDefault(); setDragging(false);
              const f = e.dataTransfer.files[0];
              if (f) { setFileName(f.name); set('transcript', ''); }
            },
          },
            fileName
              ? React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10 } },
                  React.createElement(Icons.Import, {}),
                  React.createElement('span', { style: { fontSize: 13, color: T.text } }, fileName),
                  React.createElement('button', {
                    onClick: () => setFileName(''),
                    style: { marginLeft: 'auto', background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', fontSize: 16 }
                  }, '×')
                )
              : React.createElement('div', { style: { textAlign: 'center' } },
                  React.createElement(Icons.Upload, {}),
                  React.createElement('p', { style: { margin: '6px 0 2px', fontSize: 12, color: T.text, fontWeight: 600 } }, 'Drop file here'),
                  React.createElement('p', { style: { margin: 0, fontSize: 11, color: T.textFaint } }, '.txt · .docx · .pdf · .vtt · .srt'),
                )
          ),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 12, margin: '4px 0' } },
            React.createElement('div', { style: { flex: 1, height: 1, background: T.border } }),
            React.createElement('span', { style: { fontSize: 11, color: T.textFaint } }, 'or paste transcript'),
            React.createElement('div', { style: { flex: 1, height: 1, background: T.border } }),
          ),
          React.createElement('textarea', {
            value: form.transcript,
            onChange: e => { set('transcript', e.target.value); setFileName(''); },
            placeholder: '[00:00:14] Sarah: I\'ll have the pricing section ready by Thursday — including EMEA scenarios.\n[00:01:32] Tom: I\'ll share the hiring brief with HR before Friday.\n[00:03:45] Sarah: Finance, can you update the Q2 forecast by next week?',
            rows: 8,
            style: {
              width: '100%', background: T.surface,
              border: `1px solid ${T.border}`, borderRadius: 6,
              padding: '10px 12px', color: T.text, fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace", resize: 'vertical',
              outline: 'none', boxSizing: 'border-box', lineHeight: 1.7,
            }
          }),
        ),

        React.createElement('button', {
          onClick: handleSubmit, disabled: !canSubmit || loading,
          style: {
            padding: '11px 24px', borderRadius: 6,
            background: canSubmit ? T.accent : T.surface,
            color: canSubmit ? '#fff' : T.textFaint,
            border: `1px solid ${canSubmit ? T.accent : T.border}`,
            fontSize: 13, fontWeight: 600, cursor: canSubmit ? 'pointer' : 'not-allowed',
            fontFamily: 'inherit', alignSelf: 'flex-start', transition: 'all 0.15s',
            display: 'flex', alignItems: 'center', gap: 8,
          }
        }, React.createElement(Icons.Zap, {}), 'Extract commitments →'),
      ),
    ),
  );
};

// ── Extraction review ─────────────────────────────────────────────────────────

const ExtractionReview = ({ meetingTitle = 'Q2 Planning · 22 Apr', onBack, onDone }) => {
  const { isMobile } = (window.useViewport ? window.useViewport() : { isMobile: false });
  if (isMobile) {
    return React.createElement(window.SwipeReviewCard, {
      items: MOCK_PENDING.map(p => ({ ...p, priority: p.priority || 'medium', tags: (p.tags || []).map(t => ({ label: t })) })),
      meetingTitle,
      onBack,
      onDone,
    });
  }
  const [items, setItems] = React.useState(
    MOCK_PENDING.map(p => ({
      ...p,
      state: 'pending',
      priority: p.priority || 'medium',
      tags: (p.tags || []).map(t => ({ label: t })),
    }))
  );
  const [allDone, setAllDone] = React.useState(false);

  const confirm = (id) => setItems(prev => prev.map(p => p.id === id ? { ...p, state: 'confirmed' } : p));
  const reject  = (id) => setItems(prev => prev.map(p => p.id === id ? { ...p, state: 'rejected' }  : p));
  const updatePriority = (id, priority) => setItems(prev => prev.map(p => p.id === id ? { ...p, priority } : p));
  const updateTags     = (id, tags)     => setItems(prev => prev.map(p => p.id === id ? { ...p, tags } : p));

  const confirmAbove = (threshold) => {
    setItems(prev => prev.map(p =>
      p.confidence >= threshold && p.state === 'pending' ? { ...p, state: 'confirmed' } : p
    ));
  };

  const pendingCount   = items.filter(p => p.state === 'pending').length;
  const confirmedCount = items.filter(p => p.state === 'confirmed').length;
  const rejectedCount  = items.filter(p => p.state === 'rejected').length;

  const handleDone = () => { setAllDone(true); setTimeout(onDone, 600); };

  return React.createElement('div', {
    style: { flex: 1, overflow: 'auto', padding: '28px 32px', fontFamily: "'Plus Jakarta Sans', sans-serif" }
  },
    // Header
    React.createElement('div', { style: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 } },
      React.createElement('div', {},
        React.createElement('button', {
          onClick: onBack,
          style: { display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', fontSize: 12, padding: 0, marginBottom: 12, fontFamily: 'inherit' }
        }, React.createElement(Icons.ArrowLeft, {}), 'Back'),
        React.createElement('h2', { style: { margin: '0 0 4px', fontSize: 20, fontWeight: 700, color: T.text, letterSpacing: '-0.02em' } }, meetingTitle),
        React.createElement('div', { style: { display: 'flex', gap: 16, fontSize: 12, color: T.textFaint } },
          React.createElement('span', {}, `${items.length} found`),
          React.createElement('span', { style: { color: T.onTrack } }, `${confirmedCount} confirmed`),
          rejectedCount > 0 && React.createElement('span', { style: { color: T.textFaint } }, `${rejectedCount} rejected`),
          pendingCount > 0 && React.createElement('span', { style: { color: T.risk } }, `${pendingCount} pending review`),
        ),
      ),
      React.createElement('div', { style: { display: 'flex', gap: 8 } },
        React.createElement(Btn, {
          variant: 'secondary', size: 'sm',
          onClick: () => confirmAbove(0.80),
        }, 'Confirm all ≥ 0.80'),
        React.createElement(Btn, {
          variant: 'primary', size: 'sm',
          disabled: pendingCount > 0 || confirmedCount === 0,
          onClick: handleDone,
        }, allDone ? 'Done ✓' : `Add ${confirmedCount} to tracker →`),
      ),
    ),

    // Confidence legend
    React.createElement('div', {
      style: { display: 'flex', gap: 16, marginBottom: 16, padding: '10px 14px', background: T.panel, border: `1px solid ${T.borderFaint}`, borderRadius: 6 }
    },
      React.createElement('span', { style: { fontSize: 11, color: T.textFaint } }, 'Confidence:'),
      React.createElement('span', { style: { fontSize: 11, color: T.onTrack } }, '≥ 0.80 high confidence'),
      React.createElement('span', { style: { fontSize: 11, color: T.risk } }, '0.65–0.79 review recommended'),
      React.createElement('span', { style: { fontSize: 11, color: T.overdue } }, '< 0.65 low confidence'),
    ),

    // Item list
    React.createElement('div', {
      style: { border: `1px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }
    },
      items.map((item, i) => {
        const confColor = item.confidence >= 0.80 ? T.onTrack : item.confidence >= 0.65 ? T.risk : T.overdue;
        const isDone = item.state !== 'pending';

        return React.createElement('div', {
          key: item.id,
          style: {
            display: 'flex', alignItems: 'center', gap: 14,
            padding: '14px 16px',
            background: item.state === 'confirmed' ? `${T.onTrack}08` : item.state === 'rejected' ? `${T.overdue}06` : 'transparent',
            borderBottom: i < items.length - 1 ? `1px solid ${T.borderFaint}` : 'none',
            opacity: item.state === 'rejected' ? 0.5 : 1,
            transition: 'all 0.2s',
          }
        },
          // Confidence score
          React.createElement('div', {
            style: { width: 44, textAlign: 'center', flexShrink: 0 }
          },
            React.createElement('span', {
              style: { fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700, color: confColor }
            }, item.confidence.toFixed(2)),
            item.confidence < 0.80 && React.createElement('div', { style: { fontSize: 9, color: T.risk, marginTop: 1 } }, '⚠ review'),
          ),

          // Text
          React.createElement('div', { style: { flex: 1, minWidth: 0 } },
            React.createElement('div', { style: { fontSize: 13, color: item.state === 'rejected' ? T.textFaint : T.text, marginBottom: 6 } },
              item.normalised_text
            ),
            React.createElement('div', { style: { display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', fontSize: 11, color: T.textFaint } },
              React.createElement('span', {}, item.owner_name),
              item.deadline_resolved && React.createElement('span', {}, '·'),
              item.deadline_resolved && React.createElement('span', {},
                new Date(item.deadline_resolved).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
              ),
              !isDone && React.createElement(PriorityPicker, {
                value: item.priority,
                onChange: (p) => updatePriority(item.id, p),
              }),
              isDone && React.createElement(PriorityBadge, { priority: item.priority }),
            ),
            !isDone && React.createElement('div', { style: { marginTop: 8, maxWidth: 480 } },
              React.createElement(TagsEditor, {
                tags: item.tags,
                onChange: (t) => updateTags(item.id, t),
              }),
            ),
            isDone && item.tags?.length > 0 && React.createElement('div', { style: { marginTop: 6, display: 'flex', gap: 5, flexWrap: 'wrap' } },
              item.tags.map((t, ti) =>
                React.createElement('span', {
                  key: ti,
                  style: { background: T.surface, border: `1px solid ${T.border}`, borderRadius: 3, padding: '1px 5px', fontSize: 10, color: T.textMid }
                }, typeof t === 'string' ? t : t.label)
              )
            ),
          ),

          // Actions / state
          isDone
            ? React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
                item.state === 'confirmed'
                  ? React.createElement('span', { style: { fontSize: 11, color: T.onTrack, fontWeight: 600 } }, '✓ Confirmed')
                  : React.createElement('span', { style: { fontSize: 11, color: T.textFaint, fontWeight: 600 } }, '✗ Rejected'),
                React.createElement('button', {
                  onClick: () => setItems(prev => prev.map(p => p.id === item.id ? { ...p, state: 'pending' } : p)),
                  style: { background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', fontSize: 11, fontFamily: 'inherit' }
                }, 'undo'),
              )
            : React.createElement('div', { style: { display: 'flex', gap: 6 } },
                React.createElement('button', {
                  onClick: () => confirm(item.id),
                  style: {
                    width: 28, height: 28, borderRadius: 6, border: `1px solid ${T.onTrack}55`,
                    background: T.onTrackDim, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.onTrack,
                  }
                }, React.createElement(Icons.Check, {})),
                React.createElement('button', {
                  onClick: () => reject(item.id),
                  style: {
                    width: 28, height: 28, borderRadius: 6, border: `1px solid ${T.overdue}44`,
                    background: T.overdueDim, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.overdue,
                  }
                }, React.createElement(Icons.X, {})),
              ),
        );
      })
    ),
  );
};

// ── Settings / Team ───────────────────────────────────────────────────────────

const SettingsTeam = ({ onNavigate }) => {
  const { isMobile } = (window.useViewport ? window.useViewport() : { isMobile: false });
  const [members] = React.useState([
    { id: 'u1', name: 'Sarah K.', email: 'sarah@acmecorp.com', status: 'admin', isYou: true },
    { id: 'u2', name: 'Tom R.',   email: 'tom@acmecorp.com',   status: 'active' },
    { id: 'u3', name: 'Maya L.', email: 'maya@acmecorp.com',  status: 'pending' },
  ]);
  const [showInvite, setShowInvite] = React.useState(false);
  const [inviteEmail, setInviteEmail] = React.useState('');
  const [inviteSent, setInviteSent] = React.useState(false);
  const [slackConnected, setSlackConnected] = React.useState(false);
  const [slackConnecting, setSlackConnecting] = React.useState(false);
  const [activeTab, setActiveTab] = React.useState('team');

  const tabs = [
    { id: 'team', label: 'Team members' },
    { id: 'slack', label: 'Slack' },
    { id: 'org', label: 'Organisation' },
  ];

  const sendInvite = () => {
    if (!inviteEmail.includes('@')) return;
    setInviteSent(true);
    setTimeout(() => { setInviteSent(false); setShowInvite(false); setInviteEmail(''); }, 2000);
  };

  const connectSlack = () => {
    setSlackConnecting(true);
    setTimeout(() => { setSlackConnecting(false); setSlackConnected(true); }, 1500);
  };

  return React.createElement('div', {
    style: { flex: 1, overflow: 'auto', fontFamily: "'Plus Jakarta Sans', sans-serif" }
  },
    React.createElement(PageHeader, {
      title: 'Settings',
      subtitle: 'Acme Corp · Team plan',
    }),

    // Tabs
    React.createElement('div', {
      style: { padding: isMobile ? '14px 14px 0' : '20px 32px 0', borderBottom: `1px solid ${T.borderFaint}`, display: 'flex', gap: 0, overflowX: 'auto' }
    },
      tabs.map(tab =>
        React.createElement('button', {
          key: tab.id,
          style: {
            padding: '10px 14px', background: 'none', border: 'none',
            borderBottom: `2px solid ${activeTab === tab.id ? T.accent : 'transparent'}`,
            color: activeTab === tab.id ? T.text : T.textFaint,
            fontSize: 13, fontWeight: activeTab === tab.id ? 600 : 400,
            cursor: 'pointer', fontFamily: 'inherit',
          },
          onClick: () => setActiveTab(tab.id),
        }, tab.label)
      )
    ),

    React.createElement('div', { style: { padding: isMobile ? '18px 14px' : '28px 32px', maxWidth: 640 } },

      // ── Team tab ───────────────────────────────────────────────────────────
      activeTab === 'team' && React.createElement('div', {},
        React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 } },
          React.createElement('div', {},
            React.createElement('h3', { style: { margin: '0 0 3px', fontSize: 15, fontWeight: 600, color: T.text } }, 'Team members'),
            React.createElement('p', { style: { margin: 0, fontSize: 12, color: T.textFaint } }, `${members.length} members · ${members.filter(m => m.status === 'pending').length} pending`),
          ),
          React.createElement(Btn, { variant: 'primary', size: 'sm', icon: Icons.Plus, onClick: () => setShowInvite(v => !v) }, 'Invite colleague'),
        ),

        // Invite form
        showInvite && React.createElement('div', {
          style: { background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, padding: '16px 18px', marginBottom: 16 }
        },
          React.createElement('div', { style: { fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 12 } }, 'Send invite'),
          React.createElement('div', { style: { display: 'flex', gap: 8 } },
            React.createElement('div', { style: { flex: 1 } },
              React.createElement(Input, {
                placeholder: 'colleague@acmecorp.com',
                value: inviteEmail,
                onChange: e => setInviteEmail(e.target.value),
              })
            ),
            React.createElement(Btn, {
              variant: 'primary', size: 'sm',
              onClick: sendInvite,
              disabled: inviteSent,
            }, inviteSent ? 'Sent ✓' : 'Send invite →'),
          ),
          React.createElement('p', { style: { margin: '10px 0 0', fontSize: 11, color: T.textFaint } }, 'They\'ll receive an email with a 7-day invite link.'),
        ),

        // Members table
        React.createElement('div', {
          style: { border: `1px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }
        },
          // Header
          React.createElement('div', {
            style: { display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 16, padding: '10px 16px', background: T.surface, borderBottom: `1px solid ${T.border}` }
          },
            ['Name', 'Email', 'Status'].map((h, i) =>
              React.createElement('div', { key: i, style: { fontSize: 11, fontWeight: 600, color: T.textFaint, textTransform: 'uppercase', letterSpacing: '0.06em' } }, h)
            )
          ),
          members.map((m, i) =>
            React.createElement('div', {
              key: m.id,
              style: {
                display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 16,
                padding: '13px 16px', alignItems: 'center',
                borderBottom: i < members.length - 1 ? `1px solid ${T.borderFaint}` : 'none',
              }
            },
              React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10 } },
                React.createElement(Avatar, { name: m.name, size: 24 }),
                React.createElement('span', { style: { fontSize: 13, color: T.text, fontWeight: m.isYou ? 600 : 400 } },
                  m.name, m.isYou && React.createElement('span', { style: { fontSize: 11, color: T.textFaint, marginLeft: 4 } }, '(you)')
                ),
              ),
              React.createElement('span', { style: { fontSize: 12, color: T.textFaint } }, m.email),
              React.createElement('span', {
                style: {
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10, fontWeight: 600, letterSpacing: '0.06em',
                  color: m.status === 'admin' ? T.accent : m.status === 'active' ? T.onTrack : T.risk,
                  textTransform: 'uppercase',
                }
              }, m.status),
            )
          )
        ),
      ),

      // ── Slack tab ──────────────────────────────────────────────────────────
      activeTab === 'slack' && React.createElement('div', {},
        React.createElement('h3', { style: { margin: '0 0 6px', fontSize: 15, fontWeight: 600, color: T.text } }, 'Slack integration'),
        React.createElement('p', { style: { margin: '0 0 24px', fontSize: 13, color: T.textFaint } }, 'Connect your workspace to enable automated nudges and owner responses.'),

        slackConnected
          ? React.createElement('div', {
              style: { background: T.onTrackDim, border: `1px solid ${T.onTrack}33`, borderRadius: 8, padding: '16px 18px', display: 'flex', alignItems: 'center', gap: 12 }
            },
              React.createElement(Icons.Slack, {}),
              React.createElement('div', { style: { flex: 1 } },
                React.createElement('div', { style: { fontSize: 13, fontWeight: 600, color: T.text } }, 'Acme Corp workspace connected'),
                React.createElement('div', { style: { fontSize: 12, color: T.textFaint, marginTop: 2 } }, 'Bot is active · Nudges enabled'),
              ),
              React.createElement('span', { style: { fontSize: 11, color: T.onTrack, fontWeight: 600 } }, '● Connected'),
            )
          : React.createElement('div', {
              style: { background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, padding: '24px', textAlign: 'center' }
            },
              React.createElement(Icons.Slack, {}),
              React.createElement('p', { style: { fontSize: 13, color: T.textMid, margin: '12px 0 20px' } }, 'Connect your Slack workspace to send nudges to commitment owners.'),
              React.createElement('button', {
                onClick: connectSlack, disabled: slackConnecting,
                style: { padding: '10px 22px', borderRadius: 6, background: '#4A154B', color: '#fff', border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 8 }
              }, React.createElement(Icons.Slack, {}), slackConnecting ? 'Connecting…' : 'Add to Slack'),
            ),

        Divider({ margin: '24px 0' }),
        React.createElement('h4', { style: { margin: '0 0 14px', fontSize: 13, fontWeight: 600, color: T.text } }, 'Your Slack account'),
        React.createElement('div', { style: { display: 'flex', gap: 10, alignItems: 'flex-end' } },
          React.createElement('div', { style: { flex: 1 } },
            React.createElement(Input, {
              label: 'Slack user ID',
              placeholder: 'U01234ABCDE',
              hint: 'Find it in Slack: click your name → Copy member ID',
            })
          ),
          React.createElement(Btn, { variant: 'secondary', size: 'sm' }, 'Save'),
        ),
      ),

      // ── Org tab ────────────────────────────────────────────────────────────
      activeTab === 'org' && React.createElement('div', {},
        React.createElement('h3', { style: { margin: '0 0 20px', fontSize: 15, fontWeight: 600, color: T.text } }, 'Organisation'),
        React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 14 } },
          React.createElement(Input, { label: 'Organisation name', value: 'Acme Corp', onChange: () => {} }),
          React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } },
            React.createElement('label', { style: { fontSize: 12, fontWeight: 600, color: T.textMid, letterSpacing: '0.04em' } }, 'Plan'),
            React.createElement('div', {
              style: { background: T.surface, border: `1px solid ${T.border}`, borderRadius: 6, padding: '10px 12px', fontSize: 13, color: T.text }
            }, 'Team plan · Design partner (free until Month 3)'),
          ),
          React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } },
            React.createElement('label', { style: { fontSize: 12, fontWeight: 600, color: T.textMid, letterSpacing: '0.04em' } }, 'Extraction confidence threshold'),
            React.createElement('div', { style: { display: 'flex', gap: 10, alignItems: 'center' } },
              React.createElement('input', {
                type: 'range', min: 0.5, max: 0.95, step: 0.05, defaultValue: 0.65,
                style: { flex: 1, accentColor: T.accent }
              }),
              React.createElement('span', { style: { fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: T.textMid, width: 32 } }, '0.65'),
            ),
            React.createElement('span', { style: { fontSize: 11, color: T.textFaint } }, 'Commitments below this confidence are shown for manual review'),
          ),
          React.createElement(Btn, { variant: 'primary', size: 'sm' }, 'Save changes'),
        ),
      ),
    ),
  );
};

Object.assign(window, { UploadTranscript, ExtractionReview, SettingsTeam });
