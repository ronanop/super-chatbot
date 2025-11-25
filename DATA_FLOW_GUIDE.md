# Data Flow Guide - AskCache.ai Chatbot

Complete explanation of how data flows through the application from user input to response.

## Overview

```
User Input → Frontend → Backend API → Knowledge Base Search → LLM Generation → Response → Frontend Display
```

---

## 1. User Interaction Flow

### **Step 1: User Types Message**
```
User types "who is aman" in chat widget
    ↓
Frontend (ChatWidget.jsx) captures input
    ↓
handleSendMessage() function triggered
```

**What happens:**
- Input validated (not empty, not loading)
- User message added to local state
- Input field cleared
- Loading state set to true

---

### **Step 2: Frontend Sends Request**
```
Frontend → POST /chat
    ↓
Request Body:
{
  "message": "who is aman",
  "session_id": 123 (or null for new session)
}
    ↓
Headers: Content-Type: application/json
```

**Code Location:** `chatbot-widget/src/components/ChatWidget.jsx` → `handleSendMessage()`

---

## 2. Backend Processing Flow

### **Step 3: Backend Receives Request**
```
FastAPI receives POST /chat
    ↓
app/main.py → chat_endpoint()
    ↓
Creates/retrieves chat session from PostgreSQL
```

**What happens:**
- Validates request payload
- Gets or creates `ChatSession` in database
- Saves user message to `messages` table
- Commits to database

**Code Location:** `app/main.py` → `chat_endpoint()`

---

### **Step 4: Knowledge Base Search**
```
_build_context("who is shraddha")
    ↓
Query Enhancement (query_enhancement.py)
    ↓
Generates variations:
- "who is shraddha"
- "shraddha"
- "shraddha leadership"
- "information about shraddha"
- etc.
    ↓
For each variation:
    ↓
query_similar() → Pinecone Vector Search
    ↓
Gets top 10-15 similar chunks
    ↓
Combines and deduplicates results
    ↓
Returns context string
```

**Data Flow:**
```
User Query
    ↓
Query Enhancement (expands to 5-8 variations)
    ↓
Each variation → Embedding (Gemini text-embedding-004)
    ↓
Vector Search in Pinecone (top_k=10-15 per variation)
    ↓
Combine all results (up to 25 unique matches)
    ↓
Sort by similarity score
    ↓
Extract text from top matches
    ↓
Build context string (~6000 chars max)
```

**Code Locations:**
- `app/main.py` → `_build_context()`
- `app/services/query_enhancement.py` → `enhance_query_for_search()`
- `app/vectorstore/pinecone_store.py` → `query_similar()`
- `app/services/embeddings.py` → `embed_texts()`

---

### **Step 5: LLM Generation**
```
Prompt Construction:
    ↓
Base Instructions (from admin panel or defaults)
    ↓
+ Current Date/Time
    ↓
+ Language Requirements
    ↓
+ Formatting Guidelines
    ↓
+ Knowledge Base Context (if found)
    ↓
+ User Question
    ↓
= Complete Prompt
    ↓
Send to Gemini API (models/gemini-2.5-flash)
    ↓
Get generated response
```

**Prompt Structure:**
```
You are AskCache.ai's virtual assistant...
[Custom Instructions]

CURRENT DATE AND TIME INFORMATION:
- Today's date: January 15, 2024 (Monday)
- Current time: 02:30 PM
...

FORMATTING GUIDELINES:
- ALWAYS use **bold** for important keywords...
...

CONTEXT INFORMATION:
[Knowledge Base Chunks]

USER QUESTION: who is shraddha

INSTRUCTIONS:
- Answer naturally using context...
- Bold important keywords...
```

**Code Location:** `app/main.py` → `chat_endpoint()` → `model.generate_content()`

---

### **Step 6: Response Processing**
```
Gemini API Response
    ↓
Extract reply text
    ↓
Save assistant message to PostgreSQL
    ↓
Check user message count (for form trigger)
    ↓
Return ChatResponse:
{
  "reply": "Shraddha is part of...",
  "session_id": 123,
  "prompt_for_info": false
}
```

**Code Location:** `app/main.py` → `chat_endpoint()`

---

### **Step 7: Auto-Training (Background)**
```
If context found AND auto-training enabled:
    ↓
Background Task Triggered
    ↓
process_conversation_for_training()
    ↓
Extract knowledge using Gemini
    ↓
If useful knowledge found:
    ↓
Split into chunks
    ↓
Generate embeddings
    ↓
Upsert to Pinecone
    ↓
Knowledge base updated!
```

**Code Location:** `app/services/auto_training.py`

---

## 3. Frontend Response Handling

### **Step 8: Frontend Receives Response**
```
Backend → Response JSON
    ↓
Frontend receives in handleSendMessage()
    ↓
Extract reply text
    ↓
Start typewriter effect
```

**What happens:**
- Response received
- Typewriter effect starts (word-by-word display)
- Updates message state as words appear
- Auto-scrolls chat body

**Code Location:** `chatbot-widget/src/components/ChatWidget.jsx` → `handleSendMessage()`

---

### **Step 9: Display Response**
```
Typewriter Effect:
    ↓
Split reply into words
    ↓
Display one word every 30ms
    ↓
Update message content in state
    ↓
React re-renders message bubble
    ↓
Format message (bold keywords, links)
    ↓
Display to user
```

**Code Location:** `chatbot-widget/src/components/ChatWidget.jsx` → Typewriter interval

---

## 4. Data Storage Flow

### **PostgreSQL Database**

**Tables Used:**
1. **chat_sessions**
   - Stores chat session metadata
   - Links to user (if form submitted)

2. **messages**
   - Stores all user and assistant messages
   - Linked to session_id
   - Includes timestamp

3. **users**
   - Stores user information (name, email, phone)
   - Created when form submitted

4. **bot_ui_settings**
   - Stores UI customization settings
   - Colors, bot name, icon, etc.

5. **app_settings**
   - Stores app configuration
   - API URL, custom instructions

**Data Flow:**
```
User Message → Save to messages table
    ↓
Assistant Response → Save to messages table
    ↓
Form Submission → Create/update user, link to session
    ↓
UI Settings Change → Update bot_ui_settings table
```

**Code Location:** `app/db/models.py`

---

### **Pinecone Vector Database**

**Data Flow:**
```
Knowledge Base Upload (PDF/Web)
    ↓
Extract Text → Split into Chunks
    ↓
Generate Embeddings (Gemini text-embedding-004)
    ↓
Upsert to Pinecone
    ↓
Stored as vectors with metadata:
{
  "id": "uuid",
  "values": [0.123, -0.456, ...],  // 768-dim vector
  "metadata": {
    "text": "chunk content",
    "source": "document.pdf",
    "chunk_index": 0
  }
}
```

**Query Flow:**
```
User Query → Generate Embedding
    ↓
Search Pinecone (cosine similarity)
    ↓
Get top matches with scores
    ↓
Extract text from metadata
    ↓
Return as context
```

**Code Locations:**
- `app/vectorstore/pinecone_store.py`
- `app/services/embeddings.py`
- `app/ingestion/pipeline.py`

---

### **Browser Storage (localStorage)**

**What's Stored:**
1. **Chat Messages** (`askcache_messages`)
   - All conversation history
   - Persists across reloads

2. **Session ID** (`askcache_session_id`)
   - Links to backend session
   - Persists across reloads

3. **Form Status** (`askcache_info_submitted`)
   - Whether user submitted form
   - Prevents asking again

4. **UI Settings** (`askcache_ui_settings`)
   - Custom theme, colors, bot name
   - Loads instantly (prevents flash)

**Data Flow:**
```
Settings Fetched from API
    ↓
Save to localStorage
    ↓
On Page Reload:
    ↓
Load from localStorage (instant)
    ↓
Fetch fresh from API (background)
    ↓
Update if changed
```

**Code Location:** `chatbot-widget/src/components/ChatWidget.jsx`

---

## 5. Settings & Configuration Flow

### **UI Settings Flow**
```
Admin Panel → Save Settings
    ↓
POST /admin/bot-ui/save
    ↓
Update bot_ui_settings table
    ↓
Frontend Polls /admin/bot-ui/api/settings
    ↓
Detects timestamp change
    ↓
Updates UI settings
    ↓
Saves to localStorage
    ↓
UI updates immediately
```

**Code Locations:**
- `app/admin/routes.py` → `save_bot_ui_settings()`
- `chatbot-widget/src/components/ChatWidget.jsx` → Settings polling

---

### **API URL Configuration Flow**
```
Admin Panel → Set API URL
    ↓
POST /admin/settings/api-url
    ↓
Update app_settings table
    ↓
Frontend fetches /admin/api/config
    ↓
Gets api_base_url
    ↓
Uses for all API calls
```

**Code Locations:**
- `app/admin/routes.py` → `save_api_url()`
- `chatbot-widget/src/config.js` → `fetchApiConfig()`

---

## 6. Knowledge Base Ingestion Flow

### **PDF Upload Flow**
```
Admin Panel → Upload PDF
    ↓
POST /admin/ingestion/upload
    ↓
Save file to knowledge_base/
    ↓
ingest_pdf() → Extract text
    ↓
split_text() → Create chunks
    ↓
embed_texts() → Generate embeddings
    ↓
upsert_chunks() → Save to Pinecone
    ↓
Knowledge base updated!
```

**Code Location:** `app/ingestion/pdf_loader.py`

---

### **Web Crawling Flow**
```
Admin Panel → Add URL
    ↓
POST /admin/ingestion/crawl
    ↓
crawl_urls() → Scrape pages
    ↓
Extract text from HTML
    ↓
split_text() → Create chunks
    ↓
embed_texts() → Generate embeddings
    ↓
upsert_chunks() → Save to Pinecone
    ↓
Knowledge base updated!
```

**Code Location:** `app/ingestion/crawler.py`

---

## 7. Complete End-to-End Flow

### **Example: User asks "What are your services?"**

```
1. USER ACTION
   User types: "What are your services?"
   ↓
2. FRONTEND
   ChatWidget.jsx → handleSendMessage()
   - Validates input
   - Creates user message in state
   - Shows loading indicator
   ↓
3. API REQUEST
   POST http://api-url/chat
   Body: { "message": "What are your services?", "session_id": 123 }
   ↓
4. BACKEND RECEIVES
   app/main.py → chat_endpoint()
   - Gets session from PostgreSQL
   - Saves user message to database
   ↓
5. KNOWLEDGE BASE SEARCH
   _build_context("What are your services?")
   - Query enhancement: ["what are your services", "services", "offerings", ...]
   - Each variation → Embedding → Pinecone search
   - Gets top 10-15 matches per variation
   - Combines results (up to 25 unique)
   - Builds context string (~6000 chars)
   ↓
6. PROMPT CONSTRUCTION
   Combine:
   - Base instructions
   - Date/time info
   - Formatting guidelines
   - Knowledge base context
   - User question
   ↓
7. LLM GENERATION
   Send prompt to Gemini API (models/gemini-2.5-flash)
   - Model generates response
   - Uses knowledge base context
   - Formats with bold keywords
   ↓
8. RESPONSE PROCESSING
   - Extract reply text
   - Save to PostgreSQL (messages table)
   - Check message count (for form trigger)
   - Return JSON response
   ↓
9. AUTO-TRAINING (Background)
   If context found:
   - Extract knowledge from Q&A
   - Add to Pinecone (background task)
   ↓
10. FRONTEND RECEIVES
    ChatWidget.jsx receives response
    - Extract reply text
    - Start typewriter effect
    ↓
11. DISPLAY
    Word-by-word display (30ms per word)
    - Format message (bold, links)
    - Update message bubble
    - Auto-scroll chat
    ↓
12. COMPLETION
    Typewriter completes
    - Auto-focus input field
    - User can type next message
    ↓
13. STORAGE
    Save to localStorage:
    - Messages (chat history)
    - Session ID
    - UI settings (if updated)
```

---

## 8. Data Flow Diagrams

### **Chat Flow**
```
┌─────────┐
│  User   │
└────┬────┘
     │ Types message
     ↓
┌─────────────────┐
│  Frontend       │
│  (React)        │
│  - Validate     │
│  - Add to state │
└────┬────────────┘
     │ POST /chat
     ↓
┌─────────────────┐
│  Backend API    │
│  (FastAPI)      │
│  - Save message │
│  - Get session  │
└────┬────────────┘
     │
     ├─→ PostgreSQL (save user message)
     │
     ↓
┌─────────────────┐
│ Knowledge Base  │
│ Search          │
│ - Query enhance │
│ - Pinecone      │
└────┬────────────┘
     │ Context
     ↓
┌─────────────────┐
│  LLM Generation │
│  (Gemini API)   │
│  - Generate     │
│  - Format       │
└────┬────────────┘
     │ Response
     ↓
┌─────────────────┐
│  Backend API    │
│  - Save reply   │
│  - Return JSON  │
└────┬────────────┘
     │
     ├─→ PostgreSQL (save assistant message)
     │
     ↓
┌─────────────────┐
│  Frontend       │
│  - Typewriter   │
│  - Display      │
└────┬────────────┘
     │
     ↓
┌─────────┐
│  User   │
│  Sees   │
│  Reply  │
└─────────┘
```

---

### **Knowledge Base Search Flow**
```
User Query: "who is shraddha"
    ↓
┌─────────────────────┐
│ Query Enhancement   │
│ - Expand query      │
│ - Generate variants │
└───────┬─────────────┘
        │
        ├─→ "who is shraddha"
        ├─→ "shraddha"
        ├─→ "shraddha leadership"
        ├─→ "information about shraddha"
        └─→ ...
        ↓
┌─────────────────────┐
│ Embedding Generation│
│ (Gemini API)        │
│ - Convert to vector │
└───────┬─────────────┘
        │
        ↓
┌─────────────────────┐
│ Pinecone Search     │
│ - Cosine similarity │
│ - Top K matches     │
└───────┬─────────────┘
        │
        ├─→ Match 1 (score: 0.85)
        ├─→ Match 2 (score: 0.78)
        ├─→ Match 3 (score: 0.72)
        └─→ ...
        ↓
┌─────────────────────┐
│ Context Building    │
│ - Combine matches   │
│ - Deduplicate       │
│ - Sort by score     │
└───────┬─────────────┘
        │
        ↓
Context String: "Source: leadership.pdf\nShraddha is..."
```

---

### **Settings Flow**
```
┌─────────────────┐
│  Admin Panel    │
│  - Change color │
│  - Save         │
└──────┬──────────┘
       │ POST /admin/bot-ui/save
       ↓
┌─────────────────┐
│  Backend        │
│  - Update DB    │
│  - Save file    │
└──────┬──────────┘
       │
       ├─→ PostgreSQL (bot_ui_settings)
       │
       ↓
┌─────────────────┐
│  Frontend       │
│  - Poll API     │
│  - Detect change│
└──────┬──────────┘
       │
       ├─→ Update UI
       └─→ Save to localStorage
```

---

## 9. Key Data Structures

### **Message Flow**
```javascript
// Frontend → Backend
{
  "message": "who is shraddha",
  "session_id": 123
}

// Backend → Frontend
{
  "reply": "Shraddha is part of...",
  "session_id": 123,
  "prompt_for_info": false
}
```

### **Knowledge Base Context**
```python
# Context string format
"Source: document.pdf\nChunk text here...\n\nSource: website.html\nMore text..."
```

### **UI Settings**
```javascript
{
  "bot_name": "AskCache.ai Assistant",
  "primary_color": "#4338ca",
  "bot_icon_url": "https://...",
  "welcome_message": "Hi! I'm...",
  // ... more settings
}
```

---

## 10. Performance Considerations

### **Caching Layers**
1. **Browser localStorage** - UI settings, messages
2. **React State** - Current messages, UI state
3. **Pinecone** - Vector search (fast)
4. **PostgreSQL** - Session data (indexed)

### **Optimizations**
- Query expansion runs in parallel
- Background tasks (auto-training) don't block
- Typewriter effect for perceived performance
- localStorage for instant UI load

---

## Summary

**Main Flow:**
1. User input → Frontend validation
2. API request → Backend processing
3. Knowledge base search → Pinecone vector search
4. LLM generation → Gemini API
5. Response → Frontend display
6. Storage → PostgreSQL + localStorage

**Key Points:**
- All user messages saved to PostgreSQL
- Knowledge base in Pinecone (vector search)
- UI settings cached in localStorage
- Auto-training updates knowledge base
- Settings sync via polling

This architecture ensures:
- ✅ Fast responses (caching, parallel processing)
- ✅ Persistent data (database + localStorage)
- ✅ Scalable (external APIs, vector DB)
- ✅ User-friendly (instant UI, smooth animations)

