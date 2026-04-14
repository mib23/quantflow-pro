import React, { useState } from 'react';
import { MOCK_ASK, MOCK_BID, MOCK_ORDERS } from '../constants';

const Trade: React.FC = () => {
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [qty, setQty] = useState(100);
  const [price, setPrice] = useState(245.50);

  return (
    <div className="grid grid-cols-12 gap-6 h-full">
      {/* Order Entry Panel */}
      <div className="col-span-12 lg:col-span-3 space-y-4">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
           <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-white">Order Entry</h2>
              <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">LIMIT</span>
           </div>

           <div className="space-y-4">
               <div>
                  <label className="block text-xs font-medium text-slate-500 mb-1">Symbol</label>
                  <input type="text" defaultValue="TSLA" className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-white font-mono focus:border-indigo-500 focus:outline-none uppercase" />
               </div>
               
               <div className="grid grid-cols-2 gap-2 bg-slate-950 p-1 rounded border border-slate-700 mb-4">
                  <button 
                    onClick={() => setSide('BUY')}
                    className={`py-2 text-sm font-bold rounded transition-colors ${side === 'BUY' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/50' : 'text-slate-500 hover:text-slate-300'}`}
                  >BUY</button>
                  <button 
                    onClick={() => setSide('SELL')}
                    className={`py-2 text-sm font-bold rounded transition-colors ${side === 'SELL' ? 'bg-rose-600 text-white shadow-lg shadow-rose-900/50' : 'text-slate-500 hover:text-slate-300'}`}
                  >SELL</button>
               </div>

               <div className="grid grid-cols-2 gap-4">
                   <div>
                       <label className="block text-xs font-medium text-slate-500 mb-1">Quantity</label>
                       <input 
                         type="number" 
                         value={qty} 
                         onChange={(e) => setQty(Number(e.target.value))}
                         className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-white font-mono focus:border-indigo-500 focus:outline-none" 
                       />
                   </div>
                   <div>
                       <label className="block text-xs font-medium text-slate-500 mb-1">Price</label>
                       <input 
                         type="number" 
                         value={price} 
                         onChange={(e) => setPrice(Number(e.target.value))}
                         className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-white font-mono focus:border-indigo-500 focus:outline-none" 
                       />
                   </div>
               </div>

               <div className="pt-4">
                   <button className={`w-full py-3 rounded-md font-bold text-white shadow-lg transition-transform active:scale-95 ${side === 'BUY' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'}`}>
                       {side} TSLA
                   </button>
               </div>
               
               <div className="flex justify-between text-xs text-slate-500 mt-2">
                   <span>Buying Power</span>
                   <span className="text-slate-300">$124,592.40</span>
               </div>
           </div>
        </div>
      </div>

      {/* Level 2 Order Book */}
      <div className="col-span-12 md:col-span-6 lg:col-span-5">
         <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden h-full flex flex-col">
            <div className="p-3 border-b border-slate-800 bg-slate-900">
                <h3 className="font-semibold text-slate-200">Level 2 Data <span className="text-slate-500 text-sm font-normal ml-2">TSLA</span></h3>
            </div>
            <div className="flex-1 flex flex-col font-mono text-xs">
                {/* Asks (Sell Orders) - Reverse order typically but simpler list here */}
                <div className="flex-1 overflow-hidden relative">
                    <table className="w-full">
                        <thead className="text-slate-500 bg-slate-950/50">
                            <tr>
                                <th className="text-left px-3 py-1">Price</th>
                                <th className="text-right px-3 py-1">Size</th>
                                <th className="text-right px-3 py-1">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {MOCK_ASK.slice().reverse().map((level, i) => (
                                <tr key={i} className="hover:bg-slate-800 relative">
                                    <td className="px-3 py-1 text-rose-400">{level.price.toFixed(2)}</td>
                                    <td className="px-3 py-1 text-right text-slate-300">{level.size}</td>
                                    <td className="px-3 py-1 text-right text-slate-500 relative z-10">{level.total}</td>
                                    {/* Visual Depth Bar */}
                                    <td className="absolute top-0 right-0 h-full bg-rose-900/20" style={{ width: `${(level.total / 2000) * 100}%` }}></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                
                {/* Spread */}
                <div className="bg-slate-950 py-1 text-center text-slate-500 border-y border-slate-800 text-xs">
                    Spread: 0.05 (0.02%)
                </div>

                {/* Bids (Buy Orders) */}
                 <div className="flex-1 overflow-hidden relative">
                    <table className="w-full">
                        <tbody>
                            {MOCK_BID.map((level, i) => (
                                <tr key={i} className="hover:bg-slate-800 relative">
                                    <td className="px-3 py-1 text-emerald-400">{level.price.toFixed(2)}</td>
                                    <td className="px-3 py-1 text-right text-slate-300">{level.size}</td>
                                    <td className="px-3 py-1 text-right text-slate-500 relative z-10">{level.total}</td>
                                    {/* Visual Depth Bar */}
                                    <td className="absolute top-0 right-0 h-full bg-emerald-900/20" style={{ width: `${(level.total / 2000) * 100}%` }}></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
         </div>
      </div>

      {/* Open Orders / Fills */}
      <div className="col-span-12 md:col-span-6 lg:col-span-4 flex flex-col gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-lg flex-1 flex flex-col overflow-hidden">
            <div className="p-3 border-b border-slate-800 flex justify-between items-center">
                <h3 className="font-semibold text-slate-200">Active Orders</h3>
                <button className="text-xs bg-rose-900/30 text-rose-400 border border-rose-900 px-2 py-1 rounded hover:bg-rose-900/50">Cancel All</button>
            </div>
            <div className="overflow-auto">
                <table className="w-full text-xs">
                    <thead className="bg-slate-950 text-slate-500">
                        <tr>
                            <th className="px-3 py-2 text-left">Sym</th>
                            <th className="px-3 py-2 text-left">Side</th>
                            <th className="px-3 py-2 text-right">Price</th>
                            <th className="px-3 py-2 text-right">Qty</th>
                            <th className="px-3 py-2"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {MOCK_ORDERS.map(order => (
                            <tr key={order.id} className="hover:bg-slate-800">
                                <td className="px-3 py-2 font-bold text-white">{order.symbol}</td>
                                <td className={`px-3 py-2 font-bold ${order.side === 'BUY' ? 'text-emerald-500' : 'text-rose-500'}`}>{order.side}</td>
                                <td className="px-3 py-2 text-right font-mono">{order.price.toFixed(2)}</td>
                                <td className="px-3 py-2 text-right font-mono">{order.qty}</td>
                                <td className="px-3 py-2 text-right">
                                    <button className="text-slate-500 hover:text-rose-400 font-bold">X</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
      </div>
    </div>
  );
};

export default Trade;