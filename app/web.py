import json
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .prompts import INTENT_PROMPTS
from .router import classify_intent, route_and_respond

app = FastAPI(title="LLM Prompt Router - Real-Time Studio")


class RouteRequest(BaseModel):
    message: str


PERSONA_DETAILS = {
    "code": {
        "title": "Software Engineering Expert",
        "icon": "💻",
        "color": "#38bdf8",
        "bg": "rgba(56, 189, 248, 0.12)",
        "border": "rgba(56, 189, 248, 0.35)",
        "desc": "Generates robust, production-quality code with input validation and architectural clarity.",
    },
    "data": {
        "title": "Senior Data Analyst",
        "icon": "📊",
        "color": "#34d399",
        "bg": "rgba(52, 211, 153, 0.12)",
        "border": "rgba(52, 211, 153, 0.35)",
        "desc": "Interprets statistical patterns, anomaly detection, and recommends visualizations.",
    },
    "writing": {
        "title": "Direct Writing Coach",
        "icon": "✍️",
        "color": "#c084fc",
        "bg": "rgba(192, 132, 252, 0.12)",
        "border": "rgba(192, 132, 252, 0.35)",
        "desc": "Provides actionable feedback on tone, cadence, and conciseness without ghostwriting.",
    },
    "career": {
        "title": "Pragmatic Career Advisor",
        "icon": "💼",
        "color": "#fbbf24",
        "bg": "rgba(251, 191, 36, 0.12)",
        "border": "rgba(251, 191, 36, 0.35)",
        "desc": "Delivers realistic, step-by-step career strategies and interview preparation advice.",
    },
    "unclear": {
        "title": "Clarification Guardrail",
        "icon": "❓",
        "color": "#f87171",
        "bg": "rgba(248, 113, 113, 0.12)",
        "border": "rgba(248, 113, 113, 0.35)",
        "desc": "Detects ambiguity or low confidence, prompting targeted clarification questions.",
    },
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LLM-Powered Prompt Router</title>
  
  <!-- Modern Typography & Icons -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  
  <!-- Markdown & Code Highlighting Libraries -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

  <style>
    :root {
      --bg-gradient: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #0b0f19 50%, #030712 100%);
      --card-bg: rgba(15, 23, 42, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover-border: rgba(99, 102, 241, 0.4);
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --accent-glow: rgba(99, 102, 241, 0.3);
      --code-color: #38bdf8;
      --data-color: #34d399;
      --writing-color: #c084fc;
      --career-color: #fbbf24;
      --unclear-color: #f87171;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #030712;
      background-image: var(--bg-gradient);
      background-attachment: fixed;
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1.25rem 4rem 1.25rem;
    }

    .container {
      width: 100%;
      max-width: 1080px;
    }

    /* Top Navigation Header */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2.25rem;
      padding-bottom: 1.25rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }

    .brand-icon {
      width: 42px;
      height: 42px;
      border-radius: 12px;
      background: linear-gradient(135deg, #6366f1 0%, #ec4899 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.4rem;
      box-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
    }

    .brand-text h1 {
      font-size: 1.35rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(to right, #ffffff, #cbd5e1);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-text p {
      font-size: 0.78rem;
      color: var(--text-muted);
      letter-spacing: 0.02em;
    }

    .header-badges {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.28);
      color: #34d399;
      font-size: 0.75rem;
      font-weight: 600;
      padding: 0.35rem 0.8rem;
      border-radius: 999px;
    }

    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* Main Grid Layout */
    .main-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.75rem;
    }

    /* Glassmorphic Cards */
    .glass-card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 1.25rem;
      padding: 1.5rem;
      box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .glass-card:hover {
      border-color: var(--card-hover-border);
    }

    /* Persona Selector Pills / Info bar */
    .personas-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }

    .persona-badge {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.6rem 0.85rem;
      border-radius: 0.85rem;
      font-size: 0.8rem;
      font-weight: 600;
      background: rgba(15, 23, 42, 0.5);
      border: 1px solid rgba(255, 255, 255, 0.05);
      color: var(--text-muted);
      transition: all 0.2s ease;
    }

    .persona-badge.active-code { border-color: var(--code-color); color: var(--code-color); background: rgba(56, 189, 248, 0.1); }
    .persona-badge.active-data { border-color: var(--data-color); color: var(--data-color); background: rgba(52, 211, 153, 0.1); }
    .persona-badge.active-writing { border-color: var(--writing-color); color: var(--writing-color); background: rgba(192, 132, 252, 0.1); }
    .persona-badge.active-career { border-color: var(--career-color); color: var(--career-color); background: rgba(251, 191, 36, 0.1); }

    /* Presets Section */
    .presets-container {
      margin-bottom: 1.25rem;
    }

    .presets-label {
      font-size: 0.75rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      margin-bottom: 0.6rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .chips-wrapper {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .chip {
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.06);
      color: #cbd5e1;
      padding: 0.4rem 0.8rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
    }

    .chip:hover {
      background: rgba(99, 102, 241, 0.18);
      border-color: rgba(99, 102, 241, 0.5);
      color: #ffffff;
      transform: translateY(-1px);
    }

    /* Prompt Input Card */
    .prompt-area {
      position: relative;
    }

    textarea {
      width: 100%;
      min-height: 120px;
      max-height: 320px;
      padding: 1.1rem 1.2rem;
      border-radius: 0.9rem;
      border: 1px solid rgba(255, 255, 255, 0.12);
      background: rgba(2, 6, 23, 0.85);
      color: var(--text-main);
      font-family: inherit;
      font-size: 0.95rem;
      line-height: 1.6;
      resize: vertical;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    .prompt-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 1rem;
    }

    .shortcut-hint {
      font-size: 0.75rem;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }

    .kbd {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.7rem;
    }

    .btn-submit {
      background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
      color: #ffffff;
      border: none;
      padding: 0.75rem 1.6rem;
      border-radius: 0.75rem;
      font-size: 0.9rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.6rem;
      box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35);
      transition: all 0.2s ease;
    }

    .btn-submit:hover:not(:disabled) {
      background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
      box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
      transform: translateY(-1px);
    }

    .btn-submit:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      transform: none;
    }

    /* Real-Time Pipeline Progress Indicator */
    .pipeline-container {
      display: none;
      margin: 1.5rem 0;
      padding: 1.25rem;
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(99, 102, 241, 0.25);
      border-radius: 1rem;
      animation: fadeIn 0.3s ease;
    }

    .pipeline-steps {
      display: flex;
      justify-content: space-between;
      position: relative;
    }

    .pipeline-step {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.75rem;
      color: var(--text-muted);
      z-index: 1;
      text-align: center;
      width: 25%;
    }

    .step-circle {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: #1e293b;
      border: 2px solid #334155;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      font-weight: bold;
      color: #94a3b8;
      transition: all 0.3s ease;
    }

    .pipeline-step.active .step-circle {
      border-color: #6366f1;
      background: #4f46e5;
      color: white;
      box-shadow: 0 0 12px rgba(99, 102, 241, 0.6);
      animation: pulse 1s infinite alternate;
    }

    .pipeline-step.completed .step-circle {
      border-color: #10b981;
      background: #059669;
      color: white;
    }

    /* Response & Results Section */
    .results-container {
      display: none;
      margin-top: 1.75rem;
      animation: slideUp 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes slideUp {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    /* Intent Telemetry Header */
    .telemetry-card {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      padding: 1.1rem 1.4rem;
      border-radius: 1rem 1rem 0 0;
      border: 1px solid var(--card-border);
      background: rgba(30, 41, 59, 0.5);
      gap: 1rem;
    }

    .intent-display {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }

    .intent-icon-large {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
    }

    .intent-title-group h2 {
      font-size: 1.05rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .intent-tag {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.15rem 0.55rem;
      border-radius: 6px;
    }

    .intent-desc {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 0.15rem;
    }

    .metrics-group {
      display: flex;
      align-items: center;
      gap: 1.25rem;
    }

    .metric-pill {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }

    .metric-label {
      font-size: 0.68rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }

    .metric-value {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.95rem;
      font-weight: 700;
      color: #f8fafc;
    }

    /* Response Body & Code Highlighting */
    .response-body {
      background: rgba(2, 6, 23, 0.92);
      border: 1px solid var(--card-border);
      border-top: none;
      border-radius: 0 0 1rem 1rem;
      padding: 1.75rem;
      position: relative;
    }

    .response-actions {
      display: flex;
      justify-content: flex-end;
      margin-bottom: 0.85rem;
    }

    .btn-copy {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-muted);
      padding: 0.35rem 0.75rem;
      border-radius: 0.5rem;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.2s ease;
    }

    .btn-copy:hover {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }

    .markdown-content {
      font-size: 0.95rem;
      line-height: 1.7;
      color: #e2e8f0;
    }

    .markdown-content h1,
    .markdown-content h2,
    .markdown-content h3 {
      color: #ffffff;
      margin: 1.25rem 0 0.6rem 0;
      font-weight: 700;
    }

    .markdown-content h1 { font-size: 1.25rem; }
    .markdown-content h2 { font-size: 1.1rem; }
    .markdown-content h3 { font-size: 1rem; }

    .markdown-content p {
      margin-bottom: 0.85rem;
    }

    .markdown-content ul,
    .markdown-content ol {
      margin: 0.5rem 0 0.85rem 1.4rem;
    }

    .markdown-content li {
      margin-bottom: 0.35rem;
    }

    .markdown-content pre {
      background: #1e1e2e;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 0.75rem;
      padding: 1rem;
      margin: 1rem 0;
      overflow-x: auto;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.86rem;
    }

    .markdown-content code:not(pre code) {
      font-family: 'JetBrains Mono', monospace;
      background: rgba(255, 255, 255, 0.1);
      color: #38bdf8;
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-size: 0.85em;
    }

    /* History Feed Drawer */
    .history-card {
      margin-top: 2rem;
    }

    .history-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      user-select: none;
    }

    .history-title {
      font-size: 0.9rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #cbd5e1;
    }

    .history-list {
      margin-top: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      max-height: 280px;
      overflow-y: auto;
    }

    .history-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.65rem 0.9rem;
      background: rgba(2, 6, 23, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 0.65rem;
      font-size: 0.8rem;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .history-item:hover {
      background: rgba(99, 102, 241, 0.1);
      border-color: rgba(99, 102, 241, 0.3);
    }

    .history-query {
      max-width: 65%;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: #e2e8f0;
    }

    /* Toast Notification */
    .toast {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: #10b981;
      color: #020617;
      font-weight: 700;
      font-size: 0.85rem;
      padding: 0.6rem 1.1rem;
      border-radius: 999px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
      display: none;
      animation: fadeIn 0.2s ease;
      z-index: 100;
    }
  </style>
</head>
<body>

  <div class="container">
    
    <!-- Top Header -->
    <header>
      <div class="brand">
        <div class="brand-icon">⚡</div>
        <div class="brand-text">
          <h1>LLM-Powered Prompt Router</h1>
          <p>Real-Time Intent Classification & Expert Routing Engine</p>
        </div>
      </div>
      <div class="header-badges">
        <div class="status-pill">
          <div class="status-dot"></div>
          <span>Groq Llama-3.1 8B Live</span>
        </div>
      </div>
    </header>

    <!-- Main Workspace -->
    <div class="main-grid">
      
      <!-- Persona Overview Bar -->
      <div class="personas-bar">
        <div class="persona-badge" id="badge-code">
          <span>💻</span> <span>Software Engineer</span>
        </div>
        <div class="persona-badge" id="badge-data">
          <span>📊</span> <span>Data Analyst</span>
        </div>
        <div class="persona-badge" id="badge-writing">
          <span>✍️</span> <span>Writing Coach</span>
        </div>
        <div class="persona-badge" id="badge-career">
          <span>💼</span> <span>Career Advisor</span>
        </div>
      </div>

      <!-- Prompt Input Glass Card -->
      <div class="glass-card prompt-area">
        
        <!-- Presets / Quick Prompt Chips -->
        <div class="presets-container">
          <div class="presets-label">
            <span>⚡ Quick Test Queries</span>
          </div>
          <div class="chips-wrapper">
            <button type="button" class="chip" onclick="applyPreset('how do i sort a list of objects in python?')">
              💻 Python QuickSort
            </button>
            <button type="button" class="chip" onclick="applyPreset('what\\'s the average of these numbers: 12, 45, 23, 67, 34')">
              📊 Statistical Average
            </button>
            <button type="button" class="chip" onclick="applyPreset('This paragraph sounds awkward, can you help me fix it?')">
              ✍️ Sentence Flow Critique
            </button>
            <button type="button" class="chip" onclick="applyPreset('I\\'m preparing for a job interview, any tips?')">
              💼 Interview Strategies
            </button>
            <button type="button" class="chip" onclick="applyPreset('hey, help me out')">
              ❓ Ambiguous Prompt
            </button>
          </div>
        </div>

        <form id="router-form" onsubmit="handleRoute(event)">
          <textarea 
            id="user-input" 
            name="message" 
            placeholder="Type any question or prompt here (e.g., debug a script, analyze metrics, review writing, or request career steps)..."
            required
          ></textarea>

          <div class="prompt-footer">
            <div class="shortcut-hint">
              <span>Press</span> <span class="kbd">Ctrl</span> + <span class="kbd">Enter</span> <span>to route</span>
            </div>
            <button type="submit" id="btn-submit" class="btn-submit">
              <span>Route & Execute</span>
              <span>⚡</span>
            </button>
          </div>
        </form>

        <!-- Live Routing Pipeline Progress Bar -->
        <div class="pipeline-container" id="pipeline-progress">
          <div class="pipeline-steps">
            <div class="pipeline-step" id="step-1">
              <div class="step-circle">1</div>
              <span>Ingesting</span>
            </div>
            <div class="pipeline-step" id="step-2">
              <div class="step-circle">2</div>
              <span>Classifying Intent</span>
            </div>
            <div class="pipeline-step" id="step-3">
              <div class="step-circle">3</div>
              <span>Selecting Persona</span>
            </div>
            <div class="pipeline-step" id="step-4">
              <div class="step-circle">4</div>
              <span>Generating</span>
            </div>
          </div>
        </div>

      </div>

      <!-- Results & Response Area -->
      <div class="results-container" id="results-area">
        
        <!-- Telemetry Header -->
        <div class="telemetry-card" id="telemetry-card">
          <div class="intent-display">
            <div class="intent-icon-large" id="intent-icon">🤖</div>
            <div class="intent-title-group">
              <h2>
                <span id="persona-title">Software Engineering Expert</span>
                <span class="intent-tag" id="intent-tag">CODE</span>
              </h2>
              <div class="intent-desc" id="persona-desc">Specialized AI Persona Active</div>
            </div>
          </div>

          <div class="metrics-group">
            <div class="metric-pill">
              <span class="metric-label">Confidence</span>
              <span class="metric-value" id="metric-confidence">98.0%</span>
            </div>
            <div class="metric-pill">
              <span class="metric-label">Latency</span>
              <span class="metric-value" id="metric-latency">240ms</span>
            </div>
          </div>
        </div>

        <!-- Markdown Formatted Response Output -->
        <div class="response-body">
          <div class="response-actions">
            <button type="button" class="btn-copy" onclick="copyResponse()">
              <span>📋 Copy Response</span>
            </button>
          </div>
          <div class="markdown-content" id="response-content">
            <!-- Rendered by marked.js -->
          </div>
        </div>

      </div>

      <!-- Session Audit Log / Recent Activity -->
      <div class="glass-card history-card">
        <div class="history-header" onclick="toggleHistory()">
          <div class="history-title">
            <span>📜 Recent Routing Telemetry</span>
          </div>
          <span style="font-size: 0.75rem; color: var(--text-muted);">Synced with route_log.jsonl</span>
        </div>
        <div class="history-list" id="history-list">
          <div style="color: var(--text-muted); font-size: 0.8rem; text-align: center; padding: 1rem;">
            No requests executed in this session yet.
          </div>
        </div>
      </div>

    </div>

  </div>

  <div class="toast" id="toast">Copied to clipboard!</div>

  <script>
    const PERSONAS = """ + json.dumps(PERSONA_DETAILS) + """;
    let rawResponseText = "";

    // Highlight.js configuration
    marked.setOptions({
      highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
          try {
            return hljs.highlight(code, { language: lang }).value;
          } catch (_) {}
        }
        return hljs.highlightAuto(code).value;
      },
      breaks: true
    });

    // Keyboard shortcut: Ctrl + Enter / Cmd + Enter to submit
    document.getElementById('user-input').addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('router-form').requestSubmit();
      }
    });

    function applyPreset(text) {
      const textarea = document.getElementById('user-input');
      textarea.value = text;
      textarea.focus();
      handleRoute(new Event('submit'));
    }

    async function handleRoute(e) {
      if (e) e.preventDefault();
      
      const input = document.getElementById('user-input');
      const query = input.value.trim();
      if (!query) return;

      const btnSubmit = document.getElementById('btn-submit');
      const pipeline = document.getElementById('pipeline-progress');
      const resultsArea = document.getElementById('results-area');

      // Reset UI & start animations
      btnSubmit.disabled = true;
      pipeline.style.display = 'block';
      resultsArea.style.display = 'none';
      resetBadges();

      // Animate pipeline stages
      setStep(1);
      setTimeout(() => setStep(2), 200);

      const startTime = performance.now();

      try {
        const response = await fetch('/api/route', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query })
        });

        if (!response.ok) {
          throw new Error('Server returned ' + response.status);
        }

        setStep(3);
        const data = await response.json();
        setStep(4);

        const endTime = performance.now();
        const clientLatency = Math.round(endTime - startTime);

        setTimeout(() => {
          pipeline.style.display = 'none';
          renderResult(data, clientLatency);
          btnSubmit.disabled = false;
          addHistoryItem(query, data.intent, data.confidence);
        }, 300);

      } catch (err) {
        console.error(err);
        alert('Routing request failed. Please check server logs.');
        pipeline.style.display = 'none';
        btnSubmit.disabled = false;
      }
    }

    function setStep(num) {
      for (let i = 1; i <= 4; i++) {
        const el = document.getElementById('step-' + i);
        if (i < num) {
          el.className = 'pipeline-step completed';
        } else if (i === num) {
          el.className = 'pipeline-step active';
        } else {
          el.className = 'pipeline-step';
        }
      }
    }

    function resetBadges() {
      ['code', 'data', 'writing', 'career'].forEach(key => {
        const el = document.getElementById('badge-' + key);
        if (el) el.className = 'persona-badge';
      });
    }

    function renderResult(data, latency) {
      const intentKey = data.intent in PERSONAS ? data.intent : 'unclear';
      const persona = PERSONAS[intentKey];
      rawResponseText = data.response;

      // Update Persona badge bar
      const activeBadge = document.getElementById('badge-' + intentKey);
      if (activeBadge) {
        activeBadge.classList.add('active-' + intentKey);
      }

      // Update Telemetry Header
      const card = document.getElementById('telemetry-card');
      card.style.background = persona.bg;
      card.style.borderColor = persona.border;

      document.getElementById('intent-icon').textContent = persona.icon;
      document.getElementById('persona-title').textContent = persona.title;
      
      const tag = document.getElementById('intent-tag');
      tag.textContent = intentKey.toUpperCase();
      tag.style.background = persona.color;
      tag.style.color = '#020617';

      document.getElementById('persona-desc').textContent = persona.desc;
      document.getElementById('metric-confidence').textContent = (data.confidence * 100).toFixed(1) + '%';
      document.getElementById('metric-latency').textContent = (data.latency_ms || latency) + 'ms';

      // Render Markdown Response
      const contentEl = document.getElementById('response-content');
      contentEl.innerHTML = marked.parse(data.response);

      // Re-apply highlight.js
      document.querySelectorAll('#response-content pre code').forEach((block) => {
        hljs.highlightElement(block);
      });

      document.getElementById('results-area').style.display = 'block';
    }

    function copyResponse() {
      if (!rawResponseText) return;
      navigator.clipboard.writeText(rawResponseText).then(() => {
        const toast = document.getElementById('toast');
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 2000);
      });
    }

    function addHistoryItem(query, intent, confidence) {
      const list = document.getElementById('history-list');
      const emptyMsg = list.querySelector('div[style*="text-align: center"]');
      if (emptyMsg) list.innerHTML = '';

      const item = document.createElement('div');
      item.className = 'history-item';
      const intentKey = intent in PERSONAS ? intent : 'unclear';
      const persona = PERSONAS[intentKey];

      item.innerHTML = `
        <span class="history-query">"${escapeHtml(query)}"</span>
        <span style="display:flex; align-items:center; gap:0.5rem;">
          <span style="color:${persona.color}; font-weight:700;">${persona.icon} ${intent}</span>
          <span style="color:var(--text-muted); font-family:monospace;">(${(confidence * 100).toFixed(0)}%)</span>
        </span>
      `;

      item.onclick = () => {
        document.getElementById('user-input').value = query;
        handleRoute();
      };

      list.prepend(item);
    }

    function escapeHtml(text) {
      const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
      return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    // Load initial recent activity from server logs on page load
    async function loadRecentLogs() {
      try {
        const res = await fetch('/api/logs');
        if (res.ok) {
          const logs = await res.json();
          if (logs && logs.length > 0) {
            const list = document.getElementById('history-list');
            list.innerHTML = '';
            logs.slice(-6).reverse().forEach(log => {
              addHistoryItem(log.user_message, log.intent, log.confidence);
            });
          }
        }
      } catch (_) {}
    }

    window.addEventListener('DOMContentLoaded', loadRecentLogs);
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Render the ultra-modern real-time studio UI."""
    return HTMLResponse(content=HTML_TEMPLATE)


@app.post("/api/route")
async def api_route(payload: RouteRequest) -> JSONResponse:
    """Async API endpoint for fast real-time intent classification and routing."""
    message = payload.message.strip()
    if not message:
        return JSONResponse(
            status_code=400,
            content={"error": "Message cannot be empty"},
        )

    start_time = time.perf_counter()

    # Step 1: Classify intent
    intent_obj = classify_intent(message)

    # Step 2: Route & generate response
    response_text = route_and_respond(message, intent_obj)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000)

    intent_label = str(intent_obj.get("intent", "unclear")).lower()
    confidence = float(intent_obj.get("confidence", 0.0) or 0.0)
    persona_info = PERSONA_DETAILS.get(intent_label, PERSONA_DETAILS["unclear"])

    return JSONResponse(
        content={
            "intent": intent_label,
            "confidence": confidence,
            "persona_name": persona_info["title"],
            "persona_icon": persona_info["icon"],
            "persona_desc": persona_info["desc"],
            "response": response_text,
            "latency_ms": elapsed_ms,
        }
    )


@app.get("/api/logs")
async def get_logs() -> JSONResponse:
    """Return the recent entries from route_log.jsonl."""
    log_paths = [
        os.getenv("ROUTE_LOG_PATH", "route_log.jsonl"),
        "/tmp/route_log.jsonl",
    ]

    entries: List[Dict[str, Any]] = []
    for log_path in log_paths:
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            except Exception:
                pass

    # Return last 20 entries
    return JSONResponse(content=entries[-20:])


@app.post("/", response_class=HTMLResponse)
async def handle_form_submit(message: str = Form(...)) -> HTMLResponse:
    """Fallback standard HTML form handler."""
    return HTMLResponse(content=HTML_TEMPLATE)
