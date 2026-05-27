import { motion } from "motion/react";
import { Bell, Loader2, AlertCircle } from "lucide-react";
import { Card } from "@/src/components/ui/Card";
import { cn } from "@/src/lib/utils";
import { nudgeSettingsService } from "@/src/lib/api/services";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export const NotificationsSettings = () => {
  const queryClient = useQueryClient();
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

  return (
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

            <div className="flex gap-4 p-5 bg-amber-50/60 border border-amber-200/60 rounded-[24px] text-amber-900">
              <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="text-xs font-black uppercase tracking-wider text-amber-800">Post-Deadline Escalation</p>
                <p className="text-xs font-bold text-amber-700 leading-relaxed">
                  Any overdue commitments will be automatically reminded <strong className="text-amber-900 font-black text-xs">daily</strong> post overdue until resolved.
                </p>
              </div>
            </div>
          </div>
        )}
      </Card>
    </motion.div>
  );
};
