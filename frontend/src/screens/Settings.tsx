import { useState } from "react";
import { motion } from "motion/react";
import { 
  Slack, 
  Mail, 
  Shield, 
  Users, 
  Globe, 
  Bell, 
  Trash2,
  Calendar,
  Video,
  Plus,
  CheckCircle2,
  FileUp,
  FileText,
  Sheet,
  ArrowRight,
  X,
  AlertCircle,
  Loader2,
  Building2
} from "lucide-react";
import { NotificationsSettings } from "@/src/components/NotificationsSettings";
import { Card } from "@/src/components/ui/Card";
import { Button } from "@/src/components/ui/Button";
import { Badge } from "@/src/components/ui/Badge";
import { Avatar } from "@/src/components/ui/Avatar";
import { cn } from "@/src/lib/utils";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { slackService, importService, nudgeSettingsService, gmailService, calendarService, zoomService, managerService, inviteService } from "@/src/lib/api/services";
import { authService } from "@/src/lib/api/auth";
import { useNavigate } from "react-router-dom";
import { AnimatePresence } from "motion/react";
import { useRef, DragEvent, ChangeEvent } from "react";
import { ImportSuccessModal } from "@/src/components/ImportSuccessModal";
import { LinkSlackPeopleModal } from "@/src/components/LinkSlackPeopleModal";
import { DelegationManagement } from "@/src/components/DelegationManagement";
import { APP_VERSION } from "../types";

export const Settings = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isSuccessOpen, setIsSuccessOpen] = useState(false);
  const [isSlackImportOpen, setIsSlackImportOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<'organization' | 'integrations' | 'notifications' | 'delegation' | 'data'>('organization');

  const { data: profile, isLoading: isLoadingProfile } = useQuery({
    queryKey: ['user-profile'],
    queryFn: () => authService.getProfile(),
  });

  const { data: invitations } = useQuery({
    queryKey: ['invitations'],
    queryFn: () => inviteService.list(),
    enabled: !!profile?.is_org_admin,
  });
  
  const { data: slackStatus, isLoading: isLoadingSlack } = useQuery({
    queryKey: ['slack-status'],
    queryKeyHashFn: () => 'slack-status',
    queryFn: () => slackService.getStatus(),
  });

  const inviteMutation = useMutation({
    mutationFn: (email: string) => inviteService.send(email),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invitations'] });
      setInviteEmail('');
      setInviteError(null);
    },
    onError: (err: any) => {
      setInviteError(err.response?.data?.detail || "Something went wrong. Please try again.");
    }
  });

  const resendMutation = useMutation({
    mutationFn: (id: string) => inviteService.resend(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations'] }),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => inviteService.revoke(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invitations'] }),
  });

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const disconnectSlackMutation = useMutation({
    mutationFn: () => slackService.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slack-status'] });
    }
  });

  const { data: nudgeSettings, isLoading: isLoadingNudge } = useQuery({
    queryKey: ['nudge-settings'],
    queryFn: () => nudgeSettingsService.get(),
  });

  const updateNudgeMutation = useMutation({
    mutationFn: (updates: { first_days_before?: number; second_hours_before?: number; nudge_enabled?: boolean }) => 
      nudgeSettingsService.patch(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nudge-settings'] });
    },
  });

  const handleSlackConnect = () => {
    const API_URL = (import.meta.env.VITE_API_URL || 'https://api.verato.twocents.ai/api/v1').replace(/\/$/, '');
    const token = localStorage.getItem('accessToken');
    const url = `${API_URL}/slack/oauth/start/?auth=${token}`;
    
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    
    const popup = window.open(
      url,
      'Connect to Slack',
      `width=${width},height=${height},left=${left},top=${top},status=no,menubar=no,toolbar=no`
    );

    if (popup) {
      const timer = setInterval(() => {
        if (popup.closed) {
          clearInterval(timer);
          queryClient.invalidateQueries({ queryKey: ['slack-status'] });
        }
      }, 1000);
    }
  };

  const handleDisconnect = () => {
    if (window.confirm("Are you sure you want to disconnect Slack? Verato will no longer be able to send automated nudges.")) {
      disconnectSlackMutation.mutate();
    }
  };

  const { data: gmailStatus, isLoading: isLoadingGmail } = useQuery({
    queryKey: ['gmail-status'],
    queryFn: () => gmailService.getStatus(),
  });

  const disconnectGmailMutation = useMutation({
    mutationFn: () => gmailService.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmail-status'] });
    }
  });

  const { data: calendarStatus, isLoading: isLoadingCalendar } = useQuery({
    queryKey: ['calendar-status'],
    queryFn: () => calendarService.getStatus(),
  });

  const disconnectCalendarMutation = useMutation({
    mutationFn: () => calendarService.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar-status'] });
    }
  });

  const { data: zoomStatus, isLoading: isLoadingZoom } = useQuery({
    queryKey: ['zoom-status'],
    queryFn: () => zoomService.getStatus(),
  });

  const disconnectZoomMutation = useMutation({
    mutationFn: () => zoomService.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zoom-status'] });
    }
  });

  const handleZoomConnect = () => {
    const token = localStorage.getItem('accessToken');
    if (!token) return;
    const popup = zoomService.connect(token);
    
    if (popup) {
      const timer = setInterval(async () => {
        try {
          if (popup.closed) {
            clearInterval(timer);
            queryClient.invalidateQueries({ queryKey: ['zoom-status'] });
          }
        } catch (err) {
          console.error("Error polling zoom status", err);
          if (popup.closed) {
            clearInterval(timer);
          }
        }
      }, 500);
    }
  };

  const handleCalendarConnect = () => {
    const token = localStorage.getItem('accessToken');
    if (!token) return;
    const popup = calendarService.connect(token);
    if (popup) {
      const timer = setInterval(async () => {
        try {
          if (popup.closed) {
            clearInterval(timer);
            queryClient.invalidateQueries({ queryKey: ['calendar-status'] });
          }
        } catch (err) {
          console.error("Error polling calendar status", err);
          if (popup.closed) {
            clearInterval(timer);
          }
        }
      }, 500);
    }
  };

  const handleGmailConnect = () => {
    const API_URL = (import.meta.env.VITE_API_URL || 'https://api.verato.twocents.ai/api/v1').replace(/\/$/, '');
    const token = localStorage.getItem('accessToken');
    const url = `${API_URL}/gmail/oauth/start/?auth=${token}`;
    
    const width = 600;
    const height = 750;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    
    const popup = window.open(
      url,
      'Connect to Gmail',
      `width=${width},height=${height},left=${left},top=${top},status=no,menubar=no,toolbar=no`
    );

    if (popup) {
      const timer = setInterval(async () => {
        try {
          const statusResult = await queryClient.fetchQuery({
            queryKey: ['gmail-status'],
            queryFn: () => gmailService.getStatus(),
          });
          if (statusResult?.connected || popup.closed) {
            clearInterval(timer);
            queryClient.invalidateQueries({ queryKey: ['gmail-status'] });
          }
        } catch (err) {
          console.error("Error polling gmail status", err);
          if (popup.closed) {
            clearInterval(timer);
          }
        }
      }, 2000);
    }
  };

  const handleGmailDisconnect = () => {
    if (window.confirm("Are you sure you want to disconnect Gmail?")) {
      disconnectGmailMutation.mutate();
    }
  };

  const sidebarItems = [
    { id: 'organization', label: 'Organization & Team', icon: Building2 },
    { id: 'integrations', label: 'Integrations', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'delegation', label: 'Delegation', icon: Users },
    { id: 'data', label: 'Data Import', icon: FileUp },
  ];

  return (
    <>
      <div className="max-w-6xl mx-auto px-4 md:px-0 py-10">
        <div className="mb-10">
          <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-2 underline decoration-blue-500/50 underline-offset-4 decoration-2">Settings</h1>
          <p className="text-slate-500 font-bold tracking-tight">Configure your integrations and automated workflows.</p>
        </div>

        <div className="flex flex-wrap gap-2 mb-10 border-b border-slate-200 pb-2">
          {sidebarItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveCategory(item.id as any)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 font-bold text-sm transition-all border-b-2",
                activeCategory === item.id
                  ? "text-blue-700 border-blue-600"
                  : "text-slate-600 border-transparent hover:text-slate-900"
              )}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </button>
          ))}
        </div>

        <main className="space-y-8">
          {activeCategory === 'organization' && (
            <div className="space-y-8">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
                  <div className="flex items-center gap-6">
                    <div className="w-16 h-16 bg-blue-600 rounded-[20px] flex items-center justify-center text-white shadow-2xl shadow-blue-600/30 shrink-0">
                      <Building2 className="w-9 h-9" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-black text-slate-900">Organisation</h2>
                      {isLoadingProfile ? (
                        <div className="flex items-center gap-2 mt-1 text-slate-400 font-bold text-sm">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Loading...
                        </div>
                      ) : (
                        <p className="text-slate-500 text-lg font-bold leading-relaxed">{profile?.organisation?.name || "No organisation specified"}</p>
                      )}
                    </div>
                  </div>
                </Card>
              </motion.div>

              {profile?.is_org_admin && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                  <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
                    <div className="mb-8">
                      <h2 className="text-xl font-black text-slate-900">Invite a Team Member</h2>
                      <p className="text-slate-500 font-medium text-sm">Team members get a Verato account and can log in to manage commitments.</p>
                    </div>
                    
                    <div className="flex gap-3 mb-8">
                      <input 
                        type="email"
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        placeholder="email@example.com"
                        className="w-full h-12 bg-slate-50 border border-slate-200 rounded-2xl px-5 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-bold text-sm"
                      />
                      <Button 
                        onClick={() => inviteMutation.mutate(inviteEmail)}
                        disabled={inviteMutation.isPending || !inviteEmail.trim()}
                        className="h-12 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-black px-6 border-none disabled:opacity-50"
                      >
                        {inviteMutation.isPending ? "Sending..." : "Send Invite"}
                      </Button>
                    </div>
                    {inviteError && <p className="text-red-500 text-xs font-bold mt-1 ml-1">{inviteError}</p>}

                    <div className="space-y-4">
                      <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 ml-1">Pending Invitations</h3>
                      {invitations?.filter(inv => inv.status === 'pending' || inv.status === 'expired').length === 0 ? (
                        <p className="text-slate-400 font-bold text-sm text-center py-8">No pending invitations. Invite a colleague above.</p>
                      ) : (
                        invitations?.filter(inv => inv.status === 'pending' || inv.status === 'expired').map(inv => (
                          <div key={inv.id} className="group flex items-center justify-between p-4 bg-slate-50 rounded-2xl">
                            <div>
                              <p className="font-black text-slate-900">{inv.email}</p>
                              <p className="text-xs text-slate-500 font-bold">{new Date(inv.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
                            </div>
                            <div className="flex items-center gap-4">
                              <span className={cn(
                                "text-[10px] font-black uppercase tracking-widest rounded-full px-3 py-0.5 border",
                                inv.status === 'pending' ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-slate-100 text-slate-400 border-slate-200"
                              )}>
                                {inv.status}
                              </span>
                              
                              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <Button variant="secondary" size="sm" className="h-9 rounded-xl border border-slate-200 font-bold text-sm px-4" onClick={() => resendMutation.mutate(inv.id)}>Resend</Button>
                                {revokingId === inv.id ? (
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs font-bold">Are you sure?</span>
                                    <Button variant="ghost" size="sm" className="text-red-500 font-bold text-sm" onClick={() => revokeMutation.mutate(inv.id)}>Yes, revoke</Button>
                                    <Button variant="ghost" size="sm" className="font-bold text-sm text-slate-500" onClick={() => setRevokingId(null)}>Cancel</Button>
                                  </div>
                                ) : (
                                  <Button variant="ghost" size="sm" className="text-red-500 font-bold text-sm" onClick={() => setRevokingId(inv.id)}>Revoke</Button>
                                )}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </Card>
                </motion.div>
              )}
            </div>
          )}

          {activeCategory === 'integrations' && (
            <div className="space-y-6">            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="space-y-6">
              <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
                <div className="flex flex-col md:flex-row items-start justify-between gap-6">
                  <div className="flex gap-6">
                    <div className="w-16 h-16 bg-[#4A154B]/10 rounded-[20px] flex items-center justify-center text-[#4A154B] shadow-2xl shadow-[#4A154B]/10 shrink-0">
                      <svg viewBox="0 0 24 24" className="w-9 h-9 fill-current"><path d="M5.04 15.174a1.838 1.838 0 1 0-.008 3.676 1.838 1.838 0 0 0 .008-3.676zm0-5.513a1.838 1.838 0 1 0-.008 3.676 1.838 1.838 0 0 0 .008-3.676zM10.553 5.04a1.838 1.838 0 1 0 3.676.008 1.838 1.838 0 0 0-3.676-.008zm5.513 0a1.838 1.838 0 1 0 3.676.008 1.838 1.838 0 0 0-3.676-.008zM18.96 8.826a1.838 1.838 0 1 0 .008 3.676 1.838 1.838 0 0 0-.008-3.676zm0 5.513a1.838 1.838 0 1 0 .008 3.676 1.838 1.838 0 0 0-.008-3.676zM13.447 18.96a1.838 1.838 0 1 0-3.676-.008 1.838 1.838 0 0 0 3.676.008zm-5.513 0a1.838 1.838 0 1 0-3.676-.008 1.838 1.838 0 0 0 3.676.008zM7.348 7.348h9.304v9.304H7.348V7.348z"/></svg>
                    </div>
                    <div>
                      <h2 className="text-2xl font-black text-slate-900">Slack</h2>
                      <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">Connect Slack to receive automated meeting nudges and status updates.</p>
                      
                      {isLoadingSlack ? (
                        <div className="flex items-center gap-2 mt-4 text-slate-400 font-black text-[10px] uppercase tracking-[0.2em]">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Checking Status...
                        </div>
                      ) : slackStatus?.connected ? (
                        <div className="flex items-center gap-2 mt-4 text-emerald-700 font-black text-[10px] uppercase tracking-[0.2em] bg-emerald-100/50 border border-emerald-200 px-3 py-1.5 rounded-xl inline-flex">
                           <CheckCircle2 className="w-3.5 h-3.5" />
                           Status: Connected
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 mt-4 text-slate-500 font-black text-[10px] uppercase tracking-[0.2em] bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl inline-flex">
                           <AlertCircle className="w-3.5 h-3.5" />
                           Status: Disconnected
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
                    {slackStatus?.connected ? (
                      <Button 
                        variant="secondary" 
                        onClick={() => disconnectSlackMutation.mutate()}
                        disabled={disconnectSlackMutation.isPending}
                        className="rounded-2xl border-slate-200 px-6 font-bold h-11 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 transition-all shrink-0"
                      >
                        {disconnectSlackMutation.isPending ? "Disconnecting..." : "Disconnect"}
                      </Button>
                    ) : (
                      <Button 
                        onClick={handleSlackConnect}
                        className="rounded-2xl bg-[#4A154B] text-white px-6 font-bold h-11 hover:bg-[#350d36] transition-all shrink-0 border-none"
                      >
                        Connect Slack
                      </Button>
                    )}
                  </div>
                </div>
              </Card>

              <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
                <div className="flex flex-col md:flex-row items-start justify-between gap-6">
                  <div className="flex gap-6">
                    <div className="w-16 h-16 bg-red-600 rounded-[20px] flex items-center justify-center text-white shadow-2xl shadow-red-600/30 shrink-0">
                      <Mail className="w-9 h-9" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-black text-slate-900">Gmail Connection</h2>
                      <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">Connect Gmail to synchronize emails and let the AI pick up all replies and context specific to the actions and nudges</p>
                      
                      {isLoadingGmail ? (
                        <div className="flex items-center gap-2 mt-4 text-slate-400 font-black text-[10px] uppercase tracking-[0.2em]">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Checking Status...
                        </div>
                      ) : gmailStatus?.connected ? (
                        <div className="flex items-center gap-2 mt-4 text-emerald-700 font-black text-[10px] uppercase tracking-[0.2em] bg-emerald-100/50 border border-emerald-200 px-3 py-1.5 rounded-xl inline-flex">
                           <CheckCircle2 className="w-3.5 h-3.5" />
                           Status: Connected
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 mt-4 text-slate-500 font-black text-[10px] uppercase tracking-[0.2em] bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl inline-flex">
                           <AlertCircle className="w-3.5 h-3.5" />
                           Status: Disconnected
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
                    {gmailStatus?.connected ? (
                      <Button 
                        variant="secondary" 
                        onClick={handleGmailDisconnect}
                        disabled={disconnectGmailMutation.isPending}
                        className="rounded-2xl border-slate-200 px-6 font-bold h-11 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 transition-all shrink-0"
                      >
                        {disconnectGmailMutation.isPending ? "Disconnecting..." : "Disconnect"}
                      </Button>
                    ) : (
                      <Button 
                        onClick={handleGmailConnect}
                        className="rounded-2xl bg-slate-900 text-white px-6 font-bold h-11 hover:bg-slate-800 transition-all shrink-0 border-none"
                      >
                        Connect Gmail
                      </Button>
                    )}
                  </div>
                </div>
              </Card>

              <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
                <div className="flex flex-col md:flex-row items-start justify-between gap-6">
                  <div className="flex gap-6">
                    <div className="w-16 h-16 bg-blue-100 rounded-[20px] flex items-center justify-center text-blue-700 shadow-2xl shadow-blue-500/10 shrink-0">
                      <Video className="w-9 h-9" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-black text-slate-900">Zoom</h2>
                      <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">Connect your Zoom account to synchronize meetings and automatically synch meeting notes</p>
                      
                      {isLoadingZoom ? (
                        <div className="flex items-center gap-2 mt-4 text-slate-400 font-black text-[10px] uppercase tracking-[0.2em]">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Checking Status...
                        </div>
                      ) : zoomStatus?.connected ? (
                        <div className="flex items-center gap-2 mt-4 text-emerald-700 font-black text-[10px] uppercase tracking-[0.2em] bg-emerald-100/50 border border-emerald-200 px-3 py-1.5 rounded-xl inline-flex">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Status: Connected
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 mt-4 text-slate-500 font-black text-[10px] uppercase tracking-[0.2em] bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl inline-flex">
                          <AlertCircle className="w-3.5 h-3.5" />
                          Status: Disconnected
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
                    {zoomStatus?.connected ? (
                      <Button 
                        variant="secondary" 
                        onClick={() => disconnectZoomMutation.mutate()}
                        disabled={disconnectZoomMutation.isPending}
                        className="rounded-2xl border-slate-200 px-6 font-bold h-11 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 transition-all shrink-0"
                      >
                        {disconnectZoomMutation.isPending ? "Disconnecting..." : "Disconnect"}
                      </Button>
                    ) : (
                      <Button 
                        onClick={handleZoomConnect}
                        className="rounded-2xl bg-slate-900 text-white px-6 font-bold h-11 hover:bg-slate-800 transition-all shrink-0 border-none"
                      >
                        Connect Zoom
                      </Button>
                    )}
                  </div>
                </div>
              </Card>

              <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
                <div className="flex flex-col md:flex-row items-start justify-between gap-6">
                  <div className="flex gap-6">
                    <div className="w-16 h-16 bg-blue-100 rounded-[20px] flex items-center justify-center text-blue-700 shadow-2xl shadow-blue-500/10 shrink-0">
                      <Calendar className="w-9 h-9" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-black text-slate-900">Google Calendar</h2>
                      <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">Connect your Google Calendar to sync meetings and automatically download transcripts from google meet.</p>
                      
                      {isLoadingCalendar ? (
                        <div className="flex items-center gap-2 mt-4 text-slate-400 font-black text-[10px] uppercase tracking-[0.2em]">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Checking Status...
                        </div>
                      ) : calendarStatus?.connected ? (
                        <div className="flex items-center gap-2 mt-4 text-emerald-700 font-black text-[10px] uppercase tracking-[0.2em] bg-emerald-100/50 border border-emerald-200 px-3 py-1.5 rounded-xl inline-flex">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Status: Connected
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 mt-4 text-slate-500 font-black text-[10px] uppercase tracking-[0.2em] bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl inline-flex">
                          <AlertCircle className="w-3.5 h-3.5" />
                          Status: Disconnected
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
                    {calendarStatus?.connected ? (
                      <Button 
                        variant="secondary" 
                        onClick={() => disconnectCalendarMutation.mutate()}
                        disabled={disconnectCalendarMutation.isPending}
                        className="rounded-2xl border-slate-200 px-6 font-bold h-11 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 transition-all shrink-0"
                      >
                        {disconnectCalendarMutation.isPending ? "Disconnecting..." : "Disconnect"}
                      </Button>
                    ) : (
                      <Button 
                        onClick={handleCalendarConnect}
                        className="rounded-2xl bg-slate-900 text-white px-6 font-bold h-11 hover:bg-slate-800 transition-all shrink-0 border-none"
                      >
                        Connect Google Calendar
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            </motion.div>
            </div>
          )}

          {activeCategory === 'notifications' && (
            <NotificationsSettings />
          )}
          {activeCategory === 'delegation' && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }} className="space-y-6">
              <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
                 <div className="flex gap-6 mb-8">
                  <div className="w-16 h-16 bg-blue-50 rounded-[20px] flex items-center justify-center text-blue-600 shadow-2xl shadow-blue-500/10 shrink-0">
                    <Users className="w-9 h-9" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-black text-slate-900">Delegation Management</h2>
                    <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">
                      Manage who can access your meetings or who you are acting on behalf of.
                    </p>
                  </div>
                </div>
                <DelegationManagement />
              </Card>
            </motion.div>
          )}

          {activeCategory === 'data' && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
                <div className="flex flex-col md:flex-row items-start justify-between gap-6">
                  <div className="flex gap-6">
                    <div className="w-16 h-16 bg-blue-50 rounded-[20px] flex items-center justify-center text-blue-600 shadow-2xl shadow-blue-500/10 shrink-0">
                      <FileUp className="w-9 h-9" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-black text-slate-900">Import Tasks</h2>
                      <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">
                        Bring in tasks from your existing spreadsheets, documents, or raw meeting notes. Verato will automatically extract commitments.
                      </p>
                    </div>
                  </div>
                  
                  <Button 
                    onClick={() => setIsImportModalOpen(true)}
                    className="rounded-2xl bg-slate-900 text-white px-6 font-bold h-11 hover:bg-slate-800 transition-all shrink-0 border-none"
                  >
                    Launch Importer
                  </Button>
                </div>
                <div className="mt-8 pt-8 border-t border-slate-100 text-center">
                  <p className="text-slate-400 text-xs font-bold uppercase tracking-widest">
                    Version {APP_VERSION}
                  </p>
                </div>
              </Card>
            </motion.div>
          )}
        </main>
      </div>
      <AnimatePresence>
        {isImportModalOpen && (
          <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsImportModalOpen(false)}
              className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-xl bg-white rounded-3xl shadow-2xl overflow-hidden"
            >
              <div className="absolute top-6 right-6 z-10">
                <button 
                  onClick={() => setIsImportModalOpen(false)}
                  className="p-2 hover:bg-slate-100 rounded-full text-slate-400 transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="p-8 max-h-[90vh] overflow-y-auto">
                <div className="text-center mb-8 pt-4">
                  <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <FileUp className="w-8 h-8" />
                  </div>
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight mb-2">Import your Tracker</h2>
                  <p className="text-slate-500 font-medium text-sm">Verato is useful from minute one. Bring in your existing spreadsheet or notes.</p>
                </div>
                
                <ImportTrackerSettingsContent onSuccess={() => { setIsImportModalOpen(false); setIsSuccessOpen(true); }} />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      <ImportSuccessModal isOpen={isSuccessOpen} onClose={() => setIsSuccessOpen(false)} />
      <LinkSlackPeopleModal isOpen={isSlackImportOpen} onClose={() => setIsSlackImportOpen(false)} />
      </>
  );
};

const ImportTrackerSettingsContent = ({ onSuccess }: { onSuccess: () => void }) => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState('');
  const [title, setTitle] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  };

  const validateAndSetFile = (file: File) => {
    const validExtensions = ['.csv', '.xlsx', '.docx', '.txt', '.md'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));
    
    if (isValid) {
      setFile(file);
      setPastedText(''); 
    } else {
      setError('Invalid file type. Please use .csv, .xlsx, .docx, .txt, or .md');
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const chosenFile = e.target.files?.[0];
    if (chosenFile) {
      validateAndSetFile(chosenFile);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleExtract = async () => {
    if (!title.trim()) {
      setError('Import Title is required.');
      return;
    }
    setIsLoading(true);
    setError(null);
    
    try {
      let jobId: string;
      if (file) {
        const response = await importService.upload(file, undefined, title.trim());
        jobId = response.id;
      } else {
        const response = await importService.upload(undefined, pastedText, title.trim());
        jobId = response.id;
      }
      
      let progress = 0;
      const interval = setInterval(async () => {
        progress += 25;
        if (progress >= 100) {
          clearInterval(interval);
          setIsLoading(false);
          onSuccess();
        }
      }, 800);

    } catch (err: any) {
      setError('Failed to start extraction. Please try again.');
      setIsLoading(false);
    }
  };

  const isExtractDisabled = !title.trim() || (!file && pastedText.trim().length < 10);

  return (
    <div className="space-y-6">
      {/* Title Input */}
      <div className="space-y-2 text-left">
        <label className="text-sm font-bold text-slate-700 flex items-center gap-1">
          Import Title <span className="text-rose-500">*</span>
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Q2 Engineering Sync, Marketing Plan Tracker..."
          className="w-full h-11 bg-slate-50 border border-slate-200 rounded-xl px-4 text-sm font-medium focus:border-blue-500 transition-all focus:outline-none"
          required
        />
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "relative border-2 border-dashed rounded-2xl p-10 transition-all cursor-pointer text-center",
          isDragging 
            ? 'border-blue-500 bg-blue-50/50 scale-[1.01]' 
            : file 
              ? 'border-emerald-200 bg-emerald-50/20' 
              : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
        )}
      >
        <input 
          type="file" 
          ref={fileInputRef}
          className="hidden" 
          onChange={handleFileChange}
          accept=".csv,.xlsx,.docx,.txt,.md"
        />
        
        <AnimatePresence mode="wait">
          {file ? (
            <motion.div 
              key="file-active"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center"
            >
              <div className="w-16 h-16 bg-white rounded-xl shadow-sm border border-emerald-100 flex items-center justify-center mb-4">
                {file.name.endsWith('.xlsx') || file.name.endsWith('.csv') ? (
                  <Sheet className="w-8 h-8 text-emerald-600" />
                ) : (
                  <FileText className="w-8 h-8 text-blue-600" />
                )}
              </div>
              <p className="text-sm font-bold text-slate-800 mb-1">{file.name}</p>
              <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                {(file.size / 1024).toFixed(1)} KB — Ready for extraction
              </p>
              
              <button 
                onClick={(e) => { e.stopPropagation(); handleRemoveFile(); }}
                className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-400 hover:text-rose-500 hover:border-rose-200 transition-all shadow-sm"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          ) : (
            <motion.div 
              key="file-empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="w-16 h-16 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center justify-center mx-auto mb-4">
                <FileUp className={`w-8 h-8 ${isDragging ? 'text-blue-500' : 'text-slate-300'}`} />
              </div>
              <h3 className="text-slate-900 font-bold mb-1">Drag your tracker here</h3>
              <p className="text-slate-500 text-sm font-medium">CSV, XLSX, DOCX, TXT or Markdown</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="relative py-4">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-slate-100"></div>
        </div>
        <div className="relative flex justify-center">
          <span className="bg-white px-4 text-[10px] font-black uppercase tracking-widest text-slate-400">or paste text</span>
        </div>
      </div>

      <textarea
        value={pastedText}
        onChange={(e) => { setPastedText(e.target.value); setFile(null); }}
        placeholder="Paste your meeting notes or task list here..."
        className="w-full h-32 bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm font-medium focus:border-blue-500 transition-all focus:outline-none resize-none"
      />

      {error && (
        <div className="flex items-center gap-2 p-3 bg-rose-50 border border-rose-100 rounded-xl text-rose-700 text-xs font-bold">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      <div className="space-y-4 pt-2">
        <Button 
          disabled={isExtractDisabled || isLoading}
          onClick={handleExtract}
          className="w-full h-14 text-lg font-black shadow-lg shadow-blue-500/20"
        >
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Extracting items...</span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span>Extract {file ? 'from file' : 'from text'}</span>
              <ArrowRight className="w-5 h-5" />
            </div>
          )}
        </Button>
      </div>
    </div>
  );
};
