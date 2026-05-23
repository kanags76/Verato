import { Bell, Search, User } from "lucide-react";

export const TopBar = () => {
  return (
    <div className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-8 sticky top-0 z-50 ml-64 flex-shrink-0 shadow-sm">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative w-96 max-w-full">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-bold" />
          <input 
            type="text" 
            placeholder="Search intelligence..." 
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-blue-500/40 transition-colors"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="p-2 text-verato-text-faint hover:text-verato-text hover:bg-surface rounded-lg transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-rose rounded-full border-2 border-verato-bg" />
        </button>
        
        <div className="h-8 w-[1px] bg-border-custom" />

        <div className="flex items-center gap-3 pl-2">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-bold text-verato-text">Sarah K.</p>
            <p className="text-[10px] text-verato-text-faint font-mono uppercase tracking-widest">Chief of Staff</p>
          </div>
          <div className="w-9 h-9 rounded-full bg-panel border border-border-custom flex items-center justify-center text-verato-text-mid">
            <User className="w-5 h-5" />
          </div>
        </div>
      </div>
    </div>
  );
};
