import * as React from "react";
import { cn } from "@/src/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({ children, className, onClick, ...props }) => {
  return (
    <div
      onClick={onClick}
      className={cn(
        "bg-white border border-slate-200 rounded-xl p-5 shadow-sm transition-all",
        onClick && "cursor-pointer hover:border-blue-500/40 hover:shadow-md",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
