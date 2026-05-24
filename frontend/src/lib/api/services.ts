import { apiClient } from './client';
import { Commitment, Meeting, Person, CommitmentHistory, Clarification } from '../../types';

export const getCleanDataUrl = async (file: File): Promise<string> => {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      let result = reader.result as string;
      const ext = file.name.split('.').pop()?.toLowerCase();
      let mimeType = file.type;

      // Map browser types or extensions to standard ones whitelisted by DRF extra fields / mimetypes
      if (ext === 'csv') {
        mimeType = 'text/csv';
      } else if (ext === 'xlsx') {
        mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
      } else if (ext === 'docx') {
        mimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      } else if (ext === 'txt') {
        mimeType = 'text/plain';
      } else if (ext === 'md') {
        mimeType = 'text/plain'; // Decodes perfectly as plain text
      }

      if (result.startsWith('data:')) {
        const parts = result.split(';base64,');
        if (parts.length === 2) {
          result = `data:${mimeType};base64,${parts[1]}`;
        }
      }
      resolve(result);
    };
    reader.onerror = (err) => reject(err);
    reader.readAsDataURL(file);
  });
};

export const commitmentService = {
  getAll: async (params?: { priorities?: string[], tag?: string, meeting?: string, status?: string }): Promise<Commitment[]> => {
    let url = 'commitments/';
    const queryParams = new URLSearchParams();
    
    if (params?.priorities && params.priorities.length > 0) {
      if (params.priorities.length === 1) {
        const p = params.priorities[0];
        const val = p === "High" ? "high" : p === "Med" ? "medium" : "low";
        queryParams.append('priority', val);
      }
    }

    if (params?.tag) queryParams.append('tag', params.tag);
    if (params?.meeting) queryParams.append('meeting', params.meeting);
    if (params?.status) queryParams.append('status', params.status);
    
    const queryString = queryParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }

    const { data } = await apiClient.get<any>(url);
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (data.results && Array.isArray(data.results)) return data.results;
    if (data.data && Array.isArray(data.data)) return data.data;
    return [];
  },
  getById: async (id: string): Promise<Commitment> => {
    const { data } = await apiClient.get<any>(`commitments/${id}/`);
    if (data && data.data && !data.id) return data.data;
    return data;
  },
  confirm: async (id: string): Promise<Commitment> => {
    const { data } = await apiClient.post<Commitment>(`commitments/${id}/confirm/`);
    return data;
  },
  reopen: async (id: string): Promise<Commitment> => {
    const { data } = await apiClient.post<Commitment>(`commitments/${id}/reopen/`);
    return data;
  },
  escalate: async (id: string): Promise<Commitment> => {
    const { data } = await apiClient.post<Commitment>(`commitments/${id}/escalate/`);
    return data;
  },
  resolve: async (id: string, outcome: string = 'done'): Promise<Commitment> => {
    const { data } = await apiClient.post<Commitment>(`commitments/${id}/resolve/`, { outcome });
    return data;
  },
  reject: async (id: string): Promise<Commitment> => {
    const { data } = await apiClient.post<Commitment>(`commitments/${id}/reject/`);
    return data;
  },
  update: async (id: string, updates: Partial<Commitment>): Promise<Commitment> => {
    const { data } = await apiClient.patch<Commitment>(`commitments/${id}/`, updates);
    return data;
  },
  nudge: async (id: string, method: 'email' = 'email'): Promise<any> => {
    const { data } = await apiClient.post(`commitments/${id}/nudge/`, { method });
    return data;
  },
  getHistory: async (id: string): Promise<CommitmentHistory[]> => {
    const { data } = await apiClient.get<any>(`commitments/${id}/history/`);
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (data.results && Array.isArray(data.results)) return data.results;
    if (data.history && Array.isArray(data.history)) return data.history;
    if (data.data && Array.isArray(data.data)) return data.data;
    return [];
  },
};

export const meetingService = {
  getAll: async (): Promise<Meeting[]> => {
    const { data } = await apiClient.get<any>('meetings/');
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (data.results && Array.isArray(data.results)) return data.results;
    if (data.data && Array.isArray(data.data)) return data.data;
    return [];
  },
  uploadTranscript: async (file: File, title?: string, occurredAt?: string): Promise<any> => {
    const fileText = await file.text();
    const { data } = await apiClient.post('meetings/upload/', {
      transcript: fileText,
      title: title || '',
      occurred_at: occurredAt,
    });
    return data;
  },
  uploadTranscriptText: async (text: string, title?: string, occurredAt?: string): Promise<any> => {
    const { data } = await apiClient.post('meetings/upload/', {
      transcript: text,
      title: title || '',
      occurred_at: occurredAt,
    });
    return data;
  },
  getTranscript: async (id: string): Promise<{ transcript: string }> => {
    const { data } = await apiClient.get<any>(`meetings/${id}/transcript/`);
    
    // If data is a string, return it as transcript
    if (typeof data === 'string') {
      return { transcript: data };
    }

    // Handle standard field
    if (data && data.transcript) {
      return { transcript: data.transcript };
    }

    // Handle raw_transcript field
    if (data && data.raw_transcript) {
      return { transcript: data.raw_transcript };
    }

    // Handle wrapped response
    if (data && data.data) {
      if (typeof data.data === 'string') return { transcript: data.data };
      if (data.data.transcript) return { transcript: data.data.transcript };
      if (data.data.raw_transcript) return { transcript: data.data.raw_transcript };
    }

    return { transcript: "" };
  },
  getById: async (id: string): Promise<Meeting> => {
    const { data } = await apiClient.get<any>(`meetings/${id}/`);
    if (data && data.data && !data.id) return data.data;
    return data;
  },
  getCommitments: async (id: string): Promise<Commitment[]> => {
    const { data } = await apiClient.get<any>(`meetings/${id}/commitments/`);
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (data.results && Array.isArray(data.results)) return data.results;
    if (data.data && Array.isArray(data.data)) return data.data;
    return [];
  },
  getStatus: async (id: string): Promise<{ 
    status: "pending" | "processing" | "complete" | "failed" | "pending_clarification"; 
    commitment_count?: number; 
    clarification_count?: number;
    participant_count?: number; 
    confirmed_count?: number; 
    error?: string;
  }> => {
    const { data } = await apiClient.get(`meetings/${id}/status/`);
    return data;
  },
  getClarifications: async (id: string): Promise<Clarification[]> => {
    const { data } = await apiClient.get<any>(`meetings/${id}/clarifications/`);
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (data.data && Array.isArray(data.data)) return data.data;
    return [];
  },
  submitClarifications: async (id: string, answers: { id: string, answer: string }[]): Promise<any> => {
    const { data } = await apiClient.post(`meetings/${id}/clarifications/`, { answers });
    return data;
  },
  getParticipants: async (id: string): Promise<{
    person: Person;
    speaker_label: string;
    confirmed: boolean;
  }[]> => {
    const { data } = await apiClient.get<any>(`meetings/${id}/participants/`);
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (data.results && Array.isArray(data.results)) return data.results;
    if (data.data && Array.isArray(data.data)) return data.data;
    return [];
  },
  linkParticipants: async (id: string, participants: { detected_name: string, person_id?: string, person?: { name: string, role?: string }, skip?: boolean }[]): Promise<any> => {
    const { data } = await apiClient.post(`meetings/${id}/link-participants/`, { participants });
    return data;
  },
  reprocess: async (id: string): Promise<any> => {
    const { data } = await apiClient.post(`meetings/${id}/reprocess/`);
    return data;
  },
};

export const slackService = {
  getStatus: async (): Promise<{ connected: boolean; workspace_name?: string }> => {
    const { data } = await apiClient.get('slack/status/');
    return data;
  },
  disconnect: async (): Promise<void> => {
    await apiClient.post('slack/disconnect/');
  },
  getUsers: async (): Promise<{ slack_id: string; name: string; email?: string; title?: string; avatar?: string }[]> => {
    const { data } = await apiClient.get('slack/users/sync/');
    return data;
  },
  searchUsers: async (q: string): Promise<any> => {
    const { data } = await apiClient.get('slack/users/', { params: { q } });
    return data;
  },
  importUsers: async (slackIds: string[]): Promise<any> => {
    const { data } = await apiClient.post('slack/users/import/', { slack_ids: slackIds });
    return data;
  },
};

export const gmailService = {
  getStatus: async (): Promise<{ connected: boolean; email?: string }> => {
    const { data } = await apiClient.get('gmail/status/');
    return data;
  },
  disconnect: async (): Promise<void> => {
    await apiClient.post('gmail/disconnect/');
  },
};

export const personService = {
  getAll: async (): Promise<Person[]> => {
    const { data } = await apiClient.get<any>('persons/');
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (data.results && Array.isArray(data.results)) return data.results;
    if (data.data && Array.isArray(data.data)) return data.data;
    return [];
  },
  update: async (id: string, updates: Partial<Person>): Promise<Person> => {
    const { data } = await apiClient.patch<Person>(`persons/${id}/`, updates);
    return data;
  },
  create: async (newPerson: { name: string; email?: string; role?: string; slack_id?: string }): Promise<Person> => {
    const { data } = await apiClient.post<Person>('persons/', newPerson);
    return data;
  },
  merge: async (primaryId: string, mergingIds: string[]): Promise<any> => {
    const { data } = await apiClient.post('persons/merge/', {
      primary_id: primaryId,
      duplicate_ids: mergingIds
    });
    return data;
  },
};

export const tagService = {
  getAll: async (): Promise<string[]> => {
    const { data } = await apiClient.get<string[]>('tags/');
    return data;
  },
};

export const dashboardService = {
  getStats: async (): Promise<{
    overdue: number;
    at_risk: number;
    on_track: number;
    done: number;
    total: number;
  }> => {
    const { data } = await apiClient.get('dashboard/');
    return data;
  },
};

export const importService = {
  upload: async (file?: File, text?: string, title?: string, occurredAt?: string): Promise<{ id: string }> => {
    let responseData: any;
    const body: any = {
      title: title || 'importdata',
    };

    if (file) {
      body.text = await file.text();
    } else {
      body.text = text || '';
    }

    const { data } = await apiClient.post<any>('meetings/import/', body);
    responseData = data;
    
    // Standardize the response to always have an 'id'
    const responseDataJson = data;
    const result = responseDataJson && responseDataJson.data ? responseDataJson.data : responseDataJson;
    if (result && !result.id && result.meeting_id) {
      result.id = result.meeting_id;
    }
    return result;
  },
  getJobStatus: async (jobId: string): Promise<{ status: string; progress: number }> => {
    const { data } = await apiClient.get<{ status: string; progress: number }>(`extraction-jobs/${jobId}/`);
    return data;
  },
};

export const nudgeSettingsService = {
  get: async (): Promise<{ first_days_before: number; second_hours_before: number; nudge_enabled: boolean }> => {
    const { data } = await apiClient.get('nudge-settings/');
    return data;
  },
  patch: async (updates: { first_days_before?: number; second_hours_before?: number; nudge_enabled?: boolean }): Promise<{ first_days_before: number; second_hours_before: number; nudge_enabled: boolean }> => {
    const { data } = await apiClient.patch('nudge-settings/', updates);
    return data;
  },
};

export const notificationService = {
  getAll: async (params?: { page?: number }): Promise<{ results: any[], count: number, next: string | null, previous: string | null }> => {
    const page = params?.page || 1;
    const { data } = await apiClient.get(`notifications/?page=${page}`);
    
    if (Array.isArray(data)) {
      return { results: data, count: data.length, next: null, previous: null };
    }
    
    if (data && data.results) {
      return data;
    }
    
    return { results: [], count: 0, next: null, previous: null };
  },
  getUnreadCount: async (): Promise<{ unread: number }> => {
    const { data } = await apiClient.get('notifications/unread-count/');
    if (typeof data === 'number') {
      return { unread: data };
    }
    return data || { unread: 0 };
  },
  markAsRead: async (id: string): Promise<void> => {
    await apiClient.post(`notifications/${id}/read/`);
  },
  markAllRead: async (): Promise<void> => {
    await apiClient.post('notifications/mark-all-read/');
  },
};

