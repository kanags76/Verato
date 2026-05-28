import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { initiativeService, commitmentService } from "../lib/api/services";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Loader2, ArrowLeft } from "lucide-react";
import { cn } from "@/src/lib/utils";
import { format } from "date-fns";

export const InitiativeDetail = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const { data: initiatives, isLoading: isLoadingInitiatives } = useQuery({
        queryKey: ['initiatives'],
        queryFn: initiativeService.getAll,
    });

    const initiative = initiatives?.find((i: any) => i.id === id);

    const { data: commitmentsRaw, isLoading: isLoadingCommitments } = useQuery({
        queryKey: ['commitments', initiative?.label],
        queryFn: () => commitmentService.getAll({ tag: initiative.label }),
        enabled: !!initiative?.label,
    });

    const commitments = commitmentsRaw?.map((c: any) => ({
        ...c,
        title: String(c.normalised_text || c.title || c.text || "Untitled Commitment"),
        ownerName: String(c.owner_name || c.owner || c.assigned_to || "Unassigned"),
        deadline: String(c.deadline || c.due_date || c.target_date || ""),
        status: String(c.status || "on_track").toLowerCase(),
        priority: String(c.priority || "").toUpperCase(),
    }));

    if (isLoadingInitiatives) {
        return <div className="flex justify-center p-20"><Loader2 className="animate-spin w-10 h-10 text-blue-600" /></div>;
    }

    if (!initiative) {
        return <div className="p-20 text-center text-slate-500">Initiative not found.</div>;
    }

    return (
        <div className="max-w-5xl mx-auto p-6 space-y-8">
            <Button variant="ghost" className="mb-4" onClick={() => navigate(-1)}>
                <ArrowLeft className="w-4 h-4 mr-2" /> Back
            </Button>

            <div>
                <h1 className="text-3xl font-black text-slate-900">{initiative.label}</h1>
                <p className="text-slate-500 mt-2">{initiative.description}</p>
            </div>

            {/* Momentum Placeholder */}
            <Card className="p-6">
                <h2 className="text-lg font-black mb-4">Momentum History</h2>
                <div className="h-40 bg-slate-50 rounded-xl flex items-center justify-center text-slate-400 border border-dashed">
                    Momentum visualization placeholder
                </div>
            </Card>

            {/* Commitments List */}
            <div>
                <h2 className="text-xl font-black mb-4">Commitments</h2>
                {isLoadingCommitments ? (
                    <div className="flex justify-center p-10"><Loader2 className="animate-spin" /></div>
                ) : (
                    <div className="space-y-3">
                        {commitments?.map((c: any) => (
                            <div 
                                key={c.id} 
                                className="p-4 bg-white border border-slate-100 rounded-2xl shadow-sm flex items-center justify-between cursor-pointer hover:border-blue-500 transition-all"
                                onClick={() => navigate(`/commitments/${c.id}`)}
                            >
                              <div className="flex items-center gap-4">
                                <div className={cn("w-1 h-8 rounded-full", c.priority === "HIGH" ? "bg-rose-500" : c.priority === "MED" ? "bg-amber-500" : "bg-slate-300")} />
                                <div>
                                  <div className="font-bold text-sm text-slate-900">{c.title}</div>
                                  <div className="text-xs text-slate-500 flex items-center gap-2">
                                    <span>{c.ownerName}</span>
                                    <span>•</span>
                                    <span>{c.deadline ? format(new Date(c.deadline), "MMM d") : 'No deadline'}</span>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge variant={c.status === 'done' ? 'success' : 'neutral'} className="h-6">
                                  {c.status.replace("_", " ")}
                                </Badge>
                              </div>
                            </div>
                        ))}
                        {commitments?.length === 0 && <p className="text-slate-500 text-center py-10">No commitments found for this initiative.</p>}
                    </div>
                )}
            </div>
        </div>
    );
};
