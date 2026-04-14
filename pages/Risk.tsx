import React from 'react';
import { Shield, AlertTriangle, Lock, Save } from 'lucide-react';

const Risk: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center">
          <Shield className="w-8 h-8 mr-3 text-indigo-500" />
          Risk Management & Compliance
        </h1>
        <p className="text-slate-400 mt-2">Configure global hard limits and safety checks for the trading engine.</p>
      </div>

      <div className="space-y-6">
        
        {/* Hard Limits */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <div className="bg-slate-800/50 p-4 border-b border-slate-800 flex items-center">
             <Lock className="w-5 h-5 text-rose-500 mr-2" />
             <h3 className="font-semibold text-white">Hard Limits (Auto-Kill Switch)</h3>
          </div>
          <div className="p-6 space-y-6">
             <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div>
                   <label className="block text-sm font-medium text-slate-200">Max Daily Loss Limit</label>
                   <p className="text-xs text-slate-500 mt-1">Trading halts if daily loss exceeds this amount.</p>
                </div>
                <div className="flex items-center space-x-3">
                    <span className="text-slate-400">$</span>
                    <input type="text" defaultValue="5,000" className="bg-slate-950 border border-slate-700 rounded p-2 w-32 text-right text-white font-mono" />
                </div>
             </div>

             <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div>
                   <label className="block text-sm font-medium text-slate-200">Max Single Order Value</label>
                   <p className="text-xs text-slate-500 mt-1">Reject orders larger than this notional value.</p>
                </div>
                <div className="flex items-center space-x-3">
                    <span className="text-slate-400">$</span>
                    <input type="text" defaultValue="50,000" className="bg-slate-950 border border-slate-700 rounded p-2 w-32 text-right text-white font-mono" />
                </div>
             </div>
             
             <div className="flex items-center justify-between">
                <div>
                   <label className="block text-sm font-medium text-slate-200">Max Position Size (% Equity)</label>
                   <p className="text-xs text-slate-500 mt-1">Maximum allocation per single symbol.</p>
                </div>
                <div className="flex items-center space-x-3">
                    <input type="text" defaultValue="20" className="bg-slate-950 border border-slate-700 rounded p-2 w-20 text-right text-white font-mono" />
                    <span className="text-slate-400">%</span>
                </div>
             </div>
          </div>
        </div>

        {/* Compliance */}
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
           <div className="bg-slate-800/50 p-4 border-b border-slate-800 flex items-center">
             <AlertTriangle className="w-5 h-5 text-amber-500 mr-2" />
             <h3 className="font-semibold text-white">Compliance & Restrictions</h3>
          </div>
          <div className="p-6 space-y-6">
             <div>
                <label className="block text-sm font-medium text-slate-200 mb-2">Restricted Symbols (Blacklist)</label>
                <textarea 
                  className="w-full bg-slate-950 border border-slate-700 rounded p-3 text-slate-300 font-mono text-sm h-24 focus:border-indigo-500 focus:outline-none"
                  defaultValue="GME, AMC, BB, DOGE" 
                ></textarea>
                <p className="text-xs text-slate-500 mt-2">Comma separated list of tickers forbidden from trading.</p>
             </div>
             
             <div className="flex items-center space-x-3">
                <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500" />
                <label className="text-sm text-slate-300">Enforce Market Hours (09:30 - 16:00 ET Only)</label>
             </div>
          </div>
        </div>

        <div className="flex justify-end pt-4">
            <button className="flex items-center bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-8 rounded shadow-lg transition-colors">
                <Save className="w-5 h-5 mr-2" /> Save Risk Configuration
            </button>
        </div>

      </div>
    </div>
  );
};

export default Risk;