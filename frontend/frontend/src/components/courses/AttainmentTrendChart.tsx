"use client";

import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

interface AttainmentTrendChartProps {
  data: { year: string; CO1: number; CO2: number; CO3: number; CO4: number; CO5: number }[];
}

export function AttainmentTrendChart({ data }: AttainmentTrendChartProps) {
  return (
    <div className="w-full h-[350px] relative mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 20, right: 30, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
             dataKey="year" 
             stroke="rgba(255,255,255,0.2)" 
             tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12, fontFamily: 'monospace' }} 
             tickLine={false}
             axisLine={false}
          />
          <YAxis 
             stroke="rgba(255,255,255,0.2)" 
             tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
             tickLine={false}
             axisLine={false}
             domain={[0, 100]}
          />
          <Tooltip 
             contentStyle={{ backgroundColor: '#0F172A', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px' }}
             itemStyle={{ fontWeight: 'bold' }}
             cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 2 }}
          />
          <Legend wrapperStyle={{ fontSize: '10px', fontFamily: 'monospace', textTransform: 'uppercase', color: 'rgba(255,255,255,0.5)' }} />
          
          <Line type="monotone" dataKey="CO1" stroke="#1DAEDB" strokeWidth={2} dot={{ r: 4, fill: '#1DAEDB', strokeWidth: 0 }} activeDot={{ r: 6 }} />
          <Line type="monotone" dataKey="CO2" stroke="#10B981" strokeWidth={2} dot={{ r: 4, fill: '#10B981', strokeWidth: 0 }} activeDot={{ r: 6 }} />
          <Line type="monotone" dataKey="CO3" stroke="#F59E0B" strokeWidth={2} dot={{ r: 4, fill: '#F59E0B', strokeWidth: 0 }} activeDot={{ r: 6 }} />
          <Line type="monotone" dataKey="CO4" stroke="#8B5CF6" strokeWidth={2} dot={{ r: 4, fill: '#8B5CF6', strokeWidth: 0 }} activeDot={{ r: 6 }} />
          <Line type="monotone" dataKey="CO5" stroke="#EC4899" strokeWidth={2} dot={{ r: 4, fill: '#EC4899', strokeWidth: 0 }} activeDot={{ r: 6 }} />
          
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
