// API Base URL Configuration
// The frontend will fetch the API URL from the backend on load
// This allows changing the IP address through the admin panel without rebuilding

// Fallback URLs (used if backend config fetch fails)
const NETWORK_IP = "192.168.36.34";
const NETWORK_URL = `http://${NETWORK_IP}:8000`;
const OLD_IP = "192.168.0.120";

// Get environment URL, but ignore if it's the old IP
let envUrl = import.meta.env.VITE_API_BASE_URL;
if (envUrl && envUrl.includes(OLD_IP)) {
  console.warn(`⚠️ Old IP detected in environment: ${envUrl}. Will try to fetch from backend.`);
  envUrl = null; // Ignore old IP
}

// Default fallback URL
let defaultUrl = envUrl || NETWORK_URL;

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
  // Try localhost first (fastest), then network IPs
  const possibleUrls = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    defaultUrl,
    NETWORK_URL,
  ];

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
