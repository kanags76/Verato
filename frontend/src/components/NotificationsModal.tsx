import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationService } from '../lib/api/services';
import { Bell, Check, CheckCheck, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

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

  const handleNotificationClick = (notification: any) => {
    if (notification.commitment_id) {
      navigate(`/commitments/${notification.commitment_id}`);
    } else if (notification.link) {
      navigate(notification.link);
    }
    if (!notification.is_read) {
      markReadMutation.mutate(notification.id);
    }
    onClose();
  };

  const filteredNotifications = (data?.results || [])
    .filter((n: any) => n.is_read === showRead)
    .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

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
            filteredNotifications.slice((page - 1) * 5, page * 5).map((n: any, index: number) => (
              <div 
                key={n.id} 
                className={`p-3 rounded-lg mb-2 cursor-pointer transition-colors ${n.is_read ? 'bg-white border border-slate-100' : 'bg-slate-100'}`}
                onClick={() => handleNotificationClick(n)}
              >
                <div className="flex justify-between items-start gap-2">
                  <p className={`text-xs ${n.is_read ? 'text-slate-600' : 'text-slate-900 font-bold'}`}>
                    {(page - 1) * 5 + index + 1}. {n.title} {n.message} 
                    <span className="text-[10px] text-slate-400 font-normal ml-2">{formatDate(n.created_at)}</span>
                  </p>
                  {!n.is_read && <button onClick={(e) => { e.stopPropagation(); markReadMutation.mutate(n.id); }}><Check className="w-4 h-4 text-purple-600 flex-shrink-0" /></button>}
                </div>
              </div>
            ))
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
