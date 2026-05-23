import { 
  LayoutDashboard, 
  UploadCloud, 
  Users, 
  Calendar, 
  Settings, 
  LogOut,
  ChevronRight
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/src/contexts/AuthContext";
import { cn } from "@/src/lib/utils";
import { useUI } from "./AppShell";

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Calendar, label: "Meetings", path: "/meetings" },
  { icon: Users, label: "People", path: "/people" },
  { icon: Settings, label: "Settings", path: "/settings" },
];

export const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { openUploadModal } = useUI();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="w-64 h-screen border-r border-slate-800 bg-sidebar-bg flex flex-col fixed left-0 top-0 text-white z-50">
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center font-bold text-xl uppercase">V</div>
        <span className="font-semibold tracking-tight text-white">Verato Dashboard</span>
      </div>

      <nav className="flex-1 px-4 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors group",
                isActive 
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20" 
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              )}
            >
              <item.icon className={cn("w-4 h-4", isActive ? "text-white" : "text-slate-500 group-hover:text-slate-300")} />
              {item.label}
              {isActive && <ChevronRight className="w-3 h-3 ml-auto opacity-50" />}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 space-y-3">
        <button 
          onClick={openUploadModal}
          className="flex items-center justify-center gap-3 w-full bg-blue-600 text-white py-3 rounded-2xl text-sm font-black shadow-xl shadow-blue-900/40 hover:bg-blue-500 transition-all hover:-translate-y-0.5 active:translate-y-0"
        >
          <UploadCloud className="w-5 h-5" />
          Upload Transcript
        </button>
        <button 
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors group"
        >
          <LogOut className="w-4 h-4 text-slate-500 group-hover:text-rose-400/70" />
          Sign Out
        </button>
      </div>
    </div>
  );
};
