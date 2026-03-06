import React from 'react';
import { FileText, TrendingUp, CheckCircle2, Clock, ArrowUpRight, AlertCircle } from 'lucide-react';

// Status badge colors
const statusColors = {
  NEW: { bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30', dot: 'bg-blue-500' },
  PENDING: { bg: 'bg-amber-500/15', text: 'text-amber-400', border: 'border-amber-500/30', dot: 'bg-amber-500' },
  AWAITING_APPROVAL: { bg: 'bg-purple-500/15', text: 'text-purple-400', border: 'border-purple-500/30', dot: 'bg-purple-500' },
  COMPLETED: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/30', dot: 'bg-emerald-500' },
  REVIEW_NEEDED: { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-500' },
  UNKNOWN: { bg: 'bg-gray-500/15', text: 'text-gray-400', border: 'border-gray-500/30', dot: 'bg-gray-500' },
};

/**
 * Recent Tasks Table Component
 * Displays recent tasks in a table format
 */
const RecentTasksTable = ({ tasks }) => {
  if (!tasks || tasks.length === 0) {
    return (
      <div className="glass-elevated rounded-xl p-8 border border-white/10">
        <h2 className="text-base font-semibold text-white mb-6 flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-500/20">
            <FileText size={18} className="text-blue-400" strokeWidth={2.5} />
          </div>
          Recent Tasks
        </h2>
        <div className="text-center py-12">
          <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-4">
            <FileText size={32} className="text-gray-600" strokeWidth={1.5} />
          </div>
          <p className="text-gray-400 font-medium">No recent tasks found</p>
          <p className="text-gray-600 text-sm mt-1">Tasks will appear here as they are processed</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-elevated rounded-xl border border-white/10 overflow-hidden">
      <div className="p-5 border-b border-white/10">
        <h2 className="text-base font-semibold text-white flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-500/20">
            <FileText size={18} className="text-blue-400" strokeWidth={2.5} />
          </div>
          Recent Tasks
          <span className="ml-auto text-xs font-medium text-gray-500 bg-white/5 px-2.5 py-1 rounded-full border border-white/10">
            {tasks.length} tasks
          </span>
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.02]">
              <th className="text-left py-3.5 px-5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                File
              </th>
              <th className="text-left py-3.5 px-5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                Intent
              </th>
              <th className="text-center py-3.5 px-5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                Confidence
              </th>
              <th className="text-center py-3.5 px-5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="text-right py-3.5 px-5 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                Modified Time
              </th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task, index) => {
              const statusColor = statusColors[task.status] || statusColors.UNKNOWN;
              return (
                <tr
                  key={index}
                  className="border-b border-white/5 hover:bg-white/[0.03] transition-colors duration-150 last:border-b-0"
                >
                  <td className="py-3.5 px-5">
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded bg-blue-500/10">
                        <FileText size={14} className="text-blue-400" strokeWidth={2} />
                      </div>
                      <span className="text-sm text-gray-300 font-mono truncate max-w-[220px]">
                        {task.file}
                      </span>
                    </div>
                  </td>
                  <td className="py-3.5 px-5">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm text-gray-400">{task.intent}</span>
                      <ArrowUpRight size={12} className="text-gray-600" />
                    </div>
                  </td>
                  <td className="py-3.5 px-5 text-center">
                    <div className="flex items-center justify-center gap-1.5">
                      <TrendingUp size={14} className="text-emerald-400" strokeWidth={2.5} />
                      <span className="text-sm font-mono font-semibold text-emerald-400">
                        {task.confidence.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="py-3.5 px-5 text-center">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${statusColor.bg} ${statusColor.text} ${statusColor.border}`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${statusColor.dot}`} />
                      {task.status === 'COMPLETED' ? (
                        <CheckCircle2 size={10} strokeWidth={3} />
                      ) : task.status === 'PENDING' || task.status === 'AWAITING_APPROVAL' ? (
                        <Clock size={10} strokeWidth={3} />
                      ) : task.status === 'REVIEW_NEEDED' ? (
                        <AlertCircle size={10} strokeWidth={3} />
                      ) : null}
                      {task.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-5 text-right">
                    <span className="text-xs text-gray-500 font-mono">
                      {task.modified_time}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default RecentTasksTable;
