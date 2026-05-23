import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, ArrowRight } from 'lucide-react';
import { Button } from './ui/Button';

interface ImportSuccessModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateToDashboard?: () => void;
}

export const ImportSuccessModal = ({ isOpen, onClose, onNavigateToDashboard }: ImportSuccessModalProps) => {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[300] flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
        />

        {/* Modal Container */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl overflow-hidden p-8 text-center flex flex-col items-center"
        >
          <div className="w-20 h-20 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mb-6">
            <CheckCircle2 className="w-12 h-12" />
          </div>

          <h3 className="text-2xl font-black text-slate-900 tracking-tight mb-3">
            Import Done!
          </h3>

          <p className="text-slate-600 font-medium text-sm leading-relaxed mb-8">
            All import is in the dashboard and marked as <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-xs uppercase tracking-wider">Review</span> for you to review and accept.
          </p>

          <Button 
            onClick={() => {
              if (onNavigateToDashboard) {
                onNavigateToDashboard();
              } else {
                onClose();
              }
            }}
            className="w-full h-12 font-black rounded-xl bg-slate-900 hover:bg-slate-800 text-white border-none flex items-center justify-center gap-2"
          >
            {onNavigateToDashboard ? (
              <>
                <span>Go to Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </>
            ) : (
              <span>Close</span>
            )}
          </Button>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
