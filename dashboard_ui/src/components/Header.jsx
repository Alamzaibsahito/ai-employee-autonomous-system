import React from 'react';
import { RefreshCw, ToggleLeft, ToggleRight, Zap } from 'lucide-react';

/**
 * Header Component
 * Displays dashboard title, refresh button, and dry run toggle
 */
const Header = ({ onRefresh, lastRefreshed, dryRun, onToggleDryRun, isLoading }) => {
  return (
    <header className="glass-strong sticky top-0 z-50 border-b border-white/10">
      <div className="max-w-[1800px] mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Title */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center neon-green-glow shadow-lg shadow-emerald-500/20">
                <Zap size={22} className="text-white" fill="white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white tracking-tight">AI Employee Dashboard</h1>
                <p className="text-xs text-gray-500 font-medium">Autonomous FTE Monitoring System</p>
              </div>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-4">
            {/* Last Refreshed */}
            <div className="hidden lg:flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs text-gray-400 font-medium">Last refreshed:</span>
              <span className="text-xs text-emerald-400 font-mono font-semibold">{lastRefreshed || '--:--:--'}</span>
            </div>

            {/* Dry Run Toggle */}
            <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
              <span className="text-xs text-gray-400 font-medium">DRY RUN</span>
              <button
                onClick={onToggleDryRun}
                className={`transition-all duration-300 hover:scale-110 ${
                  dryRun ? 'text-emerald-400' : 'text-gray-600'
                }`}
                title={dryRun ? 'Dry Run Enabled' : 'Dry Run Disabled'}
              >
                {dryRun ? (
                  <ToggleRight size={26} className="neon-green-glow" />
                ) : (
                  <ToggleLeft size={26} />
                )}
              </button>
            </div>

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 hover:border-cyan-400/50 hover:from-cyan-500/30 hover:to-blue-500/30 transition-all duration-200 ${
                isLoading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
              title="Refresh Dashboard"
            >
              <RefreshCw
                size={16}
                className={`text-cyan-400 ${isLoading ? 'animate-spin' : ''}`}
                strokeWidth={2.5}
              />
              <span className="hidden sm:inline text-xs font-semibold text-cyan-100">Refresh</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
