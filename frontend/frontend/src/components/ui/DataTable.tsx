"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import { 
  ChevronLeft, ChevronRight, 
  ArrowUp, ArrowDown, 
  ChevronsUpDown, 
  Search, Filter, 
  ChevronDown, ChevronUp,
  GripVertical
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export interface Column<T> {
  id: string;
  header: string;
  accessor: (item: T) => any;
  sortable?: boolean;
  resizable?: boolean;
  width?: number;
  sticky?: "left" | "right";
  render?: (val: any, item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  pageSize?: number;
  stickyHeader?: boolean;
  rowHoverHighlight?: boolean;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
  expandableRow?: (item: T) => React.ReactNode;
  freezeFirstColumn?: boolean;
}

export function DataTable<T>({
  data,
  columns: initialColumns,
  pageSize = 25,
  stickyHeader = true,
  rowHoverHighlight = true,
  emptyMessage = "No data found matching your filters",
  onRowClick,
  expandableRow,
  freezeFirstColumn = false
}: DataTableProps<T>) {
  // --- STATE ---
  const [currentPage, setCurrentPage] = useState(1);
  const [sortConfig, setSortConfig] = useState<{ id: string; direction: "asc" | "desc" }[]>([]);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(
    Object.fromEntries(initialColumns.map(c => [c.id, c.width || 150]))
  );
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState("");

  // --- REFS FOR RESIZING ---
  const resizingColumn = useRef<string | null>(null);
  const startX = useRef<number>(0);
  const startWidth = useRef<number>(0);

  // --- SEARCH & FILTER ---
  const filteredData = useMemo(() => {
    if (!searchTerm) return data;
    return data.filter(item => {
      return initialColumns.some(col => {
        const val = col.accessor(item);
        return String(val).toLowerCase().includes(searchTerm.toLowerCase());
      });
    });
  }, [data, searchTerm, initialColumns]);

  // --- SORTING ---
  const sortedData = useMemo(() => {
    if (sortConfig.length === 0) return filteredData;

    return [...filteredData].sort((a, b) => {
      for (const sort of sortConfig) {
        const col = initialColumns.find(c => c.id === sort.id);
        if (!col) continue;

        const valA = col.accessor(a);
        const valB = col.accessor(b);

        if (valA < valB) return sort.direction === "asc" ? -1 : 1;
        if (valA > valB) return sort.direction === "asc" ? 1 : -1;
      }
      return 0;
    });
  }, [filteredData, sortConfig, initialColumns]);

  // --- PAGINATION ---
  const totalPages = Math.ceil(sortedData.length / pageSize);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize]);

  // --- HANDLERS ---
  const handleSort = (id: string, multi: boolean) => {
    setSortConfig(prev => {
      const existing = prev.find(s => s.id === id);
      const direction = existing?.direction === "asc" ? "desc" : "asc";

      if (multi) {
        if (existing) {
          return prev.map(s => s.id === id ? { ...s, direction } : s);
        }
        return [...prev, { id, direction: "asc" }];
      }
      
      return [{ id, direction }];
    });
  };

  const handleResizeStart = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    resizingColumn.current = id;
    startX.current = e.pageX;
    startWidth.current = columnWidths[id];

    document.addEventListener("mousemove", handleResizeMove);
    document.addEventListener("mouseup", handleResizeEnd);
  };

  const handleResizeMove = (e: MouseEvent) => {
    if (!resizingColumn.current) return;
    const diff = e.pageX - startX.current;
    setColumnWidths(prev => ({
      ...prev,
      [resizingColumn.current!]: Math.max(50, startWidth.current + diff)
    }));
  };

  const handleResizeEnd = () => {
    resizingColumn.current = null;
    document.removeEventListener("mousemove", handleResizeMove);
    document.removeEventListener("mouseup", handleResizeEnd);
  };

  const toggleRow = (idx: number) => {
    const next = new Set(expandedRows);
    if (next.has(idx)) next.delete(idx);
    else next.add(idx);
    setExpandedRows(next);
  };

  const expandAll = () => setExpandedRows(new Set(paginatedData.map((_, i) => i)));
  const collapseAll = () => setExpandedRows(new Set());

  return (
    <div className="flex flex-col gap-4">
      
      {/* ── SEARCH & UTILS ── */}
      <div className="flex justify-between items-center px-4">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
            <input 
              type="text" 
              placeholder="Filter table..." 
              className="bg-white/5 border border-white/10 rounded-lg py-2 pl-10 pr-4 text-xs text-white profile: focus:border-brand outline-none transition-all w-64"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          {expandableRow && (
            <div className="flex gap-4">
              <button onClick={expandAll} className="text-[10px] font-mono text-brand hover:underline uppercase tracking-widest">Expand All</button>
              <button onClick={collapseAll} className="text-[10px] font-mono text-white/20 hover:text-white uppercase tracking-widest">Collapse All</button>
            </div>
          )}
        </div>
        <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">
          Showing <span className="text-white font-bold">{Math.min(paginatedData.length, sortedData.length)}</span> of <span className="text-white font-bold">{sortedData.length}</span> entries
        </div>
      </div>

      {/* ── TABLE CONTAINER (FLATTENED) ── */}
      <div className="overflow-x-auto custom-scrollbar relative">
        <table className="w-full text-left border-collapse table-fixed">
          <thead className={`${stickyHeader ? 'sticky top-0 z-20' : ''} bg-[#0b0b0f]`}>
            <tr>
              {expandableRow && <th className="w-10 p-4 border-b border-white/10"></th>}
              {initialColumns.map((col, i) => {
                const sort = sortConfig.find(s => s.id === col.id);
                const sortIndex = sortConfig.findIndex(s => s.id === col.id);
                const isFrozen = freezeFirstColumn && i === 0;

                return (
                  <th 
                    key={col.id} 
                    style={{ width: columnWidths[col.id], left: isFrozen ? 0 : 'auto' }}
                    className={`p-4 border-b border-white/10 group relative select-none ${isFrozen ? 'sticky left-0 z-30 bg-[#0d0d12] border-r' : ''}`}
                  >
                    <div className="flex items-center justify-between gap-2 overflow-hidden">
                      <div 
                        className={`flex items-center gap-2 flex-1 cursor-pointer truncate ${col.sortable ? 'hover:text-brand transition-colors' : ''}`}
                        onClick={(e) => col.sortable && handleSort(col.id, e.shiftKey)}
                      >
                        <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest truncate group-hover:text-white/60">
                          {col.header}
                        </span>
                        {col.sortable && (
                          <div className="shrink-0 flex items-center gap-1">
                            {sort ? (
                              sort.direction === "asc" ? <ArrowUp className="w-3 h-3 text-brand" /> : <ArrowDown className="w-3 h-3 text-brand" />
                            ) : (
                              <ChevronsUpDown className="w-3 h-3 text-white/5 opacity-0 group-hover:opacity-100" />
                            )}
                            {sortConfig.length > 1 && sortIndex !== -1 && (
                              <span className="text-[8px] font-mono bg-brand/20 text-brand rounded px-1">{sortIndex + 1}</span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* RESIZE HANDLE */}
                      {col.resizable !== false && (
                        <div 
                          onMouseDown={(e) => handleResizeStart(e, col.id)}
                          className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-brand/50 active:bg-brand transition-colors z-10"
                        />
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            <AnimatePresence mode="popLayout">
              {paginatedData.length === 0 ? (
                <tr>
                  <td colSpan={initialColumns.length + (expandableRow ? 1 : 0)} className="p-12 text-center text-xs text-white/20 italic">
                    {emptyMessage}
                  </td>
                </tr>
              ) : (
                paginatedData.map((item, idx) => (
                  <React.Fragment key={idx}>
                    <motion.tr 
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      onClick={() => onRowClick?.(item)}
                      className={`group transition-colors ${rowHoverHighlight ? 'hover:bg-white/[0.02]' : ''} ${onRowClick ? 'cursor-pointer' : ''}`}
                    >
                      {expandableRow && (
                        <td className="p-4 text-center">
                          <button onClick={(e) => { e.stopPropagation(); toggleRow(idx); }} className="text-white/20 hover:text-white">
                            {expandedRows.has(idx) ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                          </button>
                        </td>
                      )}
                      {initialColumns.map((col, i) => {
                        const val = col.accessor(item);
                        const isFrozen = freezeFirstColumn && i === 0;
                        return (
                          <td 
                            key={col.id} 
                            style={{ left: isFrozen ? 0 : 'auto' }}
                            className={`p-4 text-xs text-white/60 font-light truncate ${isFrozen ? 'sticky left-0 z-10 bg-[#0d0d12] border-r group-hover:bg-[#15151b]' : ''}`}
                          >
                            {col.render ? col.render(val, item) : String(val)}
                          </td>
                        );
                      })}
                    </motion.tr>
                    {expandableRow && expandedRows.has(idx) && (
                      <tr>
                        <td colSpan={initialColumns.length + 1} className="p-0 border-b border-white/5">
                          <motion.div 
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="bg-white/[0.01] overflow-hidden"
                          >
                            <div className="p-6">
                              {expandableRow(item)}
                            </div>
                          </motion.div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      {/* ── PAGINATION CONTROLS ── */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center px-4 py-2 border-t border-white/10 pt-6">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-white/20 uppercase">Go to page</span>
            <input 
              type="number" 
              min="1" 
              max={totalPages}
              value={currentPage}
              onChange={(e) => {
                const p = parseInt(e.target.value);
                if (p >= 1 && p <= totalPages) setCurrentPage(p);
              }}
              className="bg-white/5 border border-white/10 rounded px-2 py-1 text-[10px] font-mono text-brand outline-none focus:border-brand w-12 text-center"
            />
          </div>
          <div className="flex items-center gap-4">
            <button 
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              className="p-2 bg-white/5 border border-white/10 rounded-lg text-white/40 disabled:opacity-20 hover:bg-white/10 transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <div className="flex gap-2">
              {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                let pageNum = i + 1;
                if (totalPages > 5 && currentPage > 3) {
                  pageNum = currentPage - 3 + i;
                  if (pageNum + 5 > totalPages) pageNum = totalPages - 4;
                }
                if (pageNum <= 0) pageNum = i + 1;
                if (pageNum > totalPages) return null;

                return (
                  <button 
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`w-8 h-8 rounded-lg text-[10px] font-mono transition-all ${
                      currentPage === pageNum ? 'bg-brand text-white' : 'bg-white/5 text-white/20 hover:text-white'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            <button 
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              className="p-2 bg-white/5 border border-white/10 rounded-lg text-white/40 disabled:opacity-20 hover:bg-white/10 transition-all"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
