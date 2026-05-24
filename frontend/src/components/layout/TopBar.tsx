import { useState } from 'react';
import { Bell } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { notificationService } from '../../lib/api/services';
import { NotificationsModal } from '../NotificationsModal';

export const TopBar = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: unreadData } = useQuery({
    queryKey: ['unread-notifications'],
    queryFn: () => notificationService.getUnreadCount(),
    refetchInterval: 60000, // Refresh every minute
    staleTime: 0,
  });

  return (
    <div className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-8 sticky top-0 z-50 ml-64 flex-shrink-0 shadow-sm relative">
      <div className="flex items-center gap-4 flex-1">
        {/* Search removed */}
      </div>

      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <span className="text-lg font-black tracking-[0.2em] text-slate-800 uppercase font-sans">Verato</span>
      </div>

      <div className="flex items-center gap-4">
        <button onClick={() => setIsModalOpen(true)} className="relative p-2 text-slate-500 hover:text-purple-600 transition-colors">
          <Bell className="w-6 h-6" />
          {unreadData?.unread !== undefined && unreadData.unread > 0 && (
            <span className="absolute top-1 right-1 bg-rose-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
              {unreadData.unread}
            </span>
          )}
        </button>
      </div>
      <NotificationsModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
};
