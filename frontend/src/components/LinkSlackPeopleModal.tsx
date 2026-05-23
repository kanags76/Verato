import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { slackService } from "../lib/api/services";
import { 
  X, 
  Search, 
  Slack, 
  Check, 
  Loader2, 
  AlertCircle, 
  UserPlus, 
  CheckCircle2, 
  Users 
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

interface LinkSlackPeopleModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const EMPTY_ARRAY: SlackUser[] = [];

export const LinkSlackPeopleModal = ({ isOpen, onClose }: LinkSlackPeopleModalProps) => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [hasInitializedSelection, setHasInitializedSelection] = useState(false);

  // Query slack users from sync endpoint as requested
  const { data: rawData, isLoading, refetch, error } = useQuery<any>({
    queryKey: ['slack-users', 'sync'],
    queryFn: async () => {
      // GET /api/v1/slack/users/sync/
      const users = await slackService.getUsers();
      return users;
    },
    enabled: isOpen,
    retry: false
  });

  // Extract array robustly and normalize properties to avoid key/crash issues
  const slackUsers = React.useMemo<SlackUser[]>(() => {
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
        // Search any value in the response which is an array, preferring non-empty ones
        const arrays = Object.values(rawData).filter(val => Array.isArray(val)) as any[][];
        const non_empty = arrays.find(arr => arr.length > 0);
        if (non_empty) {
          rawList = non_empty;
        } else if (arrays.length > 0) {
          rawList = arrays[0];
        }
      }
    }

    // Now normalize each item in rawList to guarantee unique slack_id keys
    return rawList.map((item, idx) => {
      // Robustly check standard keys first
      let detectedId = item.slack_id || item.id || item.user_id || item.slack_user_id || item.userId || item.member_id;
      
      // Scan top-level string values for a typical Slack ID pattern (e.g., U01SARAHK) if standard keys aren't resolved
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
  }, [rawData]);

  // Automatically select all found workspace members by default for easier multi-selection exactly ONCE per load
  useEffect(() => {
    if (!isLoading && slackUsers.length > 0 && !hasInitializedSelection) {
      setSelectedIds(slackUsers.map(u => u.slack_id));
      setHasInitializedSelection(true);
    }
  }, [slackUsers, isLoading, hasInitializedSelection]);

  // Reset the initialization state when modal is closed
  useEffect(() => {
    if (!isOpen) {
      setHasInitializedSelection(false);
      setSelectedIds([]);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const toggleSelectUser = (slackId: string) => {
    setSelectedIds(prev => 
      prev.includes(slackId) 
        ? prev.filter(id => id !== slackId) 
        : [...prev, slackId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredSlackUsers.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredSlackUsers.map(u => u.slack_id));
    }
  };

  const handleImport = async () => {
    if (selectedIds.length === 0) return;
    setIsSyncing(true);
    setErrorMsg(null);
    try {
      // POST /api/v1/slack/users/import/
      await slackService.importUsers(selectedIds);

      setSyncSuccess(true);
      queryClient.invalidateQueries({ queryKey: ['people'] });
      setTimeout(() => {
        setSyncSuccess(false);
        onClose();
      }, 1500);

    } catch (err: any) {
      console.error(err);
      setErrorMsg("Failed to import the selected Slack members. Please try again.");
    } finally {
      setIsSyncing(false);
    }
  };

  const filteredSlackUsers = slackUsers.filter(u => 
    u.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    (u.title && u.title.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (u.email && u.email.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const isAllFilteredSelected = filteredSlackUsers.length > 0 && 
    filteredSlackUsers.every(u => selectedIds.includes(u.slack_id));

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[250] flex items-center justify-center p-4">
        {/* Backdrop overlay */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-slate-900/60 backdrop-blur-md"
        />

        {/* Modal Container */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.96, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 20 }}
          className="relative w-full max-w-xl bg-white rounded-[40px] shadow-3xl border border-slate-100 overflow-hidden flex flex-col max-h-[85vh]"
        >
          {/* Header */}
          <div className="p-8 border-b border-slate-100 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-50 rounded-2xl flex items-center justify-center text-[#4A154B] shadow-sm">
                <Slack className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-2">
                  Link/Import People
                </h3>
                <p className="text-slate-500 text-xs font-bold mt-0.5">
                  Select Slack contacts to import them into Verato directory.
                </p>
              </div>
            </div>
            
            <button 
              onClick={onClose}
              className="p-2 hover:bg-slate-100 rounded-full text-slate-400 transition-all focus:outline-none"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Search bar & Select All Actions */}
          <div className="px-8 pt-6 pb-2 shrink-0 space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search candidates..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-11 pl-11 pr-4 bg-slate-50 border border-slate-200 rounded-2xl text-xs font-bold text-slate-800 placeholder-slate-400 focus:outline-none focus:border-purple-500 focus:bg-white transition-all shadow-inner"
              />
            </div>

            {filteredSlackUsers.length > 0 && (
              <div className="flex items-center justify-between text-xs px-2">
                <button 
                  onClick={toggleSelectAll} 
                  className="font-black text-purple-600 hover:text-purple-800 transition-colors"
                >
                  {isAllFilteredSelected ? "Deselect All" : "Select All"}
                </button>
                <span className="text-slate-400 font-bold">
                  {selectedIds.length} of {filteredSlackUsers.length} selected
                </span>
              </div>
            )}
          </div>

          {/* Body List */}
          <div className="flex-1 overflow-y-auto px-8 py-3 space-y-2">
            {error ? (
              <div className="flex flex-col items-center justify-center py-16 text-rose-500 text-center space-y-2">
                <AlertCircle className="w-8 h-8 text-rose-400" />
                <p className="text-sm font-bold text-slate-800">Failed to load Slack Directory</p>
                <p className="text-xs text-slate-400 max-w-sm">
                  {(error as any)?.response?.data?.error || (error as any)?.message || "A network or validation error occurred while communicating with Slack."}
                </p>
              </div>
            ) : isLoading ? (
              <div className="flex flex-col items-center justify-center py-20 text-slate-400 gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
                <span className="text-xs font-bold uppercase tracking-wider">Fetching Workspace Users...</span>
              </div>
            ) : filteredSlackUsers.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-slate-400 text-center space-y-2">
                <AlertCircle className="w-8 h-8 text-slate-300" />
                <p className="text-sm font-bold text-slate-800">No members found</p>
                <p className="text-xs text-slate-400 max-w-xs">Try searching for another user or verify your Slack workspace connection is connected.</p>
              </div>
            ) : (
              <div className="space-y-1.5 divide-y divide-slate-50">
                {filteredSlackUsers.map((sUser) => {
                  const isChecked = selectedIds.includes(sUser.slack_id);
                  return (
                    <div 
                      key={sUser.slack_id} 
                      onClick={() => toggleSelectUser(sUser.slack_id)}
                      className={cn(
                        "flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition-all border select-none group/row",
                        isChecked 
                          ? "bg-purple-50/40 border-purple-100 hover:bg-purple-50" 
                          : "bg-white border-transparent hover:bg-slate-50 hover:border-slate-100"
                      )}
                    >
                      {/* Left: Checkbox + Avatar + User details */}
                      <div className="flex items-center gap-3.5 min-w-0">
                        {/* Checkbox */}
                        <div 
                          className={cn(
                            "w-5 h-5 rounded-md border flex items-center justify-center transition-all shrink-0",
                            isChecked 
                              ? "bg-purple-600 border-purple-600 text-white" 
                              : "border-slate-300 bg-white group-hover/row:border-slate-400"
                          )}
                        >
                          {isChecked && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                        </div>

                        {/* User Details */}
                        <Avatar name={sUser.name} className="w-9 h-9 rounded-full border border-slate-100 shrink-0" />
                        <div className="min-w-0">
                          <span className="text-xs font-black text-slate-900 leading-none block truncate">
                            {sUser.name}
                          </span>
                          <span className="text-[10px] font-bold text-slate-400 block mt-0.5 truncate">
                            {sUser.title || "Team Member"} • {sUser.email || "No email"}
                          </span>
                        </div>
                      </div>

                      {/* Right side decoration or ID */}
                      <span className="text-[9px] font-mono font-bold text-slate-400 tracking-wider bg-slate-50 group-hover/row:bg-white px-2 py-0.5 rounded shrink-0">
                        {sUser.slack_id}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer controls */}
          <div className="p-8 border-t border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row items-center justify-between gap-4 shrink-0">
            {errorMsg ? (
              <span className="text-xs font-bold text-rose-600 flex items-center gap-1">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {errorMsg}
              </span>
            ) : (
              <span className="text-xs font-bold text-slate-400">
                Selected users will be created as active Verato directory people.
              </span>
            )}

            <div className="flex items-center gap-3 w-full sm:w-auto shrink-0 justify-end">
              <Button
                variant="secondary"
                onClick={onClose}
                disabled={isSyncing}
                className="w-full sm:w-auto px-6 h-11 rounded-2xl font-bold border-slate-200 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </Button>
              <Button
                onClick={handleImport}
                disabled={isSyncing || syncSuccess || selectedIds.length === 0}
                className="w-full sm:w-auto px-8 h-11 rounded-2xl font-black bg-slate-900 border-none text-white hover:bg-slate-800 transition-all shadow-lg flex items-center justify-center gap-2"
              >
                {isSyncing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-white" />
                    <span>Importing...</span>
                  </>
                ) : syncSuccess ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 animate-bounce" />
                    <span>Successfully Imported!</span>
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    <span>Submit ({selectedIds.length})</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
