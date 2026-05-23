import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { 
  X, 
  HelpCircle, 
  ChevronRight, 
  ChevronLeft, 
  CheckCircle2, 
  AlertCircle,
  Loader2,
  MessageSquare
} from "lucide-react";
import { meetingService } from "@/src/lib/api/services";
import { Clarification } from "@/src/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "./ui/Button";
import { cn } from "@/src/lib/utils";

interface ClarificationModalProps {
  meetingId: string;
  onClose: () => void;
}

export const ClarificationModal = ({ meetingId, onClose }: ClarificationModalProps) => {
  const queryClient = useQueryClient();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: clarifications, isLoading } = useQuery({
    queryKey: ['clarifications', meetingId],
    queryFn: () => meetingService.getClarifications(meetingId)
  });

  const submitMutation = useMutation({
    mutationFn: (answersPayload: { id: string, answer: string }[]) => 
      meetingService.submitClarifications(meetingId, answersPayload),
    onSuccess: () => {
      // Optimistically update status to trigger fast polling
      queryClient.setQueryData(['meeting', meetingId], (old: any) => {
        if (!old) return old;
        return { ...old, status: 'processing', processing_status: 'processing' };
      });
      queryClient.setQueryData(['meetings'], (old: any[] | undefined) => {
        return old?.map(m => m.id === meetingId ? { ...m, status: 'processing', processing_status: 'processing' } : m);
      });
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] });
      onClose();
      alert("Clarifications submitted! Gemini is resuming extraction.");
    },
    onError: (error: any) => {
      if (error.response?.status === 409) {
        setErrorMsg("This meeting is no longer awaiting clarification.");
      } else if (error.response?.status === 400 && error.response?.data?.missing) {
        setErrorMsg(`Missing answers for: ${error.response.data.missing.join(", ")}`);
      } else {
        setErrorMsg("Failed to submit clarifications. Please try again.");
      }
    }
  });

  const handleNext = () => {
    if (clarifications && currentIndex < clarifications.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handleBack = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleSubmit = () => {
    if (!clarifications) return;
    const payload = clarifications.map(c => ({
      id: c.id,
      answer: answers[c.id] || ""
    }));
    submitMutation.mutate(payload);
  };

  const currentClarification = clarifications?.[currentIndex];
  const isLast = clarifications ? currentIndex === clarifications.length - 1 : false;
  const progress = clarifications ? ((currentIndex + 1) / clarifications.length) * 100 : 0;

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
        <div className="bg-white rounded-[32px] p-12 flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
          <p className="font-black text-slate-900">Loading Queries...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-md p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="bg-white w-full max-w-2xl rounded-[40px] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="p-8 border-b border-slate-50 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
              <HelpCircle className="w-6 h-6" />
            </div>
            <div className="space-y-0.5">
              <h2 className="text-xl font-black text-slate-900 tracking-tight">Gemini Clarification</h2>
              <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">
                Question {currentIndex + 1} of {clarifications?.length}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="h-1.5 bg-slate-100 w-full overflow-hidden">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            className="h-full bg-blue-600"
          />
        </div>

        {/* Content */}
        <div className="p-10 flex-1 overflow-y-auto custom-scrollbar">
          <AnimatePresence mode="wait">
            {currentClarification && (
              <motion.div
                key={currentClarification.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-8"
              >
                <div className="space-y-4">
                  <h3 className="text-2xl font-black text-slate-900 leading-tight">
                    {currentClarification.question}
                  </h3>
                  {currentClarification.context && (
                    <div className="p-6 bg-slate-50 border border-slate-100 rounded-[28px] relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-4 opacity-5">
                        <MessageSquare className="w-12 h-12" />
                      </div>
                      <p className="text-slate-500 text-sm font-bold leading-relaxed italic relative z-10">
                        "{currentClarification.context}"
                      </p>
                    </div>
                  )}
                </div>

                <div className="space-y-3">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Your Answer</label>
                  <textarea
                    value={answers[currentClarification.id] || ""}
                    onChange={(e) => setAnswers(prev => ({ ...prev, [currentClarification.id]: e.target.value }))}
                    placeholder="Provide details to help Gemini resolve this..."
                    className="w-full bg-white border-2 border-slate-100 rounded-[24px] px-6 py-5 font-bold text-slate-900 outline-none focus:border-blue-400 transition-all min-h-[140px] shadow-sm resize-none"
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {errorMsg && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-center gap-3 text-rose-600 text-sm font-bold"
            >
              <AlertCircle className="w-5 h-5" />
              {errorMsg}
            </motion.div>
          )}
        </div>

        {/* Footer */}
        <div className="p-8 border-t border-slate-50 flex items-center justify-between bg-slate-50/30">
          <Button
            variant="ghost"
            onClick={handleBack}
            disabled={currentIndex === 0}
            className="font-black text-slate-500 hover:text-slate-900 disabled:opacity-30"
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Back
          </Button>

          <div className="flex items-center gap-3">
            {isLast ? (
              <Button
                onClick={handleSubmit}
                disabled={submitMutation.isPending || (clarifications && Object.keys(answers).length < clarifications.length)}
                className="bg-slate-900 hover:bg-black text-white px-8 h-12 rounded-2xl font-black shadow-lg shadow-slate-900/20 border-none min-w-[140px]"
              >
                {submitMutation.isPending ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    Submit Answers
                    <CheckCircle2 className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            ) : (
              <Button
                onClick={handleNext}
                className="bg-blue-600 hover:bg-blue-700 text-white px-8 h-12 rounded-2xl font-black shadow-lg shadow-blue-500/20 border-none min-w-[120px]"
              >
                Next
                <ChevronRight className="w-4 h-4 ml-2" />
              </Button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};
