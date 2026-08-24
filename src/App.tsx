import { useState } from "react";
import { StoreProvider } from "./store";
import Hero from "./components/Hero";
import Danas from "./tabs/Danas";
import Buduce from "./tabs/Buduce";
import Unos from "./tabs/Unos";
import Detalji from "./tabs/Detalji";
import { ToastProvider } from "./components/Toast";

// Tab colours matching the original Streamlit app:
// plava (blue) = Danas, ljubičasta (purple) = Buduće,
// jantarna (amber) = Unos, zelena (green) = Detalji
const TABS = [
  { id: "danas",   label: "Danas",   icon: TodayIcon,  color: "#3b82f6" },
  { id: "buduce",  label: "Buduce",  icon: FutureIcon, color: "#8b5cf6" },
  { id: "unos",    label: "Unos",    icon: EditIcon,   color: "#f59e0b" },
  { id: "detalji", label: "Detalji", icon: ChartIcon,  color: "#10b981" },
];

function AppInner() {
  const [tab, setTab] = useState("danas");
  const activeTab = TABS.find(t => t.id === tab)!;

  return (
    <div className="flex h-screen overflow-hidden bg-[#1a1a1a] text-[#ececec] font-sans">

      {/* Sidebar — desktop only */}
      <aside className="hidden md:flex w-60 flex-col bg-[#212121] border-r border-white/[0.06] shrink-0">
        {/* Logo */}
        <div className="px-4 pt-5 pb-6">
          <div className="flex items-center gap-2.5 px-2">
            <div className="w-7 h-7 rounded-lg bg-[#c96442] flex items-center justify-center shrink-0">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 1.5L2 4.5V9.5L7 12.5L12 9.5V4.5L7 1.5Z" stroke="white" strokeWidth="1.4" strokeLinejoin="round"/>
                <path d="M7 4.5V9.5M4.5 6L7 4.5L9.5 6" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <span className="font-semibold text-[15px] text-[#ececec] tracking-tight">Liquidity</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 space-y-0.5">
          {TABS.map(({ id, label, icon: Icon, color }) => {
            const active = tab === id;
            return (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[14px] transition-all duration-150 text-left ${
                  active ? "font-medium" : "text-[#8a8a8a] hover:bg-white/[0.04] hover:text-[#c5c5c5]"
                }`}
                style={active ? { backgroundColor: `${color}18`, color } : {}}
              >
                <Icon active={active} color={color} />
                {label}
              </button>
            );
          })}
        </nav>

        {/* User */}
        <div className="px-2 pb-4 pt-2 border-t border-white/[0.06]">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/[0.04] cursor-pointer transition-colors">
            <div className="w-7 h-7 rounded-full bg-[#c96442]/20 border border-[#c96442]/40 flex items-center justify-center text-[11px] font-semibold text-[#c96442] shrink-0">
              MK
            </div>
            <div className="min-w-0">
              <p className="text-[13px] text-[#ececec] font-medium leading-tight truncate">Marmasin</p>
              <p className="text-[11px] text-[#8a8a8a] truncate">Osobni racun</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile header */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-white/[0.06] shrink-0">
          <div className="w-7 h-7 rounded-lg bg-[#c96442] flex items-center justify-center shrink-0">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 1.5L2 4.5V9.5L7 12.5L12 9.5V4.5L7 1.5Z" stroke="white" strokeWidth="1.4" strokeLinejoin="round"/>
              <path d="M7 4.5V9.5M4.5 6L7 4.5L9.5 6" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="font-semibold text-[15px] text-[#ececec]">Liquidity</span>
          <span className="ml-1 text-[13px]" style={{ color: activeTab.color }}>
            {activeTab.label}
          </span>
        </div>

        {/* Hero — shown on every tab */}
        <Hero />

        {/* Coloured top border matching active tab */}
        <div className="h-[2px] shrink-0 transition-all duration-300" style={{ backgroundColor: activeTab.color, opacity: 0.6 }} />

        {/* Tab content */}
        <div className="flex-1 overflow-hidden">
          {tab === "danas"   && <div className="h-full overflow-y-auto"><Danas /></div>}
          {tab === "buduce"  && <div className="h-full overflow-y-auto"><Buduce /></div>}
          {tab === "unos"    && <Unos />}
          {tab === "detalji" && <div className="h-full flex flex-col overflow-hidden"><Detalji /></div>}
        </div>

        {/* Mobile bottom nav — 2×2 grid on very small screens, row on sm+ */}
        <nav className="md:hidden grid grid-cols-4 border-t border-white/[0.06] shrink-0 bg-[#212121]">
          {TABS.map(({ id, label, icon: Icon, color }) => {
            const active = tab === id;
            return (
              <button
                key={id}
                onClick={() => setTab(id)}
                className="flex flex-col items-center gap-1 py-3 text-[10px] font-medium transition-colors"
                style={{ color: active ? color : "#8a8a8a" }}
              >
                <Icon active={active} color={color} />
                {label}
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <StoreProvider>
        <AppInner />
      </StoreProvider>
    </ToastProvider>
  );
}

/* Icons */
function TodayIcon({ active, color }: { active: boolean; color: string }) {
  const c = active ? color : "currentColor";
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="2" y="3" width="12" height="11" rx="2" stroke={c} strokeWidth="1.4"/>
      <path d="M2 7h12" stroke={c} strokeWidth="1.4"/>
      <path d="M5 1v3M11 1v3" stroke={c} strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  );
}

function FutureIcon({ active, color }: { active: boolean; color: string }) {
  const c = active ? color : "currentColor";
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="6" stroke={c} strokeWidth="1.4"/>
      <path d="M8 5v3.5l2.5 1.5" stroke={c} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function EditIcon({ active, color }: { active: boolean; color: string }) {
  const c = active ? color : "currentColor";
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M10.5 2.5l3 3L5 14H2v-3L10.5 2.5z" stroke={c} strokeWidth="1.4" strokeLinejoin="round"/>
    </svg>
  );
}

function ChartIcon({ active, color }: { active: boolean; color: string }) {
  const c = active ? color : "currentColor";
  const op = active ? "1" : "0.5";
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="2" y="9" width="3" height="5" rx="1" fill={c} fillOpacity={op}/>
      <rect x="6.5" y="6" width="3" height="8" rx="1" fill={c} fillOpacity={op}/>
      <rect x="11" y="2" width="3" height="12" rx="1" fill={c} fillOpacity={op}/>
    </svg>
  );
}
