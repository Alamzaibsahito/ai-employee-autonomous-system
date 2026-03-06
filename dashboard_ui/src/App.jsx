import React, { useState, useEffect, useCallback } from 'react';
import { dashboardApi } from './services/api';
import Header from './components/Header';
import StatsRow from './components/StatsRow';
import SystemDaemons from './components/SystemDaemons';
import RecentTasksTable from './components/RecentTasksTable';
import PendingApprovalPanel from './components/PendingApprovalPanel';
import { WifiOff } from 'lucide-react';

// Auto-refresh interval in milliseconds
const AUTO_REFRESH_INTERVAL = 5000;

/**
 * Main Dashboard App Component
 */
function App() {
  // State
  const [dashboardData, setDashboardData] = useState({
    stats: [],
    daemons: [],
    recent_tasks: [],
    pending_approvals: [],
  });
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [dryRun, setDryRun] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  /**
   * Fetch dashboard data from API
   */
  const fetchDashboardData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await dashboardApi.getDashboardData(dryRun);
      setDashboardData({
        stats: data.stats || [],
        daemons: data.daemons || [],
        recent_tasks: data.recent_tasks || [],
        pending_approvals: data.pending_approvals || [],
      });
      setLastRefreshed(data.last_refreshed || new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Failed to connect to dashboard API. Make sure the backend is running on port 8000.');
    } finally {
      setIsLoading(false);
    }
  }, [dryRun]);

  /**
   * Initial fetch and auto-refresh setup
   */
  useEffect(() => {
    // Initial fetch
    fetchDashboardData();

    // Auto-refresh interval
    const intervalId = setInterval(fetchDashboardData, AUTO_REFRESH_INTERVAL);

    // Cleanup
    return () => clearInterval(intervalId);
  }, [fetchDashboardData]);

  /**
   * Handle manual refresh
   */
  const handleRefresh = () => {
    fetchDashboardData();
  };

  /**
   * Toggle dry run mode
   */
  const handleToggleDryRun = () => {
    setDryRun(prev => !prev);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-[#0a0a0f] via-[#0f0f1a] to-[#0a0a14] pointer-events-none" />
      
      {/* Subtle grid pattern overlay */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '60px 60px'
        }}
      />

      {/* Ambient glow effects */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 right-1/4 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Main content */}
      <div className="relative z-10">
        {/* Header */}
        <Header
          onRefresh={handleRefresh}
          lastRefreshed={lastRefreshed}
          dryRun={dryRun}
          onToggleDryRun={handleToggleDryRun}
          isLoading={isLoading}
        />

        {/* Dashboard Content */}
        <main className="max-w-[1800px] mx-auto px-6 py-6 space-y-6">
          {/* Error Banner */}
          {error && (
            <div className="glass-elevated border border-red-500/30 bg-red-500/10 rounded-xl p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/20">
                <WifiOff size={18} className="text-red-400" strokeWidth={2.5} />
              </div>
              <div className="flex-1">
                <p className="text-red-400 text-sm font-medium">{error}</p>
              </div>
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            </div>
          )}

          {/* Stats Row */}
          <section aria-label="Dashboard Statistics">
            <StatsRow stats={dashboardData.stats} />
          </section>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Daemons and Tasks */}
            <div className="lg:col-span-2 space-y-6">
              {/* System Daemons */}
              <section aria-label="System Daemons">
                <SystemDaemons daemons={dashboardData.daemons} />
              </section>

              {/* Recent Tasks */}
              <section aria-label="Recent Tasks">
                <RecentTasksTable tasks={dashboardData.recent_tasks} />
              </section>
            </div>

            {/* Right Column - Pending Approvals */}
            <div className="lg:col-span-1">
              <section aria-label="Pending Approvals" className="sticky top-24">
                <PendingApprovalPanel approvals={dashboardData.pending_approvals} />
              </section>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="max-w-[1800px] mx-auto px-6 py-4">
          <div className="glass-elevated rounded-xl px-4 py-3 flex items-center justify-between text-xs border border-white/10">
            <div className="flex items-center gap-4">
              <span className="text-gray-500 font-medium">AI Employee Dashboard</span>
              <span className="hidden sm:inline text-gray-700">•</span>
              <span className="hidden sm:inline text-gray-600">Platinum Tier</span>
              <span className="hidden md:inline text-gray-700">•</span>
              <span className="hidden md:inline text-gray-600 font-mono">v1.0.0</span>
            </div>
            <div className="flex items-center gap-2.5 px-2.5 py-1 rounded-lg bg-white/5 border border-white/10">
              <div className={`w-2 h-2 rounded-full ${error ? 'bg-red-500 shadow-lg shadow-red-500/50' : 'bg-emerald-500 shadow-lg shadow-emerald-500/50 animate-pulse'}`} />
              <span className={`font-medium ${error ? 'text-red-400' : 'text-emerald-400'}`}>
                {error ? 'Disconnected' : 'Connected'}
              </span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
