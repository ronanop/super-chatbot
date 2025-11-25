import { useEffect, useMemo, useRef, useState } from "react";

import { API_BASE_URL as DEFAULT_API_BASE_URL, fetchApiConfig } from "../config";
import LoginForm, { storageKeys as authStorageKeys } from "./LoginForm";
import ChatSidebar from "./ChatSidebar";
import UserProfile from "./UserProfile";

const BOT_AVATAR = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f916.svg";
const USER_AVATAR = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/1f464.svg";

// Default settings
const defaultSettings = {
  bot_name: "AskCache.ai Assistant",
  bot_icon_url: null,
  header_image_url: null,
  welcome_message: "Hi! I'm AskCache.ai assistant. Ask me anything and I'll help you find the information you need.",
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

const storageKeys = {
  session: "askcache_session_id",
  info: "askcache_info_submitted",
  messages: "askcache_messages", // Store chat history
  uiSettings: "askcache_ui_settings", // Store UI settings for instant load
};

// Function to get initial messages with welcome message from localStorage if available
const getInitialMessages = () => {
  if (typeof window !== 'undefined') {
    try {
      const storedSettings = localStorage.getItem(storageKeys.uiSettings);
      if (storedSettings) {
        const parsed = JSON.parse(storedSettings);
        if (parsed.welcome_message) {
          return [{
            id: "welcome",
            role: "assistant",
            content: parsed.welcome_message,
          }];
        }
      }
    } catch (e) {
      // Ignore errors, use default
    }
  }
  return [{
    id: "welcome",
    role: "assistant",
    content: defaultSettings.welcome_message,
  }];
};

const initialMessages = getInitialMessages();

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

function MessageBubble({ role, content, settings = defaultSettings, isTyping = false, imageUrl = null, userImageUrl = null }) {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";

  const handleCopy = async () => {
    try {
      // Copy plain text content (without formatting)
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = content;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (fallbackErr) {
        console.error('Fallback copy failed:', fallbackErr);
      }
      document.body.removeChild(textArea);
    }
  };
  
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
      className={classNames("flex gap-4 animate-fade-in-up w-full", isUser ? "justify-end" : "justify-start")}
    >
      {!isUser && (
        <img
          src={settings.bot_icon_url || BOT_AVATAR}
          alt="Assistant"
          className="h-8 w-8 rounded-full flex-shrink-0"
        />
      )}
      <div className={classNames("flex flex-col", isUser ? "items-end max-w-[85%]" : "items-start max-w-[85%]")}>
        {isUser && (
          <img
            src={USER_AVATAR}
            alt="User"
            className="h-8 w-8 rounded-full flex-shrink-0 mb-2"
          />
        )}
        <div
          className={classNames(
            "rounded-2xl px-4 py-3 text-base leading-relaxed break-words",
            isUser ? "rounded-br-sm" : "rounded-bl-sm"
          )}
          style={{
            backgroundColor: isUser ? settings.user_message_bg : settings.bot_message_bg,
            color: isUser ? settings.user_message_text : settings.bot_message_text,
            border: isUser ? 'none' : '1px solid #e5e7eb',
            wordWrap: 'break-word',
            overflowWrap: 'break-word',
            maxWidth: '100%',
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
        {/* Display uploaded image in user message */}
        {userImageUrl && isUser && (
          <div className="mt-3 rounded-xl overflow-hidden" style={{ maxWidth: '100%' }}>
            <img
              src={userImageUrl}
              alt="Uploaded image"
              className="w-full h-auto rounded-xl"
              style={{ maxWidth: '512px', maxHeight: '512px', objectFit: 'contain' }}
              onError={(e) => {
                console.error('Failed to load image:', userImageUrl);
                e.target.style.display = 'none';
              }}
            />
          </div>
        )}
        
        {/* Display generated image if present */}
        {imageUrl && !isUser && (
          <div className="mt-3 rounded-xl overflow-hidden" style={{ maxWidth: '100%' }}>
            <img
              src={imageUrl}
              alt="Generated image"
              className="w-full h-auto rounded-xl"
              style={{ maxWidth: '512px', maxHeight: '512px', objectFit: 'contain' }}
              onError={(e) => {
                console.error('Failed to load image:', imageUrl);
                e.target.style.display = 'none';
              }}
            />
          </div>
        )}
        {/* Copy button for assistant messages */}
        {!isUser && !isTyping && (
          <button
            onClick={handleCopy}
            className="mt-2 flex items-center gap-1.5 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 transition-colors rounded-md hover:bg-gray-100"
            title={copied ? "Copied!" : "Copy response"}
            style={{
              opacity: copied ? 0.7 : 1,
            }}
          >
            {copied ? (
              <>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-3.5 w-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>Copied!</span>
              </>
            ) : (
              <>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-3.5 w-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span>Copy</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

export default function ChatWidget() {
  // Check authentication on mount
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem(authStorageKeys.authToken);
      return !!token;
    }
    return false;
  });

  // Sidebar state: open on desktop/tablet, closed on mobile
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    // Check if we're on desktop/tablet (md breakpoint = 768px)
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return false;
  });

  // Handle window resize to adjust sidebar state
  useEffect(() => {
    const handleResize = () => {
      // On desktop/tablet, sidebar should always be open
      if (window.innerWidth >= 768) {
        setSidebarOpen(true);
      }
      // On mobile, keep current state (don't auto-open)
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  const [profileOpen, setProfileOpen] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  // Load messages from localStorage on mount, fallback to initialMessages
  const [messages, setMessages] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const storedMessages = localStorage.getItem(storageKeys.messages);
        if (storedMessages) {
          const parsed = JSON.parse(storedMessages);
          // Only restore if we have messages (not just welcome)
          if (parsed && Array.isArray(parsed) && parsed.length > 1) {
            return parsed;
          }
        }
      } catch (e) {
        console.warn('Failed to load messages from localStorage:', e);
      }
    }
    return initialMessages;
  });
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadedImage, setUploadedImage] = useState(null); // Store uploaded image URL
  const [uploadingImage, setUploadingImage] = useState(false); // Track image upload status
  // Load UI settings from localStorage immediately to prevent flash of default theme
  const [uiSettings, setUiSettings] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const storedSettings = localStorage.getItem(storageKeys.uiSettings);
        if (storedSettings) {
          const parsed = JSON.parse(storedSettings);
          // Merge with defaults to ensure all properties exist
          return { ...defaultSettings, ...parsed };
        }
      } catch (e) {
        console.warn('Failed to load UI settings from localStorage:', e);
      }
    }
    return defaultSettings;
  });
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
  const inputRef = useRef(null); // Ref for input field to auto-focus
  const userScrolledUpRef = useRef(false); // Track if user manually scrolled up
  const autoScrollEnabledRef = useRef(true); // Track if auto-scroll should be enabled
  const fileInputRef = useRef(null); // Ref for hidden image file input
  const documentInputRef = useRef(null); // Ref for hidden document file input
  const [uploadedDocuments, setUploadedDocuments] = useState([]); // Store uploaded documents
  const [uploadingDocument, setUploadingDocument] = useState(false); // Track document upload status

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
      
      // Then fetch UI settings using the resolved URL (with retry and URL rediscovery)
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
            
            const mergedSettings = { ...defaultSettings, ...settings };
            setUiSettings(mergedSettings);
            
            // Save to localStorage for instant load on next page load
            try {
              localStorage.setItem(storageKeys.uiSettings, JSON.stringify(mergedSettings));
            } catch (e) {
              console.warn('Failed to save UI settings to localStorage:', e);
            }
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
          if (retryCount === 0 && (err.name === 'TypeError' || err.name === 'TimeoutError' || err.name === 'AbortError' || err.message?.includes('Failed to fetch'))) {
            console.log('Retrying settings fetch with URL rediscovery...');
            try {
              // Try to rediscover backend URL
              const newUrl = await fetchApiConfig(true);
              if (newUrl && newUrl !== apiUrl) {
                console.log('Discovered new backend URL:', newUrl);
                setApiBaseUrl(newUrl);
                setTimeout(() => fetchSettings(newUrl, 1), 500);
                return;
              }
            } catch (rediscoverErr) {
              console.error('Failed to rediscover backend:', rediscoverErr);
            }
            // Fallback: retry with same URL
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
              const mergedSettings = { ...defaultSettings, ...settings };
              setUiSettings(mergedSettings);
              
              // Save to localStorage for instant load on next page load
              try {
                localStorage.setItem(storageKeys.uiSettings, JSON.stringify(mergedSettings));
              } catch (e) {
                console.warn('Failed to save UI settings to localStorage:', e);
              }
              
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

  // Check if user is near bottom of chat (within 100px)
  const isNearBottom = () => {
    if (!chatBodyRef.current) return true;
    const { scrollTop, scrollHeight, clientHeight } = chatBodyRef.current;
    return scrollHeight - scrollTop - clientHeight < 100;
  };

  // Handle scroll events to detect manual scrolling
  useEffect(() => {
    const chatBody = chatBodyRef.current;
    if (!chatBody) return;

    const handleScroll = () => {
      // If user scrolls up, disable auto-scroll temporarily
      if (!isNearBottom()) {
        userScrolledUpRef.current = true;
        autoScrollEnabledRef.current = false;
      } else {
        // User scrolled back to bottom, re-enable auto-scroll
        userScrolledUpRef.current = false;
        autoScrollEnabledRef.current = true;
      }
    };

    chatBody.addEventListener('scroll', handleScroll);
    return () => chatBody.removeEventListener('scroll', handleScroll);
  }, []);

  // Smooth scroll to bottom when new messages arrive (only if user hasn't scrolled up)
  useEffect(() => {
    if (chatBodyRef.current && autoScrollEnabledRef.current) {
      const scrollToBottom = () => {
        if (chatBodyRef.current && autoScrollEnabledRef.current) {
          chatBodyRef.current.scrollTo({
            top: chatBodyRef.current.scrollHeight,
            behavior: 'smooth',
          });
        }
      };
      
      // Small delay to ensure DOM is updated
      const timeoutId = setTimeout(scrollToBottom, 50);
      return () => clearTimeout(timeoutId);
    }
  }, [messages, isLoading]);

  // Auto-scroll during typewriter effect (only if user hasn't scrolled up)
  useEffect(() => {
    const hasTypingMessage = messages.some(msg => msg.isTyping);
    if (hasTypingMessage && chatBodyRef.current && autoScrollEnabledRef.current) {
      const intervalId = setInterval(() => {
        if (chatBodyRef.current && autoScrollEnabledRef.current && isNearBottom()) {
          chatBodyRef.current.scrollTo({
            top: chatBodyRef.current.scrollHeight,
            behavior: 'smooth',
          });
        }
      }, 200); // Scroll every 200ms during typing (less aggressive)
      
      return () => clearInterval(intervalId);
    }
  }, [messages]);

  useEffect(() => {
    // Debug: Log API URL being used
    console.log("ChatWidget API Base URL:", apiBaseUrl);
    
    // Try sessionStorage first (current session), then localStorage (persistent)
    const storedSession = sessionStorage.getItem(storageKeys.session) || 
                          localStorage.getItem(storageKeys.session);
    if (storedSession) {
      setSessionId(Number(storedSession));
    }
    
  }, []);

  useEffect(() => {
    if (sessionId) {
      sessionStorage.setItem(storageKeys.session, String(sessionId));
      // Also save to localStorage for persistence across browser sessions
      localStorage.setItem(storageKeys.session, String(sessionId));
    }
  }, [sessionId]);
  
  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined' && messages.length > 0) {
      try {
        // Don't save if only welcome message (allow fresh start)
        if (messages.length > 1 || messages[0].id !== 'welcome') {
          localStorage.setItem(storageKeys.messages, JSON.stringify(messages));
        }
      } catch (e) {
        console.warn('Failed to save messages to localStorage:', e);
      }
    }
  }, [messages]);

  useEffect(() => {
    const body = chatBodyRef.current;
    if (body && autoScrollEnabledRef.current && isNearBottom()) {
      body.scrollTo({ top: body.scrollHeight, behavior: "smooth" });
    }
  }, [messages]);

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
    if ((!trimmed && !uploadedImage && uploadedDocuments.length === 0) || isLoading) return; // Allow sending with image or documents

    const pendingId = createMessageId();
    const assistantMessageId = createMessageId();
    const userMessage = { 
      id: pendingId, 
      role: "user", 
      content: trimmed || (uploadedImage ? "Analyze this image" : "") || (uploadedDocuments.length > 0 ? "Analyze these documents" : ""),
      imageUrl: uploadedImage ? `${apiBaseUrl}${uploadedImage}` : null // Include image in message
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setUploadedImage(null); // Clear uploaded image after sending
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
      // Get auth token
      const authToken = localStorage.getItem(authStorageKeys.authToken);
      if (!authToken) {
        setIsAuthenticated(false);
        setError("Please login to continue.");
        setIsLoading(false);
        return;
      }

      // Try to fetch with automatic retry and URL rediscovery on failure
      let response;
      let finalApiUrl = apiBaseUrl;
      let retryCount = 0;
      const maxRetries = 1; // Retry once with URL rediscovery
      
      while (retryCount <= maxRetries) {
        try {
          // Create abort controller for timeout (increased timeout for LLM responses)
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout (LLM can take time)
          
          response = await fetch(`${finalApiUrl}/chat`, {
            method: "POST",
            headers: { 
              "Content-Type": "application/json",
              "Authorization": `Bearer ${authToken}`,
            },
            body: JSON.stringify({ 
              message: trimmed || (uploadedImage ? "Analyze this image" : "") || (uploadedDocuments.length > 0 ? "Analyze these documents" : ""), 
              session_id: sessionId,
              image_url: uploadedImage ? `${finalApiUrl}${uploadedImage}` : null, // Include image URL if uploaded
              document_ids: uploadedDocuments.length > 0 ? uploadedDocuments.map(doc => doc.id) : null // Include document IDs if uploaded
            }),
            signal: controller.signal,
          });
          
          clearTimeout(timeoutId);
          
          // If successful, break out of retry loop
          if (response.ok || response.status !== 0) {
            // Update API URL if we discovered a new one
            if (finalApiUrl !== apiBaseUrl) {
              setApiBaseUrl(finalApiUrl);
              console.log("✅ Updated API URL to:", finalApiUrl);
            }
            break;
          }
        } catch (err) {
          // Network error - try to rediscover backend URL
          console.warn(`Connection attempt ${retryCount + 1} failed:`, err.message);
          
          if (retryCount < maxRetries) {
            // Try to rediscover the backend URL
            console.log("🔄 Rediscovering backend URL...");
            try {
              const newUrl = await fetchApiConfig(true); // Force rediscovery
              if (newUrl && newUrl !== finalApiUrl) {
                finalApiUrl = newUrl;
                console.log("🔄 Trying new backend URL:", finalApiUrl);
                retryCount++;
                continue; // Retry with new URL
              }
            } catch (rediscoverErr) {
              console.error("Failed to rediscover backend:", rediscoverErr);
            }
          }
          
          // If we've exhausted retries, throw error
          console.error("Network error:", err);
          console.error("Error details:", {
            name: err.name,
            message: err.message,
            stack: err.stack,
            url: `${finalApiUrl}/chat`
          });
          
          // Provide helpful error message
          let errorMessage = `Cannot connect to backend. `;
          if (err.name === 'AbortError' || err.message.includes('timeout') || err.message.includes('aborted')) {
            // Check if it's a timeout or connection issue
            if (err.message.includes('aborted without reason') || err.message.includes('signal is aborted')) {
              errorMessage += "Request timed out. The backend may be processing your request - please wait a moment and try again.";
            } else {
              errorMessage += "The server is not responding. Please check if the backend is running.";
            }
          } else if (err.message.includes('Failed to fetch') || err.message.includes('ERR_CONNECTION') || err.message.includes('ERR_NETWORK')) {
            errorMessage += "Make sure the backend server is running. Start it with: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload";
          } else if (err.message.includes('CORS') || err.message.includes('Access-Control')) {
            errorMessage += "CORS error detected. Please check backend CORS configuration.";
          } else {
            errorMessage += err.message || "Network error occurred.";
          }
          
          throw new Error(errorMessage);
        }
        
        retryCount++;
      }

      if (!response.ok) {
        let errorDetail = {};
        try {
          const text = await response.text();
          if (text) {
            errorDetail = JSON.parse(text);
          }
        } catch (e) {
          // Response is not JSON, use status text
          errorDetail = { detail: response.statusText };
        }
        
        console.error("Backend error response:", {
          status: response.status,
          statusText: response.statusText,
          detail: errorDetail,
          url: `${finalApiUrl}/chat`
        });
        
        // Handle 401 Unauthorized - token expired or invalid
        if (response.status === 401) {
          handleLogout();
          throw new Error("Session expired. Please login again.");
        }
        
        // Handle 422 Validation Error
        if (response.status === 422) {
          throw new Error(errorDetail.detail || "Invalid request format. Please check your input.");
        }
        
        // Handle 500 Server Error
        if (response.status === 500) {
          throw new Error(errorDetail.detail || "Server error occurred. Please try again later.");
        }
        
        throw new Error(errorDetail.detail || `Server error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      setSessionId(data.session_id);
      
      // Clear uploaded documents after sending (they're now in the context)
      setUploadedDocuments([]);

      // Check if image was generated - if so, skip typewriter effect and show image immediately
      const hasImage = data.image_url && data.image_url.trim();
      
      // Typewriter effect: display words one by one
      const fullText = data.reply;
      const words = fullText.split(/(\s+)/); // Split by spaces but keep the spaces
      let displayedText = "";
      let wordIndex = 0;

      // Clear any existing interval
      if (typewriterIntervalRef.current) {
        clearInterval(typewriterIntervalRef.current);
      }

      // If image is present, show message immediately without typewriter effect
      if (hasImage) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: fullText, isTyping: false, imageUrl: data.image_url }
              : msg
          )
        );
        setIsLoading(false);
        
        
        // Auto-focus input
        setTimeout(() => {
          if (inputRef.current) {
            inputRef.current.focus();
          }
        }, 100);
        return;
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
            
            
            return updatedMessages;
          });
          setIsLoading(false);
          
          // Auto-focus input field after response completes
          setTimeout(() => {
            if (inputRef.current) {
              inputRef.current.focus();
            }
          }, 100);
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
      
      // Auto-focus input field after error
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
    }
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


  const handleClearChat = async () => {
    if (isLoading) return; // Don't clear while loading
    
    // Confirm with user
    if (!window.confirm("Are you sure you want to clear the chat and start a new conversation?")) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Call backend to clear chat
      const authToken = localStorage.getItem(authStorageKeys.authToken);
      const response = await fetch(`${apiBaseUrl}/chat/clear`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authToken}`,
        },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "Couldn't clear chat. Please try again.");
      }

      const data = await response.json();
      
      // Reset to initial state
      const initialMessages = getInitialMessages();
      setMessages(initialMessages);
      setSessionId(data.new_session_id || null);
      setInput("");
      
      // Clear localStorage for messages
      try {
        localStorage.removeItem(storageKeys.messages);
        // Keep session ID updated
        if (data.new_session_id) {
          localStorage.setItem(storageKeys.session, String(data.new_session_id));
          sessionStorage.setItem(storageKeys.session, String(data.new_session_id));
        }
      } catch (e) {
        console.warn('Failed to clear localStorage:', e);
      }
      
      // Scroll to top
      if (chatBodyRef.current) {
        chatBodyRef.current.scrollTo({ top: 0, behavior: "smooth" });
      }
      
      // Auto-focus input
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
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

  // Handle login success
  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    // Clear old messages and start fresh
    setMessages(initialMessages);
    setSessionId(null);
    setError(null);
  };

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem(authStorageKeys.authToken);
    localStorage.removeItem(authStorageKeys.userEmail);
    localStorage.removeItem(authStorageKeys.userId);
    localStorage.removeItem(storageKeys.messages);
    localStorage.removeItem(storageKeys.session);
    setIsAuthenticated(false);
    setMessages(initialMessages);
    setSessionId(null);
  };

  // Handle new chat creation
  const handleNewChat = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const authToken = localStorage.getItem(authStorageKeys.authToken);
      if (!authToken) {
        setIsAuthenticated(false);
        setError("Please login to continue.");
        setIsLoading(false);
        return;
      }
      
      const response = await fetch(`${apiBaseUrl}/chat/new`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${authToken}`,
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
        setMessages(initialMessages);
        setError(null);
        // Close sidebar on mobile after creating new chat
        if (window.innerWidth < 768) {
          setSidebarOpen(false);
        }
        
        // Clear localStorage for new chat
        try {
          localStorage.setItem(storageKeys.messages, JSON.stringify(initialMessages));
          localStorage.setItem(storageKeys.session, data.session_id.toString());
        } catch (e) {
          console.warn("Failed to save to localStorage:", e);
        }
      } else {
        // Handle 401 Unauthorized - token expired or invalid
        if (response.status === 401) {
          handleLogout();
          setError("Session expired. Please login again.");
          return;
        }
        
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `Server error: ${response.status}`;
        console.error("Failed to create new chat:", errorMessage, "Response:", response.status);
        setError(`Failed to create new chat: ${errorMessage}`);
      }
    } catch (error) {
      console.error("Failed to create new chat:", error);
      setError(`Failed to create new chat: ${error.message || "Network error. Please check your connection."}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle session selection
  const handleSessionSelect = async (sessionId) => {
    setSessionId(sessionId);
    setError(null);
    // Close sidebar on mobile after selecting a session
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      setSidebarOpen(false);
    }
    setIsLoading(true);
    
    // Load messages for this session
    try {
      const authToken = localStorage.getItem(authStorageKeys.authToken);
      const response = await fetch(`${apiBaseUrl}/chat/sessions/${sessionId}/messages`, {
        headers: {
          "Authorization": `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        
        if (data.messages && data.messages.length > 0) {
          // Convert backend messages to frontend format
          const formattedMessages = data.messages.map(msg => ({
            id: `msg-${msg.id}`,
            role: msg.is_user_message ? "user" : "assistant",
            content: msg.content,
            imageUrl: null, // Could be enhanced to support images
          }));
          
          // Check if first message is from assistant (welcome message)
          // If not, prepend welcome message
          if (formattedMessages.length === 0 || formattedMessages[0].role !== "assistant") {
            setMessages([...initialMessages, ...formattedMessages]);
          } else {
            // First message is assistant, so use all messages as-is
            setMessages(formattedMessages);
          }
          
          // Save to localStorage
          try {
            localStorage.setItem(storageKeys.messages, JSON.stringify(formattedMessages));
            localStorage.setItem(storageKeys.session, sessionId.toString());
          } catch (e) {
            console.warn("Failed to save messages to localStorage:", e);
          }
        } else {
          // No messages yet, start fresh
          setMessages(initialMessages);
        }
      } else {
        if (response.status === 404) {
          setError("Chat session not found.");
        } else {
          setError("Failed to load chat history.");
        }
        setMessages(initialMessages);
      }
    } catch (error) {
      console.error("Failed to load session:", error);
      setError("Failed to load chat history. Please try again.");
      setMessages(initialMessages);
    } finally {
      setIsLoading(false);
    }
  };

  // Check for 401 errors and handle logout
  useEffect(() => {
    const handle401Error = () => {
      if (error && error.includes("401") || error && error.includes("Authentication")) {
        handleLogout();
      }
    };
    handle401Error();
  }, [error]);

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return <LoginForm onLoginSuccess={handleLoginSuccess} />;
  }

  // Full-screen mode - always show chat
  const isInIframe = window.self !== window.top;
  const isFullScreen = true; // Always full screen

  return (
    <div className="fixed inset-0 w-full h-full font-sans bg-white flex flex-col">
      {/* Sidebar */}
      <ChatSidebar
        key={sessionId} // Force re-render when session changes
        currentSessionId={sessionId}
        onSessionSelect={handleSessionSelect}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onLogout={handleLogout}
      />

      {/* Full-screen chat container */}
      <div 
        className="h-full flex flex-col transition-all duration-300"
        style={{
          backgroundColor: uiSettings.background_color || '#ffffff',
          display: 'flex',
          flexDirection: 'column',
          // On desktop/tablet (md and up): calculate width to account for sidebar
          // On mobile: full width when sidebar closed, adjusted when open
          width: window.innerWidth >= 768 
            ? `calc(100% - ${uiSettings.custom_settings?.sidebar_width || 280}px)`
            : sidebarOpen 
              ? `calc(100% - ${uiSettings.custom_settings?.sidebar_width || 280}px)`
              : '100%',
          marginLeft: window.innerWidth >= 768 ? `${uiSettings.custom_settings?.sidebar_width || 280}px` : (sidebarOpen ? `${uiSettings.custom_settings?.sidebar_width || 280}px` : '0'),
        }}
      >
          <header 
            className="flex items-center justify-between gap-3 px-4 md:px-6 py-4 border-b border-gray-200 flex-shrink-0"
            style={{
              backgroundColor: '#ffffff',
              width: '100%',
              maxWidth: '100%',
              minWidth: 0,
              overflow: 'visible', // Ensure buttons aren't clipped
            }}
          >
            <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0">
              {/* Hamburger menu button - visible on mobile, hidden on desktop/tablet */}
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0 md:hidden"
                title="Toggle sidebar"
                aria-label="Toggle sidebar"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5 text-gray-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <span className="flex h-8 w-8 items-center justify-center rounded-full text-xl overflow-hidden flex-shrink-0">
                {uiSettings.header_image_url ? (
                  <img src={uiSettings.header_image_url} alt="Bot Header" className="h-full w-full rounded-full object-cover" />
                ) : uiSettings.bot_icon_url ? (
                  <img src={uiSettings.bot_icon_url} alt="Bot" className="h-full w-full rounded-full object-cover" />
                ) : (
                  "🤖"
                )}
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="text-base md:text-lg font-semibold leading-tight truncate text-gray-900">{uiSettings.bot_name || 'AskCache.ai Assistant'}</h2>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0" style={{ minWidth: 0 }}>
              {messages.length > 1 && (
                <button
                  onClick={handleClearChat}
                  disabled={isLoading}
                  className="flex items-center justify-center h-8 w-8 rounded-lg hover:bg-gray-100 transition-colors duration-200 flex-shrink-0 text-gray-600"
                  title="Clear chat and start new conversation"
                  style={{
                    opacity: isLoading ? 0.5 : 1,
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                  }}
                >
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    className="h-5 w-5" 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={2} 
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" 
                    />
                  </svg>
                </button>
              )}
              <button
                onClick={() => setProfileOpen(true)}
                className="flex items-center justify-center h-8 px-3 rounded-lg hover:bg-gray-100 transition-colors duration-200 flex-shrink-0 text-gray-600 text-sm whitespace-nowrap"
                title="Profile Settings"
              >
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className="h-4 w-4 mr-1 flex-shrink-0" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span className="hidden sm:inline">Profile</span>
              </button>
              <button
                onClick={handleLogout}
                className="flex items-center justify-center h-8 px-3 rounded-lg hover:bg-gray-100 transition-colors duration-200 flex-shrink-0 text-gray-600 text-sm whitespace-nowrap"
                title="Logout"
              >
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className="h-4 w-4 mr-1 flex-shrink-0" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </header>

          {/* User Profile Modal */}
          <UserProfile
            isOpen={profileOpen}
            onClose={() => setProfileOpen(false)}
            onLogout={handleLogout}
          />

          <div 
            ref={chatBodyRef} 
            className="flex flex-col gap-6 overflow-y-auto flex-1 px-4 py-8"
            style={{
              backgroundColor: uiSettings.background_color || '#ffffff',
              maxWidth: '768px',
              margin: '0 auto',
              width: '100%',
              // Ensure scrolling is always enabled, even during loading
              pointerEvents: 'auto',
              touchAction: 'pan-y',
            }}
          >
            {messages.map((message) => (
              <MessageBubble 
                key={message.id} 
                role={message.role} 
                content={message.content} 
                settings={uiSettings}
                isTyping={message.isTyping}
                imageUrl={message.imageUrl || null}
                userImageUrl={message.imageUrl && message.role === "user" ? message.imageUrl : null}
              />
            ))}
            {isLoading && !messages.some(msg => msg.isTyping) && <TypingIndicator settings={uiSettings} />}

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600 animate-fade-in-up">
                {error}
              </div>
            )}
          </div>

          <div className="border-t border-gray-200 bg-white">
            <form 
              onSubmit={handleSendMessage} 
              className="max-w-3xl mx-auto px-4 py-4"
            >
            {/* Image Preview */}
            {uploadedImage && (
              <div className="mb-3 relative inline-block">
                <img 
                  src={`${apiBaseUrl}${uploadedImage}`} 
                  alt="Uploaded" 
                  className="max-w-xs max-h-48 rounded-lg border border-gray-300"
                />
                <button
                  type="button"
                  onClick={() => setUploadedImage(null)}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors"
                  title="Remove image"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
            
            {/* Document Preview */}
            {uploadedDocuments.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {uploadedDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    className="relative inline-flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg border border-gray-300"
                  >
                    <svg className="h-4 w-4 text-gray-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-sm text-gray-700 truncate max-w-[200px]" title={doc.filename}>
                      {doc.filename}
                    </span>
                    <button
                      type="button"
                      onClick={() => setUploadedDocuments(prev => prev.filter(d => d.id !== doc.id))}
                      className="ml-1 p-0.5 rounded hover:bg-gray-200 transition-colors flex-shrink-0"
                      title="Remove document"
                    >
                      <svg className="w-3 h-3 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex items-center gap-3" style={{ minWidth: 0 }}>
              {/* Document Upload Button */}
              <label className="flex items-center justify-center h-[52px] w-[52px] rounded-full border-2 border-gray-300 hover:border-indigo-500 transition-colors cursor-pointer flex-shrink-0" title="Upload document (PDF, TXT)">
                <input
                  type="file"
                  ref={documentInputRef}
                  accept=".pdf,.txt,application/pdf,text/plain"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    
                    // Validate file type
                    const fileExt = file.name.toLowerCase().split('.').pop();
                    if (!['pdf', 'txt'].includes(fileExt)) {
                      setError("Invalid file type. Please upload PDF or TXT files only.");
                      return;
                    }
                    
                    // Validate file size (50MB max)
                    if (file.size > 50 * 1024 * 1024) {
                      setError("File too large. Maximum size is 50MB.");
                      return;
                    }
                    
                    setUploadingDocument(true);
                    setError(null);
                    
                    try {
                      const authToken = localStorage.getItem(authStorageKeys.authToken);
                      if (!authToken) {
                        setIsAuthenticated(false);
                        setError("Please login to continue document upload.");
                        setUploadingDocument(false);
                        return;
                      }
                      
                      const formData = new FormData();
                      formData.append('file', file);
                      if (sessionId) {
                        formData.append('session_id', sessionId.toString());
                      }
                      
                      const response = await fetch(`${apiBaseUrl}/chat/upload-document`, {
                        method: "POST",
                        headers: {
                          "Authorization": `Bearer ${authToken}`,
                        },
                        body: formData,
                      });
                      
                      if (response.ok) {
                        const data = await response.json();
                        setUploadedDocuments(prev => [...prev, {
                          id: data.document_id,
                          filename: data.filename,
                          file_type: data.file_type,
                          file_size: data.file_size,
                        }]);
                        setSessionId(data.session_id);
                        if (!input.trim()) {
                          setInput("Analyze this document");
                        }
                      } else if (response.status === 401) {
                        handleLogout();
                        setError("Session expired. Please login again.");
                      } else {
                        const errorData = await response.json().catch(() => ({}));
                        setError(errorData.detail || "Failed to upload document.");
                      }
                    } catch (err) {
                      console.error("Failed to upload document:", err);
                      setError("Network error. Please try again.");
                    } finally {
                      setUploadingDocument(false);
                      // Reset file input
                      if (documentInputRef.current) {
                        documentInputRef.current.value = '';
                      }
                    }
                  }}
                  disabled={isLoading || uploadingDocument}
                />
                {uploadingDocument ? (
                  <svg className="h-5 w-5 animate-spin text-gray-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                )}
              </label>
              
              {/* Image Upload Button */}
              <label className="flex items-center justify-center h-[52px] w-[52px] rounded-full border-2 border-gray-300 hover:border-indigo-500 transition-colors cursor-pointer flex-shrink-0" title="Upload image">
                <input
                  type="file"
                  accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    
                    // Validate file size (20MB max)
                    if (file.size > 20 * 1024 * 1024) {
                      setError("Image too large. Maximum size is 20MB.");
                      return;
                    }
                    
                    setUploadingImage(true);
                    setError(null);
                    
                    try {
                      const authToken = localStorage.getItem(authStorageKeys.authToken);
                      const formData = new FormData();
                      formData.append('file', file);
                      
                      const response = await fetch(`${apiBaseUrl}/chat/upload-image`, {
                        method: "POST",
                        headers: {
                          "Authorization": `Bearer ${authToken}`,
                        },
                        body: formData,
                      });
                      
                      if (response.ok) {
                        const data = await response.json();
                        setUploadedImage(data.image_url);
                      } else if (response.status === 401) {
                        handleLogout();
                        setError("Session expired. Please login again.");
                      } else {
                        const errorData = await response.json().catch(() => ({}));
                        setError(errorData.detail || "Failed to upload image.");
                      }
                    } catch (err) {
                      console.error("Failed to upload image:", err);
                      setError("Network error. Please try again.");
                    } finally {
                      setUploadingImage(false);
                      // Reset file input
                      e.target.value = '';
                    }
                  }}
                  disabled={isLoading || uploadingImage}
                  ref={fileInputRef}
                />
                {uploadingImage ? (
                  <svg className="h-5 w-5 animate-spin text-gray-400" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                )}
              </label>
              
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder={isRecording ? "Listening..." : uploadedImage ? "Ask about this image..." : uploadedDocuments.length > 0 ? "Ask about these documents..." : "Message AskCache.ai..."}
                  rows={1}
                  className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-base resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  style={{
                    borderColor: isRecording ? '#ef4444' : '#d1d5db',
                    fontSize: '16px',
                    minHeight: '52px',
                    maxHeight: '200px',
                    lineHeight: '1.5',
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage(e);
                    }
                  }}
                  onFocus={(e) => {
                    if (!isRecording) {
                      e.target.style.borderColor = uiSettings.primary_color || '#4338ca';
                    }
                  }}
                  onBlur={(e) => {
                    if (!isRecording) {
                      e.target.style.borderColor = '#d1d5db';
                    }
                  }}
                  disabled={isLoading || isRecording || uploadingDocument}
                />
              </div>
              <button
                type="submit"
                className="flex items-center justify-center h-[52px] w-[52px] rounded-full text-white transition-all duration-200 disabled:cursor-not-allowed hover:opacity-90 active:scale-95 flex-shrink-0"
                  style={{
                    backgroundColor: uiSettings.primary_color || '#4338ca',
                    opacity: (isLoading || (!input.trim() && !uploadedImage && uploadedDocuments.length === 0)) ? 0.5 : 1,
                  }}
                onMouseEnter={(e) => {
                  if (!isLoading && (input.trim() || uploadedImage || uploadedDocuments.length > 0)) {
                    e.target.style.opacity = "0.9";
                    e.target.style.transform = "scale(1.05)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isLoading && (input.trim() || uploadedImage || uploadedDocuments.length > 0)) {
                    e.target.style.opacity = "1";
                    e.target.style.transform = "scale(1)";
                  }
                }}
                disabled={isLoading || (!input.trim() && !uploadedImage && uploadedDocuments.length === 0)}
              >
                {isLoading ? (
                  <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </button>
            </div>
          </form>
          </div>
        </div>
    </div>
  );
}
