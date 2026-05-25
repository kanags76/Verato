import { useState } from "react";
import { motion } from "motion/react";
import { Card } from "@/src/components/ui/Card";
import { Button } from "@/src/components/ui/Button";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { managerService, personService } from "@/src/lib/api/services";
import { authService } from "@/src/lib/api/auth";
import { Loader2, Trash2, CheckCircle2, X, Plus } from "lucide-react";

export const DelegationManagement = () => {
  const queryClient = useQueryClient();
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['delegations'],
    queryFn: () => managerService.getAll(),
  });

  const { data: userProfile } = useQuery({
    queryKey: ['profile'],
    queryFn: () => authService.getProfile(),
  });

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ['persons'],
    queryFn: () => personService.getAll(),
  });

  const addDelegateMutation = useMutation({
    mutationFn: (userId: string) => managerService.addDelegate(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['delegations'] });
      setSelectedUserId(null);
      setShowDropdown(false);
    }
  });

  const acceptMutation = useMutation({
    mutationFn: (id: string) => managerService.acceptDelegation(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['delegations'] })
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => managerService.deleteDelegation(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['delegations'] })
  });

  if (isLoading || usersLoading) return <Loader2 className="w-8 h-8 animate-spin mx-auto text-slate-400" />;

  const availableUsers = (users || []).filter(u => 
      !(data?.delegates || []).some(d => d.delegate_user.id === u.id) &&
      (u as any).is_platform_user === true &&
      (u as any).organisation === userProfile?.organisation.id
  );

  return (
    <div className="space-y-8 mt-6">
      <div className="space-y-4">
        <h3 className="text-lg font-black text-slate-900">My Delegates</h3>
        <div className="space-y-2">
            {(data?.delegates || []).map((d: any) => (
                <div key={d.id} className="flex items-center justify-between p-4 bg-slate-50 border border-slate-100 rounded-2xl">
                    <span className="font-bold text-slate-700">{d.delegate_user.name || d.delegate_user.email}</span>
                    <span className="text-xs font-black uppercase text-slate-400">{d.status}</span>
                    <Button variant="secondary" size="sm" onClick={() => deleteMutation.mutate(d.id)}><Trash2 className="w-4 h-4 text-rose-500"/></Button>
                </div>
            ))}
        </div>
        <div className="relative">
            <div 
                className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm font-medium cursor-pointer flex justify-between items-center"
                onClick={() => setShowDropdown(!showDropdown)}
            >
                {selectedUserId ? availableUsers.find(u => ((u as any).user_id || u.id) === selectedUserId)?.name : "Select a team member..."}
                <Plus className="w-4 h-4 text-slate-400"/>
            </div>
            {showDropdown && (
                <div className="absolute w-full mt-2 z-10 bg-white border border-slate-100 rounded-2xl shadow-xl max-h-60 overflow-y-auto">
                    {availableUsers.map(u => (
                        <div 
                            key={u.id}
                            className="px-4 py-3 hover:bg-slate-50 cursor-pointer text-sm font-medium text-slate-700"
                            onClick={() => { setSelectedUserId((u as any).user_id || u.id); setShowDropdown(false); }}
                        >
                            {u.name}
                        </div>
                    ))}
                </div>
            )}
        </div>
        {selectedUserId && (
            <Button onClick={() => addDelegateMutation.mutate(selectedUserId)} className="w-full">
                Add Delegate
            </Button>
        )}
      </div>

      {(data?.managing_on_behalf_of || []).length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-black text-slate-900">Managing on behalf of</h3>
          <div className="space-y-2">
              {(data?.managing_on_behalf_of || []).map((m: any) => (
                  <div key={m.id} className="flex items-center justify-between p-4 bg-slate-50 border border-slate-100 rounded-2xl">
                      <span className="font-bold text-slate-700">{m.delegator_user.name || m.delegator_user.email}</span>
                      <span className="text-xs font-black uppercase text-slate-400">{m.status}</span>
                      {m.status === 'pending' && (
                          <div className="flex gap-2">
                              <Button variant="secondary" size="sm" onClick={() => acceptMutation.mutate(m.id)}><CheckCircle2 className="w-4 h-4 text-emerald-500"/></Button>
                              <Button variant="secondary" size="sm" onClick={() => deleteMutation.mutate(m.id)}><X className="w-4 h-4 text-rose-500"/></Button>
                          </div>
                      )}
                  </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};
