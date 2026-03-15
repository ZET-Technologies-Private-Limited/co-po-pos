"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { useTheme } from "next-themes";

interface NetworkGraphProps {
  cos: { id: string, name: string }[];
  pos: { id: string, name: string }[];
  mapping: Record<string, Record<string, number>>;
}

export function NetworkGraph({ cos, pos, mapping }: NetworkGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    // Clear previous D3 render
    d3.select(svgRef.current).selectAll("*").remove();

    const width = svgRef.current.clientWidth;
    const height = 400;

    // Data processing
    const nodes = [
      ...cos.map(co => ({ id: co.id, group: "co", name: co.name, radius: 24 })),
      ...pos.map(po => ({ id: po.id, group: "po", name: po.name, radius: 18 }))
    ];

    const links: any[] = [];
    cos.forEach(co => {
      pos.forEach(po => {
        const val = mapping[co.id]?.[po.id] || 0;
        if (val > 0) {
          links.push({ source: co.id, target: po.id, value: val });
        }
      });
    });

    const svg = d3.select(svgRef.current)
      .attr("viewBox", [0, 0, width, height]);
      
    // Defs for gradients/glow
    const defs = svg.append("defs");
    const filter = defs.append("filter").attr("id", "glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "2.5").attr("result", "coloredBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // Simulation
    const simulation = d3.forceSimulation(nodes as any)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius((d: any) => d.radius + 10).iterations(2));

    // Links
    const link = svg.append("g")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d: any) => d.value === 3 ? "#7C3AED" : d.value === 2 ? "#1D4ED8" : "#06B6D4")
      .attr("stroke-width", (d: any) => Math.sqrt(d.value) * 1.5)
      .style("filter", "url(#glow)");

    // Nodes container
    const node = svg.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(d3.drag<any, any>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Node circles
    node.append("circle")
      .attr("r", (d: any) => d.radius)
      .attr("fill", (d: any) => d.group === "co" ? "#0F172A" : "#FFFFFF")
      .attr("stroke", (d: any) => d.group === "co" ? "#06B6D4" : "#1D4ED8")
      .attr("stroke-width", 2)
      .style("filter", "url(#glow)");

    // Node labels
    node.append("text")
      .text((d: any) => d.name)
      .attr("x", 0)
      .attr("y", 4)
      .attr("text-anchor", "middle")
      .attr("fill", (d: any) => d.group === "co" ? "#FFFFFF" : "#0F172A")
      .attr("font-family", "monospace")
      .attr("font-size", "10px")
      .attr("font-weight", "bold");

    // Node hover interactions
    node.on("mouseover", function(event, d) {
       d3.select(this).select("circle").attr("stroke", "#7C3AED").attr("stroke-width", 3);
       link.style("stroke-opacity", (l: any) => l.source.id === d.id || l.target.id === d.id ? 1 : 0.1);
    })
    .on("mouseout", function(event, d) {
       d3.select(this).select("circle").attr("stroke", (d: any) => d.group === "co" ? "#06B6D4" : "#1D4ED8").attr("stroke-width", 2);
       link.style("stroke-opacity", 0.6);
    });

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: any) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [cos, pos, mapping]);

  return (
    <div className="w-full bg-cosmic border border-white/10 rounded-3xl overflow-hidden shadow-2xl relative h-[400px]">
       <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-brand/10 to-transparent pointer-events-none" />
       <svg ref={svgRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
       
       <div className="absolute top-4 left-6 flex gap-4 text-xs font-mono">
         <div className="flex items-center gap-2 text-aurora">
           <div className="w-3 h-3 rounded-full border-2 border-aurora bg-cosmic" /> CO Node
         </div>
         <div className="flex items-center gap-2 text-brand">
           <div className="w-3 h-3 rounded-full border-2 border-brand bg-white" /> PO Node
         </div>
       </div>
    </div>
  );
}
