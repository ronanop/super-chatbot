import { useState, useEffect } from "react";
import { API_BASE_URL as DEFAULT_API_BASE_URL, fetchApiConfig } from "../config";
import { storageKeys as authStorageKeys } from "./LoginForm";

export default function ChatSidebar({ 
  currentSessionId, 
  onSessionSelect, 
  onNewChat,
  isOpen,
  onToggle,
  onLogout 
}) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingSessionId, setDeletingSessionId] = useState(null);
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);

  useEffect(() => {
    // Fetch API config
    fetchApiConfig().then(setApiBaseUrl);
  }, []);

  const loadSessions = async () => {
    try {
      const authToken = localStorage.getItem(authStorageKeys.authToken);
      if (!authToken) {
        setLoading(false);
        return;
      }

      // Add timeout to prevent hanging
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      const response = await fetch(`${apiBaseUrl}/chat/sessions`, {
        headers: {
          "Authorization": `Bearer ${authToken}`,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      } else if (response.status === 401) {
        // Session expired - don't show error, just return empty
        setSessions([]);
      }
    } catch (error) {
      // Only log if it's not an abort (timeout) or network error
      if (error.name !== 'AbortError' && error.name !== 'TypeError') {
        console.error("Failed to load sessions:", error);
      }
      // Don't show error to user - just leave sessions empty
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Always load sessions since sidebar is always visible
    loadSessions();
  }, [apiBaseUrl, currentSessionId]); // Reload when API URL or session changes

  const handleNewChatClick = async () => {
    await onNewChat();
    // Reload sessions after creating new chat
    setTimeout(() => loadSessions(), 500);
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation(); // Prevent triggering the session select
    
    if (!confirm("Are you sure you want to delete this chat? This action cannot be undone.")) {
      return;
    }

    try {
      setDeletingSessionId(sessionId);
      const authToken = localStorage.getItem(authStorageKeys.authToken);
      if (!authToken) return;

      const response = await fetch(`${apiBaseUrl}/chat/sessions/${sessionId}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        // Remove the deleted session from the list
        setSessions(sessions.filter(s => s.id !== sessionId));
        
        // If the deleted session was the current one, create a new chat
        if (currentSessionId === sessionId) {
          await onNewChat();
        }
      } else if (response.status === 401) {
        // Handle unauthorized - could trigger logout
        console.error("Unauthorized to delete session");
      } else {
        const errorData = await response.json().catch(() => ({}));
        alert(errorData.detail || "Failed to delete chat session.");
      }
    } catch (error) {
      console.error("Failed to delete session:", error);
      alert("Network error. Please try again.");
    } finally {
      setDeletingSessionId(null);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  };

  return (
    <>
      {/* Sidebar - Always visible on desktop/tablet, toggleable on mobile */}
      <div
        className={`fixed left-0 top-0 h-full bg-gray-50 border-r border-gray-200 z-40 transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
        style={{ width: "280px" }}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Chats</h2>
              {/* Close button - visible on mobile only */}
              <button
                onClick={onToggle}
                className="p-1 rounded hover:bg-gray-200 text-gray-600 md:hidden"
                title="Close sidebar"
                aria-label="Close sidebar"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <button
              onClick={handleNewChatClick}
              className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Chat
            </button>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-gray-500">Loading...</div>
            ) : sessions.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                No previous chats. Start a new conversation!
              </div>
            ) : (
              <div className="p-2">
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`group relative w-full p-3 rounded-lg mb-1 transition-colors ${
                      currentSessionId === session.id
                        ? "bg-indigo-100 border border-indigo-300"
                        : "hover:bg-gray-100"
                    }`}
                  >
                    <button
                      onClick={() => onSessionSelect(session.id)}
                      className="w-full text-left"
                    >
                      <div className="flex items-start justify-between gap-2 pr-6">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-900 truncate">
                            {session.preview || "New Chat"}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {formatDate(session.started_at)}
                            {session.message_count > 0 && (
                              <span className="ml-2">• {session.message_count} messages</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </button>
                    <button
                      onClick={(e) => handleDeleteSession(session.id, e)}
                      disabled={deletingSessionId === session.id}
                      className="absolute top-3 right-2 p-1.5 rounded hover:bg-red-100 text-gray-400 hover:text-red-600 transition-colors opacity-0 group-hover:opacity-100 disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete chat"
                    >
                      {deletingSessionId === session.id ? (
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-4 w-4 animate-spin"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      ) : (
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          className="h-4 w-4"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Logout Button at Bottom */}
          {onLogout && (
            <div className="p-4 border-t border-gray-200">
              <button
                onClick={onLogout}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="text-sm font-medium">Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Overlay - visible on mobile when sidebar is open */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden"
          onClick={onToggle}
          aria-label="Close sidebar"
        />
      )}
    </>
  );
}

