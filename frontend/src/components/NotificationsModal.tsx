import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationService } from '../lib/api/services';
import { Bell, Check, CheckCheck, X, FileCheck, AlertCircle, MessageSquare, Mail, UserCheck, CheckCircle, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Notification } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

const getNotificationConfig = (type: Notification['notification_type']) => {
  switch (type) {
    case 'meeting_ready': return { icon: FileCheck, color: 'text-emerald-500', bg: 'bg-emerald-50' };
    case 'meeting_failed': return { icon: AlertCircle, color: 'text-rose-500', bg: 'bg-rose-50' };
    case 'slack_reply': return { icon: MessageSquare, color: 'text-purple-500', bg: 'bg-purple-50' };
    case 'gmail_reply': return { icon: Mail, color: 'text-blue-500', bg: 'bg-blue-50' };
    case 'owner_update': return { icon: UserCheck, color: 'text-amber-500', bg: 'bg-amber-50' };
    case 'commitment_closed': return { icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-50' };
    case 'delegation_invite': return { icon: Users, color: 'text-purple-500', bg: 'bg-purple-50' };
  }
};

export const NotificationsModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const [page, setPage] = useState(1);
  const [showRead, setShowRead] = useState(false);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationService.getAll(),
    enabled: isOpen,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationService.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-notifications'] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationService.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['unread-notifications'] });
    },
  });

  if (!isOpen) return null;

  const handleNotificationClick = (notification: Notification) => {
    if (notification.commitment_id) {
      navigate(`/commitments/${notification.commitment_id}`);
    } else if (notification.notification_type === 'meeting_ready' || notification.notification_type === 'meeting_failed') {
      navigate('/meetings');
    } else if (notification.notification_type === 'delegation_invite') {
      navigate('/settings');
    }
    if (!notification.is_read) {
      markReadMutation.mutate(notification.id);
    }
    onClose();
  };

  const filteredNotifications = (data?.results || [])
    .filter((n: Notification) => n.is_read === showRead)
    .sort((a: Notification, b: Notification) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const totalPages = Math.max(1, Math.ceil(filteredNotifications.length / 5));

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Bell className="w-5 h-5 text-purple-600" />
            Notifications
          </h2>
          <div className="flex gap-2">
            <button onClick={() => markAllReadMutation.mutate()} className="text-xs font-bold text-slate-500 hover:text-purple-600 flex items-center gap-1">
              <CheckCheck className="w-4 h-4" />
              Mark all read
            </button>
            <button onClick={onClose}>
              <X className="w-5 h-5 text-slate-500" />
            </button>
          </div>
        </div>

        <div className="p-2 border-b border-slate-100">
          <button 
            onClick={() => { setShowRead(!showRead); setPage(1); }} 
            className="text-xs text-purple-600 hover:text-purple-800 font-medium"
          >
            {showRead ? 'Show unread notifications' : 'Show read notifications'}
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-2">
          {isLoading ? (
            <p className="p-4 text-center text-slate-500">Loading...</p>
          ) : filteredNotifications.length === 0 ? (
            <p className="p-4 text-center text-slate-500">No {showRead ? 'read' : 'unread'} notifications</p>
          ) : (
            filteredNotifications.slice((page - 1) * 5, page * 5).map((n: Notification) => {
              const { icon: Icon, color, bg } = getNotificationConfig(n.notification_type);
              return (
                <div 
                  key={n.id} 
                  className={`p-3 rounded-lg mb-2 cursor-pointer transition-colors ${n.is_read ? 'bg-white border border-slate-100' : 'bg-slate-100'}`}
                  onClick={() => handleNotificationClick(n)}
                >
                  <div className="flex gap-3">
                    <div className={`p-2 rounded-full ${bg}`}>
                      <Icon className={`w-4 h-4 ${color}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs ${n.is_read ? 'text-slate-600' : 'text-slate-900 font-bold'}`}>
                        {n.message}
                      </p>
                      {n.notification_type === 'delegation_invite' && (
                        <p className="text-[10px] text-slate-400 mt-1 italic">Go to Settings → Delegation to accept or decline.</p>
                      )}
                      <span className="text-[10px] text-slate-400 font-normal block mt-1">{formatDate(n.created_at)}</span>
                    </div>
                    {!n.is_read && <button onClick={(e) => { e.stopPropagation(); markReadMutation.mutate(n.id); }}><Check className="w-4 h-4 text-purple-600 flex-shrink-0" /></button>}
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="p-4 border-t border-slate-100 flex justify-between items-center text-sm">
          <button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      </div>
    </div>
  );
};
