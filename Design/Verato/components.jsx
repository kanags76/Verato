// Verato — Shared components, tokens, icons
// Exported to window for cross-script use

const T = {
  bg:       '#0c0c0f',
  surface:  '#13131a',
  panel:    '#1a1a24',
  border:   '#2a2a38',
  borderFaint: '#1e1e2a',
  text:     '#e8e8f0',
  textMid:  '#9898b0',
  textFaint:'#5a5a72',
  accent:   '#7c6af7',
  accentDim:'#3d3470',

  overdue:  '#e05a5a',
  overdueDim:'#3a1f1f',
  risk:     '#d4924a',
  riskDim:  '#3a2a1a',
  onTrack:  '#52a87c',
  onTrackDim:'#1a3328',
  delivered:'#52a87c',
  deliveredDim:'#1a3328',
  deferred: '#7c7caa',
  deferredDim:'#22223a',
  pending:  '#9898b0',
  pendingDim:'#22223a',
};

// ── Icons (inline SVG as React components) ──────────────────────────────────

const Icon = ({ d, size = 16, color = 'currentColor', strokeWidth = 1.6 }) => (
  React.createElement('svg', {
    width: size, height: size, viewBox: '0 0 24 24',
    fill: 'none', stroke: color, strokeWidth,
    strokeLinecap: 'round', strokeLinejoin: 'round',
    style: { flexShrink: 0 }
  }, React.createElement('path', { d }))
);

const Icons = {
  Dashboard:  () => React.createElement(Icon, { d: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10' }),
  Meetings:   () => React.createElement(Icon, { d: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z' }),
  Commitments:() => React.createElement(Icon, { d: 'M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11' }),
  People:     () => React.createElement(Icon, { d: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75' }),
  Settings:   () => React.createElement(Icon, { d: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z' }),
  Upload:     () => React.createElement(Icon, { d: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12' }),
  Slack:      () => React.createElement(Icon, { d: 'M14.5 10c-.83 0-1.5-.67-1.5-1.5v-5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5zM20.5 10H19V8.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM9.5 14c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5S8 21.33 8 20.5v-5c0-.83.67-1.5 1.5-1.5zM3.5 14H5v1.5c0 .83-.67 1.5-1.5 1.5S2 16.33 2 15.5 2.67 14 3.5 14zM14 14.5c0-.83.67-1.5 1.5-1.5h5c.83 0 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5h-5c-.83 0-1.5-.67-1.5-1.5zM15.5 19H14v1.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zM10 9.5C10 8.67 9.33 8 8.5 8h-5C2.67 8 2 8.67 2 9.5S2.67 11 3.5 11h5c.83 0 1.5-.67 1.5-1.5zM8.5 5H10V3.5C10 2.67 9.33 2 8.5 2S7 2.67 7 3.5 7.67 5 8.5 5z' }),
  Alert:      () => React.createElement(Icon, { d: 'M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01' }),
  Check:      () => React.createElement(Icon, { d: 'M20 6L9 17l-5-5' }),
  X:          () => React.createElement(Icon, { d: 'M18 6L6 18M6 6l12 12' }),
  ChevronRight:()=> React.createElement(Icon, { d: 'M9 18l6-6-6-6' }),
  ChevronLeft: ()=> React.createElement(Icon, { d: 'M15 18l-6-6 6-6' }),
  ArrowLeft:  () => React.createElement(Icon, { d: 'M19 12H5M12 19l-7-7 7-7' }),
  Plus:       () => React.createElement(Icon, { d: 'M12 5v14M5 12h14' }),
  Send:       () => React.createElement(Icon, { d: 'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z' }),
  Clock:      () => React.createElement(Icon, { d: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM12 6v6l4 2' }),
  Filter:     () => React.createElement(Icon, { d: 'M22 3H2l8 9.46V19l4 2v-8.54L22 3z' }),
  MoreH:      () => React.createElement(Icon, { d: 'M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z' }),
  ExternalLink:()=>React.createElement(Icon, { d: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3' }),
  Repeat:     () => React.createElement(Icon, { d: 'M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3' }),
  Zap:        () => React.createElement(Icon, { d: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z' }),
  LogOut:     () => React.createElement(Icon, { d: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9' }),
  Import:     () => React.createElement(Icon, { d: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3' }),
  Eye:        () => React.createElement(Icon, { d: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z' }),
};

// ── Status badge ─────────────────────────────────────────────────────────────

const STATUS_META = {
  pending_review: { label: 'PENDING',   color: T.pending,  bg: T.pendingDim },
  active:         { label: 'ACTIVE',    color: T.onTrack,  bg: T.onTrackDim },
  at_risk:        { label: 'AT RISK',   color: T.risk,     bg: T.riskDim },
  escalated:      { label: 'ESCALATED', color: T.overdue,  bg: T.overdueDim },
  delivered:      { label: 'DELIVERED', color: T.delivered,bg: T.deliveredDim },
  deferred:       { label: 'DEFERRED',  color: T.deferred, bg: T.deferredDim },
  cancelled:      { label: 'CANCELLED', color: T.textFaint,bg: T.borderFaint },
  overdue:        { label: 'OVERDUE',   color: T.overdue,  bg: T.overdueDim },
};

const StatusBadge = ({ status, size = 'sm' }) => {
  const meta = STATUS_META[status] || { label: status?.toUpperCase(), color: T.textMid, bg: T.borderFaint };
  const fs = size === 'lg' ? '11px' : '10px';
  const px = size === 'lg' ? '8px' : '6px';
  const py = size === 'lg' ? '4px' : '2px';
  return React.createElement('span', {
    style: {
      display: 'inline-flex', alignItems: 'center',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: fs, fontWeight: 600, letterSpacing: '0.08em',
      color: meta.color, background: meta.bg,
      padding: `${py} ${px}`, borderRadius: '3px',
      whiteSpace: 'nowrap',
    }
  }, meta.label);
};

// ── Risk dot ─────────────────────────────────────────────────────────────────

const RiskDot = ({ score }) => {
  const color = score >= 0.9 ? T.overdue : score >= 0.7 ? T.risk : T.onTrack;
  return React.createElement('span', {
    style: {
      display: 'inline-block', width: 7, height: 7,
      borderRadius: '50%', background: color, flexShrink: 0,
      marginTop: 1,
    }
  });
};

// ── Priority badge ───────────────────────────────────────────────────────────

const PRIORITY_META = {
  high:   { label: 'HIGH', short: 'P1', color: '#e05a5a', bg: '#3a1f1f', bars: 3 },
  medium: { label: 'MED',  short: 'P2', color: '#d4924a', bg: '#3a2a1a', bars: 2 },
  low:    { label: 'LOW',  short: 'P3', color: '#7c8aaa', bg: '#22273a', bars: 1 },
};

// Bars-style icon — a clean signal-strength-like visual
const PriorityIcon = ({ priority, size = 12 }) => {
  const meta = PRIORITY_META[priority] || PRIORITY_META.medium;
  const heights = [0.4, 0.7, 1.0];
  return React.createElement('div', {
    style: { display: 'flex', alignItems: 'flex-end', gap: 1.5, height: size, flexShrink: 0 }
  },
    [0, 1, 2].map(i =>
      React.createElement('div', {
        key: i,
        style: {
          width: 2.5, height: size * heights[i], borderRadius: 0.5,
          background: i < meta.bars ? meta.color : T.borderFaint,
          transition: 'background 0.15s',
        }
      })
    )
  );
};

const PriorityBadge = ({ priority, size = 'sm', showLabel = true }) => {
  const meta = PRIORITY_META[priority] || PRIORITY_META.medium;
  return React.createElement('span', {
    style: {
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: size === 'lg' ? 11 : 10, fontWeight: 600, letterSpacing: '0.08em',
      color: meta.color, background: meta.bg,
      padding: size === 'lg' ? '4px 8px' : '2px 6px', borderRadius: 3,
      whiteSpace: 'nowrap',
    }
  },
    React.createElement(PriorityIcon, { priority, size: size === 'lg' ? 11 : 9 }),
    showLabel && meta.label,
  );
};

// Editable: cycles high → medium → low → high
const PriorityPicker = ({ value, onChange, size = 'sm' }) => {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);
  return React.createElement('div', { ref, style: { position: 'relative', display: 'inline-block' } },
    React.createElement('button', {
      onClick: (e) => { e.stopPropagation(); setOpen(v => !v); },
      style: { background: 'none', border: 'none', padding: 0, cursor: 'pointer' },
    },
      React.createElement(PriorityBadge, { priority: value, size }),
    ),
    open && React.createElement('div', {
      style: {
        position: 'absolute', top: '100%', left: 0, marginTop: 4, zIndex: 100,
        background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6,
        padding: 4, display: 'flex', flexDirection: 'column', gap: 2,
        boxShadow: '0 8px 24px rgba(0,0,0,0.4)', minWidth: 110,
      }
    },
      ['high', 'medium', 'low'].map(p =>
        React.createElement('button', {
          key: p,
          onClick: (e) => { e.stopPropagation(); onChange(p); setOpen(false); },
          style: {
            background: value === p ? T.surface : 'transparent', border: 'none',
            padding: '6px 8px', borderRadius: 4, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 8,
            textAlign: 'left', fontFamily: 'inherit',
          }
        }, React.createElement(PriorityBadge, { priority: p, size }))
      )
    )
  );
};

// ── Tag input — editable with autocomplete ───────────────────────────────────

const TagsEditor = ({ tags = [], onChange, size = 'sm' }) => {
  const [input, setInput] = React.useState('');
  const [focused, setFocused] = React.useState(false);
  const inputRef = React.useRef(null);

  const labels = tags.map(t => typeof t === 'string' ? t : t.label);
  const suggestions = (window.TAG_LIBRARY || [])
    .filter(t => !labels.includes(t) && (input ? t.toLowerCase().includes(input.toLowerCase()) : true))
    .slice(0, 5);

  const add = (label) => {
    const clean = label.trim().toLowerCase();
    if (!clean || labels.includes(clean)) return;
    onChange([...tags, { label: clean }]);
    setInput('');
    inputRef.current?.focus();
  };
  const remove = (label) => onChange(tags.filter(t => (typeof t === 'string' ? t : t.label) !== label));

  return React.createElement('div', {
    style: {
      background: T.surface, border: `1px solid ${focused ? T.accent : T.border}`,
      borderRadius: 6, padding: '6px 8px',
      display: 'flex', flexWrap: 'wrap', gap: 5, alignItems: 'center',
      minHeight: 34, transition: 'border-color 0.15s', position: 'relative',
    },
    onClick: () => inputRef.current?.focus(),
  },
    labels.map(label =>
      React.createElement('span', {
        key: label,
        style: {
          background: T.panel, border: `1px solid ${T.border}`, borderRadius: 3,
          padding: '2px 6px', fontSize: 11, color: T.textMid,
          display: 'inline-flex', alignItems: 'center', gap: 5,
        }
      },
        label,
        React.createElement('button', {
          onClick: (e) => { e.stopPropagation(); remove(label); },
          style: { background: 'none', border: 'none', color: T.textFaint, cursor: 'pointer', padding: 0, fontSize: 13, lineHeight: 1, display: 'flex' }
        }, '×'),
      )
    ),
    React.createElement('input', {
      ref: inputRef,
      type: 'text',
      value: input,
      onChange: e => setInput(e.target.value),
      onFocus: () => setFocused(true),
      onBlur: () => setTimeout(() => setFocused(false), 150),
      onKeyDown: e => {
        if (e.key === 'Enter' && input.trim()) { e.preventDefault(); add(input); }
        else if (e.key === 'Backspace' && !input && labels.length) remove(labels[labels.length - 1]);
      },
      placeholder: labels.length === 0 ? 'Add tag…' : '',
      style: {
        flex: 1, minWidth: 80, background: 'none', border: 'none',
        outline: 'none', color: T.text, fontSize: 12, fontFamily: 'inherit', padding: '2px 0',
      }
    }),
    focused && (input || suggestions.length) && suggestions.length > 0 && React.createElement('div', {
      style: {
        position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 50,
        background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6,
        padding: 4, display: 'flex', flexDirection: 'column', gap: 1,
        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
      }
    },
      suggestions.map(s =>
        React.createElement('button', {
          key: s,
          onMouseDown: (e) => { e.preventDefault(); add(s); },
          style: {
            background: 'none', border: 'none', padding: '6px 8px', borderRadius: 4,
            cursor: 'pointer', textAlign: 'left', fontSize: 12, color: T.textMid,
            fontFamily: 'inherit',
          }
        }, s)
      )
    )
  );
};

// ── Avatar ────────────────────────────────────────────────────────────────────

const AVATAR_COLORS = ['#7c6af7','#52a87c','#d4924a','#e05a5a','#5ab4e0','#b05ae0'];
const Avatar = ({ name = '?', size = 28 }) => {
  const initials = name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();
  const idx = name.charCodeAt(0) % AVATAR_COLORS.length;
  return React.createElement('div', {
    style: {
      width: size, height: size, borderRadius: '50%',
      background: AVATAR_COLORS[idx],
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.35, fontWeight: 700, color: '#fff',
      flexShrink: 0, letterSpacing: '-0.02em',
    }
  }, initials);
};

// ── Button ────────────────────────────────────────────────────────────────────

const Btn = ({ children, variant = 'primary', size = 'md', onClick, disabled, style: extraStyle = {}, icon }) => {
  const [hov, setHov] = React.useState(false);
  const base = {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    fontFamily: "'Plus Jakarta Sans', sans-serif",
    fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
    border: 'none', borderRadius: '6px', transition: 'all 0.15s',
    opacity: disabled ? 0.45 : 1, whiteSpace: 'nowrap',
    fontSize: size === 'sm' ? 12 : size === 'lg' ? 14 : 13,
    padding: size === 'sm' ? '5px 10px' : size === 'lg' ? '11px 20px' : '7px 14px',
  };
  const variants = {
    primary:   { background: hov ? '#6a58e8' : T.accent, color: '#fff' },
    secondary: { background: hov ? '#252535' : T.panel, color: T.text, border: `1px solid ${T.border}` },
    ghost:     { background: hov ? T.panel : 'transparent', color: T.textMid },
    danger:    { background: hov ? '#c04444' : T.overdueDim, color: T.overdue, border: `1px solid ${T.overdue}33` },
    success:   { background: hov ? '#3d8060' : T.onTrackDim, color: T.onTrack, border: `1px solid ${T.onTrack}33` },
  };
  return React.createElement('button', {
    style: { ...base, ...variants[variant], ...extraStyle },
    onClick, disabled,
    onMouseEnter: () => setHov(true),
    onMouseLeave: () => setHov(false),
  }, icon && React.createElement(icon, {}), children);
};

// ── Input ─────────────────────────────────────────────────────────────────────

const Input = ({ label, type = 'text', value, onChange, placeholder, hint, error }) => {
  const [focused, setFocused] = React.useState(false);
  return React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } },
    label && React.createElement('label', {
      style: { fontSize: 12, fontWeight: 600, color: T.textMid, letterSpacing: '0.04em' }
    }, label),
    React.createElement('input', {
      type, value, onChange, placeholder,
      onFocus: () => setFocused(true),
      onBlur: () => setFocused(false),
      style: {
        background: T.surface, border: `1px solid ${error ? T.overdue : focused ? T.accent : T.border}`,
        borderRadius: 6, padding: '9px 12px',
        color: T.text, fontSize: 13,
        fontFamily: "'Plus Jakarta Sans', sans-serif",
        outline: 'none', width: '100%', boxSizing: 'border-box',
        transition: 'border-color 0.15s',
      }
    }),
    error && React.createElement('span', { style: { fontSize: 11, color: T.overdue } }, error),
    hint && !error && React.createElement('span', { style: { fontSize: 11, color: T.textFaint } }, hint),
  );
};

// ── Card ──────────────────────────────────────────────────────────────────────

const Card = ({ children, style: s = {}, onClick }) => {
  const [hov, setHov] = React.useState(false);
  return React.createElement('div', {
    style: {
      background: T.panel, border: `1px solid ${hov && onClick ? T.border : T.borderFaint}`,
      borderRadius: 8, padding: 20,
      cursor: onClick ? 'pointer' : 'default',
      transition: 'border-color 0.15s, background 0.15s',
      ...s,
    },
    onClick,
    onMouseEnter: () => setHov(true),
    onMouseLeave: () => setHov(false),
  }, children);
};

// ── Divider ───────────────────────────────────────────────────────────────────

const Divider = ({ margin = '16px 0' }) =>
  React.createElement('div', { style: { height: 1, background: T.borderFaint, margin } });

// ── Sidebar ───────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { id: 'dashboard',    label: 'Dashboard',    Icon: Icons.Dashboard },
  { id: 'meetings',     label: 'Meetings',     Icon: Icons.Meetings },
  { id: 'commitments',  label: 'Commitments',  Icon: Icons.Commitments },
  { id: 'people',       label: 'People',       Icon: Icons.People },
  { id: 'settings',     label: 'Settings',     Icon: Icons.Settings },
];

const Sidebar = ({ activeScreen, onNavigate, hideOnMobile = true }) => {
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  if (isMobile && hideOnMobile) return null;
  return React.createElement('div', {
    className: 'verato-sidebar',
    style: {
      width: 220, minHeight: '100vh', background: T.surface,
      borderRight: `1px solid ${T.borderFaint}`,
      display: 'flex', flexDirection: 'column',
      flexShrink: 0,
    }
  },
    // Logo
    React.createElement('div', {
      style: { padding: '22px 20px 18px', borderBottom: `1px solid ${T.borderFaint}` }
    },
      React.createElement('div', {
        style: {
          display: 'flex', alignItems: 'center', gap: 9,
          cursor: 'pointer',
        },
        onClick: () => onNavigate('dashboard'),
      },
        React.createElement('div', {
          style: {
            width: 28, height: 28, borderRadius: 6,
            background: T.accent,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }
        },
          React.createElement('span', { style: { color: '#fff', fontWeight: 800, fontSize: 13, letterSpacing: '-0.04em' } }, 'V')
        ),
        React.createElement('span', {
          style: { color: T.text, fontWeight: 700, fontSize: 15, letterSpacing: '-0.02em' }
        }, 'Verato'),
      ),
    ),
    // Nav items
    React.createElement('nav', { style: { padding: '12px 10px', flex: 1 } },
      NAV_ITEMS.map(({ id, label, Icon }) => {
        const active = activeScreen === id || (id === 'dashboard' && activeScreen === 'dashboard');
        const isRelated = (id === 'meetings' && ['upload', 'review', 'import'].includes(activeScreen))
          || (id === 'commitments' && activeScreen === 'commitment_detail')
          || (id === 'settings' && activeScreen === 'settings');
        const highlight = active || isRelated;
        return React.createElement('div', {
          key: id,
          style: {
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '8px 10px', borderRadius: 6, marginBottom: 2,
            cursor: 'pointer',
            background: highlight ? `${T.accent}18` : 'transparent',
            color: highlight ? T.accent : T.textMid,
            fontWeight: highlight ? 600 : 400,
            fontSize: 13, transition: 'all 0.12s',
          },
          onClick: () => onNavigate(id),
        },
          React.createElement(Icon, {}),
          label,
          highlight && React.createElement('div', {
            style: {
              marginLeft: 'auto', width: 4, height: 4,
              borderRadius: '50%', background: T.accent,
            }
          }),
        );
      })
    ),
    // User / org footer
    React.createElement('div', {
      style: {
        padding: '12px 16px', borderTop: `1px solid ${T.borderFaint}`,
        display: 'flex', alignItems: 'center', gap: 10,
      }
    },
      React.createElement(Avatar, { name: 'Sarah K.', size: 28 }),
      React.createElement('div', { style: { flex: 1, minWidth: 0 } },
        React.createElement('div', { style: { fontSize: 12, fontWeight: 600, color: T.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } }, 'Sarah K.'),
        React.createElement('div', { style: { fontSize: 11, color: T.textFaint } }, 'Acme Corp'),
      ),
    ),
  );
};

// ── Page header ───────────────────────────────────────────────────────────────

const PageHeader = ({ title, subtitle, actions }) => {
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  return React.createElement('div', {
    style: {
      display: 'flex',
      alignItems: isMobile ? 'stretch' : 'center',
      justifyContent: 'space-between',
      flexDirection: isMobile ? 'column' : 'row',
      gap: isMobile ? 12 : 0,
      padding: isMobile ? '18px 16px 0' : '24px 32px 0',
    }
  },
    React.createElement('div', {},
      React.createElement('h1', {
        style: { margin: 0, fontSize: isMobile ? 18 : 20, fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }
      }, title),
      subtitle && React.createElement('p', {
        style: { margin: '3px 0 0', fontSize: 13, color: T.textFaint }
      }, subtitle),
    ),
    actions && React.createElement('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, ...actions),
  );
};

// ── Onboarding step indicator ─────────────────────────────────────────────────

const StepIndicator = ({ current, total, labels = [] }) =>
  React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 0 } },
    Array.from({ length: total }, (_, i) => {
      const done = i < current;
      const active = i === current;
      return [
        React.createElement('div', {
          key: `step-${i}`,
          style: {
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
          }
        },
          React.createElement('div', {
            style: {
              width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
              background: done ? T.accent : active ? 'transparent' : T.surface,
              border: `2px solid ${done ? T.accent : active ? T.accent : T.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700,
              color: done ? '#fff' : active ? T.accent : T.textFaint,
            }
          }, done ? React.createElement(Icons.Check, {}) : i + 1),
          labels[i] && React.createElement('span', {
            style: { fontSize: 10, color: active ? T.text : T.textFaint, whiteSpace: 'nowrap' }
          }, labels[i]),
        ),
        i < total - 1 && React.createElement('div', {
          key: `line-${i}`,
          style: {
            width: 48, height: 2, marginBottom: 22,
            background: done ? T.accent : T.border,
          }
        }),
      ];
    }).flat()
  );

// ── Export everything ─────────────────────────────────────────────────────────

Object.assign(window, {
  T,
  Icons,
  Icon,
  StatusBadge,
  RiskDot,
  Avatar,
  Btn,
  Input,
  Card,
  Divider,
  Sidebar,
  PageHeader,
  StepIndicator,
  STATUS_META,
  NAV_ITEMS,
  AVATAR_COLORS,
  PriorityBadge,
  PriorityIcon,
  PriorityPicker,
  PRIORITY_META,
  TagsEditor,
});
