import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from "react";

interface ToastMessage { id: number; text: string; type: "success" | "error" }

interface ToastCtx {
  showToast: (text: string, type?: "success" | "error") => void;
}

const Ctx = createContext<ToastCtx>({ showToast: () => {} });

export function useToast() { return useContext(Ctx); }

let _globalShow: ToastCtx["showToast"] = () => {};
export function toast(text: string, type?: "success" | "error") { _globalShow(text, type); }

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const showToast = useCallback((text: string, type: "success" | "error" = "success") => {
    const id = ++nextId;
    setMessages(prev => [...prev, { id, text, type }]);
    setTimeout(() => setMessages(prev => prev.filter(m => m.id !== id)), 3000);
  }, []);

  useEffect(() => { _globalShow = showToast; }, [showToast]);

  return (
    <Ctx.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-20 md:bottom-6 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        {messages.map(m => (
          <div
            key={m.id}
            className={`px-4 py-3 rounded-xl text-[14px] font-medium shadow-xl border animate-in slide-in-from-right-4 fade-in duration-200 ${
              m.type === "success"
                ? "bg-[#262626] border-white/[0.1] text-[#ececec]"
                : "bg-red-900/80 border-red-500/30 text-red-200"
            }`}
          >
            <span className="mr-2">{m.type === "success" ? "✓" : "✕"}</span>
            {m.text}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

// Rendered inside App — just needs ToastProvider wrapping the tree
export default function Toast() { return null; }
