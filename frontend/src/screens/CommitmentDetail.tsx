import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { commitmentService, personService, gmailService } from "@/src/lib/api/services";
import { 
  ArrowLeft, 
  Send, 
  CheckCircle2, 
  Calendar, 
  Trash2, 
  Clock, 
  Activity,
  User,
  ExternalLink,
  Plus,
  Edit2,
  Save,
  X,
  Check,
  AlertCircle,
  Loader2
} from "lucide-react";
import { Card } from "@/src/components/ui/Card";
import { Button } from "@/src/components/ui/Button";
import { Badge } from "@/src/components/ui/Badge";
import { Avatar } from "@/src/components/ui/Avatar";
import { MOCK_COMMITMENTS } from "@/src/lib/mockData";
import { format, parseISO } from "date-fns";
import { cn } from "@/src/lib/utils";

export const CommitmentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editedTitle, setEditedTitle] = useState("");
  const [isEditingOwner, setIsEditingOwner] = useState(false);
  const [showPersonPicker, setShowPersonPicker] = useState(false);
  const [editedOwnerId, setEditedOwnerId] = useState("");
  const [isEditingDeadline, setIsEditingDeadline] = useState(false);
  const [editedDeadline, setEditedDeadline] = useState("");
  const [editedTags, setEditedTags] = useState<string[]>([]);
  const [isAddingTag, setIsAddingTag] = useState(false);
  const [newTag, setNewTag] = useState("");
  const [showConfirmBack, setShowConfirmBack] = useState(false);
  const [showConfirmReject, setShowConfirmReject] = useState(false);
  const [showConfidenceInfo, setShowConfidenceInfo] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [nudgeMessage, setNudgeMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const { data: commitment, isLoading, error } = useQuery({
    queryKey: ['commitment', id],
    queryFn: () => commitmentService.getById(id!),
    enabled: !!id,
  });

  const { data: people } = useQuery({
    queryKey: ['people'],
    queryFn: () => personService.getAll(),
  });

  useEffect(() => {
    if (commitment) {
      setEditedTitle(commitment.normalised_text || commitment.normalisedText || commitment.title);
      setEditedOwnerId(commitment.owner || "");
      setEditedDeadline(commitment.deadline || "");
      setEditedTags(commitment.tags || []);
    }
  }, [commitment]);

  useEffect(() => {
    if (!commitment) return;
    
    const initialTitle = commitment.normalised_text || commitment.normalisedText || commitment.title;
    const initialOwnerId = commitment.owner || "";
    const initialDeadline = commitment.deadline || "";
    const initialTags = commitment.tags || [];

    const tagsChanged = JSON.stringify(editedTags) !== JSON.stringify(initialTags);

    if (editedTitle !== initialTitle || editedOwnerId !== initialOwnerId || editedDeadline !== initialDeadline || tagsChanged) {
      setHasChanges(true);
    } else {
      setHasChanges(false);
    }
  }, [editedTitle, editedOwnerId, editedDeadline, editedTags, commitment]);

  // Navigation guard
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasChanges]);

  const { data: history } = useQuery({
    queryKey: ['commitment-history', id],
    queryFn: () => commitmentService.getHistory(id!),
    enabled: !!id,
  });

  const updateMutation = useMutation({
    mutationFn: (updates: any) => commitmentService.update(id!, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commitment', id] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
      setHasChanges(false);
      setIsEditingTitle(false);
      setIsEditingOwner(false);
      setIsEditingDeadline(false);
    }
  });

  const confirmMutation = useMutation({
    mutationFn: () => commitmentService.confirm(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commitment', id] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
    }
  });

  const reopenMutation = useMutation({
    mutationFn: () => commitmentService.reopen(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commitment', id] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
    }
  });

  const escalateMutation = useMutation({
    mutationFn: () => commitmentService.escalate(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commitment', id] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
    }
  });

  const resolveMutation = useMutation({
    mutationFn: ({ outcome }: { outcome: string }) => commitmentService.resolve(id!, outcome),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commitment', id] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
    }
  });

  const rejectMutation = useMutation({
    mutationFn: () => commitmentService.reject(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commitment', id] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
      navigate('/dashboard');
    }
  });

  const { data: gmailStatus, isLoading: isLoadingGmail } = useQuery({
    queryKey: ['gmail-status'],
    queryFn: () => gmailService.getStatus(),
  });

  const nudgeMutation = useMutation({
    mutationFn: () => commitmentService.nudge(id!, 'email'),
    onSuccess: () => {
      setNudgeMessage({ type: 'success', text: 'Nudge sent successfully via Gmail!' });
      queryClient.invalidateQueries({ queryKey: ['commitment', id] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
      setTimeout(() => {
        setNudgeMessage(null);
      }, 5000);
    },
    onError: (err: any) => {
      const errMsg = err?.response?.data?.message || err?.message || 'Failed to send manual nudge.';
      setNudgeMessage({ type: 'error', text: errMsg });
      setTimeout(() => {
        setNudgeMessage(null);
      }, 5000);
    }
  });

  const handleNudgeNow = () => {
    const rawPeople = people;
    const peopleList = Array.isArray(rawPeople) 
      ? rawPeople 
      : (rawPeople as any)?.results && Array.isArray((rawPeople as any).results)
        ? (rawPeople as any).results
        : (rawPeople as any)?.data && Array.isArray((rawPeople as any).data)
          ? (rawPeople as any).data
          : [];

    const ownerId = (editedOwnerId || commitment?.owner || "").toString().trim().toLowerCase();
    const ownerName = (commitment?.owner_name || commitment?.owner || "").toString().trim().toLowerCase();
    
    // 1. Try to find by id or owner identifier
    let ownerPerson = peopleList.find((p: any) => {
      if (!p) return false;
      const pId = String(p.id || "").trim().toLowerCase();
      const pOwner = String(p.owner || "").trim().toLowerCase();
      return (ownerId && (pId === ownerId || pOwner === ownerId)) || 
             (ownerName && (pId === ownerName || pOwner === ownerName));
    });

    // 2. Try strict name fallback matching
    if (!ownerPerson) {
      ownerPerson = peopleList.find((p: any) => {
        if (!p) return false;
        const pName = String(p.name || "").trim().toLowerCase();
        return ownerName && pName === ownerName;
      });
    }

    // 3. Try partial name matching
    if (!ownerPerson) {
      ownerPerson = peopleList.find((p: any) => {
        if (!p) return false;
        const pName = String(p.name || "").trim().toLowerCase();
        return ownerName && (pName.includes(ownerName) || ownerName.includes(pName));
      });
    }

    const displayName = commitment?.owner_name || commitment?.owner || "Owner";

    if (!ownerPerson || !ownerPerson.email) {
      setNudgeMessage({ 
        type: 'error', 
        text: `Error: Owner email does not exist for ${displayName}. Please construct or edit the person profile to include a valid email.` 
      });
      setTimeout(() => {
        setNudgeMessage(null);
      }, 6000);
      return;
    }

    // Show a visual validation/indicator first
    setNudgeMessage({
      type: 'success',
      text: `Email verified: Connected to ${displayName} (${ownerPerson.email}). Initiating nudge...`
    });

    // Short timeout so the user actually sees the beautiful visual confirmation toast before request dispatch
    setTimeout(() => {
      nudgeMutation.mutate();
    }, 1500);
  };

  const handleReviewCompleted = async () => {
    // First update the metadata
    await updateMutation.mutateAsync({
      normalised_text: editedTitle,
      owner: editedOwnerId,
      deadline: editedDeadline,
      tags: editedTags
    });
    
    // Then confirm if it was in review/pending
    const status = String(displayCommitment.status || "").toLowerCase();
    if (status === 'review' || status.includes('review') || status === 'pending') {
      confirmMutation.mutate();
    }
  };

  const handleMarkDone = () => {
    resolveMutation.mutate({ outcome: 'done' });
  };

  const handleReopen = () => {
    reopenMutation.mutate();
  };

  const handleDefer = () => {
    resolveMutation.mutate({ outcome: 'deferred' });
  };

  const handleEscalate = () => {
    escalateMutation.mutate();
  };

  const handleReject = () => {
    setShowConfirmReject(true);
  };

  const confirmReject = () => {
    rejectMutation.mutate();
    setShowConfirmReject(false);
  };

  const handleAddTag = () => {
    const trimmed = newTag.trim().toLowerCase().replace(/^#/, "");
    if (trimmed && !editedTags.includes(trimmed)) {
      setEditedTags(prev => [...prev, trimmed]);
    }
    setNewTag("");
    setIsAddingTag(false);
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedTags(prev => prev.filter(t => t !== tagToRemove));
  };

  const getOwnerDisplayName = (ownerId: string) => {
    if (!ownerId) return "Unassigned";
    
    // Check if the current commitment owner matches this ID
    if (commitment && (commitment.owner === ownerId || commitment.owner_name === ownerId) && commitment.owner_name) {
      return commitment.owner_name;
    }
    
    // Look up in people list
    const person = (people as any[])?.find(p => p.owner === ownerId || p.id === ownerId || p.name === ownerId);
    return person?.name || ownerId;
  };

  const displayCommitment = commitment || MOCK_COMMITMENTS.find(c => c.id === id) || MOCK_COMMITMENTS[0];

  const isToReview = (c: any) => {
    if (!c) return false;
    const status = String(c.status || "").toLowerCase();
    return (status === "review" || status.includes("review") || status === "pending") && !c.is_overdue;
  };

  const inReview = isToReview(displayCommitment);
  const isDone = displayCommitment?.status === "done";
  const canEdit = !isDone;

  const effectiveStatus = displayCommitment?.is_overdue ? 'overdue' : (displayCommitment?.is_escalated ? 'escalated' : displayCommitment?.status);

  const riskScore = displayCommitment?.risk_score ?? displayCommitment?.riskScore ?? 0;
  const confidenceValue = displayCommitment?.confidence !== undefined ? displayCommitment.confidence * 10 : (1 - riskScore) * 10;
  const confidenceScore = confidenceValue.toFixed(1);
  const confidencePercent = confidenceValue * 10;
  const breakdown = displayCommitment?.risk_score_breakdown || displayCommitment?.riskScoreBreakdown || {
    deadline: 50,
    owner: 35,
    recency: 15
  };

  const handleBack = (e: React.MouseEvent) => {
    if (hasChanges) {
      setShowConfirmBack(true);
    } else {
      navigate("/dashboard");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!displayCommitment) {
    return (
      <div className="max-w-5xl mx-auto p-12 text-center">
        <h2 className="text-2xl font-black text-slate-900 mb-4">Commitment Not Found</h2>
        <Link to="/dashboard" className="text-blue-600 font-bold hover:underline">Return to Dashboard</Link>
      </div>
    );
  }

  return (
    <>
      <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-5xl mx-auto pb-20"
    >
      {/* Back Link */}
      <button 
        onClick={handleBack}
        className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 transition-colors text-[10px] uppercase font-black tracking-widest mb-8 group"
      >
        <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
        Overview
      </button>

      <div className="space-y-10">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge 
                variant={effectiveStatus === "overdue" ? "error" : (effectiveStatus === "at_risk" || effectiveStatus === "deferred" || effectiveStatus === "escalated") ? "warning" : effectiveStatus === "done" ? "brand" : "success"}
                className="px-4 py-1 text-xs font-black uppercase tracking-widest shadow-sm"
              >
                {(effectiveStatus || 'on_track') === 'done' ? 'DONE' : (effectiveStatus || 'on_track').replace("_", " ")}
              </Badge>
              <Badge variant={displayCommitment.priority === "High" ? "error" : displayCommitment.priority === "Med" ? "warning" : "neutral"} className="px-3 py-1 text-[10px] font-black uppercase tracking-[0.15em] border-slate-200">
                {displayCommitment.priority} Priority
              </Badge>
            </div>
            <div className="space-y-2">
              <div className="flex items-start gap-4 group/title">
                {isEditingTitle ? (
                  <div className="flex-1 space-y-3">
                    <input
                      type="text"
                      className="w-full text-3xl md:text-4xl font-black text-slate-900 tracking-tight leading-[1.1] border-b-2 border-blue-600 outline-none bg-transparent py-1"
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <Button size="sm" className="h-8 px-4 text-[10px] font-black" onClick={() => setIsEditingTitle(false)}>
                        <Check className="w-3 h-3 mr-1" /> OK
                      </Button>
                      <Button variant="secondary" size="sm" className="h-8 px-4 text-[10px] font-black" onClick={() => {
                        setEditedTitle(displayCommitment.normalised_text || displayCommitment.normalisedText || displayCommitment.title);
                        setIsEditingTitle(false);
                      }}>
                        CANCEL
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <h1 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tight leading-[1.1] max-w-3xl">
                      {editedTitle}
                    </h1>
                    {canEdit && (
                      <button 
                        onClick={() => setIsEditingTitle(true)}
                        className="mt-2 p-2 rounded-full hover:bg-blue-50 text-slate-300 hover:text-blue-600 transition-all opacity-0 group-hover/title:opacity-100"
                      >
                        <Edit2 className="w-5 h-5" />
                      </button>
                    )}
                  </>
                )}
              </div>
              <div className="flex flex-wrap gap-2 pt-1 min-h-[32px] items-center">
                {editedTags.map((tag, idx) => (
                  <Badge 
                    key={`tag-${tag}-${idx}`} 
                    variant="neutral" 
                    className="bg-white border-slate-200 text-slate-600 pl-3 pr-1.5 py-0.5 font-bold text-[10px] group/tag flex items-center gap-1.5"
                  >
                    #{tag}
                    {canEdit && (
                      <button 
                        onClick={() => handleRemoveTag(tag)}
                        className="p-0.5 rounded-full hover:bg-slate-100 text-slate-300 hover:text-rose-500 transition-colors"
                      >
                        <X className="w-2.5 h-2.5" />
                      </button>
                    )}
                  </Badge>
                ))}
                
                {canEdit && (
                  <>
                    {isAddingTag ? (
                      <div className="flex items-center gap-1 bg-white border border-blue-200 rounded-full pl-3 pr-1 py-0.5 text-[10px]">
                        <span className="text-blue-500 font-bold">#</span>
                        <input
                          type="text"
                          className="bg-transparent outline-none w-20 font-bold text-slate-700"
                          value={newTag}
                          onChange={(e) => setNewTag(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleAddTag();
                            if (e.key === 'Escape') setIsAddingTag(false);
                          }}
                          autoFocus
                          placeholder="tag..."
                        />
                        <button 
                          onClick={handleAddTag}
                          className="p-1 rounded-full hover:bg-blue-50 text-blue-600"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                      </div>
                    ) : (
                      <button 
                        onClick={() => setIsAddingTag(true)}
                        className="h-6 w-6 flex items-center justify-center rounded-full border border-dashed border-slate-300 text-slate-400 hover:text-blue-600 hover:border-blue-200 transition-all bg-slate-50/50"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex flex-col gap-2">
            {!inReview && canEdit && hasChanges && (
              <Button 
                className="h-14 px-8 text-base font-black shadow-xl shadow-emerald-500/10 gap-3 bg-emerald-600 hover:bg-emerald-700"
                onClick={() => updateMutation.mutate({
                  normalised_text: editedTitle,
                  owner: editedOwnerId,
                  deadline: editedDeadline,
                  tags: editedTags
                })}
                disabled={updateMutation.isPending}
              >
                <Save className="w-5 h-5" />
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            )}
            {inReview ? (
              <div className="flex flex-col gap-2">
                <Button 
                  className="h-14 px-8 text-base font-black shadow-xl shadow-blue-500/10 gap-3"
                  onClick={handleReviewCompleted}
                  disabled={updateMutation.isPending || confirmMutation.isPending}
                >
                  <CheckCircle2 className="w-5 h-5" />
                  {updateMutation.isPending || confirmMutation.isPending ? 'Processing...' : 'Review Completed'}
                </Button>
                <Button 
                  variant="secondary"
                  className="h-10 px-8 text-xs font-bold border-rose-200 text-rose-600 hover:bg-rose-50"
                  onClick={handleReject}
                  disabled={rejectMutation.isPending}
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Reject Extraction
                </Button>
              </div>
            ) : null}

            {nudgeMessage && (
              <div 
                className={cn(
                  "p-3.5 rounded-2xl text-xs font-bold leading-relaxed flex items-center gap-2 border shadow-sm transition-all animate-in fade-in slide-in-from-top-2 duration-250",
                  nudgeMessage.type === 'success' 
                    ? "bg-emerald-50 border-emerald-200 text-emerald-800" 
                    : "bg-rose-50 border-rose-200 text-rose-800"
                )}
              >
                {nudgeMessage.type === 'success' ? (
                  <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600 shrink-0" />
                ) : (
                  <AlertCircle className="w-4.5 h-4.5 text-rose-600 shrink-0" />
                )}
                {nudgeMessage.text}
              </div>
            )}

            {!inReview && (effectiveStatus !== 'done' && effectiveStatus !== 'deferred' && effectiveStatus !== 'cancelled') && (
              <div className="flex flex-col gap-2">
                <Button
                  onClick={handleNudgeNow}
                  disabled={!gmailStatus?.connected || nudgeMutation.isPending}
                  className={cn(
                    "w-full h-12 font-black gap-2 transition-all shadow-md rounded-2xl border border-transparent shrink-0",
                    gmailStatus?.connected 
                      ? "bg-slate-900 text-white hover:bg-slate-800 cursor-pointer" 
                      : "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed"
                  )}
                >
                  {nudgeMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Nudging Owner...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Nudge Now
                    </>
                  )}
                </Button>
                {!gmailStatus?.connected && (
                  <div className="text-[11px] font-bold text-slate-500/90 flex items-center justify-center gap-1.5 px-1 py-1 text-center bg-slate-50 border border-slate-150 rounded-xl">
                    <AlertCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    Connect OAuth Gmail in Settings to Nudge via Email
                  </div>
                )}
              </div>
            )}

            <div className="flex gap-2">
              {effectiveStatus === 'done' || effectiveStatus === 'deferred' || effectiveStatus === 'cancelled' ? (
                <Button 
                  variant="secondary" 
                  className="flex-1 font-bold text-xs h-10 border-slate-200"
                  onClick={handleReopen}
                  disabled={reopenMutation.isPending}
                >
                  {reopenMutation.isPending ? 'Opening...' : 'Reopen'}
                </Button>
              ) : !inReview && (
                <>
                  <Button 
                    variant="secondary" 
                    className="flex-1 font-bold text-xs h-10 border-slate-200"
                    onClick={handleMarkDone}
                    disabled={resolveMutation.isPending}
                  >
                    {resolveMutation.isPending ? 'Updating...' : 'Mark as Done'}
                  </Button>
                  <Button 
                    variant="secondary" 
                    className="flex-1 font-bold text-xs h-10 border-slate-200"
                    onClick={handleDefer}
                    disabled={resolveMutation.isPending}
                  >
                    Mark as Defer
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>

        {/* 4-Cell Meta Grid */}
        <div className={cn(
          "grid grid-cols-2 gap-px bg-slate-200 border border-slate-200 rounded-3xl shadow-sm",
          inReview ? "md:grid-cols-4" : "md:grid-cols-3"
        )}>
          {[
            { 
              label: "Owner", 
              value: (
                <div className="relative">
                  <button 
                    className={cn("text-left w-full truncate font-black", canEdit && "hover:text-blue-700 underline decoration-dotted underline-offset-4 cursor-pointer")}
                    onClick={() => canEdit && setShowPersonPicker(true)}
                  >
                    {getOwnerDisplayName(editedOwnerId)}
                  </button>
                </div>
              ), 
              sub: displayCommitment.ownerRole,
              icon: User,
              color: "text-blue-600",
              extra: displayCommitment?.needs_manual_nudge === true ? (
                <div id="slack-not-linked-warn-detail" className="text-[10px] sm:text-[11px] font-bold text-rose-500 mt-2 leading-tight">
                  Owner&apos;s slack is not linked, nudges has to be done manually.
                </div>
              ) : null
            },
            { 
              label: "Deadline", 
              value: (
                <div className="relative">
                  {canEdit && isEditingDeadline ? (
                    <input 
                      type="date"
                      className="w-full bg-slate-50 border border-slate-200 rounded p-1 text-sm outline-none font-bold"
                      value={editedDeadline}
                      onChange={(e) => {
                        setEditedDeadline(e.target.value);
                        setIsEditingDeadline(false);
                      }}
                      onBlur={() => setIsEditingDeadline(false)}
                      autoFocus
                    />
                  ) : (
                    <button 
                      className={cn("text-left w-full font-black", canEdit && "hover:text-blue-700 underline decoration-dotted underline-offset-4 cursor-pointer", effectiveStatus === "overdue" ? "text-rose-600" : "text-slate-600")}
                      onClick={() => canEdit && setIsEditingDeadline(true)}
                    >
                      {editedDeadline && editedDeadline !== "undefined" ? (
                        (() => {
                           try {
                             const d = parseISO(editedDeadline);
                             return isNaN(d.getTime()) ? "No Date" : format(d, "MMM d, yyyy");
                           } catch (e) {
                             return "No Date";
                           }
                        })()
                      ) : "No Date"}
                    </button>
                  )}
                </div>
              ),
              sub: effectiveStatus === "overdue" ? "Expired" : "Expected",
              icon: Clock,
              color: effectiveStatus === "overdue" ? "text-rose-600" : "text-slate-600"
            },
            { 
              label: "Source", 
              value: displayCommitment.meeting_title || displayCommitment.sourceMeeting || "Direct Extraction",
              sub: (() => {
                try {
                  const dateStr = displayCommitment.meetingDate || displayCommitment.date;
                  if (!dateStr || dateStr === "undefined") {
                     return (displayCommitment.meeting_title || displayCommitment.sourceMeeting) ? "Date unavailable" : "Manually identified";
                  }
                  const d = parseISO(dateStr);
                  return isNaN(d.getTime()) ? "Invalid date" : format(d, "MMM d, yyyy");
                } catch (e) {
                  return "Date unavailable";
                }
              })(),
              icon: Calendar,
              color: "text-emerald-600"
            },
            inReview ? { 
              label: "Confidence", 
              value: `${confidenceScore}/10`,
              sub: confidenceValue >= 8.5 ? "Very High" : confidenceValue >= 6.0 ? "Stable" : "Low",
              icon: Activity,
              color: confidenceValue >= 8.5 ? "text-emerald-500" : confidenceValue >= 6.0 ? "text-amber-500" : "text-rose-500",
              isConfidence: true
            } : null,
          ].filter(Boolean).map((item: any, index: number, array) => (
            <div 
              key={item.label} 
              className={cn(
                "bg-white p-6 space-y-3 relative group/cell",
                // Manually apply rounding to corners since we removed overflow-hidden from grid
                index === 0 && "rounded-tl-[31px]",
                index === 1 && "rounded-tr-[31px] md:rounded-none",
                index === 2 && (array.length === 3 ? "rounded-bl-[31px] rounded-br-[31px] md:rounded-bl-none md:rounded-tr-[31px] md:rounded-br-[31px]" : "rounded-bl-[31px] md:rounded-none"),
                index === 3 && "rounded-br-[31px] md:rounded-tr-[31px] md:rounded-br-[31px]"
              )}
              onMouseEnter={() => item.isConfidence && setShowConfidenceInfo(true)}
              onMouseLeave={() => item.isConfidence && setShowConfidenceInfo(false)}
            >
              <div className="flex items-center gap-2">
                <item.icon className={cn("w-3 h-3", item.color)} />
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{item.label}</span>
              </div>
              <div className="space-y-1">
                <div className={cn("text-base font-black truncate", item.color)}>{item.value}</div>
                {item.isConfidence ? (
                  <>
                    <div className="h-1 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className={cn("h-full transition-all duration-500", confidenceValue >= 8.5 ? "bg-emerald-400" : confidenceValue >= 6.0 ? "bg-amber-400" : "bg-rose-400")}
                        style={{ width: `${confidencePercent}%` }}
                      />
                    </div>
                    {/* Tooltip Popup */}
                    {showConfidenceInfo && (
                      <motion.div 
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-3 bg-slate-900 text-white text-[10px] font-bold rounded-2xl shadow-2xl z-20 text-center pointer-events-none"
                      >
                        <div className="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-slate-900" />
                        Score from the AI that the extracted data is accurate
                      </motion.div>
                    )}
                  </>
                ) : (
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{item.sub}</p>
                )}
                {item.extra}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Main Content Area */}
          <div className="lg:col-span-12 space-y-12">
            
            {/* Risk Score Component */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-8 p-8 bg-slate-50 border border-slate-200 rounded-3xl">
              <div className="md:col-span-4 flex flex-col justify-center border-b md:border-b-0 md:border-r border-slate-200 pb-8 md:pb-0 md:pr-8">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Risk Severity</span>
                  <div className={cn(
                    "text-3xl font-black font-mono",
                    riskScore > 0.6 ? "text-rose-600" : riskScore > 0.3 ? "text-amber-600" : "text-emerald-600"
                  )}>
                    {(riskScore * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="h-3 w-full bg-slate-200/50 rounded-full overflow-hidden shadow-inner mb-4">
                  <div 
                    className={cn(
                      "h-full transition-all duration-1000 ease-out",
                      riskScore > 0.6 ? "bg-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.3)]" : riskScore > 0.3 ? "bg-amber-500" : "bg-emerald-500"
                    )}
                    style={{ width: `${riskScore * 100}%` }}
                  />
                </div>
                <p className="text-[10px] font-bold text-slate-400 uppercase leading-relaxed tracking-wider">
                  Combined signal from deadline proximity, owner historical reliability, and record recency.
                </p>
              </div>

              <div className="md:col-span-8 grid grid-cols-1 sm:grid-cols-3 gap-6">
                {[
                  { label: "Deadline", weight: 50, score: breakdown.deadline, color: "bg-rose-400" },
                  { label: "Owner", weight: 35, score: breakdown.owner, color: "bg-blue-400" },
                  { label: "Recency", weight: 15, score: breakdown.recency, color: "bg-slate-400" },
                ].map((factor) => (
                  <div key={factor.label} className="space-y-3">
                    <div className="flex justify-between items-end">
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{factor.label}</span>
                      <span className="text-[10px] font-mono font-bold text-slate-400">{factor.weight}% Wt.</span>
                    </div>
                    <div className="bg-white rounded-xl p-3 border border-slate-100 shadow-sm flex items-center justify-between">
                       <div className="h-1.5 w-16 bg-slate-100 rounded-full overflow-hidden">
                          <div className={cn("h-full", factor.color)} style={{ width: `${factor.score}%` }} />
                       </div>
                       <span className="text-xs font-black text-slate-900">{factor.score}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Original Quote */}
            <div className="space-y-6">
              <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                <Activity className="w-3 h-3 text-blue-500" />
                Original Intent & Context
              </h3>
              <div className="relative">
                <div className="absolute -left-4 top-0 bottom-0 w-1 bg-blue-500 rounded-full" />
                <blockquote className="text-xl md:text-2xl text-slate-800 font-medium italic leading-relaxed pl-4">
                  "{displayCommitment.raw_text || displayCommitment.title}"
                </blockquote>
              </div>
            </div>

            {/* History Section */}
            <div className="space-y-8 pb-12">
              <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                <Activity className="w-3 h-3 text-brand" />
                History
              </h3>
              
              <div className="space-y-6">
                {!history || history.length === 0 ? (
                  <div className="p-8 border border-dashed border-slate-200 rounded-3xl text-center">
                    <p className="text-sm font-bold text-slate-400">No activity history recorded yet.</p>
                  </div>
                ) : (
                  <div className="relative pl-8 border-l border-slate-100 space-y-8">
                    {(Array.isArray(history) ? history : [])
                      .sort((a, b) => {
                        const dateA = (a.occurred_at || a.created_at) ? parseISO(String(a.occurred_at || a.created_at)).getTime() : 0;
                        const dateB = (b.occurred_at || b.created_at) ? parseISO(String(b.occurred_at || b.created_at)).getTime() : 0;
                        return (isNaN(dateB) ? 0 : dateB) - (isNaN(dateA) ? 0 : dateA);
                      })
                      .map((item, idx) => {
                        const showLabel = item.label || null;
                        const showType = item.type || item.activity_type || null;
                        const showActor = item.actor || item.performed_by_name || null;
                        const showTarget = item.target || null;
                        const showOutcome = item.outcome || null;

                        return (
                          <div key={item.id || `history-${idx}`} className="relative group/history">
                            <div className="absolute -left-[37px] top-4 w-4 h-4 rounded-full border-2 border-white bg-blue-600 shadow-md group-hover/history:scale-110 transition-transform" />
                            
                            <div className="bg-slate-50/50 hover:bg-slate-50 p-6 rounded-3xl border border-slate-100 hover:border-slate-200 transition-all text-left space-y-3 shadow-sm hover:shadow-md">
                              <div className="flex items-center justify-between gap-3 flex-wrap">
                                <span className="text-[10px] uppercase font-black px-2.5 py-1 rounded-full bg-slate-200/50 text-slate-600 tracking-wider">
                                  {String(showType || 'activity').replace("_", " ")}
                                </span>
                                <span className="text-[10px] font-bold text-slate-400">
                                  {(item.occurred_at || item.created_at) ? (
                                    (() => {
                                      try {
                                        const d = parseISO(String(item.occurred_at || item.created_at));
                                        return isNaN(d.getTime()) ? "Unknown Date" : format(d, "MMM d, yyyy · HH:mm");
                                      } catch (e) {
                                        return "Unknown Date";
                                      }
                                    })()
                                  ) : "Unknown Date"}
                                </span>
                              </div>

                              {item.message ? (
                                <p className="text-sm text-slate-700 leading-relaxed font-bold">
                                  {item.message}
                                </p>
                              ) : item.activity_detail ? (
                                <p className="text-sm text-slate-600 leading-relaxed font-medium">
                                  {typeof item.activity_detail === 'string' ? item.activity_detail : JSON.stringify(item.activity_detail)}
                                </p>
                              ) : null}

                              {/* Structured Metadata details block */}
                              {(showLabel || showType || showActor || showTarget || showOutcome) && (
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 pt-4 mt-2 border-t border-slate-200/40">
                                  {showLabel && (
                                    <div className="space-y-0.5">
                                      <span className="text-[9px] font-black uppercase tracking-wider text-slate-400">Label</span>
                                      <p className="text-xs font-black text-slate-800">{showLabel}</p>
                                    </div>
                                  )}
                                  {showType && (
                                    <div className="space-y-0.5">
                                      <span className="text-[9px] font-black uppercase tracking-wider text-slate-400">Type</span>
                                      <p className="text-xs font-black text-[#4A154B]">{showType}</p>
                                    </div>
                                  )}
                                  {showActor && (
                                    <div className="space-y-0.5">
                                      <span className="text-[9px] font-black uppercase tracking-wider text-slate-400">Actor</span>
                                      <p className="text-xs font-bold text-blue-600 flex items-center gap-1.5 truncate">
                                        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full inline-block shrink-0" />
                                        {showActor}
                                      </p>
                                    </div>
                                  )}
                                  {showTarget && (
                                    <div className="space-y-0.5">
                                      <span className="text-[9px] font-black uppercase tracking-wider text-slate-400">Target</span>
                                      <p className="text-xs font-bold text-purple-600 flex items-center gap-1.5 truncate">
                                        <span className="w-1.5 h-1.5 bg-purple-500 rounded-full inline-block shrink-0" />
                                        {showTarget}
                                      </p>
                                    </div>
                                  )}
                                  {showOutcome && (
                                    <div className="space-y-0.5">
                                      <span className="text-[9px] font-black uppercase tracking-wider text-slate-400">Outcome</span>
                                      <div>
                                        <span className={cn(
                                          "px-2 py-0.5 text-[9px] font-black uppercase tracking-widest rounded-md inline-block",
                                          showOutcome === 'delivered' || showOutcome === 'done' || showOutcome === 'success' || showOutcome === 'resolved'
                                            ? "bg-emerald-50 text-emerald-700" 
                                            : "bg-amber-50 text-amber-700"
                                        )}>
                                          {showOutcome === 'delivered' ? 'done' : showOutcome}
                                        </span>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>

      {/* Unsaved Changes Dialog */}
      {showConfirmBack && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-[32px] p-8 shadow-2xl max-w-sm w-full text-center space-y-6"
          >
            <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto">
              <Clock className="w-8 h-8 text-amber-600" />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-black text-slate-900">Unsaved Changes</h3>
              <p className="text-sm font-medium text-slate-500">You have modified this commitment. Moving back will discard your edits.</p>
            </div>
            <div className="flex flex-col gap-2">
              <Button 
                className="h-12 w-full font-black text-sm" 
                onClick={() => {
                  setHasChanges(false);
                  navigate("/dashboard");
                }}
              >
                Discard Changes
              </Button>
              <Button 
                variant="secondary" 
                className="h-12 w-full font-bold text-sm border-slate-200" 
                onClick={() => setShowConfirmBack(false)}
              >
                Keep Editing
              </Button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Reject Confirmation Dialog */}
      {showConfirmReject && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-[32px] p-8 shadow-2xl max-w-sm w-full text-center space-y-6"
          >
            <div className="w-16 h-16 bg-rose-100 rounded-full flex items-center justify-center mx-auto">
              <Trash2 className="w-8 h-8 text-rose-600" />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-black text-slate-900">Reject Extraction?</h3>
              <p className="text-sm font-medium text-slate-500">This will permanently cancel this commitment and remove it from your dashboard.</p>
            </div>
            <div className="flex flex-col gap-2">
              <Button 
                className="h-12 w-full font-black text-sm bg-rose-600 hover:bg-rose-700 shadow-rose-200" 
                onClick={confirmReject}
                disabled={rejectMutation.isPending}
              >
                {rejectMutation.isPending ? "Rejecting..." : "Yes, Reject Extraction"}
              </Button>
              <Button 
                variant="secondary" 
                className="h-12 w-full font-bold text-sm border-slate-200" 
                onClick={() => setShowConfirmReject(false)}
              >
                Cancel
              </Button>
            </div>
          </motion.div>
        </div>
      )}

      {/* Person Picker Popup */}
      {canEdit && showPersonPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="bg-white rounded-[32px] shadow-2xl w-full max-w-sm overflow-hidden border border-slate-200 flex flex-col"
          >
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="space-y-1">
                <h3 className="text-lg font-black text-slate-900">Reassign Owner</h3>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Select a team member</p>
              </div>
              <button 
                onClick={() => setShowPersonPicker(false)} 
                className="p-2 hover:bg-slate-200 rounded-full text-slate-400 hover:text-slate-900 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-3 max-h-[400px] overflow-y-auto space-y-1 custom-scrollbar">
              {(Array.isArray(people) ? people : []).map(p => {
                // The identifier that should be sent to the API
                const personIdentifier = p.owner || p.id || p.name;
                // Check if this person matches the current edited owner
                const isSelected = editedOwnerId === personIdentifier || 
                                 (commitment?.owner_name === p.name && editedOwnerId === commitment?.owner);
                
                return (
                  <button
                    key={p.name}
                    onClick={() => {
                      setEditedOwnerId(personIdentifier);
                      setShowPersonPicker(false);
                    }}
                    className={cn(
                      "w-full flex items-center gap-3 p-3 rounded-2xl transition-all duration-200 group text-left",
                      isSelected 
                        ? "bg-blue-600 shadow-lg shadow-blue-500/20" 
                        : "hover:bg-slate-50 border border-transparent hover:border-slate-100"
                    )}
                  >
                    <Avatar 
                      name={p.name || "Unknown"} 
                      className={cn(
                        "w-10 h-10 ring-2",
                        isSelected ? "ring-blue-400" : "ring-transparent group-hover:ring-slate-200"
                      )} 
                    />
                    <div className="flex-1 min-w-0">
                      <p className={cn(
                        "text-sm font-black truncate",
                        isSelected ? "text-white" : "text-slate-900"
                      )}>{p.name}</p>
                      <p className={cn(
                        "text-[10px] font-bold truncate",
                        isSelected ? "text-blue-100" : "text-slate-400"
                      )}>{p.role || "Team Member"}</p>
                    </div>
                    {isSelected && (
                      <div className="h-6 w-6 rounded-full bg-white flex items-center justify-center">
                        <Check className="w-4 h-4 text-blue-600" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
            
            <div className="p-4 bg-slate-50 border-t border-slate-100 text-center">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                {(Array.isArray(people) ? people : []).length} Team Members Available
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </>
  );
};
