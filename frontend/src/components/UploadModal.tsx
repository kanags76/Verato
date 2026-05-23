import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { meetingService, commitmentService, personService } from "@/src/lib/api/services";
import { 
  UploadCloud, 
  FileText, 
  X, 
  CheckCircle2, 
  ArrowRight,
  Info,
  Loader2,
  Users,
  Target,
  Trash2,
  Check
} from "lucide-react";
import { Button } from "@/src/components/ui/Button";
import { Card } from "@/src/components/ui/Card";
import { Badge } from "@/src/components/ui/Badge";
import { Avatar } from "@/src/components/ui/Avatar";
import { useNavigate } from "react-router-dom";
import { useUI } from "./layout/AppShell";
import { cn } from "@/src/lib/utils";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const UploadModal = ({ isOpen, onClose }: UploadModalProps) => {
  const [uploadMode, setUploadMode] = useState<"file" | "paste">("file");
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState(new Date().toISOString().split('T')[0]);
  const [file, setFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState("");

  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { notifyUploadSuccess } = useUI();

  const uploadMutation = useMutation({
    mutationFn: (data: { file?: File, text?: string, title: string, occurredAt: string }) => {
      if (data.text) return meetingService.uploadTranscriptText(data.text, data.title, data.occurredAt);
      if (data.file) return meetingService.uploadTranscript(data.file, data.title, data.occurredAt);
      throw new Error("No data provided");
    },
    onSuccess: (data) => {
      // Optimistically add the new meeting to the cache to trigger fast polling
      if (data && data.meeting_id) {
        queryClient.setQueryData(['meetings'], (old: any[] | undefined) => {
          const newMeeting = {
            id: data.meeting_id,
            title: meetingTitle || "Untitled Meeting",
            occurred_at: meetingDate || new Date().toISOString(),
            status: "pending",
            type: "Internal",
            commitments_count: 0
          };
          return old ? [newMeeting, ...old] : [newMeeting];
        });
      }
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
      notifyUploadSuccess();
      onClose();
      if (window.location.pathname !== '/meetings') {
        navigate('/meetings');
      }
    }
  });

  const handleUpload = () => {
    if (!meetingTitle.trim()) return;
    if (uploadMode === "file" && file) {
      uploadMutation.mutate({ file, title: meetingTitle, occurredAt: meetingDate });
    } else if (uploadMode === "paste" && pastedText.trim()) {
      uploadMutation.mutate({ text: pastedText, title: meetingTitle, occurredAt: meetingDate });
    }
  };

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setUploadMode("file");
      setMeetingTitle("");
      setMeetingDate(new Date().toISOString().split('T')[0]);
      setFile(null);
      setPastedText("");
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
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
          className="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-[40px] shadow-2xl overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-8 border-b border-slate-50">
            <div className="space-y-1">
              <h2 className="text-2xl font-black text-slate-900 tracking-tight">Capture Commitment</h2>
              <p className="text-slate-500 text-sm font-bold">
                {uploadMode === "file" ? "Upload a meeting transcript to start extraction." : "Paste your transcript text below."}
              </p>
            </div>
            <button 
              onClick={onClose}
              className="p-3 bg-slate-50 text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-2xl transition-all"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
            <UploadStep 
              file={file} 
              setFile={setFile} 
              uploadMode={uploadMode}
              setUploadMode={setUploadMode}
              pastedText={pastedText}
              setPastedText={setPastedText}
              meetingTitle={meetingTitle}
              setMeetingTitle={setMeetingTitle}
              meetingDate={meetingDate}
              setMeetingDate={setMeetingDate}
              onUpload={handleUpload}
              isLoading={uploadMutation.isPending}
            />
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

const UploadStep = ({ 
  file, 
  setFile, 
  uploadMode, 
  setUploadMode, 
  pastedText, 
  setPastedText, 
  meetingTitle, 
  setMeetingTitle, 
  meetingDate, 
  setMeetingDate, 
  onUpload, 
  isLoading 
}: any) => (
  <div className="space-y-8 max-w-2xl mx-auto py-4">
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="space-y-2">
        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
          Meeting Title <span className="text-rose-500">*</span>
        </label>
        <input 
          type="text"
          value={meetingTitle}
          onChange={(e) => setMeetingTitle(e.target.value)}
          placeholder="e.g. Q3 Strategy Review"
          className="w-full bg-slate-50 border border-slate-100 rounded-2xl px-5 py-3 font-bold text-sm outline-none focus:border-blue-400 transition-all"
        />
      </div>
      <div className="space-y-2">
        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Meeting Date</label>
        <input 
          type="date"
          value={meetingDate}
          onChange={(e) => setMeetingDate(e.target.value)}
          className="w-full bg-slate-50 border border-slate-100 rounded-2xl px-5 py-3 font-bold text-sm outline-none focus:border-blue-400 transition-all"
        />
      </div>
    </div>

    <div className="flex p-1 bg-slate-100 rounded-2xl">
      <button 
        onClick={() => setUploadMode("file")}
        className={cn(
          "flex-1 py-3 text-xs font-black uppercase tracking-widest rounded-xl transition-all",
          uploadMode === "file" ? "bg-white text-blue-600 shadow-sm" : "text-slate-400 hover:text-slate-600"
        )}
      >
        Upload File
      </button>
      <button 
        onClick={() => setUploadMode("paste")}
        className={cn(
          "flex-1 py-3 text-xs font-black uppercase tracking-widest rounded-xl transition-all",
          uploadMode === "paste" ? "bg-white text-blue-600 shadow-sm" : "text-slate-400 hover:text-slate-600"
        )}
      >
        Paste Text
      </button>
    </div>

    {uploadMode === "file" ? (
      <div 
        className={cn(
          "border-2 border-dashed rounded-[32px] p-16 text-center transition-all bg-white shadow-xl shadow-slate-200/40",
          file ? "border-blue-200 bg-blue-50/10" : "border-slate-200 hover:border-blue-400"
        )}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
        }}
      >
        {!file ? (
          <div className="space-y-6">
            <div className="w-20 h-20 bg-blue-50 border border-blue-100 rounded-3xl flex items-center justify-center mx-auto text-blue-600 shadow-inner">
              <UploadCloud className="w-10 h-10" />
            </div>
            <div className="space-y-1">
              <p className="text-xl font-black text-slate-900 tracking-tight">Drag & drop transcript</p>
              <p className="text-slate-500 font-bold text-sm">Supports .txt, .docx, .pdf, .vtt</p>
            </div>
            <label className="inline-block cursor-pointer">
              <input 
                type="file" 
                className="hidden" 
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <span className="bg-slate-900 text-white px-8 py-3 rounded-2xl font-black text-sm hover:bg-slate-800 transition-all shadow-lg inline-block">
                Browse Files
              </span>
            </label>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-6">
            <div className="w-20 h-20 bg-emerald-50 border border-emerald-100 rounded-3xl flex items-center justify-center text-emerald-600">
              <FileText className="w-10 h-10" />
            </div>
            <div className="text-center">
              <p className="text-lg font-black text-slate-900 truncate max-w-sm">{file.name}</p>
              <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-1">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
            <button onClick={() => setFile(null)} className="text-rose-600 font-black text-xs uppercase tracking-widest hover:underline px-4 py-2">
              Remove File
            </button>
          </div>
        )}
      </div>
    ) : (
      <div className="space-y-4">
        <div className="relative group">
          <textarea 
            value={pastedText}
            onChange={(e) => setPastedText(e.target.value)}
            placeholder="Paste your meeting transcript here... (e.g. John: Let's focus on the Q3 roadmap...)"
            className="w-full h-80 bg-slate-50 border border-slate-200 rounded-[32px] p-8 font-medium text-slate-900 placeholder:text-slate-400 outline-none focus:border-blue-400 focus:bg-white transition-all resize-none shadow-inner custom-scrollbar"
          />
          <div className="absolute top-4 right-4 text-[10px] font-black text-slate-300 pointer-events-none uppercase tracking-widest">
            {pastedText.length} Characters
          </div>
        </div>
      </div>
    )}

    <div className="flex flex-col items-center gap-6 pt-4">
      <Button 
        disabled={isLoading || !meetingTitle.trim() || (uploadMode === "file" ? !file : !pastedText.trim())}
        onClick={onUpload}
        className="w-full max-w-sm h-16 text-lg font-black rounded-3xl shadow-2xl shadow-blue-500/30 bg-blue-600 hover:bg-blue-700 text-white border-none"
      >
        {isLoading ? (
          <div className="flex items-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin" />
            <span>Uploading...</span>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <span>Process Transcript</span>
            <ArrowRight className="w-6 h-6" />
          </div>
        )}
      </Button>

      <div className="flex items-center gap-2 text-slate-400 bg-slate-50 px-4 py-2 rounded-xl">
        <Info className="w-4 h-4 text-blue-500" />
        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Gemini preserves speaker context for extraction</span>
      </div>
    </div>
  </div>
);
