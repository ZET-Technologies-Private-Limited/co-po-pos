'use client';

import React, { useRef, useEffect } from 'react';
import { useTableTabNavigation } from '@/lib/useFormFeatures';

interface TableInputCell {
  id: string;
  value: string | number;
  placeholder?: string;
  integerOnly?: boolean;
}

interface MarksEntryTableProps {
  headers: string[];
  rows: TableInputCell[][];
  onCellChange: (rowIndex: number, colIndex: number, value: string) => void;
  onRowAdd?: () => void;
}

/**
 * SF-10: Tab Key Navigation Table
 * Tab moves to next column, Enter/Tab at end moves to next row
 */
export const MarksEntryTable: React.FC<MarksEntryTableProps> = ({
  headers,
  rows,
  onCellChange,
  onRowAdd,
}) => {
  const { focusedCell, handleKeyDown } = useTableTabNavigation(
    rows.length,
    rows[0]?.length || 0
  );
  const inputRefs = useRef<(HTMLInputElement | null)[][]>(
    rows.map(() => [])
  );

  useEffect(() => {
    const [row, col] = focusedCell;
    const input = inputRefs.current[row]?.[col];
    if (input) {
      input.focus();
    }
  }, [focusedCell]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10">
            {headers.map((header, idx) => (
              <th
                key={idx}
                className="px-4 py-2 text-left text-white/70 font-semibold whitespace-nowrap"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} className="border-b border-white/5">
              {row.map((cell, colIdx) => (
                <td key={colIdx} className="px-4 py-2">
                  <input
                    ref={(el) => {
                      if (!inputRefs.current[rowIdx]) {
                        inputRefs.current[rowIdx] = [];
                      }
                      inputRefs.current[rowIdx][colIdx] = el;
                    }}
                    type={cell.integerOnly ? 'number' : 'text'}
                    value={cell.value}
                    placeholder={cell.placeholder}
                    onChange={(e) => {
                      let newValue = e.target.value;
                      if (cell.integerOnly) {
                        newValue = newValue.replace(/[^\d]/g, '');
                      }
                      onCellChange(rowIdx, colIdx, newValue);
                    }}
                    onKeyDown={(e) => handleKeyDown(e, rowIdx, colIdx)}
                    className="w-full px-2 py-1 bg-white/5 border border-white/10 rounded text-white placeholder-white/30 outline-none focus:border-brand transition-colors"
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default MarksEntryTable;
