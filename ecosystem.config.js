/**
 * ============================================================
 * Platinum Tier - PM2 Ecosystem Configuration
 * ============================================================
 * Production process manager for AI Employee system
 * 
 * Features:
 * - Auto-restart on crash
 * - Auto-start on reboot
 * - Log rotation
 * - Memory monitoring
 * - Cluster mode support
 *
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 stop ecosystem.config.js
 *   pm2 restart ecosystem.config.js
 *   pm2 status
 *   pm2 logs
 *   pm2 monit
 * ============================================================
 */

module.exports = {
  apps: [
    {
      name: 'file_watcher',
      script: './file_watcher.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: './Logs/central/file_watcher.error.log',
      out_file: './Logs/central/file_watcher.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'process_tasks',
      script: './process_tasks.py',
      interpreter: 'python',
      interpreter_args: '-u',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: './Logs/central/process_tasks.error.log',
      out_file: './Logs/central/process_tasks.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
      },
    },
    {
      name: 'ralph_loop',
      script: './skills/ralph_loop.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      error_file: './Logs/central/ralph_loop.error.log',
      out_file: './Logs/central/ralph_loop.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'health_monitor',
      script: './platinum/health_monitor.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      error_file: './Logs/central/health_monitor.error.log',
      out_file: './Logs/central/health_monitor.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'gmail_mcp',
      script: './mcp_servers/gmail_mcp/server.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: './Logs/central/gmail_mcp.error.log',
      out_file: './Logs/central/gmail_mcp.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'linkedin_mcp',
      script: './mcp_servers/linkedin_mcp/server.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: './Logs/central/linkedin_mcp.error.log',
      out_file: './Logs/central/linkedin_mcp.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'odoo_mcp',
      script: './mcp_servers/odoo_mcp/server.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: './Logs/central/odoo_mcp.error.log',
      out_file: './Logs/central/odoo_mcp.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'twitter_mcp',
      script: './mcp_servers/social_mcp/twitter_server.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '400M',
      error_file: './Logs/central/twitter_mcp.error.log',
      out_file: './Logs/central/twitter_mcp.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'facebook_mcp',
      script: './mcp_servers/social_mcp/facebook_server.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '400M',
      error_file: './Logs/central/facebook_mcp.error.log',
      out_file: './Logs/central/facebook_mcp.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      name: 'instagram_mcp',
      script: './mcp_servers/social_mcp/instagram_server.py',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '400M',
      error_file: './Logs/central/instagram_mcp.error.log',
      out_file: './Logs/central/instagram_mcp.out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
  ],
};
