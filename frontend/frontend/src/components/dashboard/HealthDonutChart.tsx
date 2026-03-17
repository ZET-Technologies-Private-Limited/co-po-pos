"use client";

import { motion } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { AnimatedCounter } from "@/components/animated/AnimatedCounter";

const data = [
  { name: "Attained", value: 78, color: "#059669" },  // SUCCESS EMERALD
  { name: "At Risk", value: 14, color: "#D97706" },   // WARNING AMBER
  { name: "Failed", value: 8, color: "#E11D48" },     // RED ALERT
];

export function HealthDonutChart() {
  return (
    <div className="w-full flex flex-col items-start relative pb-6">
      
      <div className="relative w-[300px] h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={90}
              outerRadius={120}
              paddingAngle={5}
              dataKey="value"
              stroke="none"
              animationBegin={200}
              animationDuration={1500}
              animationEasing="ease-out"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{ background: '#FFFFFF', border: '1px solid rgba(107,114,128,0.2)', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}
              itemStyle={{ color: '#1F2937', fontWeight: 'bold' }}
            />
          </PieChart>
        </ResponsiveContainer>
        
        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
           <AnimatedCounter 
              value={78} 
              suffix="%" 
              duration={2} 
              className="text-5xl justify-center font-display font-light text-gray-900 tracking-tighter" 
           />
           <span className="text-sm text-gray-600 font-mono mt-1">Overall</span>
        </div>
      </div>
      
      <div className="flex flex-col gap-4 mt-8 w-full pl-6 border-l border-gray-300">
        {data.map((item, i) => (
           <div key={i} className="flex items-center gap-4">
              <span className="w-2 h-2 rounded-full" style={{ background: item.color }} />
              <div className="flex flex-col">
                <span className="text-gray-900 font-medium text-lg leading-none">{item.value}%</span>
                <span className="text-sm text-gray-600 tracking-wide">{item.name}</span>
              </div>
           </div>
        ))}
      </div>
    </div>
  );
}
