import { cn } from "@/src/lib/utils";

interface AvatarProps {
  name: string;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  className?: string;
}

export const Avatar = ({ name, size = "md", className }: AvatarProps) => {
  const getInitials = (n: any) => {
    try {
      if (typeof n !== "string") {
        if (!n) return "??";
        n = String(n);
      }
      
      const trimmed = (n || "").trim();
      if (!trimmed) return "??";

      // Extra safety: check if split exists on the object
      if (typeof trimmed.split !== "function") return "??";

      const parts = trimmed.split(/\s+/).filter(Boolean);
      if (parts.length === 0) return "??";
      if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();

      const firstChar = parts[0][0] || "";
      const lastChar = parts[parts.length - 1][0] || "";
      return (firstChar + lastChar).toUpperCase();
    } catch (e) {
      console.error("Avatar getInitials error:", e);
      return "??";
    }
  };

  const colors = [
    "bg-brand",
    "bg-sage",
    "bg-rose",
    "bg-amber",
    "bg-blue-500",
    "bg-purple-500",
  ];

  const getColor = (n: any) => {
    try {
      const val = typeof n === "string" ? n : (n ? String(n) : "");
      if (!val) return colors[0];
      let hash = 0;
      for (let i = 0; i < val.length; i++) {
        hash = val.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colors[Math.abs(hash) % colors.length];
    } catch (e) {
      return colors[0];
    }
  };

  const sizes = {
    xs: "w-4 h-4 text-[8px]",
    sm: "w-6 h-6 text-[10px]",
    md: "w-8 h-8 text-xs",
    lg: "w-10 h-10 text-sm",
    xl: "w-16 h-16 text-xl",
  };

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full font-bold text-white shrink-0 border border-black/5 shadow-inner",
        getColor(name),
        sizes[size],
        className
      )}
    >
      {getInitials(name)}
    </div>
  );
};
