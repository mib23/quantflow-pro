import React from 'react';
import { Play, Download, Save, BarChart3, Maximize2, Settings } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { STRATEGY_CODE, MOCK_EQUITY_DATA } from '../constants';

const StrategyLab: React.FC = () => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-8rem)]">
      
      {/* Sidebar File Tree (Simplified) */}
      <div className="hidden lg:block lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-3">
        <h3 className="text-xs font-bold text-slate-500 uppercase mb-3 px-2">Explorer</h3>
        <ul className="space-y-1 text-sm">
           <li className="px-2 py-1.5 bg-slate-800 text-white rounded cursor-pointer">moving_avg_cross.py</li>
           <li className="px-2 py-1.5 text-slate-400 hover:text-white hover:bg-slate-800/50 rounded cursor-pointer">rsi_breakout.py</li>
           <li className="px-2 py-1.5 text-slate-400 hover:text-white hover:bg-slate-800/50 rounded cursor-pointer">volatility_squeeze.py</li>
           <li className="px-2 py-1.5 text-slate-400 hover:text-white hover:bg-slate-800/50 rounded cursor-pointer">config.json</li>
        </ul>
      </div>

      {/* Editor Area */}
      <div className="col-span-1 lg:col-span-6 flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
        <div className="bg-slate-950 p-2 border-b border-slate-800 flex justify-between items-center">
            <div className="flex space-x-2">
                <span className="text-xs text-white bg-slate-800 px-3 py-1 rounded border border-slate-700">moving_avg_cross.py</span>
            </div>
            <div className="flex space-x-2">
                 <button className="p-1 hover:bg-slate-800 rounded text-slate-400"><Save className="w-4 h-4" /></button>
            </div>
        </div>
        <div className="flex-1 relative bg-[#0d1117] p-4 overflow-auto font-mono text-sm leading-relaxed">
            {/* Simple syntax highlighting simulation */}
            <pre>
                <code className="language-python table w-full" style={{color: '#c9d1d9'}}>
                    {STRATEGY_CODE.split('\n').map((line, i) => (
                        <div key={i} className="table-row">
                            <span className="table-cell text-right pr-4 text-slate-600 select-none w-8">{i + 1}</span>
                            <span className="table-cell whitespace-pre">
                                {line
                                  .replace(/class|def|if|elif|return/g, '<span style="color:#ff7b72">$&</span>')
                                  .replace(/self/g, '<span style="color:#79c0ff">self</span>')
                                  .replace(/".*?"/g, '<span style="color:#a5d6ff">$&</span>')
                                  .replace(/#.*/g, '<span style="color:#8b949e">$&</span>')
                                  .split(/<span.*?>.*?<\/span>/g).reduce((acc: any[], part, idx, arr) => {
                                      // This is a very hacky way to inject HTML into React for the demo without `dangerouslySetInnerHTML` on the whole block
                                      // Real app would use Monaco Editor.
                                      // For this demo, we'll just render the raw text unless we use dangerouslySetInnerHTML
                                      return acc; 
                                  }, [])
                                }
                                {/* Rendering raw for safety in this demo, but formatted in a monospaced block */}
                                {line} 
                            </span>
                        </div>
                    ))}
                </code>
            </pre>
        </div>
      </div>

      {/* Backtest Config & Results */}
      <div className="col-span-1 lg:col-span-4 flex flex-col gap-6">
          
          {/* Controls */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <h3 className="font-semibold text-slate-200 mb-4 flex items-center">
                  <Settings className="w-4 h-4 mr-2 text-indigo-400" /> Backtest Configuration
              </h3>
              <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                      <label className="block text-xs text-slate-500 mb-1">Start Date</label>
                      <input type="date" className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-xs text-white" />
                  </div>
                  <div>
                      <label className="block text-xs text-slate-500 mb-1">End Date</label>
                      <input type="date" className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-xs text-white" />
                  </div>
                  <div>
                      <label className="block text-xs text-slate-500 mb-1">Initial Capital</label>
                      <input type="text" defaultValue="$100,000" className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-xs text-white" />
                  </div>
                   <div>
                      <label className="block text-xs text-slate-500 mb-1">Slippage</label>
                      <input type="text" defaultValue="0.01%" className="w-full bg-slate-950 border border-slate-700 rounded p-1.5 text-xs text-white" />
                  </div>
              </div>
              <button className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2 rounded flex items-center justify-center transition-colors">
                  <Play className="w-4 h-4 mr-2" /> Run Backtest
              </button>
          </div>

          {/* Results Preview */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 flex-1 flex flex-col">
              <div className="flex justify-between items-center mb-2">
                  <h3 className="font-semibold text-slate-200">Results</h3>
                  <span className="text-xs text-emerald-400 font-mono">Sharpe: 2.15</span>
              </div>
              <div className="h-40 w-full mb-4">
                 <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={MOCK_EQUITY_DATA}>
                        <defs>
                            <linearGradient id="colorB" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                            </linearGradient>
                        </defs>
                        <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: 'none' }} />
                        <Area type="monotone" dataKey="value" stroke="#10b981" fill="url(#colorB)" strokeWidth={2} />
                    </AreaChart>
                 </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                      <div className="text-slate-500">Net Profit</div>
                      <div className="text-emerald-400 font-bold">+15.2%</div>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                      <div className="text-slate-500">Max DD</div>
                      <div className="text-rose-400 font-bold">-4.5%</div>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800">
                      <div className="text-slate-500">Win Rate</div>
                      <div className="text-slate-200 font-bold">62%</div>
                  </div>
              </div>
              
              <div className="mt-auto pt-4 flex space-x-3">
                  <button className="flex-1 border border-slate-700 text-slate-300 hover:bg-slate-800 py-2 rounded text-xs flex items-center justify-center">
                      <Download className="w-3 h-3 mr-1" /> Report
                  </button>
                  <button className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white py-2 rounded text-xs flex items-center justify-center font-bold shadow-lg shadow-emerald-900/20">
                      Deploy Live
                  </button>
              </div>
          </div>
      </div>
    </div>
  );
};

export default StrategyLab;