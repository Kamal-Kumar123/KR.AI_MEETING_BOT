# KR.AI_MEETING_BOT
GenAI-powered agentic meeting bot that transforms raw transcripts into smart summaries and action items with deadlines and owners. Built for the Flipr Gen AI Hackathon to boost productivity in hybrid/remote teams. 

# 🤖 AgenticBot - Meeting Summarizer & Action Item Extractor

> **Transform meeting chaos into clarity using GenAI-powered agentic bots.**

![Banner](./banner.png)

## 🚀 Overview

AgenticBot is a GenAI-powered meeting assistant that converts raw meeting transcripts into:

- ⚡ Lightning-fast, human-like summaries  
- ✅ Action items with deadlines and assignees  
- 📤 Shareable formats for Slack, email, Notion, etc.

This tool empowers remote teams to cut through noise, gain clarity, and stay aligned — all without manual note-taking.

---

## 🧠 Key Features

✔️ **LLM-based Summarization**  
✔️ **Action Item Extraction with Owners & Deadlines**  
✔️ **Smart Context Awareness (speaker tags, tone)**  
✔️ **Export Options for Slack / Email / Notion**  
✔️ **Deadline Inference (e.g. "by Monday", "next call")**

---

## 🔧 Tech Stack

### 🖥️ Frontend
- React.js (with TailwindCSS for UI)

### 🛠️ Backend
- FastAPI (Python)  
- RESTful APIs for frontend integration

### 🧠 AI/ML
- OpenAI GPT-4 for summarization and task detection  
- AssemblyAI / Deepgram for transcription

### 📦 Integrations
- Export to Notion, Slack, and Email
- Task management support via Trello or Asana API *(optional)*

---

## 📁 Folder Structure

```bash
agentic-bot/
│
├── backend/
│   └── main.py                # FastAPI app
│   └── summarizer.py          # GPT-based summary & task extractor
│   └── transcription.py       # Deepgram/Whisper integration
│
├── frontend/
│   └── public/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── TranscriptInput.jsx
│
├── requirements.txt
├── README.md
└── .gitignore
