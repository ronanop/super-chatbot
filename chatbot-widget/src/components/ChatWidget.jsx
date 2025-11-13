import { useEffect, useMemo, useRef, useState } from "react";

import { API_BASE_URL as DEFAULT_API_BASE_URL, fetchApiConfig } from "../config";

const BOT_AVATAR = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f916.svg";
const USER_AVATAR = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f464.svg";

// Default settings
const defaultSettings = {
  bot_name: "Cache Digitech Virtual Assistant",
  bot_icon_url: null,
  header_image_url: null,
  welcome_message: "Hi! I'm the Cache Digitech assistant. Ask me anything about our services, projects, or how we can help your business.",
  primary_color: "#4338ca",
  secondary_color: "#6366f1",
  background_color: "#ffffff",
  text_color: "#1e293b",
  user_message_bg: "#4338ca",
  user_message_text: "#ffffff",
  bot_message_bg: "#ffffff",
  bot_message_text: "#1e293b",
  link_color: "#4338ca",
  widget_position: "bottom-right",
  widget_size: "medium",
  show_branding: true,
  custom_css: null,
};

const initialMessages = [
  {
    id: "welcome",
    role: "assistant",
    content: defaultSettings.welcome_message,
  },
];

const storageKeys = {
  session: "cachedigitech_session_id",
  info: "cachedigitech_info_submitted",
};

function classNames(...classes) {
  return classes.filter(Boolean).join(" ");
}

// Typing Indicator Component
function TypingIndicator({ settings = defaultSettings }) {
  return (
    <div className="flex gap-3 justify-start animate-fade-in">
      <div className="flex items-start gap-3 max-w-[80%]">
        <div className="h-8 w-8 rounded-full bg-white/60 p-1 shadow flex items-center justify-center">
          {settings.bot_icon_url ? (
            <img src={settings.bot_icon_url} alt="Bot" className="h-full w-full rounded-full object-cover" />
          ) : (
            <span className="text-lg">🤖</span>
          )}
        </div>
        <div 
          className="rounded-2xl px-4 py-3 border"
          style={{
            backgroundColor: settings.bot_message_bg,
            borderColor: settings.bot_message_bg === '#ffffff' ? '#e2e8f0' : 'transparent',
          }}
        >
          <div className="flex gap-1.5 items-center">
            <div 
              className="w-2 h-2 rounded-full animate-bounce" 
              style={{ 
                animationDelay: '0ms',
                backgroundColor: settings.bot_message_text,
                opacity: 0.6,
              }}
            ></div>
            <div 
              className="w-2 h-2 rounded-full animate-bounce" 
              style={{ 
                animationDelay: '150ms',
                backgroundColor: settings.bot_message_text,
                opacity: 0.6,
              }}
            ></div>
            <div 
              className="w-2 h-2 rounded-full animate-bounce" 
              style={{ 
                animationDelay: '300ms',
                backgroundColor: settings.bot_message_text,
                opacity: 0.6,
              }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatMessage(content) {
  // Enhanced URL regex pattern - matches http/https URLs, including those with parentheses
  const urlRegex = /(https?:\/\/[^\s\)]+)/g;
  
  // Split by URLs first
  const parts = [];
  let lastIndex = 0;
  let match;
  
  while ((match = urlRegex.exec(content)) !== null) {
    // Add text before URL
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: content.substring(lastIndex, match.index) });
    }
    // Add URL (clean trailing punctuation)
    let url = match[0];
    // Remove trailing punctuation that's not part of URL
    url = url.replace(/[.,;:!?]+$/, '');
    parts.push({ type: 'url', content: url });
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining text
  if (lastIndex < content.length) {
    parts.push({ type: 'text', content: content.substring(lastIndex) });
  }
  
  // If no URLs found, just return the text
  if (parts.length === 0) {
    parts.push({ type: 'text', content });
  }
  
  return parts;
}

function formatTextWithBold(text) {
  // Patterns for important words/phrases:
  // 1. Text wrapped in ** (markdown bold)
  // 2. Text wrapped in * (markdown italic/emphasis)
  // 3. Text in ALL CAPS (if 3+ chars)
  // 4. Text after colons (often important labels)
  // 5. Common important terms
  
  const parts = [];
  let lastIndex = 0;
  
  // Pattern 1: **bold** or *italic*
  const markdownRegex = /(\*\*([^*]+)\*\*|\*([^*]+)\*)/g;
  let markdownMatch;
  const markdownMatches = [];
  
  while ((markdownMatch = markdownRegex.exec(text)) !== null) {
    markdownMatches.push({
      start: markdownMatch.index,
      end: markdownMatch.index + markdownMatch[0].length,
      content: markdownMatch[2] || markdownMatch[3],
      isBold: markdownMatch[0].startsWith('**')
    });
  }
  
  // Pattern 2: Words after colons (e.g., "Service:", "Price:")
  const colonRegex = /([A-Za-z][A-Za-z\s]{2,20}):\s*([A-Za-z0-9])/g;
  const colonMatches = [];
  let colonMatch;
  while ((colonMatch = colonRegex.exec(text)) !== null) {
    colonMatches.push({
      start: colonMatch.index,
      end: colonMatch.index + colonMatch[1].length + 1,
      content: colonMatch[1] + ':'
    });
  }
  
  // Combine and sort all matches
  const allMatches = [
    ...markdownMatches.map(m => ({ ...m, type: 'markdown' })),
    ...colonMatches.map(m => ({ ...m, type: 'colon' }))
  ].sort((a, b) => a.start - b.start);
  
  // Remove overlapping matches (prefer markdown over colon)
  const filteredMatches = [];
  for (const match of allMatches) {
    const overlaps = filteredMatches.some(m => 
      (match.start >= m.start && match.start < m.end) ||
      (match.end > m.start && match.end <= m.end)
    );
    if (!overlaps) {
      filteredMatches.push(match);
    }
  }
  
  // Build formatted parts
  for (const match of filteredMatches) {
    // Add text before match
    if (match.start > lastIndex) {
      const beforeText = text.substring(lastIndex, match.start);
      if (beforeText) {
        parts.push({ type: 'text', content: beforeText });
      }
    }
    
    // Add formatted match
    if (match.type === 'markdown') {
      parts.push({ 
        type: match.isBold ? 'bold' : 'italic', 
        content: match.content 
      });
    } else if (match.type === 'colon') {
      parts.push({ 
        type: 'bold', 
        content: match.content 
      });
    }
    
    lastIndex = match.end;
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    const remainingText = text.substring(lastIndex);
    if (remainingText) {
      parts.push({ type: 'text', content: remainingText });
    }
  }
  
  // If no matches, return original text
  if (parts.length === 0) {
    parts.push({ type: 'text', content: text });
  }
  
  return parts;
}

function MessageBubble({ role, content, settings = defaultSettings, isTyping = false }) {
  const isUser = role === "user";
  
  // Format content: split by lines, then format each line
  // Wrap in try-catch to prevent crashes
  let formattedLines;
  try {
    formattedLines = content.split("\n").map((line, lineIdx) => {
      if (!line.trim()) {
        return { lineIdx, parts: [{ type: 'text', content: '\n' }] };
      }
      
      try {
        // First, extract URLs
        const urlParts = formatMessage(line);
        
        // Then format each text part for bold/emphasis
        const formattedParts = [];
        urlParts.forEach(part => {
          if (part.type === 'url') {
            formattedParts.push(part);
          } else {
            try {
              // Format text for bold/emphasis
              const textParts = formatTextWithBold(part.content);
              formattedParts.push(...textParts);
            } catch (err) {
              // Fallback to plain text if formatting fails
              console.error('Error formatting text:', err);
              formattedParts.push({ type: 'text', content: part.content });
            }
          }
        });
        
        return { lineIdx, parts: formattedParts };
      } catch (err) {
        // Fallback to plain text if URL extraction fails
        console.error('Error formatting line:', err);
        return { lineIdx, parts: [{ type: 'text', content: line }] };
      }
    });
  } catch (err) {
    // Complete fallback - just show plain text
    console.error('Error formatting message:', err);
    formattedLines = content.split("\n").map((line, lineIdx) => ({
      lineIdx,
      parts: [{ type: 'text', content: line }]
    }));
  }
  
  return (
    <div 
      className={classNames("flex gap-3 animate-fade-in-up", isUser ? "justify-end" : "justify-start")}
    >
      <div className={classNames("flex items-start gap-3 max-w-[80%]", isUser && "flex-row-reverse")}> 
        <img
          src={isUser ? USER_AVATAR : (settings.bot_icon_url || BOT_AVATAR)}
          alt={isUser ? "User" : "Assistant"}
          className="h-8 w-8 rounded-full bg-white/60 p-1 shadow flex-shrink-0"
        />
        <div
          className="rounded-2xl px-4 py-2 text-sm leading-relaxed break-words"
          style={{
            backgroundColor: isUser ? settings.user_message_bg : settings.bot_message_bg,
            color: isUser ? settings.user_message_text : settings.bot_message_text,
            border: isUser ? 'none' : (settings.bot_message_bg === '#ffffff' ? '1px solid #e2e8f0' : 'none'),
            wordWrap: 'break-word',
            overflowWrap: 'break-word',
          }}
        >
          {formattedLines.map(({ lineIdx, parts }) => (
            <p key={lineIdx} className="whitespace-pre-wrap">
              {parts.map((part, partIdx) => {
                if (part.type === 'url') {
                  return (
                    <a
                      key={partIdx}
                      href={part.content}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline decoration-2 underline-offset-2"
                      style={{
                        color: isUser ? settings.user_message_text : settings.link_color,
                        opacity: isUser ? 0.9 : 1,
                      }}
                    >
                      {part.content}
                    </a>
                  );
                } else if (part.type === 'bold') {
                  return (
                    <strong key={partIdx} className="font-semibold">
                      {part.content}
                    </strong>
                  );
                } else if (part.type === 'italic') {
                  return (
                    <em key={partIdx} className="italic">
                      {part.content}
                    </em>
                  );
                } else {
                  return <span key={partIdx}>{part.content}</span>;
                }
              })}
            </p>
          ))}
          {isTyping && !isUser && (
            <span className="inline-flex items-center gap-1 ml-2" style={{ color: settings.bot_message_text }}>
              <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-1 h-1 rounded-full bg-current animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showInfoForm, setShowInfoForm] = useState(false);
  const [infoSubmitted, setInfoSubmitted] = useState(false);
  const [formData, setFormData] = useState({ name: "", email: "", phone: "" });
  const [uiSettings, setUiSettings] = useState(defaultSettings);
  // Use embed-provided URL if available, otherwise use default
  const [apiBaseUrl, setApiBaseUrl] = useState(
    typeof window !== 'undefined' && window.WIDGET_API_BASE_URL 
      ? window.WIDGET_API_BASE_URL 
      : DEFAULT_API_BASE_URL
  );
  const [isRecording, setIsRecording] = useState(false);
  const [isVoiceSupported, setIsVoiceSupported] = useState(false);
  const [shouldAutoSubmit, setShouldAutoSubmit] = useState(false);
  const [settingsLoaded, setSettingsLoaded] = useState(true); // Start as true to show widget immediately with defaults
  const lastSettingsTimestampRef = useRef(null); // Track last settings update timestamp

  const chatBodyRef = useRef(null);
  const typewriterIntervalRef = useRef(null);
  const recognitionRef = useRef(null);
  const initializationRef = useRef(false); // Prevent multiple initializations

  // Initialize Speech Recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const recognition = new SpeechRecognition();
          recognition.continuous = false;
          recognition.interimResults = false;
          // Default to English, will be updated dynamically based on user's language
          recognition.lang = 'en-US';

          recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.trim();
            if (transcript) {
              setInput(transcript);
              setIsRecording(false);
              // Trigger auto-submit after state updates
              setTimeout(() => {
                setShouldAutoSubmit(true);
              }, 300);
            } else {
              setIsRecording(false);
            }
          };

          recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            setIsRecording(false);
            setShouldAutoSubmit(false);
            if (event.error === 'no-speech') {
              setError('No speech detected. Please try again.');
            } else if (event.error === 'not-allowed') {
              setError('Microphone permission denied. Please enable microphone access.');
            }
          };

          recognition.onend = () => {
            setIsRecording(false);
            // Don't reset shouldAutoSubmit here as it might be set by onresult
          };

          recognitionRef.current = recognition;
          setIsVoiceSupported(true);
        } catch (err) {
          console.error('Failed to initialize speech recognition:', err);
          setIsVoiceSupported(false);
        }
      } else {
        setIsVoiceSupported(false);
      }
    }

    // Cleanup: stop recording if component unmounts
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore errors when stopping
        }
      }
    };
  }, []);

  // Check widget version and force reload if needed
  useEffect(() => {
    const storedVersion = sessionStorage.getItem('widget_version');
    const currentVersion = window.WIDGET_VERSION;
    
    if (currentVersion && storedVersion && storedVersion !== currentVersion) {
      console.log('Widget version changed, clearing cache...', { storedVersion, currentVersion });
      sessionStorage.clear();
      // Force reload after a short delay to ensure cleanup
      setTimeout(() => {
        window.location.reload();
      }, 100);
      return;
    }
    
    if (currentVersion) {
      sessionStorage.setItem('widget_version', currentVersion);
    }
  }, []);

  // Fetch API URL and UI settings together on mount
  useEffect(() => {
    // Prevent multiple initializations (React StrictMode in dev causes double renders)
    if (initializationRef.current) {
      return;
    }
    initializationRef.current = true;
    
    const initializeWidget = async () => {
      // First, fetch the correct API URL
      const resolvedApiUrl = await fetchApiConfig();
      setApiBaseUrl(resolvedApiUrl);
      console.log("ChatWidget API Base URL:", resolvedApiUrl);
      
      // Then fetch UI settings using the resolved URL
      const fetchSettings = async (apiUrl, retryCount = 0) => {
        try {
          // Always use cache-busting to ensure fresh settings
          const cacheBuster = `?v=${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const forceReload = window.WIDGET_FORCE_RELOAD || false;
          
          console.log('Fetching UI settings...', { apiUrl, cacheBuster, forceReload, retryCount });
          
          // Create abort controller for timeout
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
          
          const response = await fetch(`${apiUrl}/admin/bot-ui/api/settings${cacheBuster}`, {
            cache: forceReload ? 'reload' : 'no-store',
            headers: {
              'Cache-Control': 'no-cache, no-store, must-revalidate',
              'Pragma': 'no-cache',
              'Expires': '0',
              'X-Requested-With': 'XMLHttpRequest'
            },
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const settings = await response.json();
            const currentTimestamp = settings.settings_updated_at || null;
            
            // Check if settings have changed
            const settingsChanged = lastSettingsTimestampRef.current !== null && 
                                   lastSettingsTimestampRef.current !== currentTimestamp;
            
            if (settingsChanged) {
              console.log('🔄 UI Settings updated detected:', { 
                bot_name: settings.bot_name, 
                primary_color: settings.primary_color,
                old_timestamp: lastSettingsTimestampRef.current,
                new_timestamp: currentTimestamp
              });
            } else {
              console.log('✅ UI Settings fetched:', { 
                bot_name: settings.bot_name, 
                primary_color: settings.primary_color,
                timestamp: currentTimestamp || new Date().toISOString()
              });
            }
            
            // Update timestamp reference
            lastSettingsTimestampRef.current = currentTimestamp;
            
            setUiSettings({ ...defaultSettings, ...settings });
            // Update welcome message if custom
            if (settings.welcome_message) {
              setMessages((prev) => {
                // Only update welcome message if it's the first message or if it changed
                const firstMsg = prev[0];
                if (!firstMsg || firstMsg.id === "welcome") {
                  return [{
                    id: "welcome",
                    role: "assistant",
                    content: settings.welcome_message,
                  }, ...prev.slice(1)];
                }
                return prev;
              });
            }
            setSettingsLoaded(true);
          } else {
            console.warn('Failed to fetch UI settings:', response.status, response.statusText);
            // If fetch fails, still mark as loaded to show widget with defaults
            setSettingsLoaded(true);
          }
        } catch (err) {
          console.error("Failed to fetch UI settings:", err);
          
          // Retry once if it's a network error/timeout and we haven't retried yet
          if (retryCount === 0 && (err.name === 'TypeError' || err.name === 'TimeoutError' || err.name === 'AbortError')) {
            console.log('Retrying settings fetch after error...');
            setTimeout(() => fetchSettings(apiUrl, 1), 1000);
          } else {
            // Use defaults on error, but still mark as loaded
            console.warn('Using default UI settings due to fetch failure');
            setSettingsLoaded(true);
          }
        }
      };
      
      // Fetch settings with the resolved API URL
      fetchSettings(resolvedApiUrl);
    };
    
    initializeWidget();
  }, []);

  // Periodically check for settings updates (every 5 seconds)
  useEffect(() => {
    if (!apiBaseUrl || !settingsLoaded) return;
    
    const pollInterval = setInterval(() => {
      // Only poll if we have a timestamp to compare
      if (lastSettingsTimestampRef.current === null) return;
      
      const checkForUpdates = async () => {
        try {
          const cacheBuster = `?v=${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout for polling
          
          const response = await fetch(`${apiBaseUrl}/admin/bot-ui/api/settings${cacheBuster}`, {
            cache: 'no-store',
            headers: {
              'Cache-Control': 'no-cache, no-store, must-revalidate',
              'Pragma': 'no-cache',
              'Expires': '0',
              'X-Requested-With': 'XMLHttpRequest'
            },
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const settings = await response.json();
            const currentTimestamp = settings.settings_updated_at || null;
            
            // Check if settings have changed
            if (lastSettingsTimestampRef.current !== null && 
                lastSettingsTimestampRef.current !== currentTimestamp) {
              console.log('🔄 Settings updated detected via polling, refreshing...');
              
              // Update settings
              lastSettingsTimestampRef.current = currentTimestamp;
              setUiSettings({ ...defaultSettings, ...settings });
              
              // Update welcome message if it changed
              if (settings.welcome_message) {
                setMessages((prev) => {
                  const firstMsg = prev[0];
                  if (!firstMsg || firstMsg.id === "welcome") {
                    return [{
                      id: "welcome",
                      role: "assistant",
                      content: settings.welcome_message,
                    }, ...prev.slice(1)];
                  }
                  return prev;
                });
              }
            }
          }
        } catch (err) {
          // Silently fail during polling - don't spam console
          if (err.name !== 'AbortError') {
            console.debug('Settings poll check failed:', err.message);
          }
        }
      };
      
      checkForUpdates();
    }, 5000); // Poll every 5 seconds
    
    return () => clearInterval(pollInterval);
  }, [apiBaseUrl, settingsLoaded]);

  // Apply custom CSS if provided
  useEffect(() => {
    if (uiSettings.custom_css) {
      const styleId = 'chatbot-custom-css';
      let styleEl = document.getElementById(styleId);
      if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = styleId;
        document.head.appendChild(styleEl);
      }
      styleEl.textContent = uiSettings.custom_css;
    }
  }, [uiSettings.custom_css]);

  // Smooth scroll to bottom when new messages arrive or typing indicator appears
  useEffect(() => {
    if (chatBodyRef.current) {
      const scrollToBottom = () => {
        chatBodyRef.current?.scrollTo({
          top: chatBodyRef.current.scrollHeight,
          behavior: 'smooth',
        });
      };
      
      // Small delay to ensure DOM is updated
      const timeoutId = setTimeout(scrollToBottom, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [messages, isLoading]);

  // Auto-scroll during typewriter effect
  useEffect(() => {
    const hasTypingMessage = messages.some(msg => msg.isTyping);
    if (hasTypingMessage && chatBodyRef.current) {
      const intervalId = setInterval(() => {
        if (chatBodyRef.current) {
          chatBodyRef.current.scrollTo({
            top: chatBodyRef.current.scrollHeight,
            behavior: 'smooth',
          });
        }
      }, 100); // Scroll every 100ms during typing
      
      return () => clearInterval(intervalId);
    }
  }, [messages]);

  useEffect(() => {
    // Debug: Log API URL being used
    console.log("ChatWidget API Base URL:", apiBaseUrl);
    
    const storedSession = sessionStorage.getItem(storageKeys.session);
    if (storedSession) {
      setSessionId(Number(storedSession));
    }
    const storedInfo = sessionStorage.getItem(storageKeys.info);
    if (storedInfo === "1") {
      setInfoSubmitted(true);
      setShowInfoForm(false);
    }
  }, []);

  useEffect(() => {
    if (sessionId) {
      sessionStorage.setItem(storageKeys.session, String(sessionId));
    }
  }, [sessionId]);

  useEffect(() => {
    if (infoSubmitted) {
      sessionStorage.setItem(storageKeys.info, "1");
    }
  }, [infoSubmitted]);

  useEffect(() => {
    const body = chatBodyRef.current;
    if (body) {
      body.scrollTo({ top: body.scrollHeight, behavior: "smooth" });
    }
  }, [messages, showInfoForm]);

  // Auto-submit when voice transcript is ready
  useEffect(() => {
    if (shouldAutoSubmit && input.trim() && !isLoading && !isRecording) {
      setShouldAutoSubmit(false);
      
      // Auto-submit the message
      setTimeout(() => {
        if (input.trim() && !isLoading) {
          // Create a synthetic submit event
          const syntheticEvent = {
            preventDefault: () => {},
          };
          handleSendMessage(syntheticEvent);
        }
      }, 100);
    }
  }, [shouldAutoSubmit, input, isLoading, isRecording]);

  const createMessageId = () =>
    typeof crypto?.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.floor(Math.random() * 1_000_000)}`;

  const handleSendMessage = async (event) => {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading || (showInfoForm && !infoSubmitted)) return; // Block sending if form is shown

    const pendingId = createMessageId();
    const assistantMessageId = createMessageId();
    const userMessage = { id: pendingId, role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setError(null);

    // Create empty assistant message that will be filled with typewriter effect
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        isTyping: true,
      },
    ]);

    try {
      const response = await fetch(`${apiBaseUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, session_id: sessionId }),
      }).catch((err) => {
        // Network error - backend not reachable
        console.error("Network error:", err);
        console.error("API URL:", `${apiBaseUrl}/chat`);
        throw new Error(`Cannot connect to backend at ${apiBaseUrl}. Make sure the server is running.`);
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || `Server error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      setSessionId(data.session_id);

      // Typewriter effect: display words one by one
      const fullText = data.reply;
      const words = fullText.split(/(\s+)/); // Split by spaces but keep the spaces
      let displayedText = "";
      let wordIndex = 0;

      // Clear any existing interval
      if (typewriterIntervalRef.current) {
        clearInterval(typewriterIntervalRef.current);
      }

      typewriterIntervalRef.current = setInterval(() => {
        if (wordIndex < words.length) {
          displayedText += words[wordIndex];
          wordIndex++;
          
          // Update the message with current displayed text
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: displayedText }
                : msg
            )
          );
        } else {
          // Typing complete
          if (typewriterIntervalRef.current) {
            clearInterval(typewriterIntervalRef.current);
            typewriterIntervalRef.current = null;
          }
          
          // Update messages and check for form trigger
          setMessages((prev) => {
            const updatedMessages = prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, isTyping: false }
                : msg
            );
            
            // Check user message count after updating
            const userMessageCount = updatedMessages.filter(msg => msg.role === 'user').length;
            if (userMessageCount >= 2 && !infoSubmitted && !showInfoForm) {
              // Show form after 2nd message response completes
              setTimeout(() => {
                setShowInfoForm(true);
              }, 100);
            } else if (data.prompt_for_info && !infoSubmitted) {
              // Fallback to backend prompt if configured
              setTimeout(() => {
                setShowInfoForm(true);
              }, 100);
            }
            
            return updatedMessages;
          });
          setIsLoading(false);
        }
      }, 30); // 30ms per word (adjustable for speed - lower = faster)

    } catch (err) {
      // Clean up interval if it exists
      if (typewriterIntervalRef.current) {
        clearInterval(typewriterIntervalRef.current);
        typewriterIntervalRef.current = null;
      }
      
      setError(err instanceof Error ? err.message : "Unknown error. Please try again.");
      setMessages((prev) => prev.filter((message) => message.id !== pendingId && message.id !== assistantMessageId));
      setIsLoading(false);
    }
  };

  const handleFormChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };


  const handleVoiceInput = () => {
    if (!isVoiceSupported || !recognitionRef.current) {
      setError('Voice input is not supported in your browser. Please use Chrome or Edge.');
      return;
    }

    if (isRecording) {
      // Stop recording manually - don't auto-submit
      try {
        recognitionRef.current.stop();
        setIsRecording(false);
        setShouldAutoSubmit(false);
      } catch (err) {
        console.error('Error stopping voice recognition:', err);
        setIsRecording(false);
        setShouldAutoSubmit(false);
      }
    } else {
      // Start recording
      try {
        setError(null);
        setShouldAutoSubmit(false);
        // Always use English for voice recognition
        recognitionRef.current.lang = 'en-US';
        setIsRecording(true);
        recognitionRef.current.start();
      } catch (err) {
        console.error('Error starting voice recognition:', err);
        setIsRecording(false);
        setShouldAutoSubmit(false);
        if (err.message && err.message.includes('already started')) {
          // Recognition already running, just update state
          setIsRecording(true);
        } else {
          setError('Failed to start voice recording. Please try again.');
        }
      }
    }
  };

  const handleInfoSubmit = async (event) => {
    event.preventDefault();
    if (!sessionId) {
      setError("Please send a message first so we can link your details to a chat session.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/user-info`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, ...formData }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "Couldn't save your details. Please try again.");
      }

      setInfoSubmitted(true);
      setShowInfoForm(false);
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: "assistant",
          content: "Thanks! I've saved your contact details. A team member can follow up if needed.",
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWidget = () => {
    setIsOpen((prev) => !prev);
    if (!isOpen) {
      setError(null);
    }
  };

  const buttonLabel = useMemo(() => (isOpen ? "Close chat" : "Chat with us"), [isOpen]);

  // Calculate widget position
  const positionClasses = {
    "bottom-right": "bottom-6 right-6",
    "bottom-left": "bottom-6 left-6",
    "top-right": "top-6 right-6",
    "top-left": "top-6 left-6",
  };

  // Calculate widget size
  const widgetSizes = {
    small: "320px",
    medium: "400px",
    large: "500px",
  };

  const widgetWidth = widgetSizes[uiSettings.widget_size] || widgetSizes.medium;
  const positionClass = positionClasses[uiSettings.widget_position] || positionClasses["bottom-right"];

  // Detect if running in iframe
  const isInIframe = window.self !== window.top;

  // For iframe mode, always show the chat and use relative positioning
  const containerClass = isInIframe 
    ? "relative w-full h-full font-sans" 
    : `fixed ${positionClass} z-50 font-sans`;

  return (
    <div className={containerClass}>
      {!isInIframe && (
        <button
          type="button"
          onClick={toggleWidget}
          className="flex items-center gap-2 rounded-full px-4 py-3 text-sm font-semibold text-white shadow-lg transition-all duration-300 hover:scale-105 active:scale-95"
          style={{
            backgroundColor: uiSettings.primary_color,
            boxShadow: `0 10px 25px ${uiSettings.primary_color}40`,
          }}
          onMouseEnter={(e) => {
            e.target.style.opacity = "0.9";
            e.target.style.transform = "scale(1.05)";
          }}
          onMouseLeave={(e) => {
            e.target.style.opacity = "1";
            e.target.style.transform = "scale(1)";
          }}
          aria-expanded={isOpen}
        >
          <span className="h-5 w-5 transition-transform duration-300" style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}>💬</span>
          {buttonLabel}
        </button>
      )}

      {(isOpen || isInIframe) && (
        <div 
          className={`overflow-hidden rounded-3xl border border-slate-200 shadow-2xl ${isInIframe ? 'h-full' : 'mt-4 animate-slide-in-up'}`}
          style={{
            width: isInIframe ? '100%' : widgetWidth,
            height: isInIframe ? '100%' : 'auto',
            backgroundColor: uiSettings.background_color,
            animation: isInIframe ? 'none' : 'slideInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <header 
            className="flex items-center gap-3 px-5 py-4 text-white"
            style={{
              background: `linear-gradient(135deg, ${uiSettings.primary_color}, ${uiSettings.secondary_color})`,
            }}
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 text-xl overflow-hidden flex-shrink-0">
              {uiSettings.header_image_url ? (
                <img src={uiSettings.header_image_url} alt="Bot Header" className="h-full w-full rounded-full object-cover" />
              ) : uiSettings.bot_icon_url ? (
                <img src={uiSettings.bot_icon_url} alt="Bot" className="h-full w-full rounded-full object-cover" />
              ) : (
                "🤖"
              )}
            </span>
            <div>
              <h2 className="text-base font-bold leading-tight">{uiSettings.bot_name || 'Virtual Assistant'}</h2>
            </div>
          </header>

          <div 
            ref={chatBodyRef} 
            className={`flex flex-col gap-4 overflow-y-auto px-4 py-5 ${isInIframe ? 'flex-1' : 'max-h-[420px]'}`}
            style={{
              backgroundColor: uiSettings.background_color,
            }}
          >
            {messages.map((message) => (
              <MessageBubble 
                key={message.id} 
                role={message.role} 
                content={message.content} 
                settings={uiSettings}
                isTyping={message.isTyping}
              />
            ))}
            {isLoading && !messages.some(msg => msg.isTyping) && <TypingIndicator settings={uiSettings} />}

            {showInfoForm && !infoSubmitted && (
              <div className="rounded-2xl border border-indigo-200 bg-white p-4 text-sm text-slate-700 shadow animate-fade-in-up">
                <p className="mb-3 font-semibold text-indigo-600">Let us stay in touch</p>
                <p className="mb-4 text-xs text-slate-500">
                  Please share your contact details to continue chatting. Our team can follow up with tailored recommendations.
                </p>
                <form onSubmit={handleInfoSubmit} className="flex flex-col gap-3 text-sm">
                  <input
                    name="name"
                    type="text"
                    value={formData.name}
                    onChange={handleFormChange}
                    placeholder="Your name"
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 focus:outline-none transition-all duration-200"
                    style={{
                      borderColor: '#e2e8f0',
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = uiSettings.primary_color;
                      e.target.style.boxShadow = `0 0 0 3px ${uiSettings.primary_color}20`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#e2e8f0';
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                  <input
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleFormChange}
                    placeholder="Email address"
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 focus:outline-none transition-all duration-200"
                    style={{
                      borderColor: '#e2e8f0',
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = uiSettings.primary_color;
                      e.target.style.boxShadow = `0 0 0 3px ${uiSettings.primary_color}20`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#e2e8f0';
                      e.target.style.boxShadow = 'none';
                    }}
                    required
                  />
                  <input
                    name="phone"
                    type="tel"
                    value={formData.phone}
                    onChange={handleFormChange}
                    placeholder="Phone number"
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 focus:outline-none transition-all duration-200"
                    style={{
                      borderColor: '#e2e8f0',
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = uiSettings.primary_color;
                      e.target.style.boxShadow = `0 0 0 3px ${uiSettings.primary_color}20`;
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#e2e8f0';
                      e.target.style.boxShadow = 'none';
                    }}
                  />
                  <button
                    type="submit"
                    className="mt-1 rounded-xl px-3 py-2 font-semibold text-white transition-all duration-200 disabled:cursor-not-allowed hover:scale-105 active:scale-95"
                    style={{
                      backgroundColor: uiSettings.primary_color,
                      opacity: isLoading ? 0.6 : 1,
                    }}
                    onMouseEnter={(e) => {
                      if (!isLoading) {
                        e.target.style.opacity = "0.9";
                        e.target.style.transform = "scale(1.05)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isLoading) {
                        e.target.style.opacity = "1";
                        e.target.style.transform = "scale(1)";
                      }
                    }}
                    disabled={isLoading}
                  >
                    {isLoading ? "Saving..." : "Submit"}
                  </button>
                </form>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600 animate-fade-in-up">
                {error}
              </div>
            )}
          </div>

          <form 
            onSubmit={handleSendMessage} 
            className="border-t border-slate-200 p-3 sm:p-4"
            style={{
              backgroundColor: uiSettings.background_color,
            }}
          >
            <div className="flex items-center gap-2" style={{ minWidth: 0 }}>
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder={isRecording ? "Listening..." : "Type your message..."}
                className="chat-input-field rounded-2xl border border-slate-300 px-3 py-2.5 text-sm sm:px-4 sm:py-3 focus:outline-none"
                style={{
                  borderColor: isRecording 
                    ? '#ef4444' 
                    : (uiSettings.background_color === '#ffffff' ? '#cbd5e1' : 'rgba(255,255,255,0.2)'),
                  fontSize: isInIframe ? '16px' : undefined, // Prevent zoom on iOS
                  flex: '1 1 0',
                  minWidth: 0,
                }}
                onFocus={(e) => {
                  if (!isRecording) {
                    e.target.style.borderColor = uiSettings.primary_color;
                  }
                }}
                onBlur={(e) => {
                  if (!isRecording) {
                    e.target.style.borderColor = uiSettings.background_color === '#ffffff' ? '#cbd5e1' : 'rgba(255,255,255,0.2)';
                  }
                }}
                disabled={isLoading || isRecording || (showInfoForm && !infoSubmitted)}
              />
              <button
                type="button"
                onClick={handleVoiceInput}
                className={`chat-action-button flex items-center justify-center rounded-full transition-all duration-200 hover:scale-110 active:scale-95 touch-manipulation flex-shrink-0 ${
                  isRecording ? 'animate-pulse' : ''
                } ${!isVoiceSupported ? 'opacity-30 cursor-not-allowed' : ''}`}
                style={{
                  backgroundColor: isRecording ? '#ef4444' : uiSettings.primary_color,
                  opacity: (!isVoiceSupported || isLoading) ? 0.5 : 1,
                  color: 'white',
                }}
                disabled={isLoading || !isVoiceSupported || (showInfoForm && !infoSubmitted)}
                title={
                  !isVoiceSupported 
                    ? 'Voice input not supported in this browser' 
                    : (isRecording ? 'Stop recording' : 'Start voice input')
                }
              >
                {isRecording ? (
                  <svg className="chat-action-icon" fill="currentColor" viewBox="0 0 24 24">
                    <rect x="6" y="6" width="12" height="12" rx="2"/>
                  </svg>
                ) : (
                  <svg className="chat-action-icon" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>
                  </svg>
                )}
              </button>
              <button
                type="submit"
                className="chat-action-button flex items-center justify-center rounded-full text-white transition-all duration-200 disabled:cursor-not-allowed hover:scale-110 active:scale-95 touch-manipulation flex-shrink-0"
                style={{
                  backgroundColor: uiSettings.primary_color,
                  opacity: (isLoading || !input.trim()) ? 0.5 : 1,
                }}
                onMouseEnter={(e) => {
                  if (!isLoading && input.trim()) {
                    e.target.style.opacity = "0.9";
                    e.target.style.transform = "scale(1.1)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isLoading && input.trim()) {
                    e.target.style.opacity = "1";
                    e.target.style.transform = "scale(1)";
                  }
                }}
                disabled={isLoading || !input.trim() || (showInfoForm && !infoSubmitted)}
              >
                {isLoading ? (
                  <svg className="chat-action-icon animate-spin" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                ) : (
                  <span className="chat-action-text">➤</span>
                )}
              </button>
            </div>
            {uiSettings.show_branding && (
              <div className="mt-2 text-center text-xs text-slate-400">
                Powered by <span style={{ color: uiSettings.primary_color, fontWeight: 600 }}>Cache Digitech</span>
              </div>
            )}
          </form>
        </div>
      )}
    </div>
  );
}
