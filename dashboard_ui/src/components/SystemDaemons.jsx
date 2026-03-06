import React from 'react';
import { Server, Cpu, MemoryStick, Clock, Activity, Wifi, WifiOff } from 'lucide-react';

/**
 * Daemon Card Component
 * Displays status of a single daemon/service
 */
const DaemonCard = ({ name, status, uptime, ram_usage, cpu_usage }) => {
  const isOnline = status === 'ONLINE';
  const cpuPercent = parseFloat(cpu_usage) || 0;

  return (
    <div
      className={`glass-elevated rounded-xl p-4 border transition-all duration-300 group
                  ${isOnline 
                    ? 'border-emerald-500/20 hover:border-emerald-500/40 hover:shadow-lg hover:shadow-emerald-500/5' 
                    : 'border-red-500/20 hover:border-red-500/40 hover:shadow-lg hover:shadow-red-500/5'
                  }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className={`p-2 rounded-lg ${isOnline ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
            {isOnline ? (
              <Wifi size={18} className="text-emerald-400" strokeWidth={2.5} />
            ) : (
              <WifiOff size={18} className="text-red-400" strokeWidth={2.5} />
            )}
          </div>
          <span className="font-semibold text-white capitalize tracking-tight">{name}</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full status-dot ${
              isOnline ? 'bg-emerald-500 shadow-lg shadow-emerald-500/50' : 'bg-red-500 shadow-lg shadow-red-500/50'
            }`}
          />
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
              isOnline
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-red-500/20 text-red-400 border border-red-500/30'
            }`}
          >
            {status}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="space-y-3">
        {/* Uptime */}
        <div className="flex items-center gap-2.5 text-xs">
          <div className="p-1.5 rounded bg-white/5">
            <Clock size={12} className="text-gray-500" strokeWidth={2.5} />
          </div>
          <span className="text-gray-500 font-medium">Uptime:</span>
          <span className={`text-sm font-mono font-semibold ${isOnline ? 'text-white' : 'text-gray-600'}`}>{uptime}</span>
        </div>

        {/* RAM Usage */}
        <div className="flex items-center gap-2.5 text-xs">
          <div className="p-1.5 rounded bg-white/5">
            <MemoryStick size={12} className="text-gray-500" strokeWidth={2.5} />
          </div>
          <span className="text-gray-500 font-medium">RAM:</span>
          <span className={`text-sm font-mono font-semibold ${isOnline ? 'text-cyan-400' : 'text-gray-600'}`}>
            {ram_usage}
          </span>
        </div>

        {/* CPU Usage */}
        <div className="flex items-center gap-2.5 text-xs">
          <div className="p-1.5 rounded bg-white/5">
            <Cpu size={12} className="text-gray-500" strokeWidth={2.5} />
          </div>
          <span className="text-gray-500 font-medium">CPU:</span>
          <span className={`text-sm font-mono font-semibold ${isOnline ? 'text-purple-400' : 'text-gray-600'}`}>
            {cpu_usage}
          </span>
        </div>

        {/* Progress bar for CPU */}
        {isOnline && (
          <div className="pt-1">
            <div className="flex items-center justify-between text-[10px] mb-1.5">
              <span className="text-gray-500 font-medium uppercase tracking-wider">Load</span>
              <span className="text-gray-400 font-mono">{cpu_usage}</span>
            </div>
            <div className="h-2 bg-gray-800/50 rounded-full overflow-hidden border border-white/5">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  cpuPercent < 50 
                    ? 'bg-gradient-to-r from-emerald-500 to-cyan-500' 
                    : cpuPercent < 80 
                    ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                    : 'bg-gradient-to-r from-red-500 to-rose-500'
                }`}
                style={{ width: `${Math.min(cpuPercent, 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * System Daemons Section Component
 * Displays all daemon cards in a grid
 */
const SystemDaemons = ({ daemons }) => {
  if (!daemons || daemons.length === 0) {
    return (
      <div className="glass-elevated rounded-xl p-6 border border-white/10">
        <h2 className="text-base font-semibold text-white mb-5 flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-cyan-500/20">
            <Activity size={18} className="text-cyan-400" strokeWidth={2.5} />
          </div>
          System Daemons
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="glass-elevated rounded-xl p-4 skeleton">
              <div className="h-4 bg-white/10 rounded w-28 mb-3"></div>
              <div className="space-y-2">
                <div className="h-3 bg-white/10 rounded w-full"></div>
                <div className="h-3 bg-white/10 rounded w-3/4"></div>
                <div className="h-3 bg-white/10 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const onlineCount = daemons.filter(d => d.status === 'ONLINE').length;

  return (
    <div className="glass-elevated rounded-xl p-6 border border-white/10">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-base font-semibold text-white flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-cyan-500/20">
            <Activity size={18} className="text-cyan-400" strokeWidth={2.5} />
          </div>
          System Daemons
        </h2>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-gray-400">
            <span className="text-white font-semibold">{onlineCount}</span>/{daemons.length} Online
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {daemons.map((daemon, index) => (
          <DaemonCard key={index} {...daemon} />
        ))}
      </div>
    </div>
  );
};

export default SystemDaemons;
