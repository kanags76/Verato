import React, { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useQueryClient } from "@tanstack/react-query";
import { slackService, personService } from "../lib/api/services";
import { 
  X, 
  Search, 
  Slack, 
  Check, 
  Loader2, 
  AlertCircle, 
  CheckCircle2, 
  Users,
  SearchCode,
  ArrowRight
} from "lucide-react";
import { Button } from "./ui/Button";
import { Avatar } from "./ui/Avatar";
import { cn } from "../lib/utils";

interface SlackUser {
  slack_id: string;
  name: string;
  email?: string;
  title?: string;
  avatar?: string;
}

interface ManualSlackLinkModalProps {
  isOpen: boolean;
  onClose: () => void;
  person: any; // The person object to link
}

type ModalState = 
  | "idle"
  | "searching_email"
  | "searching_name"
  | "matches_found"
  | "no_match"
  | "loading_directory"
  | "manual_select"
  | "linking"
  | "success"
  | "error";

const EMPTY_ARRAY: SlackUser[] = [];

// Reusable normalizer function matching LinkSlackPeopleModal
const normalizeSlackUsers = (rawData: any): SlackUser[] => {
  let rawList: any[] = [];
  if (!rawData) return EMPTY_ARRAY;
  if (Array.isArray(rawData)) {
    rawList = rawData;
  } else if (typeof rawData === "object") {
    if (Array.isArray(rawData.unmatched_slack)) {
      rawList = rawData.unmatched_slack;
    } else if (Array.isArray(rawData.users)) {
      rawList = rawData.users;
    } else if (Array.isArray(rawData.data)) {
      rawList = rawData.data;
    } else if (Array.isArray(rawData.results)) {
      rawList = rawData.results;
    } else {
      const arrays = Object.values(rawData).filter(val => Array.isArray(val)) as any[][];
      const non_empty = arrays.find(arr => arr.length > 0);
      if (non_empty) {
        rawList = non_empty;
      } else if (arrays.length > 0) {
        rawList = arrays[0];
      }
    }
  }

  return rawList.map((item, idx) => {
    let detectedId = item.slack_id || item.id || item.user_id || item.slack_user_id || item.userId || item.member_id;
    if (!detectedId && item && typeof item === "object") {
      for (const [key, val] of Object.entries(item)) {
        if (typeof val === "string" && /^[UW][A-Z0-9]{8,11}$/.test(val)) {
          detectedId = val;
          break;
        }
      }
    }
    const id = detectedId || `slack-temp-id-${idx}`;
    return {
      slack_id: id,
      name: item.name || item.real_name || item.profile?.real_name || item.profile?.name || "Unknown Slack User",
      email: item.email || item.profile?.email || item.info?.email,
      title: item.title || item.profile?.title || item.title_name || item.info?.title,
      avatar: item.avatar || item.profile?.image_512 || item.profile?.image_192 || item.profile?.image_72
    };
  });
};

export const ManualSlackLinkModal = ({ isOpen, onClose, person }: ManualSlackLinkModalProps) => {
  const queryClient = useQueryClient();
  const [modalState, setModalState] = useState<ModalState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  // Potential matches from automatic search
  const [matches, setMatches] = useState<SlackUser[]>([]);
  
  // Full directory for manual matching
  const [directory, setDirectory] = useState<SlackUser[]>([]);
  const [directorySearch, setDirectorySearch] = useState("");
  
  // Selected single slack profile to link
  const [selectedSlackId, setSelectedSlackId] = useState<string | null>(null);

  // Trigger search when modal opens
  useEffect(() => {
    if (isOpen && person) {
      startAutomaticSearch();
    } else {
      // Reset state when closed
      setModalState("idle");
      setMatches([]);
      setDirectory([]);
      setDirectorySearch("");
      setSelectedSlackId(null);
      setErrorMessage(null);
    }
  }, [isOpen, person]);

  const startAutomaticSearch = async () => {
    if (!person) return;
    setErrorMessage(null);
    setSelectedSlackId(null);

    try {
      // Step 1: Search by Email first
      if (person.email && person.email.trim() !== "") {
        setModalState("searching_email");
        const res = await slackService.searchUsers(person.email.trim());
        const normalized = normalizeSlackUsers(res);
        if (normalized.length > 0) {
          setMatches(normalized);
          // Auto select if single match found
          if (normalized.length === 1) {
            setSelectedSlackId(normalized[0].slack_id);
          }
          setModalState("matches_found");
          return;
        }
      }

      // Step 2: Search by Name if Email match was empty/unavailable
      setModalState("searching_name");
      const resName = await slackService.searchUsers(person.name);
      const normalizedName = normalizeSlackUsers(resName);
      if (normalizedName.length > 0) {
        setMatches(normalizedName);
        if (normalizedName.length === 1) {
          setSelectedSlackId(normalizedName[0].slack_id);
        }
        setModalState("matches_found");
        return;
      }

      // Step 3: No Match Found
      setModalState("no_match");
    } catch (err: any) {
      console.error("Automatic Slack match error", err);
      // Fallback directly to no_match to let them proceed manually
      setModalState("no_match");
    }
  };

  const handlePullAllUsers = async () => {
    setModalState("loading_directory");
    setErrorMessage(null);
    try {
      const res = await slackService.getUsers();
      const normalized = normalizeSlackUsers(res);
      setDirectory(normalized);
      setModalState("manual_select");
    } catch (err: any) {
      console.error("Failed to load slack search catalog", err);
      setErrorMessage(err.message || "Failed to load Slack workspace members catalog.");
      setModalState("error");
    }
  };

  const handleLinkProfile = async (slackId: string) => {
    setModalState("linking");
    setErrorMessage(null);
    try {
      await personService.update(person.id, { slack_id: slackId });
      setModalState("success");
      queryClient.invalidateQueries({ queryKey: ["people"] });
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      console.error("Link slack mapping failed", err);
      setErrorMessage(err.response?.data?.error || err.message || "Failed to link profile.");
      setModalState("error");
    }
  };

  const filteredDirectory = useMemo(() => {
    if (!directorySearch.trim()) return directory;
    const query = directorySearch.toLowerCase();
    return directory.filter(u => 
      u.name.toLowerCase().includes(query) || 
      (u.email && u.email.toLowerCase().includes(query)) ||
      (u.title && u.title.toLowerCase().includes(query)) ||
      u.slack_id.toLowerCase().includes(query)
    );
  }, [directory, directorySearch]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="bg-white rounded-[40px] max-w-lg w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh] border border-slate-100"
      >
        {/* Header */}
        <div className="px-8 pt-8 pb-4 flex items-center justify-between border-b border-slate-50 relative shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-50 rounded-2xl flex items-center justify-center">
              <Slack className="w-5 h-5 text-[#4A154B]" />
            </div>
            <div>
              <h3 className="text-xl font-black text-slate-900">Link Slack Identity</h3>
              <p className="text-xs font-bold text-slate-400">Match {person?.name} to Slack Member</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-10 h-10 rounded-full hover:bg-slate-50 border border-slate-100 transition-colors flex items-center justify-center text-slate-400 hover:text-slate-600 focus:outline-none"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content wrapper */}
        <div className="flex-1 overflow-y-auto min-h-0">
          <AnimatePresence mode="wait">
            {/* Searching Email */}
            {modalState === "searching_email" && (
              <motion.div 
                key="searching_email"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center py-20 px-8 text-center space-y-4"
              >
                <div className="relative">
                  <Loader2 className="w-12 h-12 text-purple-600 animate-spin" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Slack className="w-4 h-4 text-[#4A154B]" />
                  </div>
                </div>
                <div className="space-y-1">
                  <h4 className="text-base font-black text-slate-800">Searching by Email...</h4>
                  <p className="text-xs font-bold text-slate-400">Trying to match "{person?.email}"</p>
                </div>
              </motion.div>
            )}

            {/* Searching Name */}
            {modalState === "searching_name" && (
              <motion.div 
                key="searching_name"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center py-20 px-8 text-center space-y-4"
              >
                <div className="relative">
                  <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <SearchCode className="w-4 h-4 text-blue-600" />
                  </div>
                </div>
                <div className="space-y-1">
                  <h4 className="text-base font-black text-slate-800">Searching by Name...</h4>
                  <p className="text-xs font-bold text-slate-400">Trying to match "{person?.name}"</p>
                </div>
              </motion.div>
            )}

            {/* Matches Found */}
            {modalState === "matches_found" && (
              <motion.div 
                key="matches_found"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-8 space-y-6"
              >
                <div className="bg-emerald-50 rounded-2xl p-4 flex gap-3 text-emerald-800 border border-emerald-100">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs font-black uppercase tracking-wider">Matching Members Found</h4>
                    <p className="text-[11px] font-bold text-emerald-700/90 leading-relaxed mt-0.5">
                      We identified corresponding profiles in your Slack team matches. Confirm candidate to link:
                    </p>
                  </div>
                </div>

                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                  {matches.map((item) => {
                    const isSelected = selectedSlackId === item.slack_id;
                    return (
                      <div 
                        key={item.slack_id}
                        onClick={() => setSelectedSlackId(item.slack_id)}
                        className={cn(
                          "flex items-center gap-4 p-4 rounded-3xl border-2 transition-all cursor-pointer",
                          isSelected 
                            ? "border-purple-500 bg-purple-50/25 ring-4 ring-purple-500/10" 
                            : "border-slate-100 bg-white hover:border-slate-200"
                        )}
                      >
                        <Avatar name={item.name} size="lg" />
                        <div className="flex-1 min-w-0">
                          <h4 className="font-black text-slate-900 text-sm truncate">{item.name}</h4>
                          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest truncate">
                            {item.title || "Slack Member"}
                          </p>
                          {item.email && <p className="text-[11px] text-slate-500 truncate mt-0.5">{item.email}</p>}
                        </div>
                        <div className={cn(
                          "w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all shrink-0",
                          isSelected ? "bg-purple-600 border-purple-600" : "border-slate-300"
                        )}>
                          {isSelected && <div className="w-2 h-2 bg-white rounded-full" />}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="flex gap-3 pt-4 border-t border-slate-50">
                  <Button 
                    variant="secondary" 
                    className="flex-1 h-12 rounded-2xl font-bold bg-slate-50 hover:bg-slate-100 border-none"
                    onClick={handlePullAllUsers}
                  >
                    Select manually
                  </Button>
                  <Button 
                    className="flex-1 h-12 rounded-2xl font-black bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-50 border-none shadow-lg shadow-purple-500/15"
                    disabled={!selectedSlackId}
                    onClick={() => selectedSlackId && handleLinkProfile(selectedSlackId)}
                  >
                    Confirm & Link
                  </Button>
                </div>
              </motion.div>
            )}

            {/* No Match Found */}
            {modalState === "no_match" && (
              <motion.div 
                key="no_match"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-8 space-y-6"
              >
                <div className="flex flex-col items-center justify-center py-6 text-slate-400 gap-3 text-center">
                  <div className="w-16 h-16 bg-rose-50 rounded-3xl flex items-center justify-center text-rose-500">
                    <AlertCircle className="w-8 h-8" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-base font-black text-slate-800">Could not match email or name</h4>
                    <p className="text-xs font-bold text-slate-400 max-w-sm mt-1">
                      No matching records found for "{person?.name}" ({person?.email || "No email"}).
                    </p>
                  </div>
                </div>

                <div className="bg-slate-50 rounded-[28px] p-5 border border-slate-100 text-center space-y-4">
                  <p className="text-xs font-bold text-slate-600 leading-relaxed">
                    Would you like to load your entire Slack Directory and search manually to link an entry?
                  </p>
                  <div className="flex gap-3">
                    <Button 
                      variant="secondary" 
                      className="flex-1 h-11 rounded-2xl font-bold bg-white hover:bg-slate-100 border-slate-200"
                      onClick={onClose}
                    >
                      No, Cancel
                    </Button>
                    <Button 
                      className="flex-1 h-11 rounded-2xl font-black bg-blue-600 hover:bg-blue-700 text-white border-none shadow-md shadow-blue-500/10"
                      onClick={handlePullAllUsers}
                    >
                      Yes, Pull List
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Loading Directory */}
            {modalState === "loading_directory" && (
              <motion.div 
                key="loading_directory"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center py-24 px-8 text-center space-y-4"
              >
                <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
                <div className="space-y-1">
                  <h4 className="text-base font-black text-slate-800">Fetching Slack Members...</h4>
                  <p className="text-xs font-bold text-slate-400">Loading complete workspace directory</p>
                </div>
              </motion.div>
            )}

            {/* Manual Select from Full List */}
            {modalState === "manual_select" && (
              <motion.div 
                key="manual_select"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col h-[50vh]"
              >
                {/* Search Bar */}
                <div className="px-8 py-3 bg-slate-50 border-y border-slate-100 shrink-0 relative">
                  <Search className="w-4 h-4 absolute left-11 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input 
                    type="text" 
                    placeholder="Search Slack directory by name or info..." 
                    value={directorySearch}
                    onChange={(e) => setDirectorySearch(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded-2xl pl-10 pr-4 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-bold"
                  />
                </div>

                {/* Directory List */}
                <div className="flex-1 overflow-y-auto px-8 py-4 space-y-2 min-h-0">
                  {filteredDirectory.length === 0 ? (
                    <div className="text-center py-12 text-slate-400">
                      <Users className="w-8 h-8 mx-auto mb-2 opacity-40" />
                      <p className="text-xs font-bold">No Slack members match "{directorySearch}"</p>
                    </div>
                  ) : (
                    filteredDirectory.map((item) => (
                      <div 
                        key={item.slack_id}
                        className="flex items-center justify-between p-3 rounded-2xl hover:bg-slate-50 border border-transparent hover:border-slate-100 transition-all"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <Avatar name={item.name} size="md" />
                          <div className="min-w-0">
                            <h4 className="font-black text-slate-800 text-xs truncate">{item.name}</h4>
                            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest truncate">
                              {item.title || "Slack Member"}
                            </p>
                          </div>
                        </div>

                        <Button 
                          size="sm"
                          variant="secondary"
                          onClick={() => handleLinkProfile(item.slack_id)}
                          className="rounded-xl border-slate-200 text-[10px] font-black uppercase tracking-widest h-8 hover:bg-blue-600 hover:text-white"
                        >
                          Link Profile
                          <ArrowRight className="w-3 h-3 ml-1" />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </motion.div>
            )}

            {/* Linking Action State */}
            {modalState === "linking" && (
              <motion.div 
                key="linking"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center justify-center py-20 px-8 text-center space-y-4"
              >
                <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
                <div className="space-y-1">
                  <h4 className="text-base font-black text-slate-800">Updating Profile...</h4>
                  <p className="text-xs font-bold text-slate-400">Linking {person?.name} to selected Slack ID</p>
                </div>
              </motion.div>
            )}

            {/* Success */}
            {modalState === "success" && (
              <motion.div 
                key="success"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="flex flex-col items-center justify-center py-20 px-8 text-center space-y-4"
              >
                <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center text-emerald-600 animate-bounce">
                  <Check className="w-8 h-8" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-lg font-black text-slate-800">Linked Successfully!</h4>
                  <p className="text-xs font-bold text-slate-400">The member directory and profile maps are updated.</p>
                </div>
              </motion.div>
            )}

            {/* Error view */}
            {modalState === "error" && (
              <motion.div 
                key="error"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-8 space-y-6"
              >
                <div className="flex flex-col items-center justify-center py-6 text-rose-500 gap-3 text-center">
                  <AlertCircle className="w-12 h-12 text-rose-500 animate-pulse" />
                  <div className="space-y-1">
                    <h4 className="text-base font-black text-slate-800">An Error Occurred</h4>
                    <p className="text-xs font-bold text-slate-400 max-w-sm mt-1">
                      {errorMessage || "We ran into an unexpected error linking this profile."}
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 pt-4 border-t border-slate-50">
                  <Button 
                    variant="secondary" 
                    className="flex-1 h-12 rounded-2xl font-bold bg-slate-50 hover:bg-slate-100 border-none"
                    onClick={onClose}
                  >
                    Close Window
                  </Button>
                  <Button 
                    className="flex-1 h-12 rounded-2xl font-black bg-blue-600 hover:bg-blue-700 text-white border-none shadow-lg shadow-blue-500/10"
                    onClick={startAutomaticSearch}
                  >
                    Try Again
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
};
