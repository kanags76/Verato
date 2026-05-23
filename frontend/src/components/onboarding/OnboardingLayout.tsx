import React from 'react';
import { motion } from 'motion/react';

interface OnboardingLayoutProps {
  currentStep: number;
  totalSteps: number;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export const OnboardingLayout = ({ 
  currentStep, 
  totalSteps, 
  title, 
  subtitle, 
  children 
}: OnboardingLayoutProps) => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-xl"
      >
        {/* Step Indicator */}
        <div className="flex justify-center gap-2 mb-12">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div 
              key={i}
              className={`h-1.5 rounded-full transition-all duration-500 ${
                i < currentStep ? 'w-8 bg-blue-600' : 
                i === currentStep - 1 ? 'w-12 bg-blue-600' : 
                'w-8 bg-slate-200'
              }`}
            />
          ))}
        </div>

        <div className="text-center mb-8">
          <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
            {title}
          </h1>
          {subtitle && (
            <p className="text-slate-500 font-medium">{subtitle}</p>
          )}
        </div>

        {children}

        <div className="mt-8 text-center">
          <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
            Step {currentStep} of {totalSteps} — Setting up your workspace
          </p>
        </div>
      </motion.div>
    </div>
  );
};
