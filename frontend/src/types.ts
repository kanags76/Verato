export const APP_VERSION = '2.1';

export interface Commitment {
  id: string;
  title: string;
  owner: string;
  owner_name?: string;
  ownerRole: string;
  deadline: string;
  sourceMeeting?: string;
  meetingDate: string;
  status: "overdue" | "at_risk" | "on_track" | "done" | "deferred" | "pending_review" | "cancelled" | "escalated";
  priority: "High" | "Med" | "Low";
  riskScore: number;
  risk_score?: number;
  tags: string[];
  nudgeCount?: number;
  normalisedText?: string;
  normalised_text?: string;
  meeting_title?: string;
  date?: string;
  confidence?: number;
  is_overdue?: boolean;
  is_escalated?: boolean;
  needs_manual_nudge?: boolean;
  can_manage?: boolean;
  raw_text?: string;
  commitments_count?: number;
  pending_count?: number;
  riskScoreBreakdown?: {
    deadline: number;
    owner: number;
    recency: number;
  };
  risk_score_breakdown?: {
    deadline: number;
    owner: number;
    recency: number;
  };
}

export interface CommitmentHistory {
  id: string;
  commitment: string;
  activity_type: string;
  activity_detail: string;
  created_at: string;
  occurred_at?: string;
  actor?: string;
  target?: string;
  message?: string;
  outcome?: string;
  performed_by_name?: string;
  label?: string;
  type?: string;
  note?: string;
  notes?: string;
}

export interface Meeting {
  id: string;
  title: string;
  date: string;
  occurred_at?: string;
  type: string;
  commitments: number;
  commitments_count?: number;
  pending_count?: number;
  status: "processed" | "processing" | "error" | "pending" | "pending_clarification" | "complete" | "failed";
  processing_status?: "pending" | "processing" | "complete" | "failed" | "pending_clarification";
  clarification_count?: number;
  error?: string;
  status_message?: string;
  transcript_url?: string;
  participants?: string[];
  summary?: string;
  external_url?: string;
  created_by_name?: string;
}

export interface Clarification {
  id: string;
  question: string;
  context: string;
  answer: string;
  order: number;
}

export interface Notification {
  id: string;
  message: string;
  notification_type: 'meeting_ready' | 'meeting_failed' | 'slack_reply' | 'gmail_reply' | 'owner_update' | 'commitment_closed' | 'delegation_invite';
  commitment_id?: string;
  is_read: boolean;
  created_at: string;
}

export interface Person {
  name: string;
  owner?: string;
  id?: string;
  role: string;
  slack_id?: string;
  slack_user_id?: string;
  commitments: number;
  meetings: number;
  deliveryRate: number;
  status: "sage" | "amber" | "rose";
}
