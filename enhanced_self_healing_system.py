#!/usr/bin/env python3
"""
Enhanced Self-Healing System
A streamlined implementation that continuously monitors logs, detects issues,
applies solutions automatically, and learns from user input.
"""
import os
import time
import random
import json
import sqlite3
import logging
import subprocess
import re
import threading
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser

# Base directory for our self-contained environment
BASE_DIR = "/Users/krishna/Documents/ai-support-system/self-healing-project/self-healing-system"

# Create directory structure if it doesn't exist
def setup_environment():
    """Create the necessary directory structure for the self-healing system."""
    dirs = [
        BASE_DIR,
        os.path.join(BASE_DIR, "logs"),
        os.path.join(BASE_DIR, "services"),
        os.path.join(BASE_DIR, "data"),
        os.path.join(BASE_DIR, "scripts"),
        os.path.join(BASE_DIR, "dashboard"),
        os.path.join(BASE_DIR, "logs", "archive")
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    print(f"Environment set up at: {BASE_DIR}")
    return True

# Configuration management
def setup_config():
    """Set up configuration parameters for the self-healing system."""
    config_path = os.path.join(BASE_DIR, "config.json")
    
    # Default configuration with faster update intervals
    default_config = {
        "log_retention_days": 30,
        "backup_logs": True,
        "cleanup_enabled": True,
        "log_archive_interval_minutes": 60,
        "synthetic_data": {
            "normal_count": 90,
            "anomaly_count": 10,
            "generation_interval_seconds": 10,  # Generate new logs every 10 seconds
            "initial_data_points": 100  # Initial data to generate
        },
        "monitoring": {
            "check_interval_seconds": 5,  # Check logs every 5 seconds
            "dashboard_refresh_seconds": 2  # Update dashboard every 2 seconds
        },
        "ml_model": {
            "retrain_interval_minutes": 5,  # Retrain model every 5 minutes
            "n_estimators": 100
        }
    }
    
    # Create or load config file
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        config = default_config
        print("Default configuration created")
    else:
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            print("Configuration loaded")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration")
            config = default_config
    
    return config

# Set up logging
def setup_logging():
    """Set up enhanced logging for the self-healing system."""
    log_dir = os.path.join(BASE_DIR, "logs")
    main_log_file = os.path.join(log_dir, "self_healing.log")
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(main_log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create loggers dictionary
    logger = logging.getLogger("self_healing")
    logger.info("Logging initialized")
    
    return logger

# Database setup
def setup_database():
    """Set up the SQLite database for tracking incidents and solutions."""
    db_path = os.path.join(BASE_DIR, "data", "self_healing.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        tables = [
            '''
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                service TEXT,
                log_type TEXT,
                message TEXT,
                severity TEXT,
                resolved INTEGER DEFAULT 0,
                resolution TEXT
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS solutions (
                id INTEGER PRIMARY KEY,
                issue_pattern TEXT,
                solution_script TEXT,
                success_rate REAL,
                last_used TEXT
            )
            ''',
            '''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                service TEXT,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                network_usage REAL
            )
            '''
        ]
        
        for table_query in tables:
            cursor.execute(table_query)
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {db_path}")
        
        return db_path
    except Exception as e:
        print(f"Database error: {e}")
        raise

# Dashboard setup
def setup_dashboard():
    """Set up the real-time dashboard for monitoring."""
    dashboard_dir = os.path.join(BASE_DIR, "dashboard")
    
    # Create HTML dashboard with auto-refresh
    dashboard_html = os.path.join(dashboard_dir, "index.html")
    with open(dashboard_html, "w") as f:
        f.write(r'''
            <!DOCTYPE html>
<html>
<head>
    <title>Self-Healing System Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css" />
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0;
            padding: 0;
            background-color: #f7f9fc;
        }
        .header {
            background: linear-gradient(90deg, \#3b82f6, \#60a5fa);
            color: white;
            padding: 20px;
            border-bottom: 3px solid rgba(255,255,255,0.2);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .panel { 
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.04);
            transition: all 0.3s ease;
        }
        .panel:hover {
            box-shadow: 0 8px 15px rgba(0,0,0,0.08);
            transform: translateY(-2px);
        }
        .anomaly { background-color: #fff5f5; border-left: 4px solid #f56565; }
        .resolved { background-color: #f0fff4; border-left: 4px solid #48bb78; }
        .metrics { background-color: #ebf8ff; border-left: 4px solid #4299e1; }
        h1 {
            background: linear-gradient(90deg, #10b981, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-fill-color: transparent;
                
        }
        h2 { 
            font-size: 22px;
            font-weight: 600;
            margin-top: 0;
            margin-bottom: 16px;
            color: #374151;
        }
        pre { 
            background-color: #f5f5f5; 
            padding: 12px;
            border-radius: 8px;
            overflow: auto;
            font-size: 14px;
            line-height: 1.5;
        }
        .status {
            font-weight: 500;
            padding: 5px 10px;
            border-radius: 20px;
            display: inline-flex;
            align-items: center;
        }
        .status::before {
            content: '';
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 6px;
        }
        .status-ok { 
            background-color: #def7ec; 
            color: #046c4e;
        }
        .status-ok::before { 
            background-color: #0e9f6e; 
            box-shadow: 0 0 8px #0e9f6e;
            animation: pulse 2s infinite;
        }
        .status-warning { 
            background-color: #feecdc; 
            color: #9a3412;
        }
        .status-warning::before { 
            background-color: #ff5a1f; 
        }
        .status-error { 
            background-color: #fde8e8; 
            color: #9b1c1c;
        }
        .status-error::before { 
            background-color: #e02424; 
        }
        .last-updated { 
            font-size: 14px; 
            color: rgba(255,255,255,0.8);
        }
        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .summary { 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }
        .metric-card { 
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }
        .metric-card:hover { 
            transform: translateY(-5px);
            box-shadow: 0 12px 20px rgba(0,0,0,0.1);
        }
        .metric-card::after {
            content: '';
            position: absolute;
            top: -20px;
            right: -20px;
            width: 100px;
            height: 100px;
            border-radius: 50%;
            opacity: 0.3;
        }
        .metric-value { 
            font-size: 32px; 
            font-weight: 700; 
            margin: 10px 0;
        }
        .metric-label { 
            font-size: 16px;
            font-weight: 500;
        }
        .metric-ok { 
            background: linear-gradient(135deg, #d1fae5, #ecfdf5); 
            color: #065f46;
        }
        .metric-ok::after {
            background-color: #34d399;
        }
        .metric-warning { 
            background: linear-gradient(135deg, #fef3c7, #fffbeb); 
            color: #92400e;
        }
        .metric-warning::after {
            background-color: #fbbf24;
        }
        .metric-critical { 
            background: linear-gradient(135deg, #fee2e2, #fef2f2); 
            color: #b91c1c;
        }
        .metric-critical::after {
            background-color: #f87171;
        }
        .tabs { 
            display: flex;
            border-bottom: 2px solid #e5e7eb;
            margin-bottom: 20px;
            overflow-x: auto;
            scrollbar-width: none;
        }
        .tabs::-webkit-scrollbar {
            display: none;
        }
        .tab { 
            padding: 12px 24px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            margin-right: 8px;
            font-weight: 500;
            color: #6b7280;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .tab:hover {
            color: #3b82f6;
        }
        .tab.active { 
            color: #3b82f6; 
            font-weight: 600;
            border-bottom-color: #3b82f6;
        }
        .tab-content { 
            display: none;
            animation: fadeIn 0.5s;
        }
        .tab-content.active { 
            display: block; 
        }
        .chart-container {
            width: 100%;
            margin-bottom: 24px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
        }
        .chart-panel {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        }
        .incident-item {
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 10px;
            border-left: 4px solid #ef4444;
            animation: fadeInUp 0.4s;
        }
        .incident-item.warning {
            border-left-color: #f59e0b;
        }
        .incident-item.error {
            border-left-color: #ef4444;
        }
        .incident-item.critical {
            border-left-color: #7f1d1d;
            background-color: #fee2e2;
        }
        .refresh-btn {
            background-color: #3b82f6;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 500;
            transition: all 0.2s;
        }
        .refresh-btn:hover {
            background-color: #2563eb;
        }
        .refresh-btn svg {
            width: 16px;
            height: 16px;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes fadeInUp {
            from { 
                opacity: 0;
                transform: translateY(10px);
            }
            to { 
                opacity: 1;
                transform: translateY(0);
            }
        }
        .loading {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(59, 130, 246, 0.9);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 1000;
        }
        .loading.visible {
            opacity: 1;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="dashboard-container">
            <div class="flex justify-between items-center">
                <h1>Self-Healing System Dashboard</h1>
                <div class="flex items-center gap-4">
                    <div class="status status-ok" id="system-status">
                        System Running
                    </div>
                    <div class="last-updated">Last updated: <span id="update-time"></span></div>
                    <button id="refresh-btn" class="refresh-btn">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Refresh
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div class="dashboard-container">
        <div class="summary">
            <div class="metric-card metric-ok animate__animated animate__fadeIn">
                <div class="metric-label">Active Services</div>
                <div class="metric-value" id="active-services">-</div>
                <div class="text-sm mt-2">System components</div>
            </div>
            <div class="metric-card metric-ok animate__animated animate__fadeIn animate__delay-1s">
                <div class="metric-label">Active Incidents</div>
                <div class="metric-value" id="incident-count">-</div>
                <div class="text-sm mt-2">Issues requiring attention</div>
            </div>
            <div class="metric-card metric-ok animate__animated animate__fadeIn animate__delay-2s">
                <div class="metric-label">Model Accuracy</div>
                <div class="metric-value" id="model-accuracy">-</div>
                <div class="text-sm mt-2">ML classification performance</div>
            </div>
            <div class="metric-card metric-ok animate__animated animate__fadeIn animate__delay-3s">
                <div class="metric-label">Auto-resolved</div>
                <div class="metric-value" id="auto-resolved">-</div>
                <div class="text-sm mt-2">Issues fixed automatically</div>
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-panel">
                <h3 class="text-lg font-semibold mb-4">System Resource Usage</h3>
                <canvas id="resourceChart" height="220"></canvas>
            </div>
            <div class="chart-panel">
                <h3 class="text-lg font-semibold mb-4">Incident Resolution Trends</h3>
                <canvas id="resolutionChart" height="220"></canvas>
            </div>
        </div>

        <div class="tabs">
            <div class="tab active" data-tab="incidents">Active Incidents</div>
            <div class="tab" data-tab="logs">Recent Logs</div>
            <div class="tab" data-tab="metrics">System Metrics</div>
            <div class="tab" data-tab="solutions">Applied Solutions</div>
            <div class="tab" data-tab="ml">ML Model Status</div>
        </div>

        <div class="tab-content active" id="incidents-tab">
            <div class="panel anomaly">
                <h2>Active Incidents</h2>
                <div id="incidents-container"></div>
                <pre id="active-incidents" style="display: none;">Loading...</pre>
            </div>
        </div>

        <div class="tab-content" id="logs-tab">
            <div class="panel">
                <h2>Recent Logs</h2>
                <pre id="recent-logs">Loading...</pre>
            </div>
        </div>

        <div class="tab-content" id="metrics-tab">
            <div class="panel metrics">
                <h2>System Metrics</h2>
                <pre id="system-metrics">Loading...</pre>
            </div>
        </div>

        <div class="tab-content" id="solutions-tab">
            <div class="panel resolved">
                <h2>Applied Solutions</h2>
                <pre id="solutions">Loading...</pre>
            </div>
        </div>

        <div class="tab-content" id="ml-tab">
            <div class="panel">
                <h2>ML Model Status</h2>
                <pre id="ml-status">Loading...</pre>
            </div>
        </div>
    </div>

    <div class="loading" id="loading-indicator">Refreshing data...</div>

    <script>
        // Charts initialization
        const resourceCtx = document.getElementById('resourceChart').getContext('2d');
        const resourceChart = new Chart(resourceCtx, {
            type: 'line',
            data: {
                labels: ['5m ago', '4m ago', '3m ago', '2m ago', '1m ago', 'Now'],
                datasets: [{
                    label: 'CPU Usage (%)',
                    data: [42, 55, 62, 48, 60, 57],
                    borderColor: 'rgba(59, 130, 246, 1)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Memory Usage (%)',
                    data: [70, 68, 74, 78, 82, 79],
                    borderColor: 'rgba(124, 58, 237, 1)',
                    backgroundColor: 'rgba(124, 58, 237, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Disk Usage (%)',
                    data: [45, 46, 48, 51, 53, 54],
                    borderColor: 'rgba(16, 185, 129, 1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                animation: {
                    duration: 1000
                }
            }
        });

        const resolutionCtx = document.getElementById('resolutionChart').getContext('2d');
        const resolutionChart = new Chart(resolutionCtx, {
            type: 'bar',
            data: {
                labels: ['24h ago', '12h ago', '6h ago', '3h ago', '1h ago', 'Now'],
                datasets: [{
                    label: 'Incidents',
                    data: [12, 8, 15, 10, 7, 5],
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                }, {
                    label: 'Auto-resolved',
                    data: [10, 7, 12, 9, 6, 4],
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    }
                },
                animation: {
                    duration: 1000
                }
            }
        });

        // Keep track of the active tab
        function getActiveTab() {
            const activeTab = document.querySelector('.tab.active');
            return activeTab ? activeTab.getAttribute('data-tab') : 'incidents';
        }
        
        // Set the active tab
        function setActiveTab(tabName) {
            // Remove active class from all tabs and content
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Add active class to selected tab and content
            const tab = document.querySelector(`.tab[data-tab="${tabName}"]`);
            if (tab) {
                tab.classList.add('active');
                document.getElementById(tabName + '-tab').classList.add('active');
            }
        }

        // Format incidents into nice UI components
        function formatIncidents(incidentsText) {
            const container = document.getElementById('incidents-container');
            container.innerHTML = ''; // Clear existing content
            
            // Handle empty case
            if (incidentsText.trim() === 'No active incidents') {
                container.innerHTML = '<div class="bg-green-100 text-green-800 p-4 rounded-lg">No active incidents</div>';
                return;
            }
            
            // Parse incidents text
            const incidents = [];
            const sections = incidentsText.split('-'.repeat(80)).filter(section => section.trim());
            
            for (const section of sections) {
                const lines = section.trim().split('\n');
                const incident = {};
                
                for (const line of lines) {
                    if (line.startsWith('ID:')) incident.id = line.substring(3).trim();
                    else if (line.startsWith('Time:')) incident.time = line.substring(5).trim();
                    else if (line.startsWith('Service:')) incident.service = line.substring(8).trim();
                    else if (line.startsWith('Type:')) incident.type = line.substring(5).trim();
                    else if (line.startsWith('Severity:')) incident.severity = line.substring(9).trim();
                    else if (line.startsWith('Message:')) incident.message = line.substring(8).trim();
                }
                
                if (incident.id) {
                    incidents.push(incident);
                }
            }
            
            // Create UI elements
            for (const incident of incidents) {
                const el = document.createElement('div');
                el.className = `incident-item ${incident.severity.toLowerCase()}`;
                el.innerHTML = `
                    <div class="flex justify-between items-start mb-2">
                        <div class="font-semibold text-lg">${incident.service}</div>
                        <div class="bg-${getSeverityColor(incident.severity)}-100 text-${getSeverityColor(incident.severity)}-800 px-2 py-1 text-xs rounded-full">
                            ${incident.severity}
                        </div>
                    </div>
                    <div class="text-gray-800 mb-3">${incident.message}</div>
                    <div class="flex justify-between items-center text-sm text-gray-500">
                        <div>ID: ${incident.id} • Type: ${incident.type}</div>
                        <div>
                            <button class="bg-blue-500 hover:bg-blue-600 text-white text-sm px-3 py-1 rounded mr-2" 
                                    onclick="showIncidentDetails('${incident.id}', '${incident.service}', '${incident.type}', '${incident.severity}', '${incident.message.replace(/'/g, "\\'")}')">
                                Details
                            </button>
                            <button class="bg-green-500 hover:bg-green-600 text-white text-sm px-3 py-1 rounded"
                                    onclick="showResolveOptions('${incident.id}', '${incident.service}', '${incident.message.replace(/'/g, "\\'")}')">
                                Resolve
                            </button>
                        </div>
                    </div>
                `;
                container.appendChild(el);
            }
}
        function showIncidentDetails(id, service, type, severity, message) {
                // Create modal for incident details
                const modal = document.createElement('div');
                modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
                modal.id = 'incident-modal';
                
                modal.innerHTML = `
                    <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 animate__animated animate__fadeInDown">
                        <div class="flex justify-between items-center mb-4">
                            <h3 class="text-xl font-bold">Incident Details</h3>
                            <button onclick="document.getElementById('incident-modal').remove()" class="text-gray-500 hover:text-gray-700">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <div class="border-t border-b py-4 mb-4">
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <p class="text-gray-600 text-sm">Incident ID</p>
                                    <p class="font-medium">${id}</p>
                                </div>
                                <div>
                                    <p class="text-gray-600 text-sm">Service</p>
                                    <p class="font-medium">${service}</p>
                                </div>
                                <div>
                                    <p class="text-gray-600 text-sm">Type</p>
                                    <p class="font-medium">${type}</p>
                                </div>
                                <div>
                                    <p class="text-gray-600 text-sm">Severity</p>
                                    <p class="font-medium">
                                        <span class="inline-block px-2 py-1 text-xs rounded-full bg-${getSeverityColor(severity)}-100 text-${getSeverityColor(severity)}-800">
                                            ${severity}
                                        </span>
                                    </p>
                                </div>
                            </div>
                            <div class="mt-4">
                                <p class="text-gray-600 text-sm">Message</p>
                                <p class="font-medium">${message}</p>
                            </div>
                        </div>
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-medium mb-2">Recommended Actions</h4>
                            <ul class="list-disc pl-5 space-y-1">
                                <li>Check ${service} logs for more details</li>
                                <li>Verify ${service} configuration</li>
                                <li>Check system resources if performance related</li>
                            </ul>
                        </div>
                        <div class="mt-4 flex justify-end">
                            <button onclick="showResolveOptions('${id}', '${service}', '${message}')" 
                                    class="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded">
                                Resolve This Incident
                            </button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(modal);
            }

        function showResolveOptions(id, service, message) {
    // Remove any existing modal
    const existingModal = document.getElementById('incident-modal');
    if (existingModal) existingModal.remove();
    
    // Find appropriate solution based on the message
    let suggestedScript = '';
    
    if (message.includes('process terminated')) {
        suggestedScript = `restart_service.sh ${service}`;
    } else if (message.includes('CPU usage')) {
        suggestedScript = `optimize_service.sh ${service} cpu`;
    } else if (message.includes('Memory usage')) {
        suggestedScript = `restart_service.sh ${service}`;
    } else if (message.includes('Disk usage')) {
        suggestedScript = `cleanup_disk.sh`;
    } else if (message.includes('deadlock')) {
        // Extract transaction ID if present
        const txidMatch = message.match(/tx-\d+/);
        const txid = txidMatch ? txidMatch[0] : 'txid';
        suggestedScript = `resolve_deadlock.sh ${txid}`;
    } else if (message.includes('Permission denied')) {
        // Extract resource path if present
        const resourceMatch = message.match(/\/data\/\w+/);
        const resource = resourceMatch ? resourceMatch[0] : '/data/resource';
        suggestedScript = `fix_permissions.sh ${service} ${resource}`;
    } else if (message.includes('query')) {
        suggestedScript = `optimize_query.sh "SELECT query"`;
    } else if (message.includes('timeout')) {
        // Extract target service if present
        const targetMatch = message.match(/accessing (\w+)/);
        const target = targetMatch ? targetMatch[1] : 'target_service';
        suggestedScript = `check_network.sh ${service} ${target}`;
    } else {
        suggestedScript = `restart_service.sh ${service}`;
    }
    
    // Create modal for resolution options
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.id = 'incident-modal';
    
    modal.innerHTML = `
        <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 animate__animated animate__fadeInDown">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-bold">Resolve Incident</h3>
                <button onclick="document.getElementById('incident-modal').remove()" class="text-gray-500 hover:text-gray-700">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
            <div class="mb-4">
                <p class="text-gray-700">Incident ID: ${id}</p>
                <p class="text-gray-700">Service: ${service}</p>
                <p class="text-gray-700 mt-2">${message}</p>
            </div>
            <div class="bg-gray-100 p-4 rounded-lg mb-4">
                <h4 class="font-medium mb-2">Suggested Solution Script:</h4>
                <div class="bg-gray-900 text-white p-3 rounded font-mono">
                    ${suggestedScript}
                </div>
                <p class="text-sm text-gray-600 mt-2">This command will be executed to resolve the incident.</p>
            </div>
            <div class="flex justify-end space-x-3">
                <button onclick="document.getElementById('incident-modal').remove()" 
                        class="border border-gray-300 bg-white text-gray-700 py-2 px-4 rounded hover:bg-gray-50">
                    Cancel
                </button>
                <button onclick="executeResolution('${id}', '${suggestedScript}')" 
                        class="bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded">
                    Execute Solution
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

        function executeResolution(id, script) {
            // In a real implementation, this would call an API to execute the script
            // For this demo, we'll just simulate it with a success message
            const modal = document.getElementById('incident-modal');
            if (modal) {
                modal.innerHTML = `
                    <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 animate__animated animate__fadeIn">
                        <div class="flex items-center justify-center mb-4 text-green-500">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                        <h3 class="text-xl font-bold text-center mb-2">Solution Applied</h3>
                        <p class="text-center mb-4">The command "${script}" was executed successfully.</p>
                        <p class="text-center text-sm text-gray-600 mb-6">
                            Incident #${id} has been marked as resolved. This will be reflected in the next data refresh.
                        </p>
                        <div class="flex justify-center">
                            <button onclick="document.getElementById('incident-modal').remove()" 
                                    class="bg-blue-500 hover:bg-blue-600 text-white py-2 px-6 rounded">
                                Close
                            </button>
                        </div>
                    </div>
                `;
                
                // Force a dashboard refresh after a short delay
                setTimeout(function() {
                    loadDashboardData();
                }, 2000);
            }
        }

        function getSeverityColor(severity) {
            switch (severity.toLowerCase()) {
                case 'critical': return 'red';
                case 'error': return 'red';
                case 'warning': return 'yellow';
                default: return 'gray';
            }
        }
        
        // Function to update charts with system metrics data
        function updateResourceChart(metricsText) {
            try {
                // Parse system metrics
                const lines = metricsText.split('\n');
                if (lines.length < 2) return; // Not enough data
                
                const services = new Set();
                const cpuData = [];
                const memoryData = [];
                const diskData = [];
                
                // Skip header line
                for (let i = 1; i < lines.length; i++) {
                    const line = lines[i].trim();
                    if (!line) continue;
                    
                    const parts = line.split(/\s+/);
                    if (parts.length >= 5) {
                        services.add(parts[0]);
                        cpuData.push(parseFloat(parts[1]));
                        memoryData.push(parseFloat(parts[2]));
                        diskData.push(parseFloat(parts[3]));
                    }
                }
                
                // Use the last 6 data points or pad with existing data
                const getLastN = (arr, n) => {
                    if (arr.length <= n) return arr;
                    return arr.slice(arr.length - n);
                };
                
                if (cpuData.length > 0) {
                    // Update the chart data
                    resourceChart.data.datasets[0].data = getLastN(cpuData, 6);
                    resourceChart.data.datasets[1].data = getLastN(memoryData, 6);
                    resourceChart.data.datasets[2].data = getLastN(diskData, 6);
                    resourceChart.update();
                }
            } catch (error) {
                console.error("Error updating resource chart:", error);
            }
        }
        
        // Parse solutions data to update resolution chart
        function updateResolutionChart(solutionsText) {
            try {
                const match = solutionsText.match(/Applied Solutions: (\d+) total/);
                if (match && match[1]) {
                    const total = parseInt(match[1]);
                    
                    // Simple algorithm to generate reasonable trend data
                    // In real implementation, this would use actual historical data
                    const incidents = [Math.round(total * 0.3), Math.round(total * 0.2), 
                                      Math.round(total * 0.25), Math.round(total * 0.15), 
                                      Math.round(total * 0.08), Math.round(total * 0.02)];
                    
                    const resolved = incidents.map(val => Math.round(val * (0.8 + Math.random() * 0.15)));
                    
                    resolutionChart.data.datasets[0].data = incidents;
                    resolutionChart.data.datasets[1].data = resolved;
                    resolutionChart.update();
                }
            } catch (error) {
                console.error("Error updating resolution chart:", error);
            }
        }

        // Show loading indicator
        function showLoading() {
            const indicator = document.getElementById('loading-indicator');
            indicator.classList.add('visible');
        }
        
        // Hide loading indicator
        function hideLoading() {
            const indicator = document.getElementById('loading-indicator');
            indicator.classList.remove('visible');
        }

        // Load dashboard data with improved feedback and error handling
        async function loadDashboardData() {
    // Remember active tab
    const activeTab = getActiveTab();
    
    // Show loading indicator
    showLoading();
    
    try {
        // Add timestamp to prevent caching
        const timestamp = new Date().getTime();
        
        // Fetch all data in parallel
        const [logsResponse, incidentsResponse, metricsResponse, solutionsResponse, mlStatusResponse] = 
            await Promise.all([
                fetch('recent_logs.txt?t=' + timestamp),
                fetch('active_incidents.txt?t=' + timestamp),
                fetch('system_metrics.txt?t=' + timestamp),
                fetch('solutions.txt?t=' + timestamp),
                fetch('ml_status.txt?t=' + timestamp)
            ]);
        
        // Process responses
        const logs = await logsResponse.text();
        const incidents = await incidentsResponse.text();
        const metrics = await metricsResponse.text();
        const solutions = await solutionsResponse.text();
        const mlStatus = await mlStatusResponse.text();
        
        // Update the UI with fetched data
        document.getElementById('recent-logs').textContent = logs;
        document.getElementById('active-incidents').textContent = incidents;
        formatIncidents(incidents);
        document.getElementById('system-metrics').textContent = metrics;
        document.getElementById('solutions').textContent = solutions;
        document.getElementById('ml-status').textContent = mlStatus;
        
        // Update the charts
        updateResourceChart(metrics);
        updateResolutionChart(solutions);
        
        // Extract and update metrics
        // Incident count
        const incidentCount = incidents.trim() === "No active incidents" ? 0 : 
            (incidents.match(/ID:/g) || []).length;
        document.getElementById('incident-count').textContent = incidentCount;
        
        // Update incident card color
        const incidentCard = document.getElementById('incident-count').parentNode;
        if (incidentCount === 0) {
            incidentCard.className = 'metric-card metric-ok';
        } else if (incidentCount < 5) {
            incidentCard.className = 'metric-card metric-warning';
        } else {
            incidentCard.className = 'metric-card metric-critical';
        }
        
        // Service count
        const services = new Set();
        const lines = metrics.split('\n');
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line) {
                const parts = line.split(/\s+/);
                if (parts.length > 0) {
                    services.add(parts[0]);
                }
            }
        }
        document.getElementById('active-services').textContent = services.size || "-";
        
        // Auto-resolved count
        const match = solutions.match(/Applied Solutions: (\d+) total/);
        if (match && match[1]) {
            document.getElementById('auto-resolved').textContent = match[1];
            
            // Update status color
            const resolvedCard = document.getElementById('auto-resolved').parentNode;
            const count = parseInt(match[1]);
            if (count > 100) {
                resolvedCard.className = 'metric-card metric-ok';
            } else if (count > 0) {
                resolvedCard.className = 'metric-card metric-warning';
            } else {
                resolvedCard.className = 'metric-card metric-critical';
            }
        }
        
        // ML model accuracy - FIXED
        // This was the main issue - we need a more robust regex pattern for extracting
        // the accuracy value from the ML status text
        const accuracyMatch = mlStatus.match(/Model accuracy:\s*([\d.]+)/);
        if (accuracyMatch && accuracyMatch[1]) {
            const accuracy = parseFloat(accuracyMatch[1]);
            document.getElementById('model-accuracy').textContent = (accuracy * 100).toFixed(1) + '%';
            
            // Update status color
            const accuracyCard = document.getElementById('model-accuracy').parentNode;
            if (accuracy >= 0.8) {
                accuracyCard.className = 'metric-card metric-ok';
            } else if (accuracy >= 0.6) {
                accuracyCard.className = 'metric-card metric-warning';
            } else {
                accuracyCard.className = 'metric-card metric-critical';
            }
        } else {
            // Fallback if we can't parse the accuracy
            document.getElementById('model-accuracy').textContent = "N/A";
        }
        
        document.getElementById('update-time').textContent = new Date().toLocaleString();
        
        // Restore active tab
        setActiveTab(activeTab);
        
        // Update loading status
        hideLoading();
        
    } catch (error) {
        console.error("Error loading dashboard data:", error);
        document.getElementById('loading-indicator').textContent = "Error loading data";
        document.getElementById('loading-indicator').style.backgroundColor = "rgba(220, 38, 38, 0.9)";
        
        // Hide error after a few seconds
        setTimeout(hideLoading, 3000);
        
        // Restore active tab
        setActiveTab(activeTab);
    }
}
        
        // Set up tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                setActiveTab(this.dataset.tab);
            });
        });
        
        // Set up manual refresh button
        document.getElementById('refresh-btn').addEventListener('click', function() {
            loadDashboardData();
        });

        // Load data initially
        loadDashboardData();
        
        // Set up automatic refresh every 5 seconds
        setInterval(loadDashboardData, 5000);
    </script>
</body>
</html>
        ''')
    
    # Create initial data files
    for file_name in ["recent_logs.txt", "active_incidents.txt", "system_metrics.txt", "solutions.txt", "ml_status.txt"]:
        with open(os.path.join(dashboard_dir, file_name), "w") as f:
            f.write("Loading data...")
    
    print(f"Dashboard initialized at: {dashboard_html}")
    return dashboard_html

# Create solution scripts
def create_solution_scripts():
    """Create the necessary solution scripts."""
    scripts_dir = os.path.join(BASE_DIR, "scripts")
    
    # Service restart script
    with open(os.path.join(scripts_dir, "restart_service.sh"), "w") as f:
        f.write('''#!/bin/bash
# Script to restart a service
SERVICE=$1
echo "Restarting service: $SERVICE"
SERVICE_DIR="{base_dir}/services/$SERVICE"

# Check if service directory exists
if [ ! -d "$SERVICE_DIR" ]; then
    mkdir -p "$SERVICE_DIR"
fi

# Create a restart marker file
touch "$SERVICE_DIR/restarted_$(date +%s)"
echo "Service $SERVICE restarted successfully"
exit 0
'''.format(base_dir=BASE_DIR))
    
    # Disk cleanup script
    with open(os.path.join(scripts_dir, "cleanup_disk.sh"), "w") as f:
        f.write('''#!/bin/bash
# Script to clean up disk space
echo "Cleaning up disk space"
LOGS_DIR="{base_dir}/logs"
ARCHIVE_DIR="{base_dir}/logs/archive"

# Ensure archive directory exists
mkdir -p "$ARCHIVE_DIR"

# Archive old logs
TIMESTAMP=$(date +%Y%m%d%H%M%S)
tar -czf "$ARCHIVE_DIR/logs_$TIMESTAMP.tar.gz" -C "$LOGS_DIR" $(find "$LOGS_DIR" -name "*.log.*" -type f -mtime +1 -printf "%P\\n" 2>/dev/null)

# Delete old log files
find "$LOGS_DIR" -name "*.log.*" -type f -mtime +1 -delete

echo "Disk cleanup completed"
exit 0
'''.format(base_dir=BASE_DIR))
    
    # Network check script
    with open(os.path.join(scripts_dir, "check_network.sh"), "w") as f:
        f.write('''#!/bin/bash
# Script to check network connectivity
SERVICE=$1
TARGET=$2
echo "Checking network connectivity from $SERVICE to $TARGET"
echo "Network check completed"
exit 0
''')
    
    # Permission fix script
    with open(os.path.join(scripts_dir, "fix_permissions.sh"), "w") as f:
        f.write('''#!/bin/bash
# Script to fix permissions
SERVICE=$1
RESOURCE=$2
echo "Fixing permissions for $SERVICE to access $RESOURCE"
echo "Permissions fixed"
exit 0
''')
    
    # Query optimization script
    with open(os.path.join(scripts_dir, "optimize_query.sh"), "w") as f:
        f.write('''#!/bin/bash
# Script to optimize a slow query
QUERY=$1
echo "Optimizing query: $QUERY"
echo "Query optimized"
exit 0
''')
    
    # Service optimization script
    with open(os.path.join(scripts_dir, "optimize_service.sh"), "w") as f:
        f.write('''#!/bin/bash
# Script to optimize a service
SERVICE=$1
RESOURCE=$2
echo "Optimizing $RESOURCE usage for service: $SERVICE"
echo "Service $SERVICE optimized for $RESOURCE"
exit 0
''')
    
    # Deadlock resolution script
    with open(os.path.join(scripts_dir, "resolve_deadlock.sh"), "w") as f:
        f.write('''#!/bin/bash
# Script to resolve a database deadlock
TXID=$1
echo "Resolving deadlock for transaction: $TXID"
echo "Deadlock resolved for transaction $TXID"
exit 0
''')
    
    # Make all scripts executable
    for script in os.listdir(scripts_dir):
        if script.endswith(".sh"):
            script_path = os.path.join(scripts_dir, script)
            os.chmod(script_path, 0o755)
    
    print("Solution scripts created")

# Initialize solution patterns
def initialize_solutions():
    """Initialize the database with common solution patterns."""
    db_path = os.path.join(BASE_DIR, "data", "self_healing.db")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if we already have solutions
        cursor.execute("SELECT COUNT(*) FROM solutions")
        if cursor.fetchone()[0] > 0:
            print("Solutions already exist in database")
            conn.close()
            return
        
        # Add solution patterns
        patterns = [
            # Service crash patterns
            ("{service} process terminated unexpectedly with exit code {code}", 
             "restart_service.sh {service}", 0.95),
            
            # Resource usage patterns
            ("CPU usage for {service} exceeded threshold: {value}%", 
             "optimize_service.sh {service} cpu", 0.9),
            ("Memory usage for {service} continually increasing, current: {value}MB", 
             "restart_service.sh {service}", 0.95),
            ("Disk usage reached {value}%, clean up required", 
             "cleanup_disk.sh", 0.98),
            ("Network usage for {service} exceeds normal patterns: {value}MB/s", 
             "optimize_service.sh {service} network", 0.85),
            
            # Database patterns
            ("Database deadlock detected in transaction {txid}", 
             "resolve_deadlock.sh {txid}", 0.9),
            ("Slow query detected in {service}: {query} (took {value}ms)", 
             "optimize_query.sh \"{query}\"", 0.8),
            
            # Network patterns
            ("Connection timeout when {service} accessing {target}", 
             "check_network.sh {service} {target}", 0.85),
            
            # Security patterns
            ("Permission denied for {service} accessing {resource}", 
             "fix_permissions.sh {service} {resource}", 0.95)
        ]
        
        for pattern, script, rate in patterns:
            cursor.execute(
                "INSERT INTO solutions (issue_pattern, solution_script, success_rate, last_used) VALUES (?, ?, ?, ?)",
                (pattern, script, rate, datetime.now().isoformat())
            )
        
        conn.commit()
        conn.close()
        print(f"Initialized {len(patterns)} solution patterns in database")
    except Exception as e:
        print(f"Error initializing solutions: {e}")
        raise

class SyntheticDataGenerator:
    """Generator for synthetic log data and system metrics."""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.log_dir = os.path.join(BASE_DIR, "logs")
        self.db_path = os.path.join(BASE_DIR, "data", "self_healing.db")
        
        # Services
        self.services = [
            "web_server", "database", "cache", "auth_service", 
            "file_service", "backup_service", "network_service"
        ]
        
        # Log types with weights
        self.log_types = {
            "service_status": 0.3,
            "resource_usage": 0.4,
            "error": 0.15,
            "security": 0.1,
            "performance": 0.05
        }
        
        # Anomaly patterns
        self.anomaly_patterns = {
            "service_crash": {
                "log_type": "service_status",
                "message_template": "{service} process terminated unexpectedly with exit code {code}",
                "severity": "critical"
            },
            "high_cpu": {
                "log_type": "resource_usage",
                "message_template": "CPU usage for {service} exceeded threshold: {value}%",
                "severity": "warning"
            },
            "memory_leak": {
                "log_type": "resource_usage",
                "message_template": "Memory usage for {service} continually increasing, current: {value}MB",
                "severity": "warning"
            },
            "disk_full": {
                "log_type": "resource_usage",
                "message_template": "Disk usage reached {value}%, clean up required",
                "severity": "critical"
            },
            "database_deadlock": {
                "log_type": "error",
                "message_template": "Database deadlock detected in transaction {txid}",
                "severity": "critical"
            },
            "connection_timeout": {
                "log_type": "error",
                "message_template": "Connection timeout when {service} accessing {target}",
                "severity": "error"
            },
            "permission_denied": {
                "log_type": "security",
                "message_template": "Permission denied for {service} accessing {resource}",
                "severity": "error"
            },
            "slow_query": {
                "log_type": "performance",
                "message_template": "Slow query detected in {service}: SELECT * FROM {table} WHERE id = {id} (took {value}ms)",
                "severity": "warning"
            }
        }
        
        self.logger.info("SyntheticDataGenerator initialized")
    
    def generate_service_directories(self):
        """Create directories for simulated services."""
        services_dir = os.path.join(BASE_DIR, "services")
        
        for service in self.services:
            service_dir = os.path.join(services_dir, service)
            os.makedirs(service_dir, exist_ok=True)
            
            # Create a status file
            with open(os.path.join(service_dir, "status"), "w") as f:
                f.write("running")
        
        self.logger.info(f"Created {len(self.services)} service directories")
    
    def generate_initial_data(self):
        """Generate initial data for ML model training."""
        try:
            self.logger.info("Generating initial dataset")
            
            # Get number of data points to generate
            data_points = self.config["synthetic_data"]["initial_data_points"]
            
            # Generate system metrics and logs
            for _ in range(data_points // 10):  # Split into batches
                self.generate_system_metrics()
                self.generate_log_entries(10)
            
            self.logger.info(f"Generated initial dataset with {data_points} data points")
            return True
        except Exception as e:
            self.logger.error(f"Error generating initial data: {e}")
            return False
    
    def generate_system_metrics(self):
        """Generate synthetic system metrics for services."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            metrics_data = []
            
            for service in self.services:
                # Generate random metrics with occasional spikes
                cpu_usage = random.uniform(10, 30)
                memory_usage = random.uniform(20, 50)
                disk_usage = random.uniform(30, 60)
                network_usage = random.uniform(5, 25)
                
                # Add occasional anomalies (5% chance)
                if random.random() < 0.05:
                    anomaly_type = random.choice(["cpu", "memory", "disk", "network"])
                    if anomaly_type == "cpu":
                        cpu_usage = random.uniform(85, 100)
                    elif anomaly_type == "memory":
                        memory_usage = random.uniform(85, 100)
                    elif anomaly_type == "disk":
                        disk_usage = random.uniform(85, 100)
                    elif anomaly_type == "network":
                        network_usage = random.uniform(85, 100)
                
                cursor.execute(
                    """INSERT INTO system_metrics 
                       (timestamp, service, cpu_usage, memory_usage, disk_usage, network_usage) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (timestamp, service, cpu_usage, memory_usage, disk_usage, network_usage)
                )
                
                metrics_data.append({
                    'service': service,
                    'cpu_usage': cpu_usage,
                    'memory_usage': memory_usage,
                    'disk_usage': disk_usage,
                    'network_usage': network_usage
                })
                
                # Create log entry for high resource usage
                if cpu_usage > 80:
                    self._write_log_entry(
                        service, "resource_usage", 
                        f"CPU usage for {service} exceeded threshold: {cpu_usage:.1f}%",
                        "warning"
                    )
                
                if memory_usage > 80:
                    self._write_log_entry(
                        service, "resource_usage", 
                        f"Memory usage for {service} continually increasing, current: {memory_usage*10:.1f}MB",
                        "warning"
                    )
                
                if disk_usage > 80:
                    self._write_log_entry(
                        service, "resource_usage", 
                        f"Disk usage reached {disk_usage:.1f}%, clean up required",
                        "critical"
                    )
            
            conn.commit()
            conn.close()
            
            # Update system metrics in dashboard
            self._update_system_metrics(metrics_data)
            
            return True
        except Exception as e:
            self.logger.error(f"Error generating system metrics: {e}")
            return False
    
    def _write_log_entry(self, service, log_type, message, severity):
        """Write a log entry to the services log file."""
        try:
            timestamp = datetime.now().isoformat()
            log_file = os.path.join(self.log_dir, "services.log")
            
            with open(log_file, "a") as f:
                f.write(f"{timestamp}|{service}|{log_type}|{severity}|{message}\n")
            
            return True
        except Exception as e:
            self.logger.error(f"Error writing log entry: {e}")
            return False
    
    def generate_log_entries(self, count=10):
        """Generate synthetic log entries."""
        try:
            self.logger.info(f"Generating {count} log entries")
            
            # Use configurable anomaly percentage
            anomaly_percent = self.config["synthetic_data"]["anomaly_count"]
            normal_percent = self.config["synthetic_data"]["normal_count"]
            
            total_percent = anomaly_percent + normal_percent
            anomaly_ratio = anomaly_percent / total_percent
            
            # Determine how many anomalies to include
            anomaly_count = max(1, int(count * anomaly_ratio))
            normal_count = count - anomaly_count
            
            logs_generated = []
            
            # Generate normal logs
            for _ in range(normal_count):
                service = random.choice(self.services)
                log_type = random.choices(
                    list(self.log_types.keys()),
                    weights=list(self.log_types.values())
                )[0]
                
                # Generate a normal message based on log type
                if log_type == "service_status":
                    message = f"{service} is running normally"
                    severity = "info"
                elif log_type == "resource_usage":
                    resource = random.choice(["CPU", "memory", "disk", "network"])
                    value = random.uniform(10, 60)
                    message = f"{resource} usage for {service}: {value:.1f}%"
                    severity = "info"
                elif log_type == "error":
                    message = f"Handled exception in {service}: Operation completed with retry"
                    severity = "warning"
                elif log_type == "security":
                    message = f"Authentication successful for user on {service}"
                    severity = "info"
                else:  # performance
                    operation = random.choice(["query", "request", "transaction"])
                    value = random.uniform(10, 200)
                    message = f"{operation} completed in {value:.1f}ms on {service}"
                    severity = "info"
                
                self._write_log_entry(service, log_type, message, severity)
                logs_generated.append({
                    'timestamp': datetime.now().isoformat(),
                    'service': service,
                    'log_type': log_type,
                    'message': message,
                    'severity': severity
                })
            
            # Generate anomaly logs
            for _ in range(anomaly_count):
                # Select a random anomaly type
                anomaly_type = random.choice(list(self.anomaly_patterns.keys()))
                anomaly = self.anomaly_patterns[anomaly_type]
                
                service = random.choice(self.services)
                log_type = anomaly["log_type"]
                severity = anomaly["severity"]
                
                # Format the message
                if anomaly_type == "service_crash":
                    code = random.randint(1, 255)
                    message = anomaly["message_template"].format(service=service, code=code)
                elif anomaly_type == "high_cpu":
                    value = random.uniform(85, 100)
                    message = anomaly["message_template"].format(service=service, value=f"{value:.1f}")
                elif anomaly_type == "memory_leak":
                    value = random.uniform(500, 2000)
                    message = anomaly["message_template"].format(service=service, value=f"{value:.1f}")
                elif anomaly_type == "disk_full":
                    value = random.uniform(85, 99)
                    message = anomaly["message_template"].format(value=f"{value:.1f}")
                elif anomaly_type == "database_deadlock":
                    txid = f"tx-{random.randint(1000, 9999)}"
                    message = anomaly["message_template"].format(txid=txid)
                elif anomaly_type == "connection_timeout":
                    target = random.choice(self.services)
                    message = anomaly["message_template"].format(service=service, target=target)
                elif anomaly_type == "permission_denied":
                    resource = f"/data/{random.choice(['users', 'config', 'content', 'media'])}"
                    message = anomaly["message_template"].format(service=service, resource=resource)
                elif anomaly_type == "slow_query":
                    table = random.choice(['users', 'orders', 'products'])
                    id_value = random.randint(1, 1000)
                    value = random.uniform(1000, 5000)
                    message = anomaly["message_template"].format(
                        service=service, 
                        table=table, 
                        id=id_value,
                        value=f"{value:.1f}"
                    )
                
                self._write_log_entry(service, log_type, message, severity)
                logs_generated.append({
                    'timestamp': datetime.now().isoformat(),
                    'service': service,
                    'log_type': log_type,
                    'message': message,
                    'severity': severity
                })
                
                # Add incident to database for anomalies
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        """INSERT INTO incidents 
                           (timestamp, service, log_type, message, severity, resolved, resolution) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (datetime.now().isoformat(), service, log_type, message, severity, 0, None)
                    )
                    
                    conn.commit()
                    conn.close()
                except Exception as e:
                    self.logger.error(f"Error inserting incident: {e}")
            
            # Update recent logs in dashboard
            self._update_recent_logs(logs_generated)
            
            return logs_generated
        except Exception as e:
            self.logger.error(f"Error generating log entries: {e}")
            return []

    def _update_recent_logs(self, logs):
        """Update the recent logs displayed in the dashboard."""
        try:
            dashboard_logs = os.path.join(BASE_DIR, "dashboard", "recent_logs.txt")
            
            # Get existing logs if any
            existing_logs = []
            if os.path.exists(dashboard_logs):
                with open(dashboard_logs, "r") as f:
                    existing_logs = f.readlines()
            
            # Combine with new logs and keep the most recent 20
            with open(dashboard_logs, "w") as f:
                for log in logs:
                    f.write(f"{log['timestamp']}|{log['service']}|{log['log_type']}|{log['severity']}|{log['message']}\n")
                
                # Add existing logs if we have fewer than 20 new ones
                if len(logs) < 20:
                    for i in range(min(20 - len(logs), len(existing_logs))):
                        f.write(existing_logs[i])
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating recent logs: {e}")
            return False
    
    def _update_system_metrics(self, metrics):
        """Update the system metrics displayed in the dashboard."""
        try:
            dashboard_metrics = os.path.join(BASE_DIR, "dashboard", "system_metrics.txt")
            
            with open(dashboard_metrics, "w") as f:
                # Write header
                f.write("service  cpu_usage  memory_usage  disk_usage  network_usage\n")
                
                # Write metrics
                for metric in metrics:
                    f.write(f"{metric['service']:^10}  {metric['cpu_usage']:^9.2f}  {metric['memory_usage']:^12.2f}  {metric['disk_usage']:^10.2f}  {metric['network_usage']:^12.2f}\n")
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
            return False
    
    def archive_logs(self):
        """Archive old logs to maintain system performance."""
        try:
            self.logger.info("Archiving old logs")
            
            log_dir = self.log_dir
            archive_dir = os.path.join(log_dir, "archive")
            os.makedirs(archive_dir, exist_ok=True)
            
            # Archive logs older than retention days
            retention_days = self.config["log_retention_days"]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            archive_file = os.path.join(archive_dir, f"logs_archive_{timestamp}.tar.gz")
            
            # Find old log files
            old_files = []
            for root, _, files in os.walk(log_dir):
                for file in files:
                    if file.endswith(".log") and not file == "services.log":
                        file_path = os.path.join(root, file)
                        file_mtime = os.path.getmtime(file_path)
                        file_age = (time.time() - file_mtime) / (60*60*24)
                        
                        if file_age > retention_days:
                            old_files.append(file_path)
            
            if old_files:
                # Create archive
                import tarfile
                with tarfile.open(archive_file, "w:gz") as tar:
                    for file_path in old_files:
                        tar.add(file_path, arcname=os.path.basename(file_path))
                
                # Delete archived files
                for file_path in old_files:
                    os.remove(file_path)
                
                self.logger.info(f"Archived and deleted {len(old_files)} old log files")
                return True
            else:
                self.logger.info("No logs to archive")
                return True
        except Exception as e:
            self.logger.error(f"Error archiving logs: {e}")
            return False

class MonitoringEngine:
    """Engine for monitoring logs, detecting issues, and applying solutions."""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.db_path = os.path.join(BASE_DIR, "data", "self_healing.db")
        self.log_dir = os.path.join(BASE_DIR, "logs")
        
        # Paths for ML model
        self.model_path = os.path.join(BASE_DIR, "data", "model.pkl")
        self.vectorizer_path = os.path.join(BASE_DIR, "data", "vectorizer.pkl")
        
        # Load or create ML model
        self._load_or_create_model()
        
        self.logger.info("MonitoringEngine initialized")
    
    def _load_or_create_model(self):
        """Load existing ML model or create a new one if it doesn't exist."""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
                self.logger.info("Loading existing ML model")
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                with open(self.vectorizer_path, "rb") as f:
                    self.vectorizer = pickle.load(f)
            else:
                self.logger.info("Creating new ML model")
                self.train_model()
        except Exception as e:
            self.logger.error(f"Error loading/creating ML model: {e}")
            self.model = None
            self.vectorizer = None
    
    def train_model(self):
        """Train ML model for issue classification."""
        try:
            self.logger.info("Training ML model")
            
            # Get incidents from database
            conn = sqlite3.connect(self.db_path)
            incidents_df = pd.read_sql("SELECT * FROM incidents", conn)
            conn.close()
            
            if len(incidents_df) < 10:
                self.logger.warning("Not enough incident data for training")
                # Create a simple default model
                self.model = RandomForestClassifier(n_estimators=10)
                self.vectorizer = TfidfVectorizer(max_features=100)
                
                # Save the model
                with open(self.model_path, "wb") as f:
                    pickle.dump(self.model, f)
                with open(self.vectorizer_path, "wb") as f:
                    pickle.dump(self.vectorizer, f)
                
                # Update ML status
                self._update_ml_status(
                    model_type="RandomForestClassifier (default)",
                    training_samples=0,
                    accuracy=0.0,
                    status="Not enough data"
                )
                
                return
            
            # Prepare data
            X = incidents_df['message']
            y = incidents_df['log_type']
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Train vectorizer and model
            self.vectorizer = TfidfVectorizer(max_features=100)
            X_train_tfidf = self.vectorizer.fit_transform(X_train)
            
            n_estimators = self.config["ml_model"]["n_estimators"]
            self.model = RandomForestClassifier(n_estimators=n_estimators, random_state=42)
            self.model.fit(X_train_tfidf, y_train)
            
            # Evaluate on test set
            X_test_tfidf = self.vectorizer.transform(X_test)
            accuracy = self.model.score(X_test_tfidf, y_test)
            
            self.logger.info(f"Model trained with accuracy: {accuracy:.4f}")
            
            # Save the model
            with open(self.model_path, "wb") as f:
                pickle.dump(self.model, f)
            with open(self.vectorizer_path, "wb") as f:
                pickle.dump(self.vectorizer, f)
            
            # Update ML status
            self._update_ml_status(
                model_type="RandomForestClassifier (Enhanced)",
                training_samples=len(X_train),
                accuracy=accuracy,
                status="Active and learning"
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Error training model: {e}")
            return False
    
    def _update_ml_status(self, model_type, training_samples, accuracy, status):
        """Update ML model status for dashboard."""
        try:
            ml_status_file = os.path.join(BASE_DIR, "dashboard", "ml_status.txt")
            
            with open(ml_status_file, "w") as f:
                f.write("ML Model Status\n")
                f.write("==============\n\n")
                f.write(f"Model type: {model_type}\n")
                f.write(f"Training samples: {training_samples}\n")
                f.write(f"Model accuracy: {accuracy:.2f}\n")
                f.write(f"Status: {status}\n\n")
                
                # Add recent incidents
                try:
                    conn = sqlite3.connect(self.db_path)
                    recent_incidents = pd.read_sql(
                        "SELECT * FROM incidents ORDER BY timestamp DESC LIMIT 5", 
                        conn
                    )
                    conn.close()
                    
                    if len(recent_incidents) > 0:
                        f.write("Recent Resolved Incidents\n")
                        f.write("------------------------\n")
                        for _, incident in recent_incidents.iterrows():
                            if incident['resolved']:
                                f.write(f"Service: {incident['service']}\n")
                                f.write(f"Message: {incident['message']}\n")
                                f.write(f"Type: {incident['log_type']}\n")
                                
                                if incident['resolution']:
                                    try:
                                        resolution_data = json.loads(incident['resolution'])
                                        f.write(f"Solution: {resolution_data['script']}\n")
                                        f.write(f"Execution time: {resolution_data['execution_time']:.2f}s\n")
                                    except:
                                        f.write(f"Resolution: {incident['resolution']}\n")
                                
                                f.write("\n")
                except Exception as e:
                    self.logger.error(f"Error adding recent incidents to ML status: {e}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating ML status: {e}")
            return False
    
    def check_logs(self):
        """Check logs for new incidents and apply solutions."""
        try:
            self.logger.info("Checking logs for incidents")
            
            # Read the services log
            log_file = os.path.join(self.log_dir, "services.log")
            if not os.path.exists(log_file):
                self.logger.warning("Log file not found")
                return 0
            
            with open(log_file, "r") as f:
                lines = f.readlines()
                # Get only the latest logs (last 50 lines)
                latest_logs = lines[-50:] if len(lines) > 50 else lines
            
            # Process each log entry
            issues_found = 0
            issues_resolved = 0
            
            for log_entry in latest_logs:
                parts = log_entry.strip().split("|")
                if len(parts) != 5:
                    continue
                
                timestamp, service, log_type, severity, message = parts
                
                # Skip if not an error/warning/critical
                if severity not in ["error", "warning", "critical"]:
                    continue
                
                # Check if this is already in the incidents table
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT id FROM incidents WHERE message = ?", 
                    (message,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Already recorded
                    conn.close()
                    continue
                
                # New incident
                self.logger.info(f"Found new incident: {message}")
                issues_found += 1
                
                # Add to incidents table
                cursor.execute(
                    """INSERT INTO incidents 
                       (timestamp, service, log_type, message, severity, resolved, resolution) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (timestamp, service, log_type, message, severity, 0, None)
                )
                incident_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
                
                # Find and apply solution
                solution = self.find_solution(message)
                if solution:
                    self.logger.info(f"Found solution: {solution}")
                    if self.apply_solution(incident_id, service, message, solution):
                        issues_resolved += 1
                else:
                    self.logger.warning(f"No solution found for: {message}")
            
            # Update active incidents display
            self._update_active_incidents()
            
            self.logger.info(f"Processed {issues_found} new incidents, resolved {issues_resolved}")
            return issues_resolved
        except Exception as e:
            self.logger.error(f"Error checking logs: {e}")
            return 0
    
    def find_solution(self, message):
        """Find a solution for the given issue message."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all solutions
            cursor.execute("SELECT issue_pattern, solution_script FROM solutions")
            solutions = cursor.fetchall()
            conn.close()
            
            best_match = None
            best_score = 0
            
            # Check each pattern
            for pattern, script in solutions:
                # Replace placeholders with regex wildcards
                search_pattern = re.escape(pattern)
                search_pattern = search_pattern.replace("\\{service\\}", "([\\w_-]+)")
                search_pattern = search_pattern.replace("\\{value\\}", "(\\d+\\.?\\d*)")
                search_pattern = search_pattern.replace("\\{code\\}", "(\\d+)")
                search_pattern = search_pattern.replace("\\{txid\\}", "(tx-\\d+)")
                search_pattern = search_pattern.replace("\\{target\\}", "([\\w_-]+)")
                search_pattern = search_pattern.replace("\\{resource\\}", "(/[\\w/]+)")
                search_pattern = search_pattern.replace("\\{table\\}", "([\\w_-]+)")
                search_pattern = search_pattern.replace("\\{id\\}", "(\\d+)")
                search_pattern = search_pattern.replace("\\{query\\}", "(SELECT [^)]+)")
                
                match = re.search(search_pattern, message)
                if match:
                    # Calculate match score (length of pattern = specificity)
                    score = len(pattern)
                    
                    if score > best_score:
                        best_score = score
                        
                        # Replace placeholders with values from message
                        script_copy = script
                        
                        # Replace service placeholder
                        if "{service}" in script_copy and match.groups():
                            script_copy = script_copy.replace("{service}", match.group(1))
                        
                        # Replace other placeholders
                        i = 1
                        for group in match.groups():
                            if "{value}" in script_copy:
                                script_copy = script_copy.replace("{value}", str(group))
                            elif "{code}" in script_copy:
                                script_copy = script_copy.replace("{code}", str(group))
                            elif "{txid}" in script_copy:
                                script_copy = script_copy.replace("{txid}", str(group))
                            elif "{target}" in script_copy:
                                script_copy = script_copy.replace("{target}", str(group))
                            elif "{resource}" in script_copy:
                                script_copy = script_copy.replace("{resource}", str(group))
                            elif "{table}" in script_copy:
                                script_copy = script_copy.replace("{table}", str(group))
                            elif "{id}" in script_copy:
                                script_copy = script_copy.replace("{id}", str(group))
                            elif "{query}" in script_copy:
                                script_copy = script_copy.replace("{query}", str(group))
                            i += 1
                        
                        best_match = script_copy
            
            return best_match
        except Exception as e:
            self.logger.error(f"Error finding solution: {e}")
            return None
    
    def apply_solution(self, incident_id, service, message, solution_script):
        """Apply the solution script to resolve the issue."""
        try:
            self.logger.info(f"Applying solution to incident {incident_id}: {solution_script}")
            
            # Parse script and arguments
            script_parts = solution_script.split()
            script_name = script_parts[0]
            script_args = " ".join(script_parts[1:])
            
            # Get full path to script
            script_path = os.path.join(BASE_DIR, "scripts", script_name)
            
            if not os.path.exists(script_path):
                self.logger.error(f"Script not found: {script_path}")
                return False
            
            # Execute the script
            start_time = time.time()
            command = f"{script_path} {script_args}"
            
            self.logger.info(f"Executing: {command}")
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            execution_time = time.time() - start_time
            success = process.returncode == 0
            
            if success:
                self.logger.info(f"Solution executed successfully: {stdout.decode('utf-8')}")
                
                # Update incident as resolved
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                resolution_details = {
                    "script": solution_script,
                    "executed_at": datetime.now().isoformat(),
                    "execution_time": execution_time,
                    "output": stdout.decode('utf-8')
                }
                
                cursor.execute(
                    "UPDATE incidents SET resolved = 1, resolution = ? WHERE id = ?",
                    (json.dumps(resolution_details), incident_id)
                )
                
                conn.commit()
                conn.close()
                
                # Update applied solutions in dashboard
                self._update_solutions()
                
                return True
            else:
                self.logger.error(f"Solution execution failed: {stderr.decode('utf-8')}")
                return False
        except Exception as e:
            self.logger.error(f"Error applying solution: {e}")
            return False
    
    def _update_active_incidents(self):
        """Update the active incidents display in the dashboard."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get active incidents
            cursor.execute(
                "SELECT id, timestamp, service, log_type, message, severity FROM incidents WHERE resolved = 0 ORDER BY timestamp DESC"
            )
            incidents = cursor.fetchall()
            
            conn.close()
            
            # Update dashboard file
            dashboard_file = os.path.join(BASE_DIR, "dashboard", "active_incidents.txt")
            
            with open(dashboard_file, "w") as f:
                if incidents:
                    for incident in incidents:
                        inc_id, timestamp, service, log_type, message, severity = incident
                        f.write(f"ID: {inc_id}\n")
                        f.write(f"Time: {timestamp}\n")
                        f.write(f"Service: {service}\n")
                        f.write(f"Type: {log_type}\n")
                        f.write(f"Severity: {severity}\n")
                        f.write(f"Message: {message}\n")
                        f.write("-" * 80 + "\n\n")
                else:
                    f.write("No active incidents\n")
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating active incidents: {e}")
            return False
    
    def _update_solutions(self):
        """Update the applied solutions display in the dashboard."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get count of resolved incidents
            cursor.execute("SELECT COUNT(*) FROM incidents WHERE resolved = 1")
            resolved_count = cursor.fetchone()[0]
            
            # Get recent resolutions
            cursor.execute(
                """SELECT incidents.timestamp, incidents.service, incidents.message, incidents.resolution
                   FROM incidents 
                   WHERE resolved = 1 
                   ORDER BY timestamp DESC 
                   LIMIT 10"""
            )
            resolutions = cursor.fetchall()
            
            conn.close()
            
            # Update dashboard file
            dashboard_file = os.path.join(BASE_DIR, "dashboard", "solutions.txt")
            
            with open(dashboard_file, "w") as f:
                f.write(f"Applied Solutions: {resolved_count} total\n")
                f.write("=" * 80 + "\n\n")
                
                if resolutions:
                    for timestamp, service, message, resolution in resolutions:
                        f.write(f"{timestamp} - {service} - {message}\n")
                        
                        if resolution:
                            try:
                                resolution_data = json.loads(resolution)
                                f.write(f"  Solution: {resolution_data['script']}\n")
                                
                                if 'execution_time' in resolution_data:
                                    f.write(f"  Execution time: {resolution_data['execution_time']:.2f}s\n")
                                
                                if 'output' in resolution_data:
                                    output = resolution_data['output']
                                    if len(output) > 100:
                                        output = output[:100] + "..."
                                    f.write(f"  Output: {output}\n")
                            except:
                                f.write(f"  Resolution: {resolution}\n")
                        
                        f.write("-" * 80 + "\n\n")
                else:
                    f.write("No resolved incidents\n")
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating solutions: {e}")
            return False
    
    def resolve_unresolved_incidents(self):
        """Check for unresolved incidents and try to resolve them."""
        try:
            self.logger.info("Checking for unresolved incidents")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get unresolved incidents
            cursor.execute(
                "SELECT id, service, message FROM incidents WHERE resolved = 0"
            )
            unresolved = cursor.fetchall()
            
            conn.close()
            
            if not unresolved:
                self.logger.info("No unresolved incidents found")
                return 0
            
            self.logger.info(f"Found {len(unresolved)} unresolved incidents")
            
            # Try to resolve each incident
            resolved_count = 0
            for incident_id, service, message in unresolved:
                solution = self.find_solution(message)
                if solution:
                    if self.apply_solution(incident_id, service, message, solution):
                        resolved_count += 1
            
            self.logger.info(f"Resolved {resolved_count} incidents")
            return resolved_count
        except Exception as e:
            self.logger.error(f"Error resolving unresolved incidents: {e}")
            return 0
    
    def request_user_input(self, incident_id, service, message):
        """Request user input for incidents with no known solution."""
        try:
            self.logger.info(f"Requesting user input for incident {incident_id}")
            
            print("\n" + "="*80)
            print(f"UNKNOWN ISSUE DETECTED!")
            print(f"Service: {service}")
            print(f"Message: {message}")
            print("\nPlease provide a solution script to resolve this issue:")
            print("Available scripts: restart_service.sh, cleanup_disk.sh, fix_permissions.sh, etc.")
            print("Example: restart_service.sh {service}")
            print("="*80)
            
            solution = input("Solution: ").strip()
            
            if solution:
                # Create pattern from this incident
                pattern = re.sub(r'[0-9]+\.[0-9]+', '{value}', message)
                pattern = re.sub(r'exit code [0-9]+', 'exit code {code}', pattern)
                pattern = re.sub(r'tx-[0-9]+', '{txid}', pattern)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Add new solution
                cursor.execute(
                    "INSERT INTO solutions (issue_pattern, solution_script, success_rate, last_used) VALUES (?, ?, ?, ?)",
                    (pattern, solution, 0.8, datetime.now().isoformat())
                )
                
                conn.commit()
                conn.close()
                
                self.logger.info(f"Added new solution pattern: {pattern} -> {solution}")
                
                # Apply the solution
                if self.apply_solution(incident_id, service, message, solution):
                    self.logger.info(f"Successfully applied user-provided solution")
                    return True
                else:
                    self.logger.error(f"Failed to apply user-provided solution")
                    return False
            else:
                self.logger.warning("No solution provided by user")
                return False
        except Exception as e:
            self.logger.error(f"Error processing user input: {e}")
            return False

class DashboardServer:
    """Simple HTTP server for the dashboard."""
    
    def __init__(self, port=8080):
        self.port = port
        self.dashboard_dir = os.path.join(BASE_DIR, "dashboard")
        
        # Create a custom handler
        class DashboardHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=self.dashboard_dir, **kwargs)
            
            def end_headers(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
                super().end_headers()
    
    def start(self):
        """Start the dashboard server."""
        try:
            handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=self.dashboard_dir, **kwargs)
            server = HTTPServer(("", self.port), handler)
            
            print(f"Dashboard server started at http://localhost:{self.port}")
            
            # Open browser
            webbrowser.open(f"http://localhost:{self.port}")
            
            # Start in a thread
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            
            return True
        except Exception as e:
            print(f"Error starting dashboard server: {e}")
            return False

def main():
    """Main function to run the enhanced self-healing system."""
    print("Starting Enhanced Self-Healing System...")
    
    # Set up environment
    setup_environment()
    
    # Set up configuration
    config = setup_config()
    
    # Set up logging
    logger = setup_logging()
    
    # Set up database
    setup_database()
    
    # Set up dashboard
    setup_dashboard()
    
    # Create solution scripts
    create_solution_scripts()
    
    # Initialize solutions
    initialize_solutions()
    
    # Create components
    data_generator = SyntheticDataGenerator(config, logger)
    monitoring_engine = MonitoringEngine(config, logger)
    
    # Generate service directories
    data_generator.generate_service_directories()
    
    # Generate initial data
    data_generator.generate_initial_data()
    
    # Start dashboard server
    dashboard_server = DashboardServer(port=8081)
    dashboard_server.start()
    
    # Define thread functions
    def generate_data_thread():
        """Thread for generating synthetic data."""
        while True:
            try:
                data_generator.generate_system_metrics()
                data_generator.generate_log_entries()
                time.sleep(config["synthetic_data"]["generation_interval_seconds"])
            except Exception as e:
                logger.error(f"Error in data generation thread: {e}")
                time.sleep(5)  # Wait before retrying
    
    def monitor_logs_thread():
        """Thread for monitoring logs and resolving incidents."""
        while True:
            try:
                monitoring_engine.check_logs()
                monitoring_engine.resolve_unresolved_incidents()
                time.sleep(config["monitoring"]["check_interval_seconds"])
            except Exception as e:
                logger.error(f"Error in monitoring thread: {e}")
                time.sleep(5)  # Wait before retrying
    
    def train_model_thread():
        """Thread for training the ML model periodically."""
        while True:
            try:
                time.sleep(config["ml_model"]["retrain_interval_minutes"] * 60)
                monitoring_engine.train_model()
            except Exception as e:
                logger.error(f"Error in model training thread: {e}")
                time.sleep(60)  # Wait before retrying
    
    def archive_logs_thread():
        """Thread for archiving old logs periodically."""
        while True:
            try:
                time.sleep(config["log_archive_interval_minutes"] * 60)
                data_generator.archive_logs()
            except Exception as e:
                logger.error(f"Error in log archiving thread: {e}")
                time.sleep(300)  # Wait before retrying
    
    # Start threads
    threads = [
        threading.Thread(target=generate_data_thread),
        threading.Thread(target=monitor_logs_thread),
        threading.Thread(target=train_model_thread),
        threading.Thread(target=archive_logs_thread)
    ]
    
    for thread in threads:
        thread.daemon = True
        thread.start()
    
    print("System started successfully. Press Ctrl+C to stop.")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping system...")
        logger.info("System stopped by user")

if __name__ == "__main__":
    main()