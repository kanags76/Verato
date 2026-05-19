// Verato — Screen 1: Sign-Up + Onboarding flow
// Screens: signup_plan → signup_form → onboarding_slack → onboarding_import → onboarding_done

const SignupPlan = ({ onSelect }) => {
  const [hov, setHov] = React.useState(null);

  const plans = [
    {
      id: 'individual',
      name: 'Individual',
      tagline: 'Just you',
      features: ['1 login', '1 Slack workspace', 'Unlimited commitment owners', 'Full extraction + tracking'],
      cta: 'Get started →',
    },
    {
      id: 'team',
      name: 'Team',
      tagline: 'You + colleagues',
      features: ['Unlimited logins', '1 shared Slack workspace', 'Invite colleagues by email', 'Full extraction + tracking'],
      cta: 'Get started →',
      recommended: true,
    },
  ];

  return React.createElement('div', {
    style: {
      minHeight: '100vh', background: T.bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: "'Plus Jakarta Sans', sans-serif",
      padding: 24,
    }
  },
    React.createElement('div', { style: { width: '100%', maxWidth: 560 } },
      // Logo
      React.createElement('div', {
        style: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 48, justifyContent: 'center' }
      },
        React.createElement('div', {
          style: { width: 32, height: 32, borderRadius: 8, background: T.accent, display: 'flex', alignItems: 'center', justifyContent: 'center' }
        }, React.createElement('span', { style: { color: '#fff', fontWeight: 800, fontSize: 15 } }, 'V')),
        React.createElement('span', { style: { color: T.text, fontWeight: 700, fontSize: 18, letterSpacing: '-0.02em' } }, 'Verato'),
      ),
      React.createElement('h2', {
        style: { textAlign: 'center', fontSize: 26, fontWeight: 800, color: T.text, margin: '0 0 6px', letterSpacing: '-0.03em' }
      }, 'Create your account'),
      React.createElement('p', {
        style: { textAlign: 'center', fontSize: 14, color: T.textFaint, margin: '0 0 36px' }
      }, 'Every commitment your organisation makes — tracked and owned.'),

      React.createElement('div', { style: { display: 'flex', gap: 16 } },
        plans.map(plan =>
          React.createElement('div', {
            key: plan.id,
            style: {
              flex: 1, background: T.panel,
              border: `1.5px solid ${hov === plan.id ? T.accent : plan.recommended ? `${T.accent}55` : T.border}`,
              borderRadius: 10, padding: '24px 22px',
              cursor: 'pointer', transition: 'border-color 0.15s, transform 0.1s',
              transform: hov === plan.id ? 'translateY(-2px)' : 'none',
              position: 'relative',
            },
            onClick: () => onSelect(plan.id),
            onMouseEnter: () => setHov(plan.id),
            onMouseLeave: () => setHov(null),
          },
            plan.recommended && React.createElement('div', {
              style: {
                position: 'absolute', top: -11, left: '50%', transform: 'translateX(-50%)',
                background: T.accent, color: '#fff', fontSize: 10, fontWeight: 700,
                padding: '3px 10px', borderRadius: 20, letterSpacing: '0.06em',
              }
            }, 'RECOMMENDED'),
            React.createElement('div', { style: { marginBottom: 16 } },
              React.createElement('h3', {
                style: { margin: 0, fontSize: 16, fontWeight: 700, color: T.text }
              }, plan.name),
              React.createElement('p', {
                style: { margin: '4px 0 0', fontSize: 13, color: T.textFaint }
              }, plan.tagline),
            ),
            Divider({ margin: '0 0 16px' }),
            React.createElement('ul', {
              style: { margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 22 }
            },
              plan.features.map((f, i) =>
                React.createElement('li', {
                  key: i, style: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: T.textMid }
                },
                  React.createElement('span', { style: { color: T.onTrack, fontSize: 11 } }, '✓'),
                  f,
                )
              )
            ),
            React.createElement('button', {
              style: {
                width: '100%', padding: '10px', borderRadius: 6,
                background: plan.recommended ? T.accent : T.surface,
                color: plan.recommended ? '#fff' : T.text,
                border: `1px solid ${plan.recommended ? T.accent : T.border}`,
                fontSize: 13, fontWeight: 600, cursor: 'pointer',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
              }
            }, plan.cta),
          )
        )
      ),
      React.createElement('p', {
        style: { textAlign: 'center', marginTop: 24, fontSize: 12, color: T.textFaint }
      }, 'No credit card required during design partner phase · Free for 3 months'),
    )
  );
};

const SignupForm = ({ plan, onBack, onSubmit }) => {
  const [form, setForm] = React.useState({ name: '', email: '', password: '', org_name: '' });
  const [errors, setErrors] = React.useState({});
  const [loading, setLoading] = React.useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const validate = () => {
    const e = {};
    if (!form.name.trim()) e.name = 'Required';
    if (!form.email.includes('@')) e.email = 'Enter a valid email';
    if (form.password.length < 8) e.password = 'At least 8 characters';
    if (!form.org_name.trim()) e.org_name = 'Required';
    return e;
  };

  const handleSubmit = () => {
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    setLoading(true);
    setTimeout(() => { setLoading(false); onSubmit(form); }, 900);
  };

  return React.createElement('div', {
    style: {
      minHeight: '100vh', background: T.bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: "'Plus Jakarta Sans', sans-serif", padding: 24,
    }
  },
    React.createElement('div', { style: { width: '100%', maxWidth: 400 } },
      React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 40, justifyContent: 'center' } },
        React.createElement('div', { style: { width: 28, height: 28, borderRadius: 6, background: T.accent, display: 'flex', alignItems: 'center', justifyContent: 'center' } },
          React.createElement('span', { style: { color: '#fff', fontWeight: 800, fontSize: 13 } }, 'V')),
        React.createElement('span', { style: { color: T.text, fontWeight: 700, fontSize: 16 } }, 'Verato'),
      ),
      React.createElement('div', { style: { marginBottom: 28 } },
        React.createElement('button', {
          onClick: onBack,
          style: { background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4, padding: 0, marginBottom: 16, fontFamily: 'inherit' }
        }, '← Back'),
        React.createElement('h2', { style: { margin: '0 0 4px', fontSize: 22, fontWeight: 800, color: T.text, letterSpacing: '-0.03em' } }, 'Your details'),
        React.createElement('p', { style: { margin: 0, fontSize: 13, color: T.textFaint } },
          plan === 'team' ? 'Creating a team account' : 'Creating an individual account'
        ),
      ),
      React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 16 } },
        React.createElement(Input, { label: 'Your name', value: form.name, onChange: e => set('name', e.target.value), placeholder: 'Sarah K.', error: errors.name }),
        React.createElement(Input, { label: 'Work email', type: 'email', value: form.email, onChange: e => set('email', e.target.value), placeholder: 'sarah@acmecorp.com', error: errors.email }),
        React.createElement(Input, { label: 'Password', type: 'password', value: form.password, onChange: e => set('password', e.target.value), placeholder: '••••••••', hint: 'At least 8 characters', error: errors.password }),
        React.createElement(Input, { label: 'Organisation name', value: form.org_name, onChange: e => set('org_name', e.target.value), placeholder: 'Acme Corp', error: errors.org_name }),
        React.createElement('button', {
          onClick: handleSubmit, disabled: loading,
          style: {
            marginTop: 4, padding: '11px', borderRadius: 6,
            background: loading ? T.accentDim : T.accent, color: '#fff',
            border: 'none', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            fontFamily: 'inherit', transition: 'background 0.15s',
          }
        }, loading ? 'Creating account…' : 'Create account →'),
      ),
      React.createElement('p', { style: { textAlign: 'center', marginTop: 20, fontSize: 12, color: T.textFaint } },
        'By creating an account you agree to our Terms of Service and Privacy Policy.'
      ),
    )
  );
};

const OnboardingSlack = ({ orgName, onConnect, onSkip, step = 0 }) => {
  const [connecting, setConnecting] = React.useState(false);
  const steps = ['Connect Slack', 'Link your ID', 'Import data', 'Done'];

  const handleConnect = () => {
    setConnecting(true);
    setTimeout(() => { setConnecting(false); onConnect(); }, 1200);
  };

  return React.createElement('div', {
    style: {
      minHeight: '100vh', background: T.bg, display: 'flex',
      fontFamily: "'Plus Jakarta Sans', sans-serif",
    }
  },
    Sidebar({ activeScreen: 'settings', onNavigate: () => {} }),
    React.createElement('div', {
      style: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 48 }
    },
      React.createElement('div', { style: { width: '100%', maxWidth: 480 } },
        React.createElement('div', { style: { marginBottom: 40, display: 'flex', justifyContent: 'center' } },
          React.createElement(StepIndicator, { current: step, total: 4, labels: steps })
        ),
        React.createElement(Card, { style: { padding: '36px 40px' } },
          React.createElement('div', {
            style: {
              width: 52, height: 52, borderRadius: 14, background: '#4A154B22',
              border: '1px solid #4A154B55', display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: 22,
            }
          },
            React.createElement(Icons.Slack, {})
          ),
          React.createElement('h2', { style: { margin: '0 0 8px', fontSize: 20, fontWeight: 700, color: T.text } }, 'Connect your Slack workspace'),
          React.createElement('p', { style: { margin: '0 0 28px', fontSize: 13, color: T.textMid, lineHeight: 1.6 } },
            'Verato sends Slack DMs to commitment owners before their deadlines. Connect your workspace to enable nudges.',
          ),
          React.createElement('div', {
            style: {
              background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8,
              padding: '14px 16px', marginBottom: 24,
              display: 'flex', alignItems: 'flex-start', gap: 12,
            }
          },
            React.createElement(Icons.Zap, {}),
            React.createElement('div', {},
              React.createElement('div', { style: { fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 4 } }, 'What Verato needs'),
              React.createElement('ul', { style: { margin: 0, padding: '0 0 0 16px', fontSize: 12, color: T.textMid, display: 'flex', flexDirection: 'column', gap: 3 } },
                ['Send direct messages to commitment owners', 'Read button responses (Done / Delayed / Blocked)', 'No access to channel messages or files'].map((t, i) =>
                  React.createElement('li', { key: i }, t)
                )
              )
            )
          ),
          React.createElement('button', {
            onClick: handleConnect, disabled: connecting,
            style: {
              width: '100%', padding: '11px 20px', borderRadius: 6,
              background: '#4A154B', color: '#fff', border: 'none',
              fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              opacity: connecting ? 0.7 : 1,
            }
          },
            React.createElement(Icons.Slack, {}),
            connecting ? 'Connecting…' : 'Add to Slack'
          ),
          React.createElement('button', {
            onClick: onSkip,
            style: {
              width: '100%', padding: '9px', marginTop: 10,
              background: 'none', border: 'none', color: T.textFaint,
              fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
            }
          }, 'Skip for now — connect later from Settings'),
        ),
      )
    )
  );
};

const OnboardingImport = ({ onNext, onSkip }) => {
  const [text, setText] = React.useState('');
  const [dragging, setDragging] = React.useState(false);
  const [fileName, setFileName] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  const steps = ['Connect Slack', 'Link your ID', 'Import data', 'Done'];

  const handleExtract = () => {
    if (!text.trim() && !fileName) return;
    setLoading(true);
    setTimeout(() => { setLoading(false); onNext(); }, 1400);
  };

  return React.createElement('div', {
    style: { minHeight: '100vh', background: T.bg, display: 'flex', fontFamily: "'Plus Jakarta Sans', sans-serif" }
  },
    Sidebar({ activeScreen: 'settings', onNavigate: () => {} }),
    React.createElement('div', {
      style: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 48 }
    },
      React.createElement('div', { style: { width: '100%', maxWidth: 520 } },
        React.createElement('div', { style: { marginBottom: 40, display: 'flex', justifyContent: 'center' } },
          React.createElement(StepIndicator, { current: 2, total: 4, labels: steps })
        ),
        React.createElement(Card, { style: { padding: '36px 40px' } },
          React.createElement('h2', { style: { margin: '0 0 6px', fontSize: 20, fontWeight: 700, color: T.text } }, 'Import your existing commitments'),
          React.createElement('p', { style: { margin: '0 0 28px', fontSize: 13, color: T.textMid } },
            'Start with your existing tracker — Verato will extract and structure everything automatically.'
          ),
          // Drop zone
          React.createElement('div', {
            style: {
              border: `1.5px dashed ${dragging ? T.accent : T.border}`,
              borderRadius: 8, padding: '28px 20px', textAlign: 'center',
              background: dragging ? `${T.accent}08` : T.surface,
              cursor: 'pointer', marginBottom: 18, transition: 'all 0.15s',
            },
            onDragOver: e => { e.preventDefault(); setDragging(true); },
            onDragLeave: () => setDragging(false),
            onDrop: e => {
              e.preventDefault(); setDragging(false);
              const f = e.dataTransfer.files[0];
              if (f) { setFileName(f.name); setText(''); }
            },
          },
            fileName
              ? React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'center' } },
                  React.createElement(Icons.Import, {}),
                  React.createElement('span', { style: { fontSize: 13, color: T.text } }, fileName),
                  React.createElement('button', {
                    onClick: () => setFileName(''),
                    style: { background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', fontSize: 16 }
                  }, '×')
                )
              : React.createElement('div', {},
                  React.createElement(Icons.Upload, {}),
                  React.createElement('p', { style: { margin: '8px 0 4px', fontSize: 13, color: T.text, fontWeight: 600 } }, 'Drop your file here'),
                  React.createElement('p', { style: { margin: 0, fontSize: 11, color: T.textFaint } }, '.csv · .xlsx · .docx · .txt · .md'),
                )
          ),
          React.createElement('div', {
            style: { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }
          },
            React.createElement('div', { style: { flex: 1, height: 1, background: T.border } }),
            React.createElement('span', { style: { fontSize: 11, color: T.textFaint } }, 'or paste text'),
            React.createElement('div', { style: { flex: 1, height: 1, background: T.border } }),
          ),
          React.createElement('textarea', {
            value: text,
            onChange: e => { setText(e.target.value); setFileName(''); },
            placeholder: '• Sarah to send pricing deck by Thursday\n• Tom hiring brief to HR by Friday\n• Finance to update Q2 forecast…',
            style: {
              width: '100%', minHeight: 120, background: T.surface,
              border: `1px solid ${T.border}`, borderRadius: 6,
              padding: '10px 12px', color: T.text, fontSize: 12,
              fontFamily: "'Plus Jakarta Sans', sans-serif", resize: 'vertical',
              outline: 'none', boxSizing: 'border-box', lineHeight: 1.6,
            }
          }),
          React.createElement('div', { style: { display: 'flex', gap: 10, marginTop: 18 } },
            React.createElement('button', {
              onClick: handleExtract,
              disabled: loading || (!text.trim() && !fileName),
              style: {
                flex: 1, padding: '10px', borderRadius: 6,
                background: (text.trim() || fileName) ? T.accent : T.surface,
                color: (text.trim() || fileName) ? '#fff' : T.textFaint,
                border: `1px solid ${(text.trim() || fileName) ? T.accent : T.border}`,
                fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
                transition: 'all 0.15s',
              }
            }, loading ? 'Extracting…' : 'Extract items →'),
          ),
          React.createElement('button', {
            onClick: onSkip,
            style: { width: '100%', padding: '9px', marginTop: 8, background: 'none', border: 'none', color: T.textFaint, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }
          }, "Skip this step — I'll start fresh"),
        ),
      )
    )
  );
};

Object.assign(window, { SignupPlan, SignupForm, OnboardingSlack, OnboardingImport });
