import React from 'react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import { Play, Square, Settings, ChevronDown, ChevronUp } from 'lucide-react';
import { MOCK_EQUITY_DATA, MOCK_POSITIONS, MOCK_STRATEGIES, MOCK_LOGS } from '../constants';

const Dashboard: React.FC = () => {
  return (
    <div className="grid grid-cols-12 gap-6 h-full">
      
      {/* LEFT COLUMN */}
      <div className="col-span-12 lg:col-span-8 space-y-6">
        
        {/* Equity Curve */}
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 shadow-lg relative overflow-hidden group">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-slate-100 font-semibold flex items-center">
              <span className="w-1 h-5 bg-indigo-500 rounded-full mr-2"></span>
              Equity Curve
            </h3>
            <div className="flex space-x-2 text-xs">
              <button className="px-3 py-1 bg-slate-800 text-slate-300 rounded hover:bg-slate-700">1D</button>
              <button className="px-3 py-1 bg-indigo-600 text-white rounded">1W</button>
              <button className="px-3 py-1 bg-slate-800 text-slate-300 rounded hover:bg-slate-700">1M</button>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_EQUITY_DATA}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="time" stroke="#475569" tick={{fontSize: 12}} tickLine={false} axisLine={false} />
                <YAxis stroke="#475569" tick={{fontSize: 12}} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }}
                  itemStyle={{ color: '#818cf8' }}
                />
                <Area type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorValue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Positions Table */}
        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden shadow-lg">
           <div className="p-4 border-b border-slate-800 flex justify-between items-center">
            <h3 className="text-slate-100 font-semibold flex items-center">
              <span className="w-1 h-5 bg-emerald-500 rounded-full mr-2"></span>
              Open Positions
            </h3>
            <span className="text-xs text-slate-500">Market Value: $54,320.00</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-slate-400">
              <thead className="bg-slate-950 text-xs uppercase text-slate-500 font-medium">
                <tr>
                  <th className="px-4 py-3">Symbol</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3 text-right">Avg Price</th>
                  <th className="px-4 py-3 text-right">Last</th>
                  <th className="px-4 py-3 text-right">P&L</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {MOCK_POSITIONS.map((pos) => (
                  <tr key={pos.symbol} className="hover:bg-slate-800/50 transition-colors">
                    <td className="px-4 py-3 font-medium text-white">{pos.symbol}</td>
                    <td className="px-4 py-3 text-right font-mono text-slate-300">{pos.qty}</td>
                    <td className="px-4 py-3 text-right font-mono">{pos.avgPrice.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-mono text-slate-300">{pos.currentPrice.toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right font-mono font-bold ${pos.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {pos.pnl >= 0 ? '+' : ''}{pos.pnl} ({pos.pnlPercent}%)
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button className="text-xs bg-slate-800 hover:bg-rose-900/30 text-rose-400 hover:text-rose-300 border border-slate-700 hover:border-rose-800 px-2 py-1 rounded transition-colors">
                        Close
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* System Logs */}
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 shadow-lg h-48 overflow-y-auto">
             <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 sticky top-0 bg-slate-900 pb-2">System Logs</h3>
             <div className="space-y-2 font-mono text-xs">
                {MOCK_LOGS.map(log => (
                    <div key={log.id} className="flex space-x-3 border-b border-slate-800/50 pb-1 last:border-0">
                        <span className="text-slate-500">{log.timestamp}</span>
                        <span className={`font-bold ${
                            log.level === 'INFO' ? 'text-indigo-400' : 
                            log.level === 'WARN' ? 'text-amber-400' : 'text-rose-500'
                        }`}>[{log.level}]</span>
                        <span className="text-slate-300">{log.message}</span>
                    </div>
                ))}
             </div>
        </div>

      </div>

      {/* RIGHT COLUMN */}
      <div className="col-span-12 lg:col-span-4 space-y-6">
        
        {/* Active Strategies */}
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 shadow-lg">
          <div className="flex justify-between items-center mb-4">
             <h3 className="text-slate-100 font-semibold">Active Strategies</h3>
             <button className="text-slate-500 hover:text-white"><Settings className="w-4 h-4" /></button>
          </div>
          
          <div className="space-y-3">
            {MOCK_STRATEGIES.map((strategy) => (
              <div key={strategy.id} className="bg-slate-950 border border-slate-800 rounded-md p-3 hover:border-slate-700 transition-all">
                <div className="flex justify-between items-start mb-2">
                   <div>
                       <div className="flex items-center space-x-2">
                           <span className={`w-2 h-2 rounded-full ${strategy.status === 'RUNNING' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></span>
                           <h4 className="text-sm font-medium text-white">{strategy.name}</h4>
                       </div>
                       <p className="text-xs text-slate-500 mt-1">Target: {strategy.symbols.join(', ')}</p>
                   </div>
                   <div className="text-right">
                       <span className={`block text-xs font-mono font-bold ${strategy.dailyPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                           {strategy.dailyPnl >= 0 ? '+' : ''}${strategy.dailyPnl}
                       </span>
                       <span className="text-[10px] text-slate-600">Daily PnL</span>
                   </div>
                </div>
                <div className="flex space-x-2 mt-3">
                    {strategy.status === 'RUNNING' ? (
                        <button className="flex-1 flex items-center justify-center space-x-1 bg-rose-900/20 text-rose-500 hover:bg-rose-900/40 py-1.5 rounded text-xs border border-rose-900/50 transition-colors">
                            <Square className="w-3 h-3 fill-current" /> <span>Stop</span>
                        </button>
                    ) : (
                        <button className="flex-1 flex items-center justify-center space-x-1 bg-emerald-900/20 text-emerald-500 hover:bg-emerald-900/40 py-1.5 rounded text-xs border border-emerald-900/50 transition-colors">
                            <Play className="w-3 h-3 fill-current" /> <span>Start</span>
                        </button>
                    )}
                    <button className="px-3 py-1.5 bg-slate-800 text-slate-400 hover:text-white rounded text-xs border border-slate-700">Config</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Market Sentiment / Mini Tickers */}
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 shadow-lg">
            <h3 className="text-slate-100 font-semibold mb-4">Watchlist</h3>
            <div className="space-y-2">
                {[
                    { s: 'SPY', p: 445.20, chg: 1.2 },
                    { s: 'QQQ', p: 372.15, chg: 0.8 },
                    { s: 'IWM', p: 184.40, chg: -0.5 },
                    { s: 'VIX', p: 14.20, chg: -5.4 },
                ].map(ticker => (
                    <div key={ticker.s} className="flex justify-between items-center p-2 rounded hover:bg-slate-800 cursor-pointer">
                        <span className="font-bold text-slate-200 w-12">{ticker.s}</span>
                        <div className="flex-1 mx-4 h-8 relative">
                           {/* Mini Sparkline Simulation */}
                           <svg className="w-full h-full" viewBox="0 0 100 20" preserveAspectRatio="none">
                               <path d={`M0,10 Q25,${ticker.chg > 0 ? 5 : 15} 50,10 T100,${ticker.chg > 0 ? 2 : 18}`} 
                                     fill="none" 
                                     stroke={ticker.chg > 0 ? '#10b981' : '#f43f5e'} 
                                     strokeWidth="2" />
                           </svg>
                        </div>
                        <div className="text-right">
                             <div className="text-sm font-mono text-white">{ticker.p}</div>
                             <div className={`text-xs font-mono flex items-center justify-end ${ticker.chg >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {ticker.chg >= 0 ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                                {Math.abs(ticker.chg)}%
                             </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>

      </div>
    </div>
  );
};

export default Dashboard;