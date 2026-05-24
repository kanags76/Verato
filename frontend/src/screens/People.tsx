import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { personService, slackService } from "@/src/lib/api/services";
import { LinkSlackPeopleModal } from "@/src/components/LinkSlackPeopleModal";
import { ManualSlackLinkModal } from "@/src/components/ManualSlackLinkModal";
import { 
  Users, 
  Search, 
  Slack, 
  ExternalLink, 
  Edit2, 
  Save, 
  X, 
  Merge, 
  Check, 
  UserPlus
} from "lucide-react";
import { Card } from "@/src/components/ui/Card";
import { Avatar } from "@/src/components/ui/Avatar";
import { Button } from "@/src/components/ui/Button";
import { cn } from "@/src/lib/utils";

export const People = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ name: "", role: "", email: "" });
  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState({ name: "", email: "", role: "" });
  const [showMergeConfirm, setShowMergeConfirm] = useState(false);
  const [primaryId, setPrimaryId] = useState<string | null>(null);
  const [isMergingInProgress, setIsMergingInProgress] = useState(false);
  const [showSlackImportModal, setShowSlackImportModal] = useState(false);
  const [selectedPersonToLink, setSelectedPersonToLink] = useState<any | null>(null);
  const [isManualLinkOpen, setIsManualLinkOpen] = useState(false);

  const { data: slackStatus } = useQuery({
    queryKey: ['slack-status'],
    queryKeyHashFn: () => 'slack-status',
    queryFn: () => slackService.getStatus(),
  });

  const { data: peopleResponse, isLoading } = useQuery({
    queryKey: ['people'],
    queryFn: personService.getAll,
  });
  
  const updateMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string, updates: any }) => personService.update(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['people'] });
      setEditingId(null);
    }
  });

  const createMutation = useMutation({
    mutationFn: (newPerson: { name: string; email?: string; role?: string }) => personService.create(newPerson),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['people'] });
      setShowAddModal(false);
      setAddForm({ name: "", email: "", role: "" });
    }
  });

  const mergeMutation = useMutation({
    mutationFn: ({ primaryId, mergingIds }: { primaryId: string, mergingIds: string[] }) => 
      personService.merge(primaryId, mergingIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey:['people'] });
      setSelectedIds([]);
      setPrimaryId(null);
      setShowMergeConfirm(false);
      setIsMergingInProgress(false);
    },
    onError: () => {
      setIsMergingInProgress(false);
    }
  });

  const people = Array.isArray(peopleResponse) 
    ? peopleResponse 
    : (peopleResponse as any)?.results && Array.isArray((peopleResponse as any).results)
      ? (peopleResponse as any).results
      : (peopleResponse as any)?.data && Array.isArray((peopleResponse as any).data)
        ? (peopleResponse as any).data
        : [];

  const filteredPeople = people.filter((p: any) => 
    (p.name?.toLowerCase() || "").includes(searchQuery.toLowerCase()) ||
    (p.role?.toLowerCase() || p.title?.toLowerCase() || "").includes(searchQuery.toLowerCase())
  );

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleStartEdit = (person: any) => {
    setEditingId(person.id);
    setEditForm({ 
      name: person.name, 
      role: person.role || person.title || "",
      email: person.email || ""
    });
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditForm({ name: "", role: "", email: "" });
  };

  const handleSaveEdit = (id: string) => {
    updateMutation.mutate({
      id,
      updates: {
        name: editForm.name,
        role: editForm.role || editForm.name, // Fallback if role is empty
        email: editForm.email || ""
      }
    });
  };

  const handleMerge = () => {
    setShowMergeConfirm(true);
    // Auto-select the first as primary if none selected
    if (selectedIds.length > 0) setPrimaryId(selectedIds[0]);
  };

  const handleCreatePerson = (e: React.FormEvent) => {
    e.preventDefault();
    if (!addForm.name.trim()) return;
    createMutation.mutate({
      name: addForm.name,
      email: addForm.email || undefined,
      role: addForm.role || undefined
    });
  };

  const executeMerge = () => {
    if (!primaryId) return;
    setIsMergingInProgress(true);
    const mergingIds = selectedIds.filter(id => id !== primaryId);
    mergeMutation.mutate({ primaryId, mergingIds });
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-20 px-4 md:px-0">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900 mb-2">People</h1>
          <p className="text-slate-500 font-medium tracking-tight">Manage stakeholders and project contributors identified from transcripts.</p>
        </div>
        
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center gap-3 w-full">
          <div className="relative group w-full lg:w-80">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" />
            <input 
              type="text" 
              placeholder="Filter by name or role..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-white border border-slate-200 rounded-2xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all w-full shadow-sm font-bold"
            />
          </div>
          <div className="flex flex-wrap items-stretch gap-2.5">
            <Button 
              variant="secondary" 
              className="rounded-2xl h-[42px] border-slate-200 font-bold gap-2 hover:bg-slate-50 transition-colors shrink-0 justify-center px-4 animate-duration-100"
              onClick={() => setShowSlackImportModal(true)}
              disabled={!slackStatus?.connected}
            >
              <Slack className="w-4 h-4 text-[#4A154B]" />
              <span>Link/Import People</span>
            </Button>
            <Button 
              variant="secondary" 
              className="rounded-2xl h-[42px] border-slate-200 font-bold gap-2 hover:bg-slate-50 transition-colors shrink-0 justify-center px-4"
              onClick={() => setShowAddModal(true)}
            >
              <UserPlus className="w-4 h-4" />
              <span>Add Person</span>
            </Button>
          </div>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {selectedIds.length > 1 && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="bg-blue-600 rounded-[32px] p-6 text-white flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl shadow-blue-200 sticky top-4 z-40 border border-blue-400"
          >
            <div className="flex items-center gap-4 text-center md:text-left">
              <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm shrink-0">
                <Merge className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-black">{selectedIds.length} People Selected</h3>
                <p className="text-blue-100 text-sm font-bold opacity-80">You can deduplicate these entries by merging them into one unified profile.</p>
              </div>
            </div>
            <div className="flex items-center gap-3 w-full md:w-auto">
              <Button 
                variant="secondary" 
                onClick={() => setSelectedIds([])}
                className="flex-1 md:flex-none h-12 rounded-2xl text-slate-900 font-bold bg-white hover:bg-slate-50 border-none px-6"
              >
                Clear Selection
              </Button>
              <Button 
                onClick={handleMerge}
                className="flex-1 md:flex-none h-12 rounded-2xl bg-slate-900 hover:bg-black text-white font-black px-8 border-none gap-2"
              >
                Merge Profiles
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Add Person Modal */}
      <AnimatePresence>
        {showAddModal && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-white rounded-[40px] p-8 max-w-lg w-full shadow-2xl space-y-8 border border-slate-100"
            >
              <div className="space-y-2">
                <div className="w-16 h-16 bg-blue-50 rounded-3xl flex items-center justify-center mb-4">
                  <UserPlus className="w-8 h-8 text-blue-600" />
                </div>
                <h2 className="text-3xl font-black text-slate-900">Add New Person</h2>
                <p className="text-slate-500 font-bold leading-relaxed">
                  Manually add a stakeholder or team member who wasn't automatically identified.
                </p>
              </div>

              <form onSubmit={handleCreatePerson} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Full Name *</label>
                  <input 
                    type="text"
                    required
                    value={addForm.name}
                    onChange={(e) => setAddForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g. Satya Nadella"
                    className="w-full h-14 bg-slate-50 border border-slate-200 rounded-2xl px-5 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-bold"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Email Address</label>
                  <input 
                    type="email"
                    value={addForm.email}
                    onChange={(e) => setAddForm(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="e.g. satya@microsoft.com"
                    className="w-full h-14 bg-slate-50 border border-slate-200 rounded-2xl px-5 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-bold"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-1">Role / Title</label>
                  <input 
                    type="text"
                    value={addForm.role}
                    onChange={(e) => setAddForm(prev => ({ ...prev, role: e.target.value }))}
                    placeholder="e.g. Strategic Manager"
                    className="w-full h-14 bg-slate-50 border border-slate-200 rounded-2xl px-5 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-bold"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <Button 
                    type="button"
                    variant="secondary" 
                    className="flex-1 h-14 rounded-2xl font-bold bg-slate-50 hover:bg-slate-100 border-none"
                    onClick={() => {
                      setShowAddModal(false);
                      setAddForm({ name: "", email: "", role: "" });
                    }}
                    disabled={createMutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button 
                    type="submit"
                    className="flex-[2] h-14 rounded-2xl font-black bg-blue-600 hover:bg-blue-700 text-white shadow-xl shadow-blue-500/20 disabled:opacity-50 border-none"
                    disabled={createMutation.isPending || !addForm.name.trim()}
                  >
                    {createMutation.isPending ? "Creating..." : "Add Stakeholder"}
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 gap-4">
        {isLoading && (
          <div className="flex justify-center py-20">
            <div className="flex flex-col items-center gap-4">
              <div className="animate-spin rounded-full h-10 w-10 border-4 border-slate-200 border-t-blue-600"></div>
              <p className="text-slate-400 font-bold text-sm uppercase tracking-widest">Identifying people...</p>
            </div>
          </div>
        )}

        {!isLoading && filteredPeople.length === 0 && (
          <div className="bg-slate-50 rounded-[40px] border-2 border-dashed border-slate-200 p-20 text-center">
            <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-slate-100">
              <Users className="w-10 h-10 text-slate-300" />
            </div>
            <h3 className="text-xl font-black text-slate-900 mb-2">No people found</h3>
            <p className="text-slate-500 font-bold max-w-xs mx-auto">Try adjusting your filters or upload more transcripts to identify stakeholders.</p>
          </div>
        )}

        {filteredPeople.map((person: any, idx: number) => {
          const isSelected = selectedIds.includes(person.id || String(idx));
          const isEditing = editingId === person.id;

          return (
            <motion.div
              key={person.id || `person-${idx}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(idx * 0.03, 0.5) }}
            >
              <Card className={cn(
                "p-4 md:p-6 transition-all duration-300 border-2 rounded-[32px] group relative overflow-hidden",
                isSelected ? "border-blue-500 bg-blue-50/50 shadow-lg shadow-blue-500/5" : "border-slate-100 bg-white hover:border-slate-200"
              )}>
                <div className="flex items-center gap-4 md:gap-8 relative z-10">
                  <div className="flex items-center gap-4">
                    <div 
                      onClick={() => toggleSelect(person.id || String(idx))}
                      className={cn(
                        "w-6 h-6 rounded-lg border-2 cursor-pointer flex items-center justify-center transition-all",
                        isSelected ? "bg-blue-600 border-blue-600" : "border-slate-200 hover:border-slate-300"
                      )}
                    >
                      {isSelected && <Check className="w-4 h-4 text-white" />}
                    </div>
                    <Avatar name={person.name} size="xl" className="ring-4 ring-slate-50 shrink-0" />
                  </div>

                  <div className="flex-1 grid grid-cols-1 md:grid-cols-12 items-center gap-4 md:gap-8">
                    <div className="md:col-span-5 space-y-1">
                      {isEditing ? (
                        <div className="space-y-3">
                          <div>
                            <label className="text-[8px] font-black uppercase tracking-widest text-slate-400 ml-1">Full Name</label>
                            <input 
                              type="text"
                              value={editForm.name}
                              onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                              className="w-full text-sm font-bold text-slate-900 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                              autoFocus
                              placeholder="Full Name"
                            />
                          </div>
                          <div>
                            <label className="text-[8px] font-black uppercase tracking-widest text-slate-400 ml-1">Role / Title</label>
                            <input 
                              type="text"
                              value={editForm.role}
                              onChange={(e) => setEditForm(prev => ({ ...prev, role: e.target.value }))}
                              placeholder="Title / Role (e.g. CEO, Product Manager)"
                              className="w-full text-xs font-bold text-slate-500 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                            />
                          </div>
                          <div>
                            <label className="text-[8px] font-black uppercase tracking-widest text-slate-400 ml-1">Email Address</label>
                            <input 
                              type="email"
                              value={editForm.email}
                              onChange={(e) => setEditForm(prev => ({ ...prev, email: e.target.value }))}
                              placeholder="Email Address (required for Gmail nudges)"
                              className="w-full text-xs font-bold text-slate-500 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                            />
                          </div>
                        </div>
                      ) : (
                        <>
                          <h3 className="text-lg font-black text-slate-900 leading-tight group-hover:text-blue-600 transition-colors">{person.name}</h3>
                          <div className="space-y-1">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{person.role || person.title || "No role specified"}</p>
                            {person.email ? (
                              <p className="text-xs font-bold text-slate-600 flex items-center gap-1.5">
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider">Email:</span>
                                <span className="text-slate-700 bg-slate-50 px-2 py-0.5 rounded-lg border border-slate-100">{person.email}</span>
                              </p>
                            ) : (
                              <p className="text-[11px] font-bold text-slate-400/80 italic">No email linked</p>
                            )}
                          </div>
                        </>
                      )}
                    </div>

                    <div className="md:col-span-3 flex items-center">
                      {person.slack_id ? (
                        <a 
                          href={`https://slack.com/app_redirect?channel=${person.slack_id}`} 
                          target="_blank" 
                          rel="noreferrer"
                          className="flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-slate-100 hover:bg-[#4A154B] hover:text-white text-slate-600 transition-all font-black text-[10px] uppercase tracking-widest cursor-pointer"
                        >
                          <Slack className="w-4 h-4 text-[#4A154B]" />
                          Slack
                          <ExternalLink className="w-3 h-3 opacity-50" />
                        </a>
                      ) : slackStatus?.connected ? (
                        <Button
                          variant="secondary"
                          onClick={() => {
                            setSelectedPersonToLink(person);
                            setIsManualLinkOpen(true);
                          }}
                          className="flex items-center gap-2 px-5 h-10 rounded-2xl border-slate-200 text-purple-700 hover:text-white hover:bg-[#4A154B] hover:border-[#4A154B] transition-all font-black text-[10px] uppercase tracking-widest bg-white"
                        >
                          <Slack className="w-4 h-4 text-[#4A154B]" />
                          Link Slack
                        </Button>
                      ) : (
                        <div className="flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-slate-50 text-slate-300 font-black text-[10px] uppercase tracking-widest cursor-not-allowed">
                          <Slack className="w-4 h-4 opacity-30" />
                          Slack
                        </div>
                      )}
                    </div>

                    <div className="md:col-span-4 flex items-center justify-end gap-2">
                      {isEditing ? (
                        <>
                          <Button 
                            variant="secondary" 
                            size="sm" 
                            onClick={handleCancelEdit}
                            className="rounded-xl font-bold border-slate-200 h-10 px-4"
                          >
                            <X className="w-4 h-4 mr-2" />
                            Cancel
                          </Button>
                          <Button 
                            size="sm" 
                            onClick={() => handleSaveEdit(person.id)}
                            disabled={updateMutation.isPending}
                            className="rounded-xl font-black bg-blue-600 hover:bg-blue-700 text-white h-10 px-5 shadow-lg shadow-blue-500/20 disabled:opacity-50"
                          >
                            <Save className={cn("w-4 h-4 mr-2", updateMutation.isPending && "animate-pulse")} />
                            {updateMutation.isPending ? "Saving..." : "Save"}
                          </Button>
                        </>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={() => handleStartEdit(person)}
                            className="rounded-xl font-black text-[10px] uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all text-slate-400 hover:text-blue-600 hover:bg-blue-50 h-10 px-4"
                          >
                            <Edit2 className="w-4 h-4 mr-2" />
                            Edit Profile
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                {/* Decorative background element for hovered state */}
                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-32 h-32 bg-blue-500/5 blur-[60px] rounded-full pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity" />
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Merge Selection Modal */}
      <AnimatePresence>
        {showMergeConfirm && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-white rounded-[40px] p-8 max-w-xl w-full shadow-2xl space-y-8 border border-slate-100"
            >
              <div className="space-y-2">
                <div className="w-16 h-16 bg-blue-50 rounded-3xl flex items-center justify-center mb-4">
                  <Merge className="w-8 h-8 text-blue-600" />
                </div>
                <h2 className="text-3xl font-black text-slate-900">Choose Primary Profile</h2>
                <p className="text-slate-500 font-bold leading-relaxed">
                  Select the profile you want to keep. All other selected profiles will be merged into this one.
                </p>
              </div>

              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                {people
                  .filter((p: any) => selectedIds.includes(p.id))
                  .map((person: any) => (
                    <div 
                      key={person.id}
                      onClick={() => setPrimaryId(person.id)}
                      className={cn(
                        "flex items-center gap-4 p-4 rounded-2xl border-2 transition-all cursor-pointer",
                        primaryId === person.id 
                          ? "border-blue-500 bg-blue-50/50 ring-4 ring-blue-500/10" 
                          : "border-slate-100 bg-white hover:border-slate-200"
                      )}
                    >
                      <div className={cn(
                        "w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all",
                        primaryId === person.id ? "bg-blue-600 border-blue-600" : "border-slate-300"
                      )}>
                        {primaryId === person.id && <div className="w-2 h-2 bg-white rounded-full" />}
                      </div>
                      <Avatar name={person.name} size="md" />
                      <div>
                        <h4 className="font-black text-slate-900">{person.name}</h4>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                          {person.role || person.title || "No role"}
                        </p>
                      </div>
                      {primaryId === person.id && (
                        <div className="ml-auto">
                          <Check className="w-5 h-5 text-blue-600" />
                        </div>
                      )}
                    </div>
                  ))}
              </div>

              <div className="flex gap-3 pt-4">
                <Button 
                  variant="secondary" 
                  className="flex-1 h-14 rounded-2xl font-bold bg-slate-50 hover:bg-slate-100 h-10 py-0"
                  onClick={() => {
                    setShowMergeConfirm(false);
                    setPrimaryId(null);
                  }}
                  disabled={isMergingInProgress}
                >
                  Cancel
                </Button>
                <Button 
                  className="flex-[2] h-14 rounded-2xl font-black bg-blue-600 hover:bg-blue-700 text-white shadow-xl shadow-blue-500/20 disabled:opacity-50"
                  onClick={executeMerge}
                  disabled={!primaryId || isMergingInProgress}
                >
                  {isMergingInProgress ? "Merging Profiles..." : "Complete Merge"}
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      <LinkSlackPeopleModal isOpen={showSlackImportModal} onClose={() => setShowSlackImportModal(false)} />
      <ManualSlackLinkModal 
        isOpen={isManualLinkOpen} 
        onClose={() => {
          setIsManualLinkOpen(false);
          setSelectedPersonToLink(null);
        }} 
        person={selectedPersonToLink}
      />
    </div>
  );
};

