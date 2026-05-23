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
import { Card } from "@/src/components/ui/Card";
import { Button } from "@/src/components/ui/Button";
import { Badge } from "@/src/components/ui/Badge";
import { Avatar } from "@/src/components/ui/Avatar";
import { cn } from "@/src/lib/utils";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { slackService, importService, nudgeSettingsService, gmailService } from "@/src/lib/api/services";
import { authService } from "@/src/lib/api/auth";
import { useNavigate } from "react-router-dom";
import { AnimatePresence } from "motion/react";
import { useRef, DragEvent, ChangeEvent } from "react";
import { ImportSuccessModal } from "@/src/components/ImportSuccessModal";
import { LinkSlackPeopleModal } from "@/src/components/LinkSlackPeopleModal";

export const Settings = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isSuccessOpen, setIsSuccessOpen] = useState(false);
  const [isSlackImportOpen, setIsSlackImportOpen] = useState(false);

  const { data: profile, isLoading: isLoadingProfile } = useQuery({
    queryKey: ['user-profile'],
    queryFn: () => authService.getProfile(),
  });

  const { data: slackStatus, isLoading: isLoadingSlack } = useQuery({
    queryKey: ['slack-status'],
    queryKeyHashFn: () => 'slack-status',
    queryFn: () => slackService.getStatus(),
  });

  const disconnectMutation = useMutation({
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

  const handleConnect = () => {
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
      disconnectMutation.mutate();
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

  return (
    <div className="max-w-3xl mx-auto space-y-10 px-4 md:px-0">
      <div>
        <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-2 underline decoration-blue-500/50 underline-offset-4 decoration-2">Settings</h1>
        <p className="text-slate-500 font-bold tracking-tight">Configure your integrations and automated workflows.</p>
      </div>

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

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="space-y-6">
          <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
            <div className="flex flex-col md:flex-row items-start justify-between mb-10 gap-6">
              <div className="flex gap-6">
                <div className="w-16 h-16 bg-slate-900 rounded-[20px] flex items-center justify-center text-white shadow-2xl shadow-slate-900/30 shrink-0">
                  <Slack className="w-9 h-9" />
                </div>
                <div>
                  <h2 className="text-2xl font-black text-slate-900">Slack Connection</h2>
                  <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">Verato sends automated nudges to stakeholders via direct message to ensure accountability.</p>
                  
                  {isLoadingSlack ? (
                    <div className="flex items-center gap-2 mt-4 text-slate-400 font-black text-[10px] uppercase tracking-[0.2em]">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Checking Status...
                    </div>
                  ) : slackStatus?.connected ? (
                    <div className="flex items-center gap-2 mt-4 text-emerald-700 font-black text-[10px] uppercase tracking-[0.2em] bg-emerald-100/50 border border-emerald-200 px-3 py-1.5 rounded-xl inline-flex">
                       <CheckCircle2 className="w-3.5 h-3.5" />
                       Status: Connected to {slackStatus.workspace_name || "Workspace"}
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
                <Button 
                  variant="secondary" 
                  onClick={() => setIsSlackImportOpen(true)}
                  disabled={!slackStatus?.connected}
                  className="rounded-2xl border-slate-200 px-6 font-bold h-11 hover:bg-slate-50 text-slate-700 transition-all shrink-0 flex items-center justify-center gap-2"
                >
                  <Slack className="w-4 h-4 text-[#4A154B]" />
                  <span>Link/Import People</span>
                </Button>

                {slackStatus?.connected ? (
                  <Button 
                    variant="secondary" 
                    onClick={handleDisconnect}
                    disabled={disconnectMutation.isPending}
                    className="rounded-2xl border-slate-200 px-6 font-bold h-11 hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 transition-all shrink-0"
                  >
                    {disconnectMutation.isPending ? "Disconnecting..." : "Disconnect"}
                  </Button>
                ) : (
                  <Button 
                    onClick={handleConnect}
                    className="rounded-2xl bg-slate-900 text-white px-6 font-bold h-11 hover:bg-slate-800 transition-all shrink-0 border-none"
                  >
                    Connect Slack
                  </Button>
                )}
              </div>
            </div>

          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} className="space-y-6">
          <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
            <div className="flex flex-col md:flex-row items-start justify-between gap-6">
              <div className="flex gap-6">
                <div className="w-16 h-16 bg-red-600 rounded-[20px] flex items-center justify-center text-white shadow-2xl shadow-red-600/30 shrink-0">
                  <Mail className="w-9 h-9" />
                </div>
                <div>
                  <h2 className="text-2xl font-black text-slate-900">Gmail Connection</h2>
                  <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">Connect Gmail to synchronize emails and automate your Chief of Staff workflow directly from your inbox.</p>
                  
                  {isLoadingGmail ? (
                    <div className="flex items-center gap-2 mt-4 text-slate-400 font-black text-[10px] uppercase tracking-[0.2em]">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Checking Status...
                    </div>
                  ) : gmailStatus?.connected ? (
                    <div className="flex items-center gap-2 mt-4 text-emerald-700 font-black text-[10px] uppercase tracking-[0.2em] bg-emerald-100/50 border border-emerald-200 px-3 py-1.5 rounded-xl inline-flex">
                       <CheckCircle2 className="w-3.5 h-3.5" />
                       Status: Connected as {gmailStatus.email}
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
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <Card className="p-8 bg-white border-2 border-slate-100 rounded-[32px] shadow-xl shadow-slate-200/40">
            <div className="flex gap-6 mb-8">
              <div className="w-16 h-16 bg-purple-50 rounded-[20px] flex items-center justify-center text-[#4A154B] shadow-2xl shadow-purple-500/10 shrink-0">
                <Bell className="w-9 h-9" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-slate-900">Reminders & Nudges</h2>
                <p className="text-slate-500 text-sm mt-1 font-bold leading-relaxed max-w-md">
                  Configure the automatic Slack notifications sent to commitment owners when deadlines are approaching.
                </p>
              </div>
            </div>

            {isLoadingNudge ? (
              <div className="flex items-center gap-2 text-slate-400 font-extrabold text-sm py-4">
                <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
                Loading nudge preferences...
              </div>
            ) : (
              <div className="space-y-6">
                {/* Nudge Activation Status Toggle */}
                <div className="flex flex-col md:flex-row md:items-center justify-between p-6 bg-slate-50/50 border border-slate-100 rounded-[24px] gap-4">
                  <div>
                    <span className={cn(
                      "text-[10px] uppercase font-black px-2.5 py-1 rounded-full tracking-wider mb-2 inline-block transition-colors",
                      nudgeSettings?.nudge_enabled 
                        ? "bg-emerald-100 text-emerald-800" 
                        : "bg-slate-200 text-slate-600"
                    )}>
                      {nudgeSettings?.nudge_enabled ? "Active" : "Disabled"}
                    </span>
                    <p className="text-base font-black text-slate-900">Nudge Notifications Status</p>
                    <p className="text-xs text-slate-500 font-bold mt-0.5">Toggle automated Reminders and Overdue Nudges on or off.</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-black text-slate-500">
                      {nudgeSettings?.nudge_enabled ? "Enabled" : "Disabled"}
                    </span>
                    <button
                      type="button"
                      disabled={updateNudgeMutation.isPending}
                      onClick={() => updateNudgeMutation.mutate({ nudge_enabled: !nudgeSettings?.nudge_enabled })}
                      className={cn(
                        "relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-purple-500/10 disabled:opacity-50",
                        nudgeSettings?.nudge_enabled ? "bg-purple-600" : "bg-slate-300"
                      )}
                    >
                      <span
                        className={cn(
                          "pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out",
                          nudgeSettings?.nudge_enabled ? "translate-x-5" : "translate-x-0"
                        )}
                      />
                    </button>
                  </div>
                </div>

                {/* First Reminder */}
                <div className="flex flex-col md:flex-row md:items-center justify-between p-6 bg-slate-50/50 border border-slate-100 rounded-[24px] gap-4">
                  <div>
                    <span className="text-[10px] bg-purple-100 text-purple-850 font-black px-2.5 py-1 rounded-full uppercase tracking-wider mb-2 inline-block">First Reminder</span>
                    <p className="text-base font-black text-slate-900">Automatic Days Before</p>
                    <p className="text-xs text-slate-500 font-bold mt-0.5">Select when the initial warning nudge should be delivered.</p>
                  </div>
                  <div className="relative min-w-[200px]">
                    <select 
                      value={nudgeSettings?.first_days_before ?? 2}
                      onChange={(e) => updateNudgeMutation.mutate({ first_days_before: parseInt(e.target.value) })}
                      disabled={updateNudgeMutation.isPending}
                      className="w-full bg-white border-2 border-slate-200 rounded-xl px-4 py-3 text-sm font-black text-slate-700 focus:outline-none focus:ring-4 focus:ring-purple-500/10 focus:border-purple-600 transition-all cursor-pointer disabled:opacity-50"
                    >
                      <option value={1}>1 Day Before</option>
                      <option value={2}>2 Days Before</option>
                      <option value={5}>5 Days Before</option>
                    </select>
                  </div>
                </div>

                {/* Second Reminder */}
                <div className="flex flex-col md:flex-row md:items-center justify-between p-6 bg-slate-50/50 border border-slate-100 rounded-[24px] gap-4">
                  <div>
                    <span className="text-[10px] bg-indigo-100 text-indigo-850 font-black px-2.5 py-1 rounded-full uppercase tracking-wider mb-2 inline-block">Final Alert</span>
                    <p className="text-base font-black text-slate-900">Automatic Hours Before</p>
                    <p className="text-xs text-slate-500 font-bold mt-0.5">Select when the high-priority final status-check triggers.</p>
                  </div>
                  <div className="relative min-w-[200px]">
                    <select 
                      value={nudgeSettings?.second_hours_before ?? 48}
                      onChange={(e) => updateNudgeMutation.mutate({ second_hours_before: parseInt(e.target.value) })}
                      disabled={updateNudgeMutation.isPending}
                      className="w-full bg-white border-2 border-slate-200 rounded-xl px-4 py-3 text-sm font-black text-slate-700 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-600 transition-all cursor-pointer disabled:opacity-50"
                    >
                      <option value={24}>24 Hours Before</option>
                      <option value={48}>48 Hours Before</option>
                      <option value={72}>72 Hours Before</option>
                    </select>
                  </div>
                </div>

                {/* Info Note Highlight */}
                <div className="flex gap-4 p-5 bg-amber-50/60 border border-amber-200/60 rounded-[24px] text-amber-900">
                  <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div className="space-y-0.5">
                    <p className="text-xs font-black uppercase tracking-wider text-amber-800">Post-Deadline Escalation</p>
                    <p className="text-xs font-bold text-amber-700 leading-relaxed">
                      Any overdue commitments will be automatically reminded <strong className="text-amber-900 font-black text-xs">daily</strong> post overdue until resolved.
                    </p>
                  </div>
                </div>

                {updateNudgeMutation.isPending && (
                  <p className="text-[10px] font-bold text-[#4A154B] flex items-center gap-1.5 animate-pulse justify-end">
                    <Loader2 className="w-3 h-3 animate-spin" /> Saving changes in patch mode...
                  </p>
                )}
              </div>
            )}
          </Card>
        </motion.div>

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
          </Card>
        </motion.div>
      </div>

      {/* Import Modal */}
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
    </div>
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
