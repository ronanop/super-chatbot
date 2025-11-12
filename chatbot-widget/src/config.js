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

// Try to fetch API URL from backend
let API_BASE_URL = defaultUrl;

// Function to fetch API config from backend
async function fetchApiConfig() {
  // Try multiple possible backend URLs
  const possibleUrls = [
    defaultUrl,
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    NETWORK_URL,
  ];

  for (const baseUrl of possibleUrls) {
    try {
      const response = await fetch(`${baseUrl}/admin/api/config`, {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
      });
      
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
      // Try next URL
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
