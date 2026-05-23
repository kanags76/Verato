import React from 'react';
import { useNavigate } from 'react-router-dom';
import { OnboardingLayout } from '../../components/onboarding/OnboardingLayout';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { MessageSquare, Bell, ShieldCheck, CheckCircle2, Loader2, Slack, ChevronRight } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { slackService } from '../../lib/api/services';

export const ConnectSlack = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: slackStatus, isLoading: isLoadingSlack } = useQuery({
    queryKey: ['slack-status'],
    queryKeyHashFn: () => 'slack-status',
    queryFn: () => slackService.getStatus(),
  });

  const handleConnectSlack = () => {
    const API_URL = (import.meta.env.VITE_API_URL || 'https://api.verato.twocents.ai/api/v1').replace(/\/$/, '');
    const token = localStorage.getItem('accessToken');
    const url = `${API_URL}/slack/oauth/start/?auth=${token}`;
    
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    
    const popup = window.open(
      url,
      'Connect to Slack',
      `width=${width},height=${height},left=${left},top=${top},status=no,menubar=no,toolbar=no`
    );

    if (popup) {
      const timer = setInterval(() => {
        if (popup.closed) {
          clearInterval(timer);
          queryClient.invalidateQueries({ queryKey: ['slack-status'] });
        }
      }, 1000);
    }
  };

  const handleNextStep = () => {
    navigate('/onboarding/import');
  };

  const handleSkip = () => {
    navigate('/onboarding/import');
  };

  return (
    <OnboardingLayout 
      currentStep={1}
      totalSteps={2}
      title="Connect Slack"
      subtitle="Verato uses Slack to nudge commitment owners so you don't have to."
    >
      <Card className="p-8 shadow-xl border-slate-200">
        <div className="space-y-8">
          <div className="bg-slate-50 rounded-2xl p-6 border border-slate-100">
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-4">Permissions Required</h3>
            <div className="space-y-4">
              <div className="flex gap-4">
                <div className="w-10 h-10 bg-white rounded-lg border border-slate-200 flex items-center justify-center shrink-0 shadow-sm">
                  <MessageSquare className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-900">Direct Messages</p>
                  <p className="text-xs text-slate-500">Send nudge messages directly to your team members.</p>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-10 h-10 bg-white rounded-lg border border-slate-200 flex items-center justify-center shrink-0 shadow-sm">
                  <Bell className="w-5 h-5 text-amber-500" />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-900">Button Responses</p>
                  <p className="text-xs text-slate-500">Capture when owners mark tasks 'done' from Slack.</p>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="w-10 h-10 bg-white rounded-lg border border-slate-200 flex items-center justify-center shrink-0 shadow-sm">
                  <ShieldCheck className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-900">No Channel Access</p>
                  <p className="text-xs text-slate-500 font-medium">Verato cannot read your private or public channels.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            {isLoadingSlack ? (
              <Button disabled className="w-full h-14 text-lg font-bold flex items-center justify-center gap-3">
                <Loader2 className="w-5 h-5 animate-spin" />
                Checking Slack status...
              </Button>
            ) : slackStatus?.connected ? (
              <div className="space-y-4">
                <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-xl flex items-center gap-3 text-emerald-700">
                  <CheckCircle2 className="w-6 h-6 shrink-0" />
                  <div>
                    <p className="text-sm font-black uppercase tracking-tight">Slack Connected</p>
                    <p className="text-xs font-bold opacity-80">Linked to: {slackStatus.workspace_name}</p>
                  </div>
                </div>
                <Button 
                  onClick={handleNextStep}
                  className="w-full h-14 bg-blue-600 hover:bg-blue-700 text-white text-lg font-bold shadow-lg shadow-blue-200 flex items-center justify-center gap-3"
                >
                  Continue to Next Step
                  <ChevronRight className="w-5 h-5" />
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <Button 
                  onClick={handleConnectSlack}
                  className="w-full h-14 bg-[#4A154B] hover:bg-[#3b113c] text-white text-lg font-bold border-none shadow-lg shadow-purple-200 flex items-center justify-center gap-3"
                >
                  <Slack className="w-6 h-6" />
                  Connect Slack
                </Button>
                
                <button 
                  onClick={handleSkip}
                  className="w-full py-2 text-xs font-bold text-slate-400 hover:text-slate-600 transition-colors"
                >
                  Skip for now — connect later from Settings
                </button>
              </div>
            )}
          </div>
        </div>
      </Card>

      <div className="mt-8 flex justify-center gap-6">
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
          Secure OAuth 2.0
        </div>
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
          Revocable anytime
        </div>
      </div>
    </OnboardingLayout>
  );
};
