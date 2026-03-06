/**
 * WhatsApp Watcher MCP Skill
 * 
 * Monitors WhatsApp Web for incoming messages and routes them to the AI Employee Vault.
 * Designed for production use with logging, error handling, and session persistence.
 * 
 * @module whatsapp-watcher
 */

'use strict';

// Load environment variables first
require('dotenv').config();

const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode-terminal');
const winston = require('winston');
const fs = require('fs');
const path = require('path');

// =============================================================================
// Configuration - Environment Variable Based
// =============================================================================

const CONFIG = {
  // Paths
  BASE_DIR: process.env.WHATSAPP_BASE_DIR || path.resolve(__dirname, '..', '..'),
  SESSION_PATH: process.env.WHATSAPP_SESSION_PATH || path.resolve(__dirname, '..', 'sessions'),
  VAULT_PATH: process.env.WHATSAPP_VAULT_PATH || path.resolve(__dirname, '..', '..', '..', 'AI_Employee_Vault', 'Needs_Action', 'whatsapp'),
  LOG_PATH: process.env.WHATSAPP_LOG_PATH || path.resolve(__dirname, '..', '..', '..', 'Logs', 'central'),
  
  // Behavior
  LOG_LEVEL: process.env.WHATSAPP_LOG_LEVEL || 'info',
  MESSAGE_FILE_PREFIX: process.env.WHATSAPP_MESSAGE_PREFIX || 'msg',
  SESSION_NAME: process.env.WHATSAPP_SESSION_NAME || 'whatsapp-session',
  
  // Timing
  RECONNECT_DELAY: parseInt(process.env.WHATSAPP_RECONNECT_DELAY || '5000', 10),
  MAX_RECONNECT_ATTEMPTS: parseInt(process.env.WHATSAPP_MAX_RECONNECT_ATTEMPTS || '10', 10),
  
  // Security
  SECURE_MODE: process.env.WHATSAPP_SECURE_MODE !== 'false'
};

// =============================================================================
// Directory Setup
// =============================================================================

function ensureDirectories() {
  const dirs = [
    CONFIG.SESSION_PATH,
    CONFIG.VAULT_PATH,
    CONFIG.LOG_PATH
  ];
  
  for (const dir of dirs) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      console.log(`[SETUP] Created directory: ${dir}`);
    }
  }
}

// =============================================================================
// Logger Setup - Winston
// =============================================================================

function setupLogger() {
  const logFile = path.join(CONFIG.LOG_PATH, 'whatsapp.log');
  
  const logger = winston.createLogger({
    level: CONFIG.LOG_LEVEL,
    format: winston.format.combine(
      winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
      winston.format.errors({ stack: true }),
      winston.format.splat(),
      winston.format.json()
    ),
    defaultMeta: { service: 'whatsapp-watcher' },
    transports: [
      // Console output
      new winston.transports.Console({
        format: winston.format.combine(
          winston.format.colorize(),
          winston.format.simple()
        )
      }),
      // File output
      new winston.transports.File({
        filename: logFile,
        maxsize: 10485760, // 10MB
        maxFiles: 5
      })
    ]
  });
  
  return logger;
}

// =============================================================================
// Message Handler
// =============================================================================

function generateMessageFilename(contactName, timestamp) {
  const safeName = contactName.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 50);
  const dateStr = new Date(timestamp).toISOString().replace(/[:.]/g, '-').substring(0, 19);
  return `${CONFIG.MESSAGE_FILE_PREFIX}_${safeName}_${dateStr}.json`;
}

function saveMessageToVault(messageData, logger) {
  try {
    const filename = generateMessageFilename(
      messageData.contactName || 'Unknown',
      messageData.timestamp
    );
    const filePath = path.join(CONFIG.VAULT_PATH, filename);
    
    fs.writeFileSync(filePath, JSON.stringify(messageData, null, 2), 'utf8');
    logger.info('Message saved to vault', { filePath, contact: messageData.contactName });
    return true;
  } catch (error) {
    logger.error('Failed to save message to vault', { error: error.message, stack: error.stack });
    return false;
  }
}

function processMessage(message, client, logger) {
  // Ignore messages from the same user (bot's own messages)
  if (message.fromMe) {
    logger.debug('Skipping own message', { id: message.id._serialized });
    return;
  }
  
  // Ignore status messages
  if (message.type === 'status' || message.isStatus) {
    logger.debug('Skipping status message', { id: message.id._serialized });
    return;
  }
  
  logger.info('Processing incoming message', {
    from: message.from,
    type: message.type,
    hasMedia: message.hasMedia
  });
  
  // Build message data object
  const messageData = {
    id: message.id._serialized,
    timestamp: message.timestamp,
    receivedAt: new Date().toISOString(),
    from: message.from,
    fromName: message._data?.notify || 'Unknown',
    contactName: message._data?.notify || 'Unknown',
    body: message.body,
    type: message.type,
    hasMedia: message.hasMedia,
    isGroup: message.from.includes('@g.us'),
    groupId: message.from.includes('@g.us') ? message.from : null,
    replyTo: message.hasQuotedMsg ? message._data?.quotedMsg?.id?._serialized : null,
    mentions: message.mentionedIds || [],
    raw: CONFIG.LOG_LEVEL === 'debug' ? message._data : undefined
  };
  
  // Handle media messages
  if (message.hasMedia) {
    messageData.mediaInfo = {
      mimetype: message._data?.mimetype,
      filename: message._data?.filename,
      filesize: message._data?.filesize,
      caption: message.caption || null
    };
    logger.info('Message contains media', {
      mimetype: messageData.mediaInfo.mimetype,
      filesize: messageData.mediaInfo.filesize
    });
  }
  
  // Save to vault
  saveMessageToVault(messageData, logger);
  
  // Optional: Send acknowledgment (can be disabled via env)
  if (process.env.WHATSAPP_SEND_ACK === 'true') {
    client.sendMessage(message.from, '🤖 Message received by AI Employee system. Processing...')
      .catch(err => logger.warn('Failed to send acknowledgment', { error: err.message }));
  }
}

// =============================================================================
// WhatsApp Client Setup
// =============================================================================

let reconnectAttempts = 0;
let client = null;

function createWhatsAppClient(logger) {
  const clientOptions = {
    authStrategy: new LocalAuth({
      clientId: CONFIG.SESSION_NAME,
      dataPath: CONFIG.SESSION_PATH
    }),
    puppeteer: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu'
      ]
    },
    restartOnAuthFail: true,
    takeoverOnConflict: true,
    takeoverTimeoutMs: 0
  };
  
  logger.info('Initializing WhatsApp client', {
    sessionPath: CONFIG.SESSION_PATH,
    secureMode: CONFIG.SECURE_MODE
  });
  
  return new Client(clientOptions);
}

function setupClientEvents(client, logger) {
  // QR Code - First run authentication
  client.on('qr', (qr) => {
    logger.warn('QR Code received - scan to authenticate');
    console.log('\n' + '='.repeat(60));
    console.log('📱 WHATSAPP AUTHENTICATION REQUIRED');
    console.log('='.repeat(60));
    console.log('\nScan the QR code below with WhatsApp mobile app:\n');
    QRCode.generate(qr, { small: true });
    console.log('\n' + '='.repeat(60));
    console.log('Waiting for authentication...\n');
  });
  
  // Authentication successful
  client.on('authenticated', () => {
    logger.info('WhatsApp authentication successful');
    console.log('✅ WhatsApp authenticated successfully!');
    reconnectAttempts = 0;
  });
  
  // Authentication failure
  client.on('auth_failure', (msg) => {
    logger.error('Authentication failure', { message: msg });
    console.error('❌ Authentication failure:', msg);
    
    if (reconnectAttempts < CONFIG.MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++;
      logger.info(`Reconnect attempt ${reconnectAttempts}/${CONFIG.MAX_RECONNECT_ATTEMPTS}`);
      setTimeout(() => {
        logger.info('Attempting to restart client...');
        client.destroy().catch(() => {});
        initializeWhatsApp(logger);
      }, CONFIG.RECONNECT_DELAY);
    } else {
      logger.error('Max reconnect attempts reached. Exiting.');
      process.exit(1);
    }
  });
  
  // Client ready
  client.on('ready', () => {
    logger.info('WhatsApp client ready');
    console.log('✅ WhatsApp Watcher is ready and listening for messages!');
    reconnectAttempts = 0;
  });
  
  // Incoming message
  client.on('message', (message) => {
    processMessage(message, client, logger);
  });
  
  // Message reaction (optional logging)
  client.on('message_reaction', (reaction) => {
    logger.debug('Message reaction received', {
      messageId: reaction.id._serialized,
      reaction: reaction.reaction
    });
  });
  
  // Disconnected
  client.on('disconnected', (reason) => {
    logger.warn('WhatsApp disconnected', { reason });
    console.log('⚠️  WhatsApp disconnected:', reason);
    
    if (reconnectAttempts < CONFIG.MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++;
      logger.info(`Reconnect attempt ${reconnectAttempts}/${CONFIG.MAX_RECONNECT_ATTEMPTS}`);
      setTimeout(() => {
        logger.info('Attempting to reconnect...');
        client.destroy().catch(() => {});
        initializeWhatsApp(logger);
      }, CONFIG.RECONNECT_DELAY);
    } else {
      logger.error('Max reconnect attempts reached. Exiting.');
      process.exit(1);
    }
  });
  
  // Loading screen progress
  client.on('loading_screen', (percent, message) => {
    logger.debug('Loading screen', { percent, message });
  });
  
  // Remote session logged out
  client.on('logout', () => {
    logger.warn('Logged out from remote session');
    console.log('⚠️  Logged out from remote session');
  });
  
  // Unhandled errors
  client.on('error', (err) => {
    logger.error('Client error', { error: err.message, stack: err.stack });
    console.error('❌ Client error:', err.message);
  });
}

function initializeWhatsApp(logger) {
  try {
    client = createWhatsAppClient(logger);
    setupClientEvents(client, logger);
    client.initialize();
  } catch (error) {
    logger.error('Failed to initialize WhatsApp client', { error: error.message, stack: error.stack });
    throw error;
  }
}

// =============================================================================
// Graceful Shutdown
// =============================================================================

async function gracefulShutdown(signal, logger) {
  logger.info(`Received ${signal}. Shutting down gracefully...`);
  console.log(`\n🛑 Received ${signal}. Shutting down gracefully...`);
  
  if (client) {
    try {
      await client.destroy();
      logger.info('WhatsApp client destroyed');
      console.log('✅ WhatsApp client destroyed');
    } catch (error) {
      logger.error('Error destroying client', { error: error.message });
    }
  }
  
  logger.info('Shutdown complete');
  process.exit(0);
}

function setupGracefulShutdown(logger) {
  process.on('SIGINT', () => gracefulShutdown('SIGINT', logger));
  process.on('SIGTERM', () => gracefulShutdown('SIGTERM', logger));
  
  // Handle uncaught exceptions
  process.on('uncaughtException', (error) => {
    logger.error('Uncaught exception', { error: error.message, stack: error.stack });
    console.error('❌ Uncaught exception:', error.message);
    gracefulShutdown('uncaughtException', logger);
  });
  
  process.on('unhandledRejection', (reason, promise) => {
    logger.error('Unhandled rejection', { reason: reason?.message || reason });
    console.error('❌ Unhandled rejection:', reason);
  });
}

// =============================================================================
// Health Check Endpoint (for orchestrator integration)
// =============================================================================

function getHealthStatus() {
  return {
    service: 'whatsapp-watcher',
    status: client ? 'running' : 'stopped',
    authenticated: client?.info ? true : false,
    sessionPath: CONFIG.SESSION_PATH,
    vaultPath: CONFIG.VAULT_PATH,
    logPath: CONFIG.LOG_PATH,
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  };
}

// Export for orchestrator integration
module.exports = {
  initializeWhatsApp,
  getHealthStatus,
  CONFIG
};

// =============================================================================
// Main Entry Point
// =============================================================================

async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('🚀 WhatsApp Watcher MCP Skill Starting...');
  console.log('='.repeat(60) + '\n');
  
  // Setup
  ensureDirectories();
  const logger = setupLogger();
  
  logger.info('WhatsApp Watcher starting', {
    version: '1.0.0',
    config: {
      sessionPath: CONFIG.SESSION_PATH,
      vaultPath: CONFIG.VAULT_PATH,
      logPath: CONFIG.LOG_PATH,
      logLevel: CONFIG.LOG_LEVEL,
      secureMode: CONFIG.SECURE_MODE
    }
  });
  
  // Setup graceful shutdown
  setupGracefulShutdown(logger);
  
  // Initialize WhatsApp client
  initializeWhatsApp(logger);
  
  // Log startup complete
  logger.info('WhatsApp Watcher initialization complete');
  console.log('\n📋 Configuration:');
  console.log(`   Session Path: ${CONFIG.SESSION_PATH}`);
  console.log(`   Vault Path:   ${CONFIG.VAULT_PATH}`);
  console.log(`   Log Path:     ${CONFIG.LOG_PATH}`);
  console.log(`   Log Level:    ${CONFIG.LOG_LEVEL}`);
  console.log('\n' + '='.repeat(60) + '\n');
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error('Failed to start WhatsApp Watcher:', error);
    process.exit(1);
  });
}
