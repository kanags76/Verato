import { useState, MouseEvent, useRef, DragEvent, ChangeEvent } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  AlertCircle, 
  Clock, 
  CheckCircle2, 
  MoreHorizontal,
  ArrowUpRight,
  Filter,
  ListFilter,
  Search,
  AlertTriangle,
  Info,
  X,
  Hash,
  ChevronLeft,
  ChevronRight,
  FileUp,
  FileText,
  Sheet,
  ArrowRight,
  Loader2
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { commitmentService, dashboardService, tagService, importService, meetingService, personService } from "@/src/lib/api/services";
import { Link, useNavigate } from "react-router-dom";
import { Card } from "@/src/components/ui/Card";
import { Badge } from "@/src/components/ui/Badge";
import { Avatar } from "@/src/components/ui/Avatar";
import { Button } from "@/src/components/ui/Button";
import { MOCK_COMMITMENTS } from "@/src/lib/mockData";
import { cn } from "@/src/lib/utils";
import { format, parseISO, startOfWeek } from "date-fns";
import { ImportSuccessModal } from "@/src/components/ImportSuccessModal";

export const Dashboard = () => {
  const [activeTab, setActiveTab] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedPriorities, setSelectedPriorities] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagSearchTerm, setTagSearchTerm] = useState("");
  const [isTagFilterOpen, setIsTagFilterOpen] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isSuccessOpen, setIsSuccessOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  const ITEMS_PER_PAGE = 10;

  const { data: commitmentsData, isLoading, isError, error, isSuccess } = useQuery({
    queryKey: ['commitments', selectedPriorities, selectedTags],
    queryFn: () => commitmentService.getAll({ 
      priorities: selectedPriorities, 
      tag: selectedTags.length === 1 ? selectedTags[0] : undefined 
    }),
  });

  const { data: tagsData, isLoading: isTagsLoading, isError: isTagsError } = useQuery({
    queryKey: ['tags'],
    queryFn: tagService.getAll,
  });

  const { data: people } = useQuery({
    queryKey: ['people'],
    queryFn: () => personService.getAll(),
  });

  const extractTags = (data: any): string[] => {
    let rawTags = [];
    if (!data) rawTags = [];
    else if (Array.isArray(data)) rawTags = data;
    else if (data.results && Array.isArray(data.results)) rawTags = data.results;
    else if (data.tags && Array.isArray(data.tags)) rawTags = data.tags;
    else if (data.data && Array.isArray(data.data)) rawTags = data.data;
    
    const uniqueTags = Array.from(new Set(rawTags.map((t: any) => {
      if (typeof t === 'string') return t;
      if (typeof t === 'object' && t !== null) {
        return t.name || t.label || t.tag || t.text || String(t);
      }
      return String(t);
    })));
    
    return uniqueTags;
  };

  const tags = extractTags(tagsData);

  const { data: statsData } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: dashboardService.getStats,
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

  const commitmentsRaw = extractCommitments(commitmentsData);
  const isDemoMode = isSuccess && commitmentsRaw.length === 0 && !searchTerm && selectedPriorities.length === 0 && selectedTags.length === 0;
  const isServerError = isError;

  const commitments = isDemoMode ? MOCK_COMMITMENTS : commitmentsRaw;

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
    return (c.status === "at_risk" || c.is_escalated) && !isOverdue(c) && !isToReview(c);
  };

  const isToReview = (c: any) => {
    const status = String(c.status || "").toLowerCase();
    return (status === "review" || status.includes("review") || status === "pending") && !isOverdue(c);
  };

  const checkIfNeedsManualNudge = (c: any) => {
    if (c.status === "done" || c.status === "deferred" || c.status === "cancelled") {
      return false;
    }
    
    if (c.needs_manual_nudge === true) return true;
    if (c.needs_manual_nudge === false) return false;
    
    if (!c.ownerName || c.ownerName.toLowerCase() === 'unassigned') {
      return false;
    }

    const ownerId = c.owner;
    const ownerName = c.ownerName;

    const rawPeople = people;
    const normalizedPeople = Array.isArray(rawPeople) 
      ? rawPeople 
      : (rawPeople as any)?.results && Array.isArray((rawPeople as any).results)
        ? (rawPeople as any).results
        : (rawPeople as any)?.data && Array.isArray((rawPeople as any).data)
          ? (rawPeople as any).data
          : [];

    const foundPerson = normalizedPeople.find((p: any) => {
      if (!p) return false;
      const pId = String(p.id || p.owner || "").toLowerCase();
      const searchId = String(ownerId || "").toLowerCase();
      return searchId && pId === searchId;
    });

    let targetPerson = foundPerson;
    if (!targetPerson) {
      targetPerson = normalizedPeople.find((p: any) => {
        if (!p) return false;
        const pName = String(p.name || "").toLowerCase();
        const searchName = String(ownerName || "").toLowerCase();
        return searchName && pName === searchName;
      });
    }

    if (targetPerson) {
      const slackUserId = targetPerson.slack_user_id !== undefined ? targetPerson.slack_user_id : targetPerson.slack_id;
      const hasSlack = !!(slackUserId && String(slackUserId).trim() !== "" && String(slackUserId) !== "null" && String(slackUserId) !== "undefined");
      return !hasSlack;
    }

    return true; 
  };

  const getConfidencePercent = (c: any) => {
    const risk = typeof c.riskScore === 'number' ? c.riskScore : 0;
    const confidenceVal = c.confidence !== undefined ? c.confidence * 10 : (1 - risk) * 10;
    return Math.round(confidenceVal * 10);
  };

  const getConfidenceStyleAndLabel = (c: any) => {
    const percent = getConfidencePercent(c);
    if (percent < 60) {
      return {
        badgeStyle: "bg-rose-50 text-rose-700 border-rose-100",
        iconStyle: "text-rose-600",
        label: `${percent}% Conf`
      };
    } else if (percent < 85) {
      return {
        badgeStyle: "bg-amber-50 text-amber-700 border-amber-100",
        iconStyle: "text-amber-600",
        label: `${percent}% Conf`
      };
    } else {
      return {
        badgeStyle: "bg-emerald-50 text-emerald-700 border-emerald-100",
        iconStyle: "text-emerald-600",
        label: `${percent}% Conf`
      };
    }
  };

  const stats = {
    overdue: commitments.filter(c => isOverdue(c)).length,
    at_risk: commitments.filter(c => isAtRisk(c)).length,
    to_review: commitments.filter(c => isToReview(c)).length,
    on_track: commitments.filter(c => (c.status === "on_track" || c.status === "active") && !isOverdue(c) && !isAtRisk(c) && !isToReview(c)).length,
    deferred: commitments.filter(c => c.status === "deferred").length,
    done: commitments.filter(c => c.status === "done").length,
    manual_nudges: commitments.filter(c => checkIfNeedsManualNudge(c)).length,
    total: commitments.filter(c => c.status !== "done" && c.status !== "deferred").length,
  };

  const statCards = [
    { id: 'overdue', label: "Overdue", count: stats.overdue, icon: AlertCircle, color: "text-rose", bg: "bg-rose/10" },
    { id: 'at_risk', label: "At Risk", count: stats.at_risk, icon: Clock, color: "text-amber", bg: "bg-amber/10" },
    { id: 'to_review', label: "To Review", count: stats.to_review, icon: FileUp, color: "text-blue-600", bg: "bg-blue-50" },
    { id: 'on_track', label: "On Track", count: stats.on_track, icon: CheckCircle2, color: "text-sage", bg: "bg-sage/10" },
    { id: 'deferred', label: "Deferred", count: stats.deferred, icon: AlertCircle, color: "text-slate-500", bg: "bg-slate-100" },
    { id: 'done', label: "Done", count: stats.done, icon: CheckCircle2, color: "text-slate-400", bg: "bg-slate-50" },
    { id: 'manual_nudges', label: "Manual Nudges Needed", count: stats.manual_nudges, icon: AlertTriangle, color: "text-purple-700", bg: "bg-purple-100/35" },
  ];

  const togglePriority = (p: string) => {
    setCurrentPage(1);
    setSelectedPriorities(prev => 
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    );
  };

  const displayCommitments = commitments.filter(c => {
    // Search filtering
    if (searchTerm) {
      if (!(c.title?.toLowerCase().includes(searchTerm.toLowerCase()) || 
            c.ownerName?.toLowerCase().includes(searchTerm.toLowerCase()))) {
        return false;
      }
    }

    // Status filtering
    let matchesStatus = true;
    if (activeTab === "all") {
      matchesStatus = c.status !== "done" && c.status !== "deferred";
    } else if (activeTab === "needs_attention") {
      matchesStatus = isOverdue(c) || isAtRisk(c) || isToReview(c);
    } else if (activeTab === "on_track") {
      matchesStatus = (c.status === "on_track" || c.status === "active") && !isOverdue(c) && !isAtRisk(c) && !isToReview(c);
    } else if (activeTab === "deferred") {
      matchesStatus = c.status === "deferred";
    } else if (activeTab === "overdue") {
      matchesStatus = isOverdue(c);
    } else if (activeTab === "at_risk") {
      matchesStatus = isAtRisk(c);
    } else if (activeTab === "to_review") {
      matchesStatus = isToReview(c);
    } else if (activeTab === "manual_nudges") {
      matchesStatus = checkIfNeedsManualNudge(c);
    } else {
      matchesStatus = c.status === activeTab;
    }
    
    if (!matchesStatus) return false;

    // Priority filtering
    if (selectedPriorities.length > 0 && !selectedPriorities.includes(c.priority)) {
      return false;
    }

    // Tag filtering (client-side fallback/composition)
    if (selectedTags.length > 0) {
      const hasAnyTag = selectedTags.some(tag => c.tags?.includes(tag));
      if (!hasAnyTag) return false;
    }

    return true;
  }).sort((a, b) => {
    const isAOverdue = isOverdue(a);
    const isBOverdue = isOverdue(b);
    
    if (isAOverdue && !isBOverdue) return -1;
    if (!isAOverdue && isBOverdue) return 1;
    
    const isAAtRisk = isAtRisk(a);
    const isBAtRisk = isAtRisk(b);
    
    if (isAAtRisk && !isBAtRisk) return -1;
    if (!isAAtRisk && isBAtRisk) return 1;

    const isAToReview = isToReview(a);
    const isBToReview = isToReview(b);

    if (isAToReview && !isBToReview) return -1;
    if (!isAToReview && isBToReview) return 1;
    
    const dateA = a.deadline ? new Date(a.deadline).getTime() : 0;
    const dateB = b.deadline ? new Date(b.deadline).getTime() : 0;
    return (isNaN(dateA) ? 0 : dateA) - (isNaN(dateB) ? 0 : dateB);
  });

  const totalPages = Math.ceil(displayCommitments.length / ITEMS_PER_PAGE);
  const paginatedCommitments = displayCommitments.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const handleTabChange = (tabId: string) => {
    setActiveTab(prev => prev === tabId ? "all" : tabId);
    setCurrentPage(1);
  };

  const handleTagClick = (e: MouseEvent, tag: string) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedTags(prev => prev.includes(tag) ? prev : [...prev, tag]);
    setCurrentPage(1);
  };

  const toggleTag = (tag: string) => {
    setSelectedTags(prev => 
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    );
    setCurrentPage(1);
  };

  const clearTagFilter = () => {
    setSelectedTags([]);
    setCurrentPage(1);
  };

  const weekStart = startOfWeek(new Date(), { weekStartsOn: 1 });

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

  return (
    <div className="max-w-7xl mx-auto space-y-10 pb-20">
      {/* Error and Info Banners */}
      <AnimatePresence>
        {isServerError && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-rose-600 text-white p-3 flex items-center justify-center gap-3 font-bold text-sm shadow-xl rounded-xl mb-6">
              <AlertTriangle className="w-5 h-5" />
              <span>Connectivity Issue: There was an issue with the server (Error Code: {(error as any)?.response?.status || '500'}). Live data is currently unavailable.</span>
            </div>
          </motion.div>
        )}

        {isDemoMode && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-blue-600 text-white p-3 px-6 flex items-center justify-between gap-3 font-bold text-sm shadow-xl rounded-xl mb-6">
              <div className="flex items-center gap-3">
                <Info className="w-5 h-5" />
                <span>You are in Demo mode!</span>
              </div>
              <Button 
                onClick={() => setIsImportModalOpen(true)}
                variant="secondary" 
                size="sm"
                className="bg-white/15 dark:bg-white/10 hover:bg-white/25 text-white border-white/20 font-black text-[10px] uppercase tracking-widest h-8"
              >
                Import Tasks
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header section */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-slate-900 mb-2">Dashboard</h1>
          <p className="text-slate-500 font-medium tracking-tight">Week of {format(weekStart, "MMM d, yyyy")}</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-4 gap-4 md:gap-5">
        {statCards.map((stat, idx) => (
            <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            onClick={() => setActiveTab(prev => prev === stat.id ? "all" : stat.id)}
            className="cursor-pointer group h-full"
          >
            <Card className={cn(
              "relative h-full overflow-hidden bg-white shadow-sm transition-all border-slate-200 hover:shadow-md flex flex-col justify-between py-2.5 px-4",
              activeTab === stat.id && "ring-2 ring-blue-500 border-transparent shadow-lg shadow-blue-500/10"
            )}>
              <div className="flex items-start justify-between relative z-10 mb-2">
                <div className={cn("p-1.5 rounded-lg", stat.bg)}>
                  <stat.icon className={cn("w-3.5 h-3.5 md:w-4 md:h-4", stat.color)} />
                </div>
              </div>
              
              <div className="relative z-10 w-full overflow-hidden">
                <p className="text-[9px] md:text-[10px] font-black uppercase tracking-widest text-slate-400 mb-0.5 leading-none truncate" title={stat.label}>
                  {stat.label}
                </p>
                <p className="text-xl md:text-2xl font-black text-slate-900 font-mono tracking-tighter">
                  {stat.count}
                </p>
              </div>

              {/* Decorative background element */}
              <div className={cn(
                "absolute -right-4 -bottom-4 w-20 h-20 rounded-full blur-3xl opacity-0 group-hover:opacity-20 transition-opacity", 
                stat.bg
              )} />
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Main content table area */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100">
          <div className="flex items-center gap-6 px-2 overflow-x-auto scrollbar-none pb-0.5 w-full sm:w-auto">
            {[
              { id: "all", label: "All Open" },
              { id: "needs_attention", label: "Needs Attention" },
              { id: "to_review", label: "To Review" },
              { id: "on_track", label: "On Track" },
              { id: "deferred", label: "Deferred" },
              { id: "done", label: "Done" },
              { id: "manual_nudges", label: "Manual Nudges Needed" }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={cn(
                  "py-4 text-xs transition-all relative shrink-0",
                  activeTab === tab.id 
                    ? "text-blue-600 font-black" 
                    : "text-slate-400 hover:text-slate-600 font-bold"
                )}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <motion.div 
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600"
                  />
                )}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-4 relative">
            {selectedPriorities.length > 0 && (
              <button 
                onClick={() => setSelectedPriorities([])}
                className="text-[10px] font-bold text-blue-600 hover:text-blue-700 transition-colors"
                id="clear-priority-filters"
              >
                Clear
              </button>
            )}
            <div className="flex items-center gap-1.5" id="tag-filter-container">
              <div className="relative">
                <button
                  onClick={() => setIsTagFilterOpen(!isTagFilterOpen)}
                  className={cn(
                    "p-1.5 rounded-lg border transition-all hover:bg-slate-50",
                    (isTagFilterOpen || selectedTags.length > 0) ? "border-blue-500 text-blue-600 bg-blue-50/30" : "border-slate-200 text-slate-400"
                  )}
                  title="Filter by tags"
                >
                  <Filter className="w-4 h-4" />
                </button>

                <AnimatePresence>
                  {isTagFilterOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      className="absolute right-0 top-full mt-2 w-72 bg-white rounded-2xl shadow-2xl border border-slate-200 z-[100] overflow-hidden flex flex-col"
                    >
                      <div className="p-4 border-b border-slate-50">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">Filter Tags</span>
                          {selectedTags.length > 0 && (
                            <button 
                              onClick={clearTagFilter}
                              className="text-[9px] font-bold text-blue-600 hover:text-blue-700"
                            >
                              Clear ({selectedTags.length})
                            </button>
                          )}
                        </div>
                        <div className="relative group">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                          <input 
                            type="text"
                            placeholder="Find a tag..."
                            className="w-full bg-slate-50 border-none text-xs font-medium py-2 pl-8 pr-3 rounded-xl focus:ring-2 focus:ring-blue-500/20 outline-none transition-all"
                            value={tagSearchTerm}
                            onChange={(e) => setTagSearchTerm(e.target.value)}
                            autoFocus
                          />
                        </div>
                      </div>

                      <div className="p-2 max-h-64 overflow-y-auto">
                        <div className="grid grid-cols-1 gap-1">
                          {isTagsLoading ? (
                            <div className="flex flex-col items-center justify-center py-8">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mb-2"></div>
                              <p className="text-[10px] text-slate-400 font-bold">Loading tags...</p>
                            </div>
                          ) : isTagsError ? (
                            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
                              <AlertTriangle className="w-6 h-6 text-rose-500 mb-2" />
                              <p className="text-[10px] font-bold text-rose-600">Failed to load tags</p>
                            </div>
                          ) : tags.filter(tag => tag.toLowerCase().includes(tagSearchTerm.toLowerCase())).length > 0 ? (
                            tags
                              .filter(tag => tag.toLowerCase().includes(tagSearchTerm.toLowerCase()))
                              .map(tag => (
                              <button
                                key={tag}
                                onClick={() => toggleTag(tag)}
                                className={cn(
                                  "flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all text-left group",
                                  selectedTags.includes(tag) 
                                    ? "bg-blue-50 text-blue-600" 
                                    : "text-slate-600 hover:bg-slate-50"
                                )}
                              >
                                <div className={cn(
                                  "w-1.5 h-1.5 rounded-full transition-all",
                                  selectedTags.includes(tag) ? "bg-blue-600 scale-125" : "bg-slate-300 group-hover:bg-slate-400"
                                )} />
                                {tag}
                                {selectedTags.includes(tag) && (
                                  <div className="ml-auto">
                                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                                  </div>
                                )}
                              </button>
                            ))
                          ) : (
                            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
                              <Hash className="w-6 h-6 text-slate-100 mb-2" />
                              <p className="text-[10px] font-bold text-slate-400">No tags match your search</p>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {selectedTags.length > 0 && (
                        <div className="p-2 border-t border-slate-50 bg-slate-50/30">
                          <button 
                            onClick={() => setIsTagFilterOpen(false)}
                            className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all shadow-lg shadow-blue-500/20"
                          >
                            Apply Filters
                          </button>
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {["High", "Med", "Low"].map((p) => {
                const isActive = selectedPriorities.includes(p);
                return (
                  <button
                    key={p}
                    onClick={() => togglePriority(p)}
                    id={`priority-chip-${p}`}
                    className={cn(
                      "px-3 py-1.5 rounded-lg text-xs font-bold transition-all border",
                      isActive 
                        ? "bg-slate-900 border-slate-900 text-white shadow-sm" 
                        : "bg-white border-slate-200 text-slate-500 hover:border-slate-300"
                    )}
                  >
                    {p}
                  </button>
                );
              })}
            </div>
            
            {/* Pagination UI - Top Right below Low box */}
            {totalPages > 1 && (
              <div className="absolute right-2 top-full mt-8 flex items-center gap-3">
                <span className="text-[10px] font-bold text-slate-400">
                  Page <span className="text-slate-900">{currentPage}</span> of {totalPages}
                </span>
                <div className="flex items-center gap-1">
                  <button 
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-1 hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent rounded transition-all"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </button>
                  <button 
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="p-1 hover:bg-slate-100 disabled:opacity-30 disabled:hover:bg-transparent rounded transition-all"
                  >
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Tag Filter Banner */}
        <AnimatePresence>
          {selectedTags.length > 0 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="flex flex-wrap items-center gap-2 bg-blue-50 border border-blue-100 px-4 py-2 rounded-xl">
                 <Hash className="w-3.5 h-3.5 text-blue-500" />
                 <span className="text-xs font-bold text-slate-600 mr-2">
                   Filtered by tags:
                 </span>
                 <div className="flex flex-wrap gap-1.5 flex-1">
                   {selectedTags.map(tag => (
                     <div 
                      key={tag}
                      className="flex items-center gap-1 bg-white border border-blue-200 px-2 py-0.5 rounded-lg shadow-sm"
                     >
                       <span className="text-[10px] font-black text-blue-600">#{tag}</span>
                       <button 
                        onClick={() => toggleTag(tag)}
                        className="p-0.5 hover:bg-slate-100 rounded text-slate-400 hover:text-rose-500 transition-all"
                       >
                         <X className="w-2.5 h-2.5" />
                       </button>
                     </div>
                   ))}
                 </div>
                 <button 
                   onClick={clearTagFilter}
                   className="flex items-center gap-1.5 px-2 py-1 hover:bg-blue-100 rounded-lg text-blue-500 hover:text-blue-600 transition-all text-[10px] font-bold"
                   id="clear-all-tags"
                 >
                   clear all
                   <X className="w-3 h-3" />
                 </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Commitment List */}
        <div className="space-y-3 mt-12">
          {isLoading && !commitmentsData && (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          )}

          {!isServerError && displayCommitments.length === 0 && !isLoading && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col items-center justify-center py-20 bg-slate-50/50 rounded-2xl border-2 border-dashed border-slate-100"
            >
              <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-4">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Nothing here — all clear</h3>
              <p className="text-slate-500 text-sm font-medium">No commitments found for this filter.</p>
            </motion.div>
          )}
          
          {!isServerError && paginatedCommitments.map((commitment, idx) => {
            const overdue = isOverdue(commitment);
            return (
            <motion.div
              key={commitment.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + idx * 0.05 }}
            >
              <Link to={`/commitments/${commitment.id}`}>
                <Card className="p-0 border-slate-200 bg-white hover:border-blue-500/30 group shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all">
                  <div className="flex items-center gap-4 p-4">
                    {/* Indicators */}
                    <div className="flex items-center gap-2">
                      <div className="flex flex-col gap-1 w-1 h-8">
                        <div className={cn("flex-1 rounded-full", commitment.priority === "High" ? "bg-rose-500" : commitment.priority === "Med" ? "bg-amber-500" : "bg-slate-200")} />
                        <div className={cn("flex-1 rounded-full", (commitment.priority === "High" || commitment.priority === "Med") ? (commitment.priority === "High" ? "bg-rose-500/40" : "bg-amber-500/40") : "bg-slate-100")} />
                      </div>
                      <div className="relative group/risk flex flex-col items-center gap-1 cursor-help">
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

                        {/* Tooltip for Risk Score */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/risk:block bg-slate-900 text-white text-[10px] font-medium px-2 py-1 rounded shadow-lg whitespace-nowrap z-50 pointer-events-none">
                          Risk Signal as {(commitment.riskScore * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>

                    <div className="flex-1 min-w-0 flex flex-col gap-1">
                      {/* Line 1: Meta info */}
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] font-black uppercase tracking-wider text-blue-600 bg-blue-50/50 px-1.5 py-0.5 rounded border border-blue-100/50">
                          {commitment.sourceMeeting}
                        </span>
                        
                        <div className="flex items-center gap-6 ml-auto">
                          <div className="flex items-center">
                            <span className="text-[10px] font-bold text-slate-500">{commitment.ownerName}</span>
                          </div>

                          <div className="flex items-center gap-1 font-mono text-[10px] font-bold text-slate-400 w-16">
                            <Clock className="w-3 h-3" />
                            {formatDateSafely(commitment.deadline, "MMM d")}
                          </div>

                          <div className="w-12 text-center">
                            <Badge variant={commitment.priority === "High" ? "error" : commitment.priority === "Med" ? "warning" : "neutral"} className="h-4 px-1.5 text-[9px] min-w-full justify-center">
                              {commitment.priority}
                            </Badge>
                          </div>

                          {isToReview(commitment) && (() => {
                            const conf = getConfidenceStyleAndLabel(commitment);
                            return (
                              <div className="relative group/conf flex items-center justify-center cursor-help shrink-0">
                                <span className={cn("text-[10px] font-bold py-0.5 px-2 rounded border flex items-center gap-1", conf.badgeStyle)}>
                                  <Info className={cn("w-2.5 h-2.5 inline", conf.iconStyle)} />
                                  {conf.label}
                                </span>
                                
                                {/* Tooltip for Confidence Score */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/conf:block bg-slate-900 text-white text-[10px] font-medium px-2 py-1 rounded shadow-lg whitespace-nowrap z-50 pointer-events-none">
                                  Confidence Level: {getConfidencePercent(commitment)}%
                                </div>
                              </div>
                            );
                          })()}

                          <div className="w-24 text-right">
                            <Badge variant={
                              overdue ? "error" : 
                              isAtRisk(commitment) ? "warning" : 
                              isToReview(commitment) ? "brand" :
                              commitment.status === "done" ? "success" :
                              "success"
                            } className="h-4 px-1.5 text-[9px] min-w-full justify-center">
                              {overdue ? "OVERDUE" : (commitment.is_escalated ? "ESCALATED" : (isToReview(commitment) ? "REVIEW" : (commitment.status === 'done' ? 'DONE' : commitment.status.replace("_", " "))))}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      {/* Line 2: Normalised Text */}
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors">
                          {commitment.normalisedText || commitment.title}
                        </h3>
                        
                        <div className="flex items-center gap-3 ml-4 shrink-0">
                          {commitment.nudgeCount && commitment.nudgeCount > 0 && (
                            <span className="flex items-center gap-1 text-[9px] text-amber-600 font-black uppercase">
                              <AlertCircle className="w-2.5 h-2.5" />
                              {commitment.nudgeCount} Nudges
                            </span>
                          )}
                          
                          <div className="flex items-center gap-1">
                            {commitment.tags && commitment.tags.slice(0, 3).map(tag => (
                              <button 
                                key={tag} 
                                onClick={(e) => handleTagClick(e, tag)}
                                className="text-[8px] font-bold text-slate-400 bg-slate-50 px-1 py-0.5 border border-slate-100 rounded hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 transition-all cursor-pointer"
                              >
                                #{tag}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    <button className="p-1 text-slate-300 hover:text-slate-900 hover:bg-slate-50 rounded transition-all ml-2">
                      <MoreHorizontal className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </Card>
              </Link>
            </motion.div>
            );
          })}
        </div>
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
                
                <ImportTrackerContent onSuccess={() => { setIsImportModalOpen(false); setIsSuccessOpen(true); }} />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      <ImportSuccessModal isOpen={isSuccessOpen} onClose={() => setIsSuccessOpen(false)} />
    </div>
  );
};

const ImportTrackerContent = ({ onSuccess }: { onSuccess: () => void }) => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
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
    if (!file) return;
    if (!title.trim()) {
      setError('Import Title is required.');
      return;
    }
    setIsLoading(true);
    setError(null);
    
    try {
      const { id } = await importService.upload(file, undefined, title.trim());
      
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

  const isExtractDisabled = !file || !title.trim();

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
              <span>Extract from file</span>
              <ArrowRight className="w-5 h-5" />
            </div>
          )}
        </Button>
      </div>
    </div>
  );
};
