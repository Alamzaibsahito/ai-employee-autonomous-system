import axios from 'axios';

// API base URL
const API_BASE_URL = 'http://localhost:8000';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Dashboard API Service
 * Handles all API calls to the backend
 */
export const dashboardApi = {
  /**
   * Health check
   */
  async healthCheck() {
    const response = await apiClient.get('/health');
    return response.data;
  },

  /**
   * Get dashboard statistics
   */
  async getStats() {
    const response = await apiClient.get('/api/stats');
    return response.data;
  },

  /**
   * Get system daemon status
   */
  async getDaemons() {
    const response = await apiClient.get('/api/daemons');
    return response.data;
  },

  /**
   * Get recent tasks
   */
  async getRecentTasks(limit = 10) {
    const response = await apiClient.get('/api/tasks/recent', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Get pending approvals
   */
  async getPendingApprovals() {
    const response = await apiClient.get('/api/approvals/pending');
    return response.data;
  },

  /**
   * Get complete dashboard data
   */
  async getDashboardData(dryRun = false) {
    const response = await apiClient.get('/api/dashboard', {
      params: { dry_run: dryRun },
    });
    return response.data;
  },

  /**
   * Get folder information
   */
  async getFolderInfo() {
    const response = await apiClient.get('/api/folders');
    return response.data;
  },
};

export default apiClient;
