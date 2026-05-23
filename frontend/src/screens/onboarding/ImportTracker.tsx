import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { OnboardingLayout } from '../../components/onboarding/OnboardingLayout';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { 
  FileUp, 
  X, 
  FileText, 
  Sheet, 
  ArrowRight, 
  Loader2,
  AlertCircle
} from 'lucide-react';
import { importService, meetingService } from '../../lib/api/services';
import { ImportSuccessModal } from '../../components/ImportSuccessModal';

export const ImportTracker = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState('');
  const [title, setTitle] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSuccessOpen, setIsSuccessOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  };

  const validateAndSetFile = (file: File) => {
    const validExtensions = ['.csv', '.xlsx', '.docx', '.txt', '.md'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));
    
    if (isValid) {
      setFile(file);
      setPastedText(''); // Clear text if file is chosen
    } else {
      setError('Invalid file type. Please use .csv, .xlsx, .docx, .txt, or .md');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const chosenFile = e.target.files?.[0];
    if (chosenFile) {
      validateAndSetFile(chosenFile);
    }
  };

  const handleRemoveFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleExtract = async () => {
    if (!title.trim()) {
      setError('Import Title is required.');
      return;
    }
    setIsLoading(true);
    setError(null);
    
    try {
      let jobId: string;
      if (file) {
        const response = await importService.upload(file, undefined, title.trim());
        jobId = response.id;
      } else {
        const response = await importService.upload(undefined, pastedText, title.trim());
        jobId = response.id;
      }
      
      // Simulate polling progress
      let progress = 0;
      const interval = setInterval(async () => {
        progress += 25;
        if (progress >= 100) {
          clearInterval(interval);
          setIsLoading(false);
          setIsSuccessOpen(true);
        }
      }, 800);

    } catch (err: any) {
      setError('Failed to start extraction. Please try again.');
      setIsLoading(false);
    }
  };

  const handleStartFresh = () => {
    navigate('/dashboard');
  };

  const isExtractDisabled = !title.trim() || (!file && pastedText.trim().length < 10);

  return (
    <OnboardingLayout 
      currentStep={2}
      totalSteps={2}
      title="Import your Tracker"
      subtitle="Verato is useful from minute one. Bring in your existing spreadsheet or notes."
    >
      <Card className="p-8 shadow-xl border-slate-200">
        <div className="space-y-6">
          {/* Title Input */}
          <div className="space-y-2">
            <label className="text-sm font-bold text-slate-700 flex items-center gap-1">
              Import Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Q2 Engineering Sync, Marketing Plan Tracker..."
              className="w-full h-11 bg-slate-50 border border-slate-200 rounded-xl px-4 text-sm font-medium focus:border-blue-500 transition-all focus:outline-none"
              required
            />
          </div>

          {/* Drag & Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative border-2 border-dashed rounded-2xl p-10 transition-all cursor-pointer text-center
              ${isDragging 
                ? 'border-blue-500 bg-blue-50/50 scale-[1.01]' 
                : file 
                  ? 'border-emerald-200 bg-emerald-50/20' 
                  : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
              }
            `}
          >
            <input 
              type="file" 
              ref={fileInputRef}
              className="hidden" 
              onChange={handleFileChange}
              accept=".csv,.xlsx,.docx,.txt,.md"
            />
            
            <AnimatePresence mode="wait">
              {file ? (
                <motion.div 
                  key="file-active"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex flex-col items-center"
                >
                  <div className="w-16 h-16 bg-white rounded-xl shadow-sm border border-emerald-100 flex items-center justify-center mb-4">
                    {file.name.endsWith('.xlsx') || file.name.endsWith('.csv') ? (
                      <Sheet className="w-8 h-8 text-emerald-600" />
                    ) : (
                      <FileText className="w-8 h-8 text-blue-600" />
                    )}
                  </div>
                  <p className="text-sm font-bold text-slate-800 mb-1">{file.name}</p>
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                    {(file.size / 1024).toFixed(1)} KB — Ready for extraction
                  </p>
                  
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleRemoveFile(); }}
                    className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-400 hover:text-rose-500 hover:border-rose-200 transition-all shadow-sm"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </motion.div>
              ) : (
                <motion.div 
                  key="file-empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <div className="w-16 h-16 bg-white rounded-xl shadow-sm border border-slate-100 flex items-center justify-center mx-auto mb-4">
                    <FileUp className={`w-8 h-8 ${isDragging ? 'text-blue-500' : 'text-slate-300'}`} />
                  </div>
                  <h3 className="text-slate-900 font-bold mb-1">Drag your tracker here</h3>
                  <p className="text-slate-500 text-sm font-medium">CSV, XLSX, DOCX, TXT or Markdown</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="relative py-4">
            <div className="absolute inset-0 flex items-center" aria-hidden="true">
              <div className="w-full border-t border-slate-100"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="bg-white px-4 text-[10px] font-black uppercase tracking-widest text-slate-400">or paste text</span>
            </div>
          </div>

          {/* Text Fallback */}
          <textarea
            value={pastedText}
            onChange={(e) => { setPastedText(e.target.value); setFile(null); }}
            placeholder="Paste your meeting notes or task list here..."
            className="w-full h-32 bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm font-medium focus:border-blue-500 transition-all focus:outline-none resize-none"
          />

          {error && (
            <div className="flex items-center gap-2 p-3 bg-rose-50 border border-rose-100 rounded-xl text-rose-700 text-xs font-bold">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <div className="space-y-4 pt-2">
            <Button 
              disabled={isExtractDisabled || isLoading}
              onClick={handleExtract}
              className="w-full h-14 text-lg font-black shadow-lg shadow-blue-500/20"
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Extracting items...</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span>Extract {file ? 'from file' : 'from text'}</span>
                  <ArrowRight className="w-5 h-5" />
                </div>
              )}
            </Button>
            
            <button 
              onClick={handleStartFresh}
              className="w-full py-2 text-xs font-bold text-slate-400 hover:text-slate-600 transition-colors"
            >
              I'll start fresh — skip this
            </button>
          </div>
        </div>
      </Card>
      <ImportSuccessModal 
        isOpen={isSuccessOpen} 
        onClose={() => setIsSuccessOpen(false)} 
        onNavigateToDashboard={() => navigate('/dashboard')} 
      />
    </OnboardingLayout>
  );
};
