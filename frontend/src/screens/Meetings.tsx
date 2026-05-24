import React, { useState } from "react";
import { motion } from "motion/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { meetingService } from "@/src/lib/api/services";
import { format, parseISO } from "date-fns";
import { useUI } from "@/src/components/layout/AppShell";
import { 
  FileText, 
  Calendar as CalendarIcon, 
  Clock, 
  ChevronRight,
  MoreVertical,
  Plus,
  BarChart2,
  CheckCircle2,
  UploadCloud,
  RefreshCw,
  AlertTriangle,
  HelpCircle,
  MessageSquare
} from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "@/src/components/ui/Card";
import { Badge } from "@/src/components/ui/Badge";
import { Button } from "@/src/components/ui/Button";
import { cn } from "@/src/lib/utils";
import { ClarificationModal } from "@/src/components/ClarificationModal";

import { Meeting } from "@/src/types";

export const Meetings = () => {
  const { openUploadModal, lastUploadTime } = useUI();
  const queryClient = useQueryClient();
  const [clarifyMeetingId, setClarifyMeetingId] = useState<string | null>(null);

  const { data: meetings, isLoading } = useQuery<Meeting[]>({
    queryKey: ['meetings'],
    queryFn: meetingService.getAll,
    refetchInterval: (query) => {
      // Poll faster if any meeting is in a transient state or if we just uploaded a meeting
      const hasProcessing = query.state.data?.some(m => 
        m.status === "processing" || m.status === "pending" ||
        m.processing_status === "processing" || m.processing_status === "pending"
      );
      
      const isRecentlyUploaded = Date.now() - lastUploadTime < 60000; // 60 seconds

      return (hasProcessing || isRecentlyUploaded) ? 5000 : 30000;
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: (id: string) => meetingService.reprocess(id),
    onSuccess: (_, variables) => {
      // Optimistically update status to trigger fast polling
      queryClient.setQueryData(['meetings'], (old: Meeting[] | undefined) => {
        return old?.map(m => m.id === variables ? { ...m, status: 'processing' as const, processing_status: 'processing' as const } : m);
      });
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      alert("Extraction restarted successfully.");
    },
    onError: (error) => {
      console.error("Reprocess error:", error);
      alert("Failed to restart extraction. Please try again.");
    }
  });

  const handleReprocess = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    reprocessMutation.mutate(id);
  };

  const displayMeetings = Array.isArray(meetings) 
    ? [...meetings].sort((a, b) => {
        try {
          const dateA = new Date(a.occurred_at || a.date).getTime();
          const dateB = new Date(b.occurred_at || b.date).getTime();
          return dateB - dateA;
        } catch (e) {
          return 0;
        }
      })
    : [];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-slate-900 mb-2">Meeting History</h1>
          <p className="text-slate-500 font-medium tracking-tight">Browse transcripts and extracted commitment batches.</p>
        </div>
        <div className="flex gap-3">
          <Button onClick={openUploadModal} className="gap-2 shadow-xl shadow-blue-500/20 h-12 px-6 rounded-2xl bg-blue-600 hover:bg-blue-700 font-bold transition-all">
            <UploadCloud className="w-5 h-5" />
            Upload Transcript
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {isLoading && displayMeetings.length === 0 && (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}
        
        {displayMeetings.length === 0 && !isLoading && (
          <div className="py-20 text-center space-y-4">
            <div className="w-20 h-20 bg-slate-50 rounded-[32px] flex items-center justify-center mx-auto text-slate-300">
              <FileText className="w-10 h-10" />
            </div>
            <div className="space-y-1">
              <h3 className="font-black text-slate-900 text-lg">No meetings yet</h3>
              <p className="text-slate-500 text-sm font-bold max-w-xs mx-auto">Upload your first meeting transcript to start extracting commitments with AI.</p>
            </div>
            <Button onClick={openUploadModal} variant="secondary" className="rounded-xl font-black border-slate-200">
              Upload Now
            </Button>
          </div>
        )}

        {displayMeetings.map((meeting, idx) => (
          <motion.div
            key={meeting.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
          >
            <Link to={`/meetings/${meeting.id}`}>
              <Card className={cn(
                "p-0 border-slate-200 hover:border-blue-500/30 transition-all group overflow-hidden bg-white shadow-sm cursor-pointer",
                (meeting.status === "pending_clarification" || meeting.processing_status === "pending_clarification") && "border-amber-200 bg-amber-50/10"
              )}>
                 <div className="flex items-center gap-6 p-5">
                    <div className={cn(
                      "p-3 rounded-xl flex items-center justify-center",
                      (meeting.status === "processing" || meeting.status === "pending" || meeting.processing_status === "processing" || meeting.processing_status === "pending") ? "bg-blue-50 text-blue-600" : 
                      (meeting.status === "pending_clarification" || meeting.processing_status === "pending_clarification") ? "bg-amber-50 text-amber-600" :
                      "bg-slate-50 border border-slate-200 text-slate-400"
                    )}>
                      {(meeting.status === "processing" || meeting.status === "pending" || meeting.processing_status === "processing" || meeting.processing_status === "pending") ? (
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        >
                          <Clock className="w-6 h-6" />
                        </motion.div>
                      ) : (meeting.status === "pending_clarification" || meeting.processing_status === "pending_clarification") ? (
                        <HelpCircle className="w-6 h-6" />
                      ) : (
                        <FileText className="w-6 h-6" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors truncate">
                          {meeting.title}
                        </h3>
                        <Badge variant="neutral">{meeting.type}</Badge>
                        {meeting.external_url?.includes("meet.google.com") && (
                          <Badge variant="success" className="gap-1.5 flex items-center">
                            <CalendarIcon className="w-3 h-3" />
                            Google Meet
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-xs font-bold text-slate-400">
                        <span className="flex items-center gap-1.5 capitalize">
                          <CalendarIcon className="w-3.5 h-3.5" />
                          {(() => {
                            try {
                              const d = parseISO(meeting.occurred_at || meeting.date);
                              return isNaN(d.getTime()) ? (meeting.occurred_at || meeting.date) : format(d, "MMM d, yyyy");
                            } catch (e) {
                              return meeting.occurred_at || meeting.date;
                            }
                          })()}
                        </span>
                        
                        <span className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Total commitments - {meeting.commitments_count || meeting.commitments || 0}
                        </span>

                        {(meeting.pending_count || 0) > 0 && (
                          <span className="flex items-center gap-1.5 text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-100">
                            Pending review : {meeting.pending_count}
                          </span>
                        )}

                        {(meeting.status === "processing" || meeting.status === "pending" || meeting.processing_status === "processing" || meeting.processing_status === "pending") && (
                          <span className="text-blue-600 flex items-center gap-1.5 animate-pulse uppercase tracking-wider text-[10px]">
                            {meeting.status_message || "Extraction in progress..."}
                          </span>
                        )}

                        {(meeting.status === "pending_clarification" || meeting.processing_status === "pending_clarification") && (
                          <span className="text-amber-600 flex items-center gap-1.5 font-black uppercase tracking-wider text-[10px]">
                            <AlertTriangle className="w-3 h-3 animate-pulse" />
                            Awaiting Clarification ({meeting.clarification_count || 0})
                          </span>
                        )}

                        {(meeting.status === "error" || meeting.status === "failed" || meeting.processing_status === "failed") && (
                          <span className="text-rose-600 flex items-center gap-1.5 uppercase tracking-wider text-[10px] font-black italic">
                            <AlertTriangle className="w-3 h-3" />
                            {meeting.error || "Extraction Failed"}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                       {(meeting.status === "pending_clarification" || meeting.processing_status === "pending_clarification") && (
                         <Button 
                           size="sm" 
                           onClick={(e) => {
                             e.preventDefault();
                             e.stopPropagation();
                             setClarifyMeetingId(meeting.id);
                           }}
                           className="h-8 rounded-lg bg-amber-600 hover:bg-amber-700 text-[10px] font-black uppercase tracking-widest gap-1.5 border-none shadow-lg shadow-amber-500/20"
                         >
                           <MessageSquare className="w-3 h-3" />
                           Clarify
                         </Button>
                       )}
                       
                       {(meeting.status === "failed" || meeting.processing_status === "failed" || meeting.status === "error") && (
                         <Button 
                           size="sm" 
                           onClick={(e) => handleReprocess(e, meeting.id)}
                           disabled={reprocessMutation.isPending}
                           className="h-8 rounded-lg bg-slate-900 hover:bg-slate-800 text-[10px] font-black uppercase tracking-widest gap-1.5 border-none"
                         >
                           <RefreshCw className={cn("w-3 h-3", reprocessMutation.isPending && "animate-spin")} />
                           Rerun Extraction
                         </Button>
                       )}
                       <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
                    </div>
                 </div>
                 
                 {/* Progress bar for processing state */}
                 {(meeting.status === "processing" || meeting.status === "pending" || meeting.processing_status === "processing" || meeting.processing_status === "pending") && (
                   <div className="h-0.5 w-full bg-slate-50 relative">
                     <motion.div 
                       initial={{ x: "-100%" }}
                       animate={{ x: "100%" }}
                       transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                       className="absolute inset-0 w-1/3 bg-blue-600"
                     />
                   </div>
                 )}
              </Card>
            </Link>
          </motion.div>
        ))}
      </div>

      {clarifyMeetingId && (
        <ClarificationModal 
          meetingId={clarifyMeetingId} 
          onClose={() => setClarifyMeetingId(null)} 
        />
      )}
    </div>
  );
};
