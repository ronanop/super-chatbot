// API Base URL Configuration
// The frontend will fetch the API URL from the backend on load
// This allows changing the IP address through the admin panel without rebuilding

// Fallback URLs (used if backend config fetch fails)
// Use environment variable or try to detect from current hostname
const getDefaultUrl = () => {
  // First, try environment variable
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) {
    return envUrl;
  }
  
  // If in browser, try to detect from current location
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port || (protocol === 'https:' ? '443' : '80');
    
    // If same origin, use current origin
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return `${protocol}//${hostname}${port && port !== '80' && port !== '443' ? `:${port}` : ''}`;
    }
  }
  
  // Fallback to localhost for development
  return 'http://localhost:8000';
};

const defaultUrl = getDefaultUrl();

// Check if running in embed mode (iframe) - use window.WIDGET_API_BASE_URL if set
// Note: fetchApiConfig() will prioritize window.WIDGET_API_BASE_URL when called
let API_BASE_URL = defaultUrl;

// Function to fetch API config from backend
async function fetchApiConfig() {
  // If running in embed mode with WIDGET_API_BASE_URL set, use it directly
  if (window.WIDGET_API_BASE_URL) {
    console.log("✅ Using embed-provided API URL:", window.WIDGET_API_BASE_URL);
    API_BASE_URL = window.WIDGET_API_BASE_URL;
    return API_BASE_URL;
  }
  
  // Try multiple possible backend URLs in order of likelihood
  // Try current origin first, then localhost, then default
  const possibleUrls = [];
  
  // If in browser, add current origin
  if (typeof window !== 'undefined') {
    const origin = window.location.origin;
    if (origin && !possibleUrls.includes(origin)) {
      possibleUrls.push(origin);
    }
  }
  
  // Add default URL
  if (defaultUrl && !possibleUrls.includes(defaultUrl)) {
    possibleUrls.push(defaultUrl);
  }
  
  // Add localhost fallbacks for development
  if (!possibleUrls.includes('http://localhost:8000')) {
    possibleUrls.push('http://localhost:8000');
  }
  if (!possibleUrls.includes('http://127.0.0.1:8000')) {
    possibleUrls.push('http://127.0.0.1:8000');
  }

  for (const baseUrl of possibleUrls) {
    try {
      // Add timeout to prevent long waits on unreachable URLs
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout per URL
      
      const response = await fetch(`${baseUrl}/admin/api/config`, {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        const config = await response.json();
        if (config.api_base_url) {
          API_BASE_URL = config.api_base_url;
          console.log("✅ Fetched API URL from backend:", API_BASE_URL);
          console.log("  Auto-detect:", config.auto_detect);
          return API_BASE_URL;
        }
      }
    } catch (err) {
      // Try next URL (silently continue)
      continue;
    }
  }
  
  // If all attempts failed, use default
  console.warn("⚠️ Could not fetch API config from backend, using default:", defaultUrl);
  API_BASE_URL = defaultUrl;
  return API_BASE_URL;
}

// Fetch config immediately (but don't block - use default for now)
fetchApiConfig().then(() => {
  console.log("🔧 Final API Configuration:");
  console.log("  Hostname:", window.location.hostname);
  console.log("  API Base URL:", API_BASE_URL);
  console.log("  Environment URL:", envUrl || "(not set)");
});

// Export the API_BASE_URL (will be updated when fetch completes)
export { API_BASE_URL, fetchApiConfig };
