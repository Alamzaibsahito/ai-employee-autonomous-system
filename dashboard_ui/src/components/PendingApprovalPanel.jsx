import React from 'react';
import { Clock, FileText, AlertCircle, CheckCircle, XCircle, Shield } from 'lucide-react';

/**
 * Pending Approval Panel Component
 * Displays pending approval items in a side panel
 */
const PendingApprovalPanel = ({ approvals }) => {
  if (!approvals || approvals.length === 0) {
    return (
      <div className="glass-elevated rounded-xl p-6 h-full border border-white/10">
        <h2 className="text-base font-semibold text-white mb-6 flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-purple-500/20">
            <Clock size={18} className="text-purple-400" strokeWidth={2.5} />
          </div>
          Pending Approval
        </h2>
        <div className="text-center py-12">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
            <CheckCircle size={32} className="text-emerald-500" strokeWidth={1.5} />
          </div>
          <p className="text-gray-300 font-medium">No pending approvals</p>
          <p className="text-gray-600 text-sm mt-1">All caught up!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-elevated rounded-xl p-6 h-full border border-white/10">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-base font-semibold text-white flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-purple-500/20">
            <Clock size={18} className="text-purple-400" strokeWidth={2.5} />
          </div>
          Pending Approval
        </h2>
        <span className="text-xs font-semibold text-amber-400 bg-amber-500/15 px-2.5 py-1 rounded-full border border-amber-500/30">
          {approvals.length} pending
        </span>
      </div>

      <div className="space-y-3 overflow-y-auto max-h-[600px] pr-1 -mr-1">
        {approvals.map((approval, index) => (
          <div
            key={index}
            className="glass-elevated p-4 rounded-xl border border-white/10 hover:border-purple-500/30 
                       transition-all duration-200 hover:bg-white/[0.05] group"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2.5 flex-1 min-w-0">
                <div className="p-2 rounded-lg bg-purple-500/10 group-hover:bg-purple-500/20 transition-colors">
                  <FileText size={14} className="text-purple-400" strokeWidth={2} />
                </div>
                <span className="text-sm font-medium text-white truncate flex-1">
                  {approval.file}
                </span>
              </div>
            </div>

            {/* Type Badge */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[10px] font-semibold px-2 py-1 rounded bg-purple-500/15 text-purple-400 border border-purple-500/30 uppercase tracking-wider">
                {approval.action_type}
              </span>
            </div>

            {/* Summary */}
            <p className="text-xs text-gray-500 line-clamp-2 mb-4 leading-relaxed">
              {approval.summary}
            </p>

            {/* Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-white/10">
              <div className="flex items-center gap-1.5 text-xs text-gray-500">
                <Clock size={12} strokeWidth={2.5} />
                <span className="font-mono">{approval.created_at}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  className="flex items-center justify-center w-7 h-7 rounded-lg bg-emerald-500/15 text-emerald-400 
                           hover:bg-emerald-500/25 hover:scale-105 transition-all duration-200 border border-emerald-500/30"
                  title="Approve"
                >
                  <CheckCircle size={14} strokeWidth={2.5} />
                </button>
                <button
                  className="flex items-center justify-center w-7 h-7 rounded-lg bg-red-500/15 text-red-400 
                           hover:bg-red-500/25 hover:scale-105 transition-all duration-200 border border-red-500/30"
                  title="Reject"
                >
                  <XCircle size={14} strokeWidth={2.5} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Info Footer */}
      <div className="mt-5 pt-4 border-t border-white/10">
        <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <Shield size={14} className="text-amber-400 mt-0.5 flex-shrink-0" strokeWidth={2.5} />
          <div>
            <p className="text-xs font-medium text-amber-400">Human Verification Required</p>
            <p className="text-[10px] text-amber-500/80 mt-0.5">All approvals require manual review before processing</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PendingApprovalPanel;
