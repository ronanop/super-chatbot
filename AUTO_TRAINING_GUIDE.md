# Auto-Training Guide

## Overview

The chatbot now includes **automatic learning capabilities** that allow it to continuously improve by learning from conversations and adding new information to the knowledge base.

## Features

### 1. Knowledge Base Only Responses

The chatbot is now configured to **ONLY respond using information from the knowledge base**:

- ✅ **Strict Knowledge Base Mode**: Chatbot only uses information from the provided context
- ✅ **No Hallucinations**: Prevents the chatbot from making up information
- ✅ **Clear Feedback**: If information isn't available, users are informed and directed to contact support

**How it works:**
- When a user asks a question, the system searches the knowledge base
- If relevant context is found, the chatbot responds using ONLY that context
- If no context is found, the chatbot politely informs the user that the information isn't available

### 2. Auto-Training System

The chatbot automatically learns from successful conversations:

- ✅ **Real-time Learning**: After each successful conversation, the chatbot analyzes the Q&A
- ✅ **Knowledge Extraction**: Uses AI to extract factual information from conversations
- ✅ **Automatic Addition**: Adds extracted knowledge to the knowledge base
- ✅ **Background Processing**: Runs asynchronously - doesn't slow down responses
- ✅ **Smart Filtering**: Only adds useful, factual information (skips "I don't know" responses)

**How it works:**
1. User asks a question → Bot responds using knowledge base
2. If response contains useful information, the conversation is analyzed
3. AI extracts structured knowledge from the Q&A
4. Extracted knowledge is added to the knowledge base
5. Future users asking similar questions benefit from this learned information

## Configuration

### Environment Variable

Control auto-training via the `ENABLE_AUTO_TRAINING` environment variable:

```bash
# Enable auto-training (default)
ENABLE_AUTO_TRAINING=true

# Disable auto-training
ENABLE_AUTO_TRAINING=false
```

Add this to your `.env` file.

### Admin Panel

Access auto-training controls in the admin panel:

1. Go to **Admin Panel** → **App Settings**
2. Scroll to **Auto-Training** section
3. Click **"Trigger Batch Auto-Training"** to manually process recent conversations

## Manual Batch Training

You can manually trigger batch training to process recent conversations:

### Via Admin Panel

1. Navigate to `/admin/settings`
2. Scroll to **Auto-Training** section
3. Click **"🚀 Trigger Batch Auto-Training (Last 7 Days)"**

### Via API

```bash
POST /admin/settings/auto-train
```

Requires admin authentication.

### What Gets Processed

- Conversations from the last 7 days (configurable)
- Bot responses with substantial content (>100 characters)
- Responses that contain factual information
- Skips "I don't know" type responses

## How Knowledge is Extracted

The auto-training system uses Gemini AI to extract knowledge:

1. **Input**: User question + Bot response
2. **Processing**: AI analyzes and extracts factual information
3. **Output**: Structured knowledge text
4. **Storage**: Knowledge is chunked and added to Pinecone vector database

**Example:**
```
User: "What are your business hours?"
Bot: "We're open Monday-Friday 9 AM to 6 PM EST."

Extracted Knowledge:
"Cache Digitech business hours: Monday-Friday, 9 AM to 6 PM EST."
```

## Monitoring

### Check Logs

Auto-training activities are logged:

```bash
# View logs
docker-compose logs -f backend

# Or if running manually
# Check console output for auto-training messages
```

### Log Messages

- `"Added X chunks to knowledge base from conversation"` - Success
- `"Auto-training failed: ..."` - Error occurred
- `"Batch training: Processed X conversations"` - Batch training complete

## Best Practices

### 1. Quality Control

- Review learned knowledge periodically
- Remove incorrect information if needed (via admin panel → Ingestion)
- Monitor for duplicate or low-quality entries

### 2. Initial Knowledge Base

- Start with a comprehensive knowledge base
- Auto-training supplements, not replaces, manual knowledge base
- Upload important documents and crawl key pages first

### 3. Monitoring

- Check logs regularly for auto-training activity
- Monitor knowledge base size
- Review learned content quality

### 4. Disabling When Needed

Disable auto-training if:
- You want strict control over knowledge base content
- You're experiencing quality issues
- You want to review before adding

## Troubleshooting

### Auto-Training Not Working

1. **Check Environment Variable**:
   ```bash
   echo $ENABLE_AUTO_TRAINING
   # Should be "true" (or not set, defaults to true)
   ```

2. **Check Logs**:
   ```bash
   docker-compose logs backend | grep -i "auto-training"
   ```

3. **Verify Knowledge Base Responses**:
   - Auto-training only works when knowledge base context is found
   - If chatbot says "I don't have information", auto-training won't trigger

### Knowledge Not Being Added

- Check if responses contain factual information
- Verify responses aren't too short (<50 characters)
- Ensure responses don't match "I don't know" patterns
- Check Pinecone connection and API keys

### Too Much Knowledge Being Added

- Review extraction quality
- Consider adjusting extraction prompt in `app/services/auto_training.py`
- Disable auto-training temporarily
- Manually review and clean knowledge base

## Technical Details

### Files Modified

- `app/main.py` - Updated prompt to enforce knowledge base only, added auto-training trigger
- `app/services/auto_training.py` - New auto-training service
- `app/admin/routes.py` - Added batch training endpoint
- `app/admin/templates/app_settings.html` - Added auto-training UI

### Architecture

```
User Question
    ↓
Knowledge Base Search
    ↓
Context Found? → Yes → Generate Response → Auto-Train
    ↓ No
Return "No Information" Message
```

### Background Processing

- Uses FastAPI `BackgroundTasks` for async processing
- Creates separate database sessions for thread safety
- Non-blocking - doesn't affect response time

## Future Enhancements

Potential improvements:
- User feedback mechanism (thumbs up/down)
- Quality scoring for learned knowledge
- Automatic deduplication
- Scheduled batch training
- Knowledge base analytics

---

**Status**: ✅ Active and Ready
**Version**: 1.0.0

