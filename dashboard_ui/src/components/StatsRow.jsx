import React from 'react';
import {
  Inbox,
  AlertCircle,
  Clock,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';

// Icon mapping
const iconMap = {
  Inbox: Inbox,
  AlertCircle: AlertCircle,
  Clock: Clock,
  CheckCircle: CheckCircle,
  AlertTriangle: AlertTriangle,
};

// Color mapping - Modern gradient scheme
const colorMap = {
  blue: {
    gradient: 'from-blue-500/20 to-cyan-500/20',
    border: 'border-blue-500/30',
    iconBg: 'bg-gradient-to-br from-blue-500 to-cyan-500',
    text: 'text-blue-400',
    glow: 'shadow-blue-500/10',
    valueColor: 'text-blue-100',
  },
  amber: {
    gradient: 'from-amber-500/20 to-orange-500/20',
    border: 'border-amber-500/30',
    iconBg: 'bg-gradient-to-br from-amber-500 to-orange-500',
    text: 'text-amber-400',
    glow: 'shadow-amber-500/10',
    valueColor: 'text-amber-100',
  },
  purple: {
    gradient: 'from-purple-500/20 to-pink-500/20',
    border: 'border-purple-500/30',
    iconBg: 'bg-gradient-to-br from-purple-500 to-pink-500',
    text: 'text-purple-400',
    glow: 'shadow-purple-500/10',
    valueColor: 'text-purple-100',
  },
  green: {
    gradient: 'from-emerald-500/20 to-green-500/20',
    border: 'border-emerald-500/30',
    iconBg: 'bg-gradient-to-br from-emerald-500 to-green-500',
    text: 'text-emerald-400',
    glow: 'shadow-emerald-500/10',
    valueColor: 'text-emerald-100',
  },
  red: {
    gradient: 'from-red-500/20 to-rose-500/20',
    border: 'border-red-500/30',
    iconBg: 'bg-gradient-to-br from-red-500 to-rose-500',
    text: 'text-red-400',
    glow: 'shadow-red-500/10',
    valueColor: 'text-red-100',
  },
};

/**
 * Stats Card Component
 * Displays a single statistic card
 */
const StatsCard = ({ label, value, icon, color }) => {
  const IconComponent = iconMap[icon] || Inbox;
  const colors = colorMap[color] || colorMap.blue;

  return (
    <div
      className={`glass-elevated rounded-2xl p-5 border ${colors.border} bg-gradient-to-br ${colors.gradient}
                  transition-all duration-300 hover:scale-[1.02] hover:shadow-xl ${colors.glow} group`}
    >
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">{label}</p>
          <p className={`text-4xl font-bold ${colors.valueColor} tracking-tight`}>{value}</p>
        </div>
        <div className={`p-3 rounded-xl ${colors.iconBg} shadow-lg group-hover:scale-110 transition-transform duration-300`}>
          <IconComponent size={22} className="text-white" strokeWidth={2.5} />
        </div>
      </div>
    </div>
  );
};

/**
 * Stats Row Component
 * Displays all statistics cards in a row
 */
const StatsRow = ({ stats }) => {
  if (!stats || stats.length === 0) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="glass-elevated rounded-2xl p-5 skeleton">
            <div className="h-3 bg-white/10 rounded w-20 mb-3"></div>
            <div className="h-10 bg-white/10 rounded w-16"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {stats.map((stat, index) => (
        <StatsCard key={index} {...stat} />
      ))}
    </div>
  );
};

export default StatsRow;
