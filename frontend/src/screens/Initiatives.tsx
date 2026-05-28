import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { initiativeService, tagService } from "../lib/api/services";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { RefreshCw, Loader2, Edit2 } from "lucide-react";
import { cn } from "@/src/lib/utils";
import { format } from "date-fns";

export const Initiatives = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [isManageTagsOpen, setIsManageTagsOpen] = useState(false);

    const { data: initiatives, isLoading: isInitiativesLoading } = useQuery({
        queryKey: ['initiatives'],
        queryFn: initiativeService.getAll,
    });

    const refreshMutation = useMutation({
        mutationFn: (id: string) => initiativeService.generateSummary(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['initiatives'] });
        },
    });

    return (
        <div className="max-w-7xl mx-auto space-y-8 pb-20 p-6">
            <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-black tracking-tight text-slate-900">Initiatives</h1>
                  <p className="text-slate-500 font-medium">Strategic efforts and their progress.</p>
                </div>
                <Button variant="secondary" onClick={() => setIsManageTagsOpen(true)}>Manage Tags</Button>
            </div>

            {isInitiativesLoading ? (
                <div className="flex justify-center p-20"><Loader2 className="animate-spin w-10 h-10 text-blue-600" /></div>
            ) : initiatives && initiatives.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {initiatives.map((ini) => (
                        <Card key={ini.id} className="p-6">
                           <div className="flex justify-between items-start mb-4">
                               <div>
                                   <h2 className="text-xl font-black">{ini.label}</h2>
                                   <p className="text-slate-500 text-sm mt-1">{ini.description}</p>
                               </div>
                                <Button size="sm" variant="ghost" onClick={() => refreshMutation.mutate(ini.id)} disabled={refreshMutation.isPending}>
                                   {refreshMutation.isPending ? <Loader2 className="animate-spin w-4 h-4"/> : <RefreshCw className="w-4 h-4 text-slate-400" />}
                               </Button>
                           </div>
                           
                           {/* View Commitments Button */}
                           <Button 
                             variant="secondary" 
                             className="w-full text-xs font-black uppercase mb-4" 
                             onClick={() => navigate(`/initiatives/${ini.id}`)}
                           >
                            View Details
                           </Button>
                           
                           {/* Status Pill Row */}
                           <div className="flex flex-wrap gap-2 mb-4">
                               {ini.counts.active > 0 && <span className="bg-blue-100 text-blue-800 text-[10px] uppercase font-black px-2 py-1 rounded-full">Active: {ini.counts.active}</span>}
                               {ini.counts.at_risk > 0 && <span className="bg-amber-100 text-amber-800 text-[10px] uppercase font-black px-2 py-1 rounded-full">At Risk: {ini.counts.at_risk}</span>}
                               {ini.counts.escalated > 0 && <span className="bg-rose-100 text-rose-800 text-[10px] uppercase font-black px-2 py-1 rounded-full">Escalated: {ini.counts.escalated}</span>}
                               {ini.counts.done > 0 && <span className="bg-emerald-100 text-emerald-800 text-[10px] uppercase font-black px-2 py-1 rounded-full">Done: {ini.counts.done}</span>}
                           </div>

                           {ini.ai_summary && (
                               <div className="bg-slate-50 p-4 rounded-xl text-sm leading-relaxed text-slate-700">
                                   {ini.ai_summary}
                                   <div className="text-[10px] text-slate-400 mt-2">Summary updated: {ini.ai_summary_at ? format(new Date(ini.ai_summary_at), 'PPPp') : 'N/A'}</div>
                               </div>
                           )}
                        </Card>
                    ))}
                </div>
            ) : (
                <div className="text-center p-20 bg-slate-50 rounded-3xl border-2 border-dashed text-slate-500">
                    No strategic initiatives yet. Promote a tag to an initiative from the Tags tab.
                </div>
            )}
            
            {/* Manage Tags Modal - Simplified for now */}
            {isManageTagsOpen && <ManageTagsModal onClose={() => setIsManageTagsOpen(false)} />}
        </div>
    );
};

const ManageTagsModal = ({ onClose }: { onClose: () => void }) => {
    const { data: tags, isLoading } = useQuery({
        queryKey: ['tags-manage'],
        queryFn: tagService.searchTags,
    });
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<'active' | 'unused'>('active');
    const [editingTagId, setEditingTagId] = useState<string | null>(null);
    const [editLabel, setEditLabel] = useState("");

    const updateMutation = useMutation({
        mutationFn: ({ id, payload }: { id: string, payload: any }) => tagService.updateTag(id, payload),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tags-manage'] }),
    });

    const mergeMutation = useMutation({
        mutationFn: ({ id, intoLabel }: { id: string, intoLabel: string }) => tagService.mergeTag(id, intoLabel),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tags-manage'] }),
    });

    const allTags = tags || [];
    const activeTags = allTags.filter((t: any) => t.usage > 0);
    const unusedTags = allTags.filter((t: any) => t.usage === 0);

    return (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-6 z-[100]">
            <Card className="w-full max-w-2xl p-6 max-h-[85vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-black">Manage Tags</h2>
                    <Button variant="ghost" onClick={onClose}>Close</Button>
                </div>
                
                <div className="flex gap-4 mb-6 border-b border-slate-200">
                    <button className={cn("pb-2 font-black text-sm", activeTab === 'active' ? "border-b-2 border-slate-900" : "text-slate-500")} onClick={() => setActiveTab('active')}>Active ({activeTags.length})</button>
                    <button className={cn("pb-2 font-black text-sm", activeTab === 'unused' ? "border-b-2 border-slate-900" : "text-slate-500")} onClick={() => setActiveTab('unused')}>Unused ({unusedTags.length})</button>
                </div>

                {isLoading ? <Loader2 className="animate-spin"/> : (
                    activeTab === 'active' ? (
                        <div className="space-y-3">
                            {activeTags.map((tag: any) => (
                                <div key={tag.id} className="grid grid-cols-[1fr,auto] items-center gap-3 bg-white border border-slate-100 p-3 rounded-2xl shadow-sm">
                                    <div className="flex items-center gap-2">
                                        {editingTagId === tag.id ? (
                                            <input 
                                                className="font-bold text-sm border-b border-blue-500 focus:outline-none" 
                                                value={editLabel} 
                                                onChange={(e) => setEditLabel(e.target.value)}
                                            />
                                        ) : (
                                            <div className="font-bold text-sm truncate">{tag.label}</div>
                                        )}
                                        {editingTagId === tag.id ? (
                                            <div className="flex gap-1">
                                                <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => {
                                                    if(editLabel && editLabel !== tag.label) updateMutation.mutate({ id: tag.id, payload: { label: editLabel } });
                                                    setEditingTagId(null);
                                                }}>Save</Button>
                                                <Button size="sm" variant="ghost" className="h-6 w-6 p-0" onClick={() => setEditingTagId(null)}>X</Button>
                                            </div>
                                        ) : (
                                            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => {
                                                setEditingTagId(tag.id);
                                                setEditLabel(tag.label);
                                            }}><Edit2 className="w-3 h-3 text-slate-400"/></Button>
                                        )}
                                        <div className="text-[10px] font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{tag.usage}</div>
                                    </div>
                                    
                                    <div className="flex items-center gap-2 justify-end">
                                    <Button variant={tag.is_initiative ? "primary" : "secondary"} size="sm" className={cn("text-[10px] font-black uppercase rounded-full h-8", tag.is_initiative ? "bg-blue-600 text-white" : "border-slate-300 text-slate-600")} onClick={() => {
                                        if (tag.is_initiative) {
                                            updateMutation.mutate({ id: tag.id, payload: { is_initiative: false } });
                                        } else {
                                            const desc = prompt("Enter description for initiative");
                                            updateMutation.mutate({ id: tag.id, payload: { is_initiative: true, description: desc || '' } });
                                        }
                                    }}>
                                        {tag.is_initiative ? "Initiative" : "Make Initiative"}
                                    </Button>

                                    <select className="text-xs bg-slate-100 p-2 rounded-xl h-8" onChange={(e) => {
                                        if (e.target.value) mergeMutation.mutate({ id: tag.id, intoLabel: e.target.value });
                                        e.target.value = "";
                                    }}>
                                        <option value="">Merge into...</option>
                                        {activeTags.filter(t => t.id !== tag.id).map(t => <option key={t.id} value={t.label}>{t.label}</option>)}
                                    </select>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="bg-slate-50 p-4 rounded-xl text-sm leading-relaxed text-slate-700">
                           {unusedTags.map(t => t.label).join(", ")}
                        </div>
                    )
                )}
            </Card>
        </div>
    )
}


export default Initiatives;