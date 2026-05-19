// Verato — Mock data for prototype

const MOCK_COMMITMENTS = [
  {
    id: 'c1',
    normalised_text: 'Q2 board deck — pricing section',
    raw_text: 'I\'ll have the pricing section of the board deck to you by end of Thursday — it\'ll include the EMEA scenarios.',
    status: 'escalated',
    priority: 'high',
    risk_score: 0.97,
    owner: { id: 'p1', name: 'Sarah K.', role: 'CFO', delivery_rate: 0.72 },
    deadline: '2026-04-30',
    meeting: { id: 'm1', title: 'Q2 Planning', occurred_at: '2026-04-22T14:00:00Z' },
    confidence: 0.94,
    tags: [{ label: 'q2 board prep' }, { label: 'pricing' }],
    escalations: [
      { method: 'slack', occurred_at: '2026-04-29T09:00:00Z', outcome: 'pending' },
      { method: 'auto', occurred_at: '2026-04-30T09:00:00Z', outcome: 'escalated' },
    ],
    history: [
      { at: '2026-04-22T14:31:00Z', note: 'Extracted from Q2 Planning (confidence 0.94)' },
      { at: '2026-04-22T14:45:00Z', note: 'Confirmed by CoS → status: Active' },
      { at: '2026-04-29T09:00:00Z', note: 'Slack nudge sent to Sarah K.' },
      { at: '2026-04-30T09:00:00Z', note: 'Deadline passed → auto-escalated' },
    ],
    created_at: '2026-04-22T14:31:00Z',
    source: 'transcript',
  },
  {
    id: 'c2',
    normalised_text: 'Engineering lead hiring brief',
    raw_text: 'Tom to share the hiring brief for the engineering lead role with HR before end of Friday.',
    status: 'at_risk',
    priority: 'medium',
    risk_score: 0.78,
    owner: { id: 'p2', name: 'Tom R.', role: 'CTO', delivery_rate: 0.85 },
    deadline: '2026-05-05',
    meeting: { id: 'm1', title: 'Q2 Planning', occurred_at: '2026-04-22T14:00:00Z' },
    confidence: 0.81,
    tags: [{ label: 'hiring' }, { label: 'engineering' }],
    escalations: [
      { method: 'slack', occurred_at: '2026-05-03T09:00:00Z', outcome: 'pending' },
    ],
    history: [
      { at: '2026-04-22T14:31:00Z', note: 'Extracted from Q2 Planning (confidence 0.81)' },
      { at: '2026-04-22T14:45:00Z', note: 'Confirmed by CoS → status: Active' },
      { at: '2026-05-03T09:00:00Z', note: 'Slack nudge sent — no response in 9hrs' },
      { at: '2026-05-03T12:00:00Z', note: 'Risk score crossed 0.70 → status: At Risk' },
    ],
    created_at: '2026-04-22T14:31:00Z',
    source: 'transcript',
  },
  {
    id: 'c3',
    normalised_text: 'Product roadmap v2 draft',
    raw_text: 'Maya will circulate the updated product roadmap v2 for feedback by next Friday.',
    status: 'active',
    priority: 'medium',
    risk_score: 0.28,
    owner: { id: 'p3', name: 'Maya L.', role: 'CPO', delivery_rate: 0.94 },
    deadline: '2026-05-08',
    meeting: { id: 'm2', title: 'Product Review', occurred_at: '2026-04-29T10:00:00Z' },
    confidence: 0.89,
    tags: [{ label: 'product' }, { label: 'roadmap' }],
    escalations: [],
    history: [
      { at: '2026-04-29T10:30:00Z', note: 'Extracted from Product Review (confidence 0.89)' },
      { at: '2026-04-29T11:00:00Z', note: 'Confirmed by CoS → status: Active' },
      { at: '2026-05-02T10:00:00Z', note: 'Maya updated: draft in progress' },
    ],
    created_at: '2026-04-29T10:30:00Z',
    source: 'transcript',
  },
  {
    id: 'c4',
    normalised_text: 'EMEA contract review — legal sign-off',
    raw_text: 'Legal team to complete the EMEA contract review and confirm sign-off by end of April.',
    status: 'escalated',
    priority: 'high',
    risk_score: 0.99,
    owner: { id: 'p4', name: 'James O.', role: 'General Counsel', delivery_rate: 0.68 },
    deadline: '2026-04-30',
    meeting: { id: 'm3', title: 'Legal Review', occurred_at: '2026-04-20T09:00:00Z' },
    confidence: 0.77,
    tags: [{ label: 'legal' }, { label: 'emea' }],
    escalations: [],
    history: [
      { at: '2026-04-20T09:30:00Z', note: 'Extracted from Legal Review (confidence 0.77)' },
      { at: '2026-04-20T10:00:00Z', note: 'Confirmed by CoS → status: Active' },
      { at: '2026-04-28T09:00:00Z', note: 'Slack nudge sent to James O.' },
      { at: '2026-04-30T09:00:00Z', note: 'Deadline passed → auto-escalated' },
    ],
    created_at: '2026-04-20T09:30:00Z',
    source: 'transcript',
  },
  {
    id: 'c5',
    normalised_text: 'Q3 headcount plan submission',
    raw_text: 'Finance to submit the Q3 headcount plan to the board by May 10.',
    status: 'active',
    priority: 'high',
    risk_score: 0.35,
    owner: { id: 'p5', name: 'Priya M.', role: 'CFO', delivery_rate: 0.91 },
    deadline: '2026-05-10',
    meeting: { id: 'm1', title: 'Q2 Planning', occurred_at: '2026-04-22T14:00:00Z' },
    confidence: 0.86,
    tags: [{ label: 'finance' }, { label: 'q3 planning' }],
    escalations: [],
    history: [
      { at: '2026-04-22T14:31:00Z', note: 'Extracted from Q2 Planning (confidence 0.86)' },
      { at: '2026-04-22T14:47:00Z', note: 'Confirmed by CoS → status: Active' },
    ],
    created_at: '2026-04-22T14:31:00Z',
    source: 'transcript',
  },
  {
    id: 'c6',
    normalised_text: 'Vendor security questionnaire response',
    raw_text: 'Engineering to complete and return the vendor security questionnaire by Friday 2 May.',
    status: 'delivered',
    priority: 'low',
    risk_score: 0.0,
    owner: { id: 'p2', name: 'Tom R.', role: 'CTO', delivery_rate: 0.85 },
    deadline: '2026-05-02',
    meeting: { id: 'm2', title: 'Product Review', occurred_at: '2026-04-29T10:00:00Z' },
    confidence: 0.92,
    tags: [{ label: 'security' }, { label: 'vendor' }],
    escalations: [],
    history: [
      { at: '2026-04-29T10:30:00Z', note: 'Extracted from Product Review (confidence 0.92)' },
      { at: '2026-04-29T11:00:00Z', note: 'Confirmed by CoS → status: Active' },
      { at: '2026-05-02T16:00:00Z', note: 'Tom replied "Done" in Slack → Delivered' },
    ],
    created_at: '2026-04-29T10:30:00Z',
    source: 'transcript',
  },
];

const MOCK_PENDING = [
  {
    id: 'p1',
    raw_text: 'Sarah will send pricing deck by Thursday',
    normalised_text: 'Sarah K. will send the pricing deck by Thursday 30 Apr',
    confidence: 0.94,
    owner_name: 'Sarah K.',
    deadline_text: 'end of Thursday',
    deadline_resolved: '2026-04-30',
    tags: ['q2 board prep', 'pricing'],
  },
  {
    id: 'p2',
    raw_text: 'Tom to share hiring brief with HR',
    normalised_text: 'Tom R. to share the engineering hiring brief with HR',
    confidence: 0.81,
    owner_name: 'Tom R.',
    deadline_text: 'end of Friday',
    deadline_resolved: '2026-05-02',
    tags: ['hiring'],
  },
  {
    id: 'p3',
    raw_text: 'Finance to update Q2 forecast',
    normalised_text: 'Finance team to update the Q2 forecast model',
    confidence: 0.73,
    owner_name: 'Finance team',
    deadline_text: 'next week',
    deadline_resolved: '2026-05-08',
    tags: ['finance', 'q2'],
  },
  {
    id: 'p4',
    raw_text: 'Ben to set up the design review session',
    normalised_text: 'Ben will organise and send the calendar invite for the design review',
    confidence: 0.68,
    owner_name: 'Ben A.',
    deadline_text: 'tomorrow',
    deadline_resolved: '2026-04-23',
    tags: ['design'],
  },
  {
    id: 'p5',
    raw_text: 'Legal to circulate the updated NDA template',
    normalised_text: 'Legal team to circulate the updated NDA template to all stakeholders',
    confidence: 0.88,
    owner_name: 'James O.',
    deadline_text: 'by end of next week',
    deadline_resolved: '2026-05-09',
    tags: ['legal'],
  },
];

const MOCK_MEETINGS = [
  { id: 'm1', title: 'Q2 Planning', occurred_at: '2026-04-22T14:00:00Z', meeting_type: 'leadership', processing_status: 'complete', commitment_count: 8 },
  { id: 'm2', title: 'Product Review', occurred_at: '2026-04-29T10:00:00Z', meeting_type: 'team', processing_status: 'complete', commitment_count: 5 },
  { id: 'm3', title: 'Legal Review', occurred_at: '2026-04-20T09:00:00Z', meeting_type: 'project', processing_status: 'complete', commitment_count: 3 },
  { id: 'm4', title: 'Engineering Standup', occurred_at: '2026-05-01T09:30:00Z', meeting_type: 'team', processing_status: 'complete', commitment_count: 2 },
];

const MOCK_PEOPLE = [
  { id: 'p1', name: 'Sarah K.', role: 'CFO', delivery_rate: 0.72, total_commitments: 14, meeting_count: 8 },
  { id: 'p2', name: 'Tom R.',   role: 'CTO', delivery_rate: 0.85, total_commitments: 21, meeting_count: 12 },
  { id: 'p3', name: 'Maya L.', role: 'CPO', delivery_rate: 0.94, total_commitments: 9,  meeting_count: 6 },
  { id: 'p4', name: 'James O.',role: 'General Counsel', delivery_rate: 0.68, total_commitments: 7, meeting_count: 4 },
  { id: 'p5', name: 'Priya M.',role: 'Finance Lead', delivery_rate: 0.91, total_commitments: 11, meeting_count: 7 },
];

// Common tags (used for autocomplete suggestions)
const TAG_LIBRARY = [
  'q2 board prep', 'pricing', 'hiring', 'engineering', 'product', 'roadmap',
  'legal', 'emea', 'finance', 'q3 planning', 'security', 'vendor', 'design',
  'ops', 'marketing', 'sales', 'fundraising', 'q2', 'urgent', 'investor',
];

// Add priority to pending items (suggested by extraction)
MOCK_PENDING.forEach((p, i) => {
  p.priority = ['high', 'medium', 'medium', 'low', 'medium'][i] || 'medium';
});

Object.assign(window, { MOCK_COMMITMENTS, MOCK_PENDING, MOCK_MEETINGS, MOCK_PEOPLE, TAG_LIBRARY });
