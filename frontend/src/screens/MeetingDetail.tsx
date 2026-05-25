import React from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { 
  Calendar, 
  Users, 
  FileText, 
  Download, 
  ArrowLeft,
  Clock,
  ChevronRight,
  ExternalLink,
  Target,
  X,
  RefreshCw,
  AlertTriangle,
  HelpCircle,
  MessageSquare
} from "lucide-react";
import { meetingService, commitmentService, personService } from "@/src/lib/api/services";
import { format, parseISO } from "date-fns";
import { useUI } from "@/src/components/layout/AppShell";
import { Card } from "@/src/components/ui/Card";
import { Button } from "@/src/components/ui/Button";
import { Badge } from "@/src/components/ui/Badge";
import { Avatar } from "@/src/components/ui/Avatar";
import { cn } from "@/src/lib/utils";
import ReactMarkdown from "react-markdown";
import { AlertCircle, MoreHorizontal } from "lucide-react";
import { ClarificationModal } from "@/src/components/ClarificationModal";

export const MeetingDetail = () => {
  const { id } = useParams<{ id: string }>();
  const { lastUploadTime } = useUI();
  const queryClient = useQueryClient();
  const [isTranscriptModalOpen, setIsTranscriptModalOpen] = React.useState(false);
  const [isClarifyModalOpen, setIsClarifyModalOpen] = React.useState(false);
  const [transcriptContent, setTranscriptContent] = React.useState("");
  const [isFetchingTranscript, setIsFetchingTranscript] = React.useState(false);

  const { data: meeting, isLoading: isLoadingMeeting } = useQuery({
    queryKey: ['meeting', id],
    queryFn: () => meetingService.getById(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const processingStatus = query.state.data?.processing_status;
      const hasProcessing = status === "processing" || status === "pending" || processingStatus === "processing" || processingStatus === "pending";
      const isRecentlyUploaded = Date.now() - lastUploadTime < 60000;
      return (hasProcessing || isRecentlyUploaded) ? 5000 : 30000;
    }
  });

  const reprocessMutation = useMutation({
    mutationFn: () => meetingService.reprocess(id!),
    onSuccess: () => {
      // Optimistically update status to trigger fast polling
      queryClient.setQueryData(['meeting', id], (old: any) => {
        if (!old) return old;
        return { ...old, status: 'processing', processing_status: 'processing' };
      });
      queryClient.invalidateQueries({ queryKey: ['meeting', id] });
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      alert("Extraction restarted successfully.");
    },
    onError: (error) => {
      console.error("Reprocess error:", error);
      alert("Failed to restart extraction. Please try again.");
    }
  });

  const { data: commitments, isLoading: isLoadingCommitments } = useQuery({
    queryKey: ['meeting-commitments', id],
    queryFn: () => commitmentService.getAll({ meeting: id! }),
    enabled: !!id
  });

  const { data: participants, isLoading: isLoadingParticipants } = useQuery({
    queryKey: ['meeting-participants', id],
    queryFn: () => meetingService.getParticipants(id!),
    enabled: !!id
  });

  const { data: people } = useQuery({
    queryKey: ['people'],
    queryFn: () => personService.getAll(),
  });

  const extractCommitments = (data: any) => {
    let items = [];
    if (!data) items = [];
    else if (Array.isArray(data)) items = data;
    else if (data.results && Array.isArray(data.results)) items = data.results;
    else if (data.data && Array.isArray(data.data)) items = data.data;
    else if (data.items && Array.isArray(data.items)) items = data.items;
    else if (data.commitments && Array.isArray(data.commitments)) items = data.commitments;
    
    return items.map((c: any) => ({
      ...c,
      title: String(c.title || c.text || "Untitled Commitment"),
      ownerName: String(c.owner_name || c.owner || c.assigned_to || "Unassigned"),
      deadline: String(c.deadline || c.due_date || c.target_date || ""),
      sourceMeeting: String(c.sourceMeeting || c.source_meeting || c.meeting_title || "Unknown Meeting"),
      status: String(c.status || "on_track").toLowerCase(),
      priority: (() => {
        const p = String(c.priority || "").toUpperCase();
        if (p === "P1" || p === "HIGH") return "High";
        if (p === "P2" || p === "MED" || p === "MEDIUM") return "Med";
        if (p === "P3" || p === "LOW") return "Low";
        return "Med";
      })(),
      riskScore: typeof c.riskScore === 'number' ? c.riskScore : (typeof c.risk_score === 'number' ? c.risk_score : 0),
      is_escalated: !!(c.is_escalated),
      is_overdue: !!(c.is_overdue),
      tags: (Array.isArray(c.tags) ? c.tags : (Array.isArray(c.tags_list) ? c.tags_list : [])).map((t: any) => {
        if (typeof t === 'string') return t;
        if (typeof t === 'object' && t !== null) return String(t.name || t.label || t.tag || t.text || t);
        return String(t);
      }),
      normalisedText: String(c.normalised_text || c.normalisedText || c.title || ""),
    }));
  };

  const processedCommitments = extractCommitments(commitments);

  const isOverdue = (c: any) => {
    if (c.is_overdue) return true;
    if (c.status === "overdue") return true;
    if (c.status === "done") return false;
    try {
      return new Date(c.deadline) < new Date();
    } catch (e) {
      return false;
    }
  };

  const isAtRisk = (c: any) => {
    const status = String(c.status || "").toLowerCase();
    return (status === "at_risk" || c.is_escalated) && !isOverdue(c) && !isToReview(c);
  };

  const isToReview = (c: any) => {
    const status = String(c.status || "").toLowerCase();
    return (status === "review" || status.includes("review") || status === "pending" || status === "pending_review") && !isOverdue(c);
  };

  const findOwnerSlackStatus = (commitment: any) => {
    if (!commitment.ownerName || commitment.ownerName.toLowerCase() === 'unassigned') {
      return true;
    }

    const ownerId = commitment.owner;
    const ownerName = commitment.ownerName;

    const rawPeople = people;
    const normalizedPeople = Array.isArray(rawPeople) 
      ? rawPeople 
      : (rawPeople as any)?.results && Array.isArray((rawPeople as any).results)
        ? (rawPeople as any).results
        : (rawPeople as any)?.data && Array.isArray((rawPeople as any).data)
          ? (rawPeople as any).data
          : [];

    const normalizedParticipants = Array.isArray(participants) ? participants : [];

    // Compare the owner field to id in persons response
    const foundPerson = normalizedPeople.find((p: any) => {
      if (!p) return false;
      const pId = String(p.id || p.owner || "").toLowerCase();
      const searchId = String(ownerId || "").toLowerCase();
      return searchId && pId === searchId;
    });

    let targetPerson = foundPerson;
    if (!targetPerson) {
      // Fallback by name
      targetPerson = normalizedPeople.find((p: any) => {
        if (!p) return false;
        const pName = String(p.name || "").toLowerCase();
        const searchName = String(ownerName || "").toLowerCase();
        return searchName && pName === searchName;
      });
    }

    if (targetPerson) {
      // Look for slack_user_id. If it's null (or falsy) then return false to display the note
      const slackUserId = targetPerson.slack_user_id !== undefined ? targetPerson.slack_user_id : targetPerson.slack_id;
      return !!(slackUserId && String(slackUserId).trim() !== "" && String(slackUserId) !== "null" && String(slackUserId) !== "undefined");
    }

    // 2. Fallback search in participants of this meeting
    const foundParticipant = normalizedParticipants.find((part: any) => {
      const p = part.person;
      if (!p) return false;
      const pId = String(p.id || p.owner || "").toLowerCase();
      const pName = String(p.name || "").toLowerCase();

      const searchId = String(ownerId || "").toLowerCase();
      const searchName = String(ownerName || "").toLowerCase();

      return (searchId && pId === searchId) || (searchName && pName === searchName);
    });

    if (foundParticipant && foundParticipant.person) {
      const sp = foundParticipant.person;
      const slackUserId = sp.slack_user_id !== undefined ? sp.slack_user_id : sp.slack_id;
      return !!(slackUserId && String(slackUserId).trim() !== "" && String(slackUserId) !== "null" && String(slackUserId) !== "undefined");
    }

    return false;
  };

  const formatDateSafely = (dateStr: string, formatStr: string) => {
    try {
      if (!dateStr) return "N/A";
      const date = parseISO(dateStr);
      if (isNaN(date.getTime())) return "Invalid Date";
      return format(date, formatStr);
    } catch (e) {
      return "Error";
    }
  };

  const handleViewTranscript = async () => {
    if (!id) return;
    try {
      setIsFetchingTranscript(true);
      const data = await meetingService.getTranscript(id);
      setTranscriptContent(data.transcript);
      setIsTranscriptModalOpen(true);
    } catch (error) {
      console.error("Failed to fetch transcript:", error);
    } finally {
      setIsFetchingTranscript(false);
    }
  };

  if (isLoadingMeeting || !meeting) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const formattedDate = (() => {
    try {
      const d = parseISO(meeting.date);
      return isNaN(d.getTime()) ? meeting.date : format(d, "MMMM d, yyyy");
    } catch (e) {
      return meeting.date;
    }
  })();

  return (
    <div className="max-w-6xl mx-auto space-y-10">
      {/* Breadcrumbs / Back navigation */}
      <div className="flex items-center gap-2 text-sm font-bold text-slate-400">
        <Link to="/meetings" className="hover:text-blue-600 transition-colors flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Meetings
        </Link>
        <ChevronRight className="w-3 h-3" />
        <span className="text-slate-900">Meeting Details</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-8">
          <div className="space-y-4">
            <h1 className="text-4xl font-black tracking-tighter text-slate-900 leading-tight">
              {meeting.title}
            </h1>
            <div className="flex items-center gap-2 text-blue-700 bg-blue-50 px-4 py-2 rounded-full w-fit">
              <Users className="w-5 h-5" />
              <span className="font-bold">Managed by {meeting.created_by_name || "Unknown"}</span>
            </div>
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-2 text-slate-500 font-bold">
                <Calendar className="w-5 h-5 text-blue-500" />
                {formattedDate}
              </div>
              <div className="flex items-center gap-2 text-slate-500 font-bold">
                <Clock className="w-5 h-5 text-blue-500" />
                {meeting.type || "Internal Sync"}
              </div>
              <Badge variant={meeting.status === 'processed' ? 'success' : 'neutral'}>
                {meeting.status}
              </Badge>
              {(meeting.status === "pending_clarification" || meeting.processing_status === "pending_clarification") && (
                <Badge variant="warning" className="animate-pulse gap-1.5 uppercase font-black bg-amber-100 text-amber-700 border-amber-200">
                  <HelpCircle className="w-3.5 h-3.5" />
                  Awaiting Clarification
                </Badge>
              )}
              {meeting.processing_status === "failed" && (
                <Badge variant="error" className="animate-pulse gap-1.5 uppercase font-black">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Failed Extraction
                </Badge>
              )}
            </div>
          </div>

          {/* Meeting Summary */}
          {meeting.summary && (
            <div className="space-y-4">
              <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                Meeting Summary
              </h2>
              <Card className="p-8 bg-slate-50 border-none rounded-[32px] overflow-hidden relative">
                <div className="absolute top-0 right-0 p-4 opacity-5">
                  <MessageSquare className="w-24 h-24" />
                </div>
                <div className="prose prose-slate max-w-none relative z-10">
                  <div className="text-slate-700 font-medium leading-relaxed">
                    <ReactMarkdown>{meeting.summary}</ReactMarkdown>
                  </div>
                </div>
              </Card>
            </div>
          )}

          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
                <Target className="w-5 h-5 text-blue-600" />
                Extracted Commitments
              </h2>
              <span className="text-xs font-black bg-slate-100 px-3 py-1 rounded-full text-slate-500 uppercase tracking-widest">
                {commitments?.length || 0} items
              </span>
            </div>

            {isLoadingCommitments ? (
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-24 bg-slate-50 animate-pulse rounded-3xl" />
                ))}
              </div>
            ) : (meeting.status === "pending_clarification" || meeting.processing_status === "pending_clarification") ? (
              <Card className="p-12 border-dashed border-2 flex flex-col items-center justify-center text-center space-y-6 bg-amber-50/30 border-amber-200 rounded-[40px]">
                <div className="w-20 h-20 bg-amber-100/50 rounded-full flex items-center justify-center text-amber-600 shadow-inner">
                  <HelpCircle className="w-10 h-10" />
                </div>
                <div className="space-y-2 max-w-sm">
                  <h3 className="font-black text-amber-900 text-xl tracking-tight">Commitments Hidden</h3>
                  <p className="text-amber-800/60 text-sm font-bold leading-relaxed">
                    AI extraction is paused. Please answer the clarification questions in the sidebar to finalize the list of commitments.
                  </p>
                </div>
                <Button 
                  onClick={() => setIsClarifyModalOpen(true)}
                  className="rounded-2xl font-black bg-amber-600 hover:bg-amber-700 text-white px-8 h-12 shadow-lg shadow-amber-500/20 border-none"
                >
                  Start Clarification
                </Button>
              </Card>
            ) : processedCommitments && processedCommitments.length > 0 ? (
              <div className="space-y-3">
                {processedCommitments.map((commitment) => {
                  const overdue = isOverdue(commitment);
                  const atRisk = isAtRisk(commitment);
                  const toReview = isToReview(commitment);
                  
                  return (
                    <Link key={commitment.id} to={`/commitments/${commitment.id}`}>
                      <Card className="p-0 border-slate-200 bg-white hover:border-blue-500/30 group shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all">
                        <div className="flex items-center gap-4 p-4">
                          {/* Indicators */}
                          <div className="flex items-center gap-2">
                            <div className="flex flex-col gap-1 w-1 h-8">
                              <div className={cn("flex-1 rounded-full", commitment.priority === "High" ? "bg-rose-500" : commitment.priority === "Med" ? "bg-amber-500" : "bg-slate-200")} />
                              <div className={cn("flex-1 rounded-full", (commitment.priority === "High" || commitment.priority === "Med") ? (commitment.priority === "High" ? "bg-rose-500/40" : "bg-amber-500/40") : "bg-slate-100")} />
                            </div>
                            <div className="flex flex-col items-center gap-1">
                              <div className={cn(
                                "w-2.5 h-2.5 rounded-full ring-2 ring-white shadow-sm",
                                commitment.riskScore > 0.7 ? "bg-rose-500" : 
                                commitment.riskScore > 0.3 ? "bg-amber-500" : 
                                "bg-emerald-500"
                              )} />
                              <span className={cn(
                                "text-[8px] font-black font-mono",
                                commitment.riskScore > 0.7 ? "text-rose-600" : 
                                commitment.riskScore > 0.3 ? "text-amber-600" : 
                                "text-emerald-600"
                              )}>
                                {(commitment.riskScore * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>

                          <div className="flex-1 min-w-0 flex flex-col gap-1.5">
                            {/* Line 1: Summary and Owner */}
                            <div className="flex items-center justify-between gap-4">
                              <h3 className="text-sm font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors">
                                {commitment.normalisedText || commitment.title}
                              </h3>
                              <div className="flex flex-col items-end shrink-0 gap-1 text-right">
                                <span className="text-[10px] font-black text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                                  {commitment.ownerName}
                                </span>
                                {!findOwnerSlackStatus(commitment) && commitment.ownerName !== "Unassigned" && (
                                  <span id={`slack-not-linked-warn-${commitment.id}`} className="text-[9px] font-bold text-rose-500 max-w-[140px] sm:max-w-[185px] leading-tight break-words">
                                    Owner&apos;s slack is not linked, nudges has to be done manually.
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Line 2: Date, Priority, Status, Tags */}
                            <div className="flex items-center gap-4">
                              <div className="flex items-center gap-3">
                                <div className="flex items-center gap-1 font-mono text-[10px] font-bold text-slate-400">
                                  <Clock className="w-3 h-3" />
                                  {formatDateSafely(commitment.deadline, "MMM d")}
                                </div>

                                <Badge variant={commitment.priority === "High" ? "error" : commitment.priority === "Med" ? "warning" : "neutral"} className="h-4 px-1.5 text-[9px] justify-center">
                                  {commitment.priority}
                                </Badge>

                                <Badge variant={
                                  overdue ? "error" : 
                                  atRisk ? "warning" : 
                                  toReview ? "brand" :
                                  commitment.status === "done" ? "success" :
                                  "success"
                                } className="h-4 px-1.5 text-[9px] justify-center uppercase">
                                  {overdue ? "OVERDUE" : (commitment.is_escalated ? "ESCALATED" : (toReview ? "REVIEW" : (commitment.status === 'done' ? 'DONE' : commitment.status.replace("_", " "))))}
                                </Badge>
                              </div>
                              
                              <div className="flex items-center gap-1.5 ml-auto">
                                {commitment.nudgeCount && commitment.nudgeCount > 0 && (
                                  <span className="flex items-center gap-1 text-[9px] text-amber-600 font-black uppercase mr-2">
                                    <AlertCircle className="w-2.5 h-2.5" />
                                    {commitment.nudgeCount} Nudges
                                  </span>
                                )}
                                
                                {commitment.tags && commitment.tags.slice(0, 3).map((tag: string) => (
                                  <span 
                                    key={tag} 
                                    className="text-[8px] font-bold text-slate-400 bg-slate-50 px-1 py-0.5 border border-slate-100 rounded"
                                  >
                                    #{tag}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>

                          <button className="p-1 text-slate-300 hover:text-slate-900 hover:bg-slate-50 rounded transition-all ml-2">
                            <MoreHorizontal className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </Card>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <Card className="p-10 border-dashed border-2 flex flex-col items-center justify-center text-center space-y-4 bg-slate-50/50">
                <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center text-slate-400">
                  <Target className="w-6 h-6" />
                </div>
                <div>
                  <p className="font-bold text-slate-900">No commitments found</p>
                  <p className="text-sm text-slate-500 font-medium">No actionable items were extracted from this transcript.</p>
                </div>
              </Card>
            )}
          </div>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-8">
          {/* Clarification Alert */}
          {(meeting.status === "pending_clarification" || meeting.processing_status === "pending_clarification") && (
            <Card className="p-6 bg-amber-50 border-amber-200 space-y-4 rounded-[28px] shadow-xl shadow-amber-500/10">
              <div className="flex gap-4">
                <div className="p-3 bg-amber-100 rounded-2xl text-amber-600 shrink-0 h-fit">
                  <HelpCircle className="w-6 h-6 animate-pulse" />
                </div>
                <div className="space-y-1">
                  <h3 className="font-black text-amber-900 leading-tight">Clarification Needed</h3>
                  <p className="text-amber-700/70 text-xs font-bold leading-relaxed">
                    AI needs more information to accurately resolve speakers or deadlines for this meeting.
                  </p>
                </div>
              </div>
              <Button 
                onClick={() => setIsClarifyModalOpen(true)}
                className="w-full h-12 rounded-xl bg-amber-600 hover:bg-amber-700 font-black gap-2 border-none text-white shadow-lg shadow-amber-500/20"
              >
                <MessageSquare className="w-4 h-4" />
                Clarify Details ({meeting.clarification_count || 0})
              </Button>
            </Card>
          )}

          {/* Reprocess Alert */}
          {(meeting.status === "failed" || meeting.status === "error" || meeting.processing_status === "failed") && (
            <Card className="p-6 bg-rose-50 border-rose-200 space-y-4 rounded-[28px]">
              <div className="flex gap-4">
                <div className="p-3 bg-rose-100 rounded-2xl text-rose-600 shrink-0 h-fit">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="font-black text-rose-900 leading-tight">Extraction Failed</h3>
                  <p className="text-rose-700/70 text-xs font-bold leading-relaxed">
                    Something went wrong while AI was parsing this meeting. You can try running the extraction process again.
                  </p>
                </div>
              </div>
              <Button 
                onClick={() => reprocessMutation.mutate()}
                disabled={reprocessMutation.isPending}
                className="w-full h-12 rounded-xl bg-rose-600 hover:bg-rose-700 font-black gap-2 border-none"
              >
                <RefreshCw className={cn("w-4 h-4", reprocessMutation.isPending && "animate-spin")} />
                {reprocessMutation.isPending ? "Restarting..." : "Rerun Extraction"}
              </Button>
            </Card>
          )}

          {/* Transcript Access */}
          <Card className="p-8 bg-slate-900 text-white space-y-6 shadow-2xl shadow-blue-500/10 border-none rounded-[32px]">
            <div className="space-y-2">
              <h3 className="text-lg font-black flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-400" />
                Meeting Transcript
              </h3>
              <p className="text-slate-400 text-sm font-bold leading-relaxed">
                Review the full raw transcript processed for this meeting.
              </p>
            </div>
            <div className="space-y-3">
              <Button 
                onClick={handleViewTranscript}
                disabled={isFetchingTranscript}
                className="w-full h-14 rounded-2xl bg-blue-600 hover:bg-blue-700 font-black gap-2 border-none"
              >
                {isFetchingTranscript ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <ExternalLink className="w-4 h-4" />
                )}
                View Transcript
              </Button>
              <Button 
                variant="secondary" 
                onClick={() => meeting.transcript_url && window.open(meeting.transcript_url, '_blank')}
                disabled={!meeting.transcript_url}
                className="w-full h-14 rounded-2xl border-slate-700 hover:bg-slate-800 text-slate-300 font-bold gap-2"
              >
                <Download className="w-4 h-4" />
                Download PDF
              </Button>
            </div>
          </Card>

          {/* Transcript Modal */}
          {isTranscriptModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white rounded-[32px] w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden"
              >
                <div className="p-8 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
                  <div className="space-y-1">
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
                      <FileText className="w-6 h-6 text-blue-600" />
                      Meeting Transcript
                    </h2>
                    <p className="text-slate-500 font-bold text-sm tracking-wide uppercase">
                      {meeting.title}
                    </p>
                  </div>
                  <button 
                    onClick={() => setIsTranscriptModalOpen(false)}
                    className="p-3 hover:bg-slate-50 rounded-2xl text-slate-400 hover:text-slate-900 transition-all border border-slate-100 shadow-sm"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-12 custom-scrollbar bg-slate-50/30">
                  <div className="max-w-2xl mx-auto">
                    <pre className="whitespace-pre-wrap font-sans text-slate-700 leading-relaxed text-base">
                      {transcriptContent || "No transcript available."}
                    </pre>
                  </div>
                </div>

                <div className="p-6 border-t border-slate-100 flex justify-end bg-white">
                  <Button 
                    onClick={() => setIsTranscriptModalOpen(false)}
                    className="h-12 px-8 rounded-xl font-black"
                  >
                    Close
                  </Button>
                </div>
              </motion.div>
            </div>
          )}

          {/* Participants */}
          <div className="space-y-4">
            <h3 className="text-sm font-black text-slate-400 uppercase tracking-[0.2em] ml-2">
              Participants
            </h3>
            <Card className="p-6 bg-white border-slate-100 space-y-4 rounded-[28px]">
              {isLoadingParticipants ? (
                <div className="space-y-4">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="h-10 bg-slate-50 animate-pulse rounded-xl" />
                  ))}
                </div>
              ) : participants && participants.length > 0 ? (
                <div className="space-y-4">
                  {participants.map(p => (
                    <div key={p.speaker_label} className="flex items-center gap-3">
                      <Avatar name={p.person?.name || p.speaker_label} size="sm" />
                      <div className="flex flex-col">
                        <span className="text-sm font-black text-slate-900">{p.person?.name || p.speaker_label}</span>
                        {p.person?.role && <span className="text-[10px] text-slate-400 font-bold uppercase">{p.person.role}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-3 text-slate-400 italic text-sm font-medium p-4">
                  <Users className="w-4 h-4" />
                  No participants identified
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
      {isClarifyModalOpen && (
        <ClarificationModal 
          meetingId={id!} 
          onClose={() => setIsClarifyModalOpen(false)} 
        />
      )}
    </div>
  );
};
