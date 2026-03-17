"use client";

import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";

interface AttainmentBarChartProps {
  data: { co: string; score: number }[];
  threshold: number;
}

export function AttainmentBarChart({ data, threshold }: AttainmentBarChartProps) {
  return (
    <div className="w-full h-[350px] relative mt-4">
      {/* Target threshold label */}
      <div 
        className="absolute w-max flex items-center gap-2 z-10 text-xs font-mono text-gray-700 bg-amber-50/90 backdrop-blur-sm px-2 py-1 rounded-md border border-amber-300"
        style={{ top: `calc(${100 - threshold}% - 12px)`, right: 0 }}
      >
         <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
         Target: {threshold}%
      </div>

      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: -20, bottom: 0 }}>
          <XAxis 
             dataKey="co" 
             stroke="rgba(107,114,128,0.3)" 
             tick={{ fill: 'rgba(75,85,99,0.7)', fontSize: 12, fontFamily: 'monospace' }} 
             tickLine={false}
             axisLine={false}
          />
          <YAxis 
             stroke="rgba(107,114,128,0.3)" 
             tick={{ fill: 'rgba(75,85,99,0.7)', fontSize: 12 }}
             tickLine={false}
             axisLine={false}
             domain={[0, 100]}
          />
          <Tooltip 
             contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#D1D5DB', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}
             itemStyle={{ color: '#1F2937', fontWeight: 'bold' }}
             cursor={{ fill: 'rgba(59,130,246,0.05)' }}
          />
          
          <ReferenceLine y={threshold} stroke="#D97706" strokeDasharray="3 3" />
          
          <Bar 
             dataKey="score" 
             radius={[6, 6, 0, 0]}
             isAnimationActive={true}
             animationDuration={1500}
             animationEasing="cubic-bezier(0.16, 1, 0.3, 1)"
          >
            {data.map((entry, index) => (
              <Cell 
                 key={`cell-${index}`} 
                 fill={entry.score >= threshold ? '#059669' : '#D97706'} 
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
