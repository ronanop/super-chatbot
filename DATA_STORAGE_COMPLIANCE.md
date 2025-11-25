# Data Storage & Compliance Guide

Complete breakdown of where data is stored, what data is collected, and compliance considerations.

## Overview

This document explains:
- **Where** data is stored (physical/logical location)
- **What** data is stored
- **Who** has access
- **How long** data is retained
- **How** to delete data
- **Compliance** considerations

---

## Data Storage Locations

### 1. **PostgreSQL Database** (Your Server)

**Location:** Your cloud server or managed database service

**What's Stored:**

#### **Table: `chat_sessions`**
```sql
- id (integer, primary key)
- user_id (integer, foreign key to users table, nullable)
- created_at (timestamp)
- updated_at (timestamp)
```

**Data Stored:**
- Session IDs
- Timestamps (when session created/updated)
- Link to user (if form submitted)

**PII (Personally Identifiable Information):** None directly (only links to users table)

**Retention:** Indefinite (until manually deleted)

**Compliance Notes:**
- Contains session metadata only
- Links to user data if form submitted
- Can be deleted without affecting messages

---

#### **Table: `messages`**
```sql
- id (integer, primary key)
- session_id (integer, foreign key)
- content (text) - The actual message text
- is_user_message (boolean)
- timestamp (timestamp)
```

**Data Stored:**
- **User messages** (all user queries)
- **Assistant responses** (all bot replies)
- Session association
- Timestamps

**PII:** ✅ **YES** - Contains user conversations, potentially sensitive information

**Retention:** Indefinite (until manually deleted)

**Compliance Notes:**
- ⚠️ **HIGH RISK** - Contains all conversation history
- May contain sensitive business information
- May contain personal information shared by users
- Required for GDPR "Right to be Forgotten" requests

**Example Data:**
```json
{
  "id": 123,
  "session_id": 45,
  "content": "What are your pricing plans?",
  "is_user_message": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

#### **Table: `users`**
```sql
- id (integer, primary key)
- name (string, nullable)
- email (string, nullable)
- phone (string, nullable)
- created_at (timestamp)
```

**Data Stored:**
- User names
- Email addresses
- Phone numbers
- Creation timestamp

**PII:** ✅ **YES** - Contains personal information

**Retention:** Indefinite (until manually deleted)

**Compliance Notes:**
- ⚠️ **HIGH RISK** - Contains personal data
- Required for GDPR compliance
- Must support data deletion requests
- Email addresses are identifiers

**Example Data:**
```json
{
  "id": 10,
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

#### **Table: `bot_ui_settings`**
```sql
- id (integer, primary key)
- bot_name (string)
- bot_icon_url (string, nullable)
- header_image_url (string, nullable)
- welcome_message (text, nullable)
- primary_color (string)
- secondary_color (string)
- ... (other UI settings)
- updated_at (timestamp)
```

**Data Stored:**
- UI customization settings
- Bot configuration
- No user data

**PII:** ❌ **NO** - Configuration data only

**Retention:** Indefinite

**Compliance Notes:**
- No personal data
- Safe to keep indefinitely
- Not subject to GDPR deletion requests

---

#### **Table: `app_settings`**
```sql
- id (integer, primary key)
- api_base_url (string, nullable)
- custom_instructions (text, nullable)
- updated_at (timestamp)
```

**Data Stored:**
- Application configuration
- Custom chatbot instructions
- No user data

**PII:** ❌ **NO** - Configuration data only

**Retention:** Indefinite

**Compliance Notes:**
- No personal data
- Safe to keep indefinitely

---

### 2. **Pinecone Vector Database** (External Service)

**Location:** Pinecone's cloud infrastructure (managed service)

**What's Stored:**

#### **Vector Embeddings**
```json
{
  "id": "uuid-string",
  "values": [0.123, -0.456, ...],  // 768-dimensional vector
  "metadata": {
    "text": "Chunk of text from knowledge base",
    "source": "document.pdf",
    "chunk_index": 0,
    "auto_learned": "false",
    "learned_date": "2024-01-15T10:30:00Z"
  }
}
```

**Data Stored:**
- Vector embeddings (mathematical representations)
- Text chunks from knowledge base
- Source information (file names, URLs)
- Metadata (chunk index, learning date)

**PII:** ⚠️ **POTENTIALLY** - Depends on knowledge base content

**Retention:** Indefinite (until manually deleted)

**Compliance Notes:**
- ⚠️ **MEDIUM RISK** - Contains knowledge base content
- May contain business information
- May contain information extracted from conversations (auto-training)
- Text chunks may contain sensitive data if knowledge base does
- Pinecone is a third-party service (check their compliance)

**Important:**
- Knowledge base content is stored here
- Auto-training adds conversation-derived content
- Source files (PDFs) are NOT stored here (only text chunks)

---

### 3. **Browser localStorage** (User's Device)

**Location:** User's web browser on their device

**What's Stored:**

#### **Chat Messages** (`askcache_messages`)
```json
[
  {
    "id": "welcome",
    "role": "assistant",
    "content": "Hi! I'm..."
  },
  {
    "id": "uuid-1",
    "role": "user",
    "content": "What are your services?"
  },
  {
    "id": "uuid-2",
    "role": "assistant",
    "content": "We offer..."
  }
]
```

**PII:** ✅ **YES** - Contains conversation history

**Retention:** Until user clears browser data

**Compliance Notes:**
- ⚠️ **MEDIUM RISK** - Stored on user's device
- User controls this data (can clear it)
- Not accessible by your server
- Persists across sessions
- Subject to browser storage limits

---

#### **Session ID** (`askcache_session_id`)
```json
"123"
```

**PII:** ⚠️ **INDIRECT** - Links to session in database

**Retention:** Until user clears browser data

**Compliance Notes:**
- Links to database records
- Can be used to identify user sessions
- Should be cleared when session ends (optional)

---

#### **Form Status** (`askcache_info_submitted`)
```json
"1"
```

**PII:** ⚠️ **INDIRECT** - Indicates form submission

**Retention:** Until user clears browser data

**Compliance Notes:**
- Indicates user submitted form
- Links to user record in database
- Can be cleared by user

---

#### **UI Settings** (`askcache_ui_settings`)
```json
{
  "bot_name": "AskCache.ai Assistant",
  "primary_color": "#4338ca",
  ...
}
```

**PII:** ❌ **NO** - UI preferences only

**Retention:** Until user clears browser data

**Compliance Notes:**
- No personal data
- Safe to store
- User preference data

---

### 4. **File System** (Your Server)

**Location:** Your cloud server's file system

**What's Stored:**

#### **Knowledge Base Files** (`knowledge_base/`)
- Uploaded PDF files
- Text files
- Other documents

**PII:** ⚠️ **POTENTIALLY** - Depends on file content

**Retention:** Until manually deleted

**Compliance Notes:**
- ⚠️ **MEDIUM RISK** - Contains source documents
- May contain sensitive business information
- Files are processed and stored in Pinecone
- Original files remain on server

---

#### **Uploaded Images** (`uploads/header_images/`)
- Custom header images
- Bot icons

**PII:** ❌ **NO** - Images only

**Retention:** Until manually deleted

**Compliance Notes:**
- No personal data
- Safe to keep

---

#### **Scraped Content** (`scraped/`)
- Web scraped content (if saved)
- Temporary files

**PII:** ⚠️ **POTENTIALLY** - Depends on scraped content

**Retention:** Until manually deleted

**Compliance Notes:**
- May contain public web content
- Check source website terms
- Usually safe if public content

---

### 5. **External Services** (Third-Party)

#### **Google Gemini API**
**Location:** Google's cloud infrastructure

**Data Sent:**
- User queries
- Knowledge base context
- System prompts
- Generated responses

**Data Stored:** Google's servers (check Google's privacy policy)

**PII:** ✅ **YES** - Contains user queries and responses

**Retention:** According to Google's policy (typically not stored long-term)

**Compliance Notes:**
- ⚠️ **HIGH RISK** - Data sent to third party
- Check Google's data processing agreement
- May be subject to Google's retention policies
- Consider data processing agreement (DPA)

---

#### **Pinecone API**
**Location:** Pinecone's cloud infrastructure

**Data Sent:**
- Vector embeddings
- Query vectors
- Metadata

**Data Stored:** Pinecone's servers

**PII:** ⚠️ **POTENTIALLY** - Depends on knowledge base content

**Retention:** Until manually deleted from Pinecone

**Compliance Notes:**
- ⚠️ **MEDIUM RISK** - Third-party service
- Check Pinecone's compliance certifications
- Data is stored in Pinecone's infrastructure
- Consider DPA with Pinecone

---

## Data Flow for Compliance

### **User Conversation Flow**
```
User types message
    ↓
Frontend (Browser) - localStorage
    ↓
POST to Backend API
    ↓
Backend (Your Server) - PostgreSQL
    ├─→ messages table (user message)
    ├─→ chat_sessions table (session metadata)
    ↓
Knowledge Base Search
    ↓
Pinecone (Third-Party) - Vector search
    ↓
LLM Generation
    ↓
Google Gemini API (Third-Party) - Processes query
    ↓
Backend (Your Server) - PostgreSQL
    └─→ messages table (assistant response)
    ↓
Frontend (Browser) - localStorage
    └─→ Messages saved locally
```

**Key Compliance Points:**
- ✅ Data stored in YOUR database (PostgreSQL) - You control it
- ⚠️ Data sent to Google Gemini API - Third party
- ⚠️ Data stored in Pinecone - Third party
- ⚠️ Data cached in user's browser - User controls

---

### **Form Submission Flow**
```
User submits form
    ↓
Frontend (Browser) - localStorage
    └─→ Form status saved
    ↓
POST to Backend API
    ↓
Backend (Your Server) - PostgreSQL
    ├─→ users table (name, email, phone)
    └─→ chat_sessions table (link user to session)
    ↓
Frontend (Browser) - localStorage
    └─→ Form status saved
```

**Key Compliance Points:**
- ✅ Personal data stored in YOUR database
- ⚠️ Form data cached in browser
- ⚠️ Email addresses are identifiers (GDPR)

---

## Data Retention & Deletion

### **Current Retention Policy**

**PostgreSQL:**
- **Messages:** Indefinite (no automatic deletion)
- **Sessions:** Indefinite (no automatic deletion)
- **Users:** Indefinite (no automatic deletion)
- **Settings:** Indefinite (configuration data)

**Pinecone:**
- **Vectors:** Indefinite (until manually deleted)
- **Knowledge Base:** Indefinite (until manually deleted)

**localStorage:**
- **Messages:** Until user clears browser data
- **Session ID:** Until user clears browser data
- **Form Status:** Until user clears browser data

**File System:**
- **PDFs:** Indefinite (until manually deleted)
- **Images:** Indefinite (until manually deleted)

---

### **How to Delete Data**

#### **Delete User Data (GDPR Right to be Forgotten)**

**Option 1: Via Admin Panel** (Manual)
```
1. Go to Admin Panel → Sessions
2. Find user's session
3. Delete session (cascades to messages)
4. Delete user record
```

**Option 2: Via SQL** (Direct)
```sql
-- Delete user's messages
DELETE FROM messages 
WHERE session_id IN (
  SELECT id FROM chat_sessions WHERE user_id = [USER_ID]
);

-- Delete user's sessions
DELETE FROM chat_sessions WHERE user_id = [USER_ID];

-- Delete user
DELETE FROM users WHERE id = [USER_ID];
```

**Option 3: Via API** (Programmatic)
```python
# Add endpoint to delete user data
@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    # Delete messages
    sessions = db.query(models.ChatSession).filter(models.ChatSession.user_id == user_id).all()
    for session in sessions:
        db.query(models.Message).filter(models.Message.session_id == session.id).delete()
    
    # Delete sessions
    db.query(models.ChatSession).filter(models.ChatSession.user_id == user_id).delete()
    
    # Delete user
    db.query(models.User).filter(models.User.id == user_id).delete()
    db.commit()
```

---

#### **Delete Knowledge Base Data**

**Pinecone:**
```python
# Delete by source
from app.vectorstore.pinecone_store import delete_by_path

delete_by_path("document.pdf")

# Delete all (careful!)
from app.vectorstore.pinecone_store import delete_all
delete_all()
```

**File System:**
```bash
# Delete PDF files
rm knowledge_base/path/to/file.pdf

# Delete all knowledge base files
rm -rf knowledge_base/*
```

---

#### **Clear Browser Data**

**User Action:**
- Clear browser localStorage
- Clear browser cache
- Or use incognito/private mode

**Programmatic (Frontend):**
```javascript
// Clear all chatbot data
localStorage.removeItem('askcache_messages');
localStorage.removeItem('askcache_session_id');
localStorage.removeItem('askcache_info_submitted');
localStorage.removeItem('askcache_ui_settings');
```

---

## Compliance Considerations

### **GDPR (General Data Protection Regulation)**

**What Applies:**
- ✅ User conversations (messages table)
- ✅ User personal data (users table)
- ✅ Session data (chat_sessions table)
- ⚠️ Knowledge base content (if contains personal data)

**Requirements:**
1. **Right to Access** - Users can request their data
2. **Right to Rectification** - Users can correct their data
3. **Right to Erasure** - Users can request deletion
4. **Right to Portability** - Users can export their data
5. **Data Minimization** - Only collect necessary data
6. **Purpose Limitation** - Use data only for stated purpose
7. **Storage Limitation** - Don't keep data longer than needed

**Current Status:**
- ⚠️ No automatic data deletion
- ⚠️ No data export functionality
- ⚠️ No user access to their data
- ✅ Data stored in your control (PostgreSQL)
- ⚠️ Data sent to third parties (Google, Pinecone)

**Recommendations:**
- Add data export endpoint
- Add data deletion endpoint
- Add data retention policy
- Add user consent mechanism
- Add privacy policy

---

### **CCPA (California Consumer Privacy Act)**

**What Applies:**
- ✅ Personal information (name, email, phone)
- ✅ Conversation history
- ✅ Session data

**Requirements:**
- Right to know what data is collected
- Right to delete personal information
- Right to opt-out of sale (not applicable here)
- Right to non-discrimination

**Current Status:**
- ⚠️ No user-facing data access
- ⚠️ No deletion mechanism for users
- ✅ Data stored in your control

---

### **HIPAA (If Applicable)**

**If handling health information:**
- ⚠️ Requires encryption at rest
- ⚠️ Requires encryption in transit (HTTPS)
- ⚠️ Requires access controls
- ⚠️ Requires audit logs
- ⚠️ Requires BAA (Business Associate Agreement) with third parties

**Current Status:**
- ✅ HTTPS supported (if configured)
- ⚠️ No encryption at rest (database)
- ⚠️ No audit logs
- ⚠️ No BAA with Google/Pinecone

---

## Data Security

### **Data in Transit**
- ✅ HTTPS/SSL (if configured)
- ✅ API calls encrypted
- ✅ Database connections encrypted (if configured)

### **Data at Rest**
- ⚠️ PostgreSQL: No encryption by default (can be added)
- ⚠️ File system: No encryption by default
- ✅ Pinecone: Encrypted (managed service)
- ✅ Google: Encrypted (managed service)

### **Access Control**
- ✅ Admin panel: Session-based authentication
- ✅ Database: Credential-protected
- ⚠️ No user-level access controls
- ⚠️ No role-based access control (RBAC)

---

## Recommendations for Compliance

### **Immediate Actions**

1. **Add Data Export Endpoint**
   ```python
   @app.get("/admin/users/{user_id}/export")
   async def export_user_data(user_id: int, db: Session = Depends(get_db)):
       # Export all user data as JSON
   ```

2. **Add Data Deletion Endpoint**
   ```python
   @app.delete("/admin/users/{user_id}")
   async def delete_user_data(user_id: int, db: Session = Depends(get_db)):
       # Delete all user data
   ```

3. **Add Privacy Policy**
   - Explain what data is collected
   - Explain where data is stored
   - Explain how data is used
   - Explain user rights

4. **Add Data Retention Policy**
   - Define retention periods
   - Implement automatic deletion
   - Document retention periods

5. **Add User Consent**
   - Consent checkbox for form
   - Link to privacy policy
   - Clear explanation of data use

### **Long-Term Actions**

1. **Database Encryption**
   - Enable PostgreSQL encryption
   - Encrypt sensitive columns
   - Use encryption keys

2. **Audit Logging**
   - Log all data access
   - Log all deletions
   - Log all exports

3. **Access Controls**
   - Role-based access control
   - User-level permissions
   - Audit trail

4. **Data Minimization**
   - Only collect necessary data
   - Anonymize where possible
   - Delete old data automatically

---

## Data Storage Summary

| Data Type | Location | Contains PII? | Retention | Compliance Risk |
|-----------|----------|---------------|-----------|-----------------|
| **User Messages** | PostgreSQL | ✅ Yes | Indefinite | ⚠️ High |
| **Assistant Responses** | PostgreSQL | ⚠️ Potentially | Indefinite | ⚠️ Medium |
| **User Info (Form)** | PostgreSQL | ✅ Yes | Indefinite | ⚠️ High |
| **Session Data** | PostgreSQL | ⚠️ Indirect | Indefinite | ⚠️ Medium |
| **Knowledge Base** | Pinecone | ⚠️ Potentially | Indefinite | ⚠️ Medium |
| **Chat History** | Browser localStorage | ✅ Yes | Until cleared | ⚠️ Medium |
| **PDF Files** | File System | ⚠️ Potentially | Indefinite | ⚠️ Medium |
| **UI Settings** | PostgreSQL + localStorage | ❌ No | Indefinite | ✅ Low |

---

## Third-Party Data Processing

### **Google Gemini API**
- **Data Sent:** User queries, context, prompts
- **Data Stored:** According to Google's policy
- **Location:** Google's infrastructure
- **Compliance:** Check Google's DPA
- **Risk:** ⚠️ High (user conversations)

### **Pinecone**
- **Data Sent:** Vector embeddings, metadata
- **Data Stored:** Pinecone's infrastructure
- **Location:** Pinecone's cloud
- **Compliance:** Check Pinecone's certifications
- **Risk:** ⚠️ Medium (knowledge base content)

---

## Compliance Checklist

- [ ] Privacy policy created
- [ ] Data retention policy defined
- [ ] User consent mechanism added
- [ ] Data export functionality implemented
- [ ] Data deletion functionality implemented
- [ ] Database encryption enabled
- [ ] HTTPS/SSL configured
- [ ] Access controls implemented
- [ ] Audit logging enabled
- [ ] DPA signed with Google (if required)
- [ ] DPA signed with Pinecone (if required)
- [ ] Data minimization practices implemented
- [ ] User rights documented
- [ ] Data breach notification process defined

---

## Summary

**Your Data Storage:**
- ✅ **PostgreSQL** (Your server) - You control it
- ✅ **File System** (Your server) - You control it
- ⚠️ **Browser localStorage** (User's device) - User controls it

**Third-Party Storage:**
- ⚠️ **Google Gemini API** - Third party (check DPA)
- ⚠️ **Pinecone** - Third party (check compliance)

**Compliance Priority:**
1. **High Priority:** User messages, user personal data
2. **Medium Priority:** Knowledge base content, session data
3. **Low Priority:** UI settings, configuration

**Key Actions Needed:**
- Add data export functionality
- Add data deletion functionality
- Implement data retention policy
- Add privacy policy
- Enable database encryption
- Sign DPAs with third parties (if required)

