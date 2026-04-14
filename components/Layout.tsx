import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  CandlestickChart, 
  FlaskConical, 
  ShieldAlert, 
  Settings, 
  Activity,
  LogOut,
  Bell
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const Layout: React.FC<LayoutProps> = ({ children, activeTab, setActiveTab }) => {
  const [time, setTime] = useState(new Date());

  React.useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'trade', label: 'Trade & Orders', icon: CandlestickChart },
    { id: 'strategy', label: 'Strategy Lab', icon: FlaskConical },
    { id: 'risk', label: 'Risk Mgmt', icon: ShieldAlert },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-300 font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between z-20 shadow-xl">
        <div>
          <div className="h-16 flex items-center px-6 border-b border-slate-800">
            <Activity className="text-indigo-500 w-6 h-6 mr-3" />
            <span className="text-lg font-bold text-white tracking-wide">Letiao-Quant</span>
          </div>

          <nav className="mt-6 px-3 space-y-1">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-md transition-all duration-200 group ${
                  activeTab === item.id
                    ? 'bg-indigo-600/10 text-indigo-400 border-l-2 border-indigo-500'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white border-l-2 border-transparent'
                }`}
              >
                <item.icon className={`w-5 h-5 mr-3 transition-colors ${
                  activeTab === item.id ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'
                }`} />
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center p-3 rounded-lg bg-slate-800/50 mb-2">
            <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center text-white font-bold text-xs">
              JS
            </div>
            <div className="ml-3">
              <p className="text-xs font-medium text-white">John Smith</p>
              <p className="text-[10px] text-slate-500">Senior Trader</p>
            </div>
          </div>
          <button className="w-full flex items-center justify-center px-4 py-2 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors">
            <LogOut className="w-4 h-4 mr-2" /> Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-8 sticky top-0 z-10">
          <div className="flex items-center space-x-6">
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Net Liquidity</span>
              <span className="text-xl font-mono font-bold text-emerald-400">$124,592.40</span>
            </div>
            <div className="h-8 w-px bg-slate-800 mx-2"></div>
            <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Day P&L</span>
              <span className="text-sm font-mono font-medium text-emerald-500">+$1,240.50 (+1.01%)</span>
            </div>
            <div className="h-8 w-px bg-slate-800 mx-2"></div>
             <div className="flex flex-col">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Broker</span>
              <div className="flex items-center">
                <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse"></span>
                <span className="text-sm font-medium text-slate-300">IBKR (15ms)</span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4">
             <div className="text-right hidden md:block">
                <p className="text-sm font-mono text-slate-300">{time.toLocaleTimeString()}</p>
                <p className="text-xs text-slate-500">{time.toLocaleDateString()}</p>
             </div>
             <button className="p-2 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 relative">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-rose-500 rounded-full border-2 border-slate-900"></span>
             </button>
             <button className="p-2 rounded-full text-slate-400 hover:text-white hover:bg-slate-800">
                <Settings className="w-5 h-5" />
             </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 bg-slate-950">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;