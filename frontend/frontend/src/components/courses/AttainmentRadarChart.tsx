"use client";

import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface AttainmentRadarChartProps {
  data: { subject: string; current: number; previous: number }[];
}

export function AttainmentRadarChart({ data }: AttainmentRadarChartProps) {
  return (
    <div className="w-full h-[350px] relative">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="rgba(255,255,255,0.1)" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12, fontFamily: 'monospace' }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} />
          
          <Radar 
            name="Previous Semester" 
            dataKey="previous" 
            stroke="#1D4ED8" 
            fill="#1D4ED8" 
            fillOpacity={0.2} 
            isAnimationActive={true}
            animationDuration={2000}
          />
          
          <Radar 
            name="Current Semester" 
            dataKey="current" 
            stroke="#06B6D4" 
            fill="#06B6D4" 
            fillOpacity={0.5} 
            isAnimationActive={true}
            animationDuration={2000}
            animationBegin={500}
          />
          
          <Legend wrapperStyle={{ fontSize: '12px', opacity: 0.8 }} />
          <Tooltip 
             contentStyle={{ backgroundColor: '#0F172A', borderColor: 'rgba(255,255,255,0.1)', borderRadius: '12px' }}
             itemStyle={{ color: '#F8FAFC' }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
