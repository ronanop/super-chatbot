// API Base URL Configuration
// The frontend will dynamically detect the backend URL and adapt to network changes
// This allows automatic adjustment when switching WiFi networks

// Function to get all possible network IPs dynamically
async function getNetworkIPs() {
  const ips = [];
  
  // Always include localhost variants
  ips.push('localhost');
  ips.push('127.0.0.1');
  
  // Try to get local network IP using WebRTC (works in modern browsers)
  try {
    const pc = new RTCPeerConnection({ iceServers: [] });
    const candidatePromise = new Promise((resolve) => {
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          const candidate = event.candidate.candidate;
          // Extract IP from candidate string (format: "candidate:... host ...")
          const match = candidate.match(/([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})/);
          if (match && match[1]) {
            const ip = match[1];
            // Filter out localhost and public IPs, keep only private network IPs
            if (
              ip.startsWith('192.168.') ||
              ip.startsWith('10.') ||
              ip.startsWith('172.16.') ||
              ip.startsWith('172.17.') ||
              ip.startsWith('172.18.') ||
              ip.startsWith('172.19.') ||
              ip.startsWith('172.20.') ||
              ip.startsWith('172.21.') ||
              ip.startsWith('172.22.') ||
              ip.startsWith('172.23.') ||
              ip.startsWith('172.24.') ||
              ip.startsWith('172.25.') ||
              ip.startsWith('172.26.') ||
              ip.startsWith('172.27.') ||
              ip.startsWith('172.28.') ||
              ip.startsWith('172.29.') ||
              ip.startsWith('172.30.') ||
              ip.startsWith('172.31.')
            ) {
              if (!ips.includes(ip)) {
                ips.push(ip);
              }
            }
          }
        }
      };
      // Resolve after a short timeout
      setTimeout(() => resolve(), 1000);
    });
    
    // Create a dummy data channel to trigger ICE candidate gathering
    pc.createDataChannel('');
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    
    await candidatePromise;
    pc.close();
  } catch (e) {
    // WebRTC method failed, continue with other methods
    console.debug('WebRTC IP detection failed:', e);
  }
  
  // If we're accessing via a specific hostname/IP, add it
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname && hostname !== 'localhost' && hostname !== '127.0.0.1' && !ips.includes(hostname)) {
      ips.push(hostname);
    }
  }
  
  return ips;
}

// Fallback URLs (used if backend config fetch fails)
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
let API_BASE_URL = defaultUrl;
let lastSuccessfulUrl = null; // Cache the last successful URL

// Function to test if a backend URL is reachable
async function testBackendUrl(baseUrl, timeout = 2000) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    const response = await fetch(`${baseUrl}/health`, {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      return { success: true, url: baseUrl };
    }
  } catch (err) {
    // URL not reachable
  }
  return { success: false, url: baseUrl };
}

// Function to fetch API config from backend with dynamic IP detection
async function fetchApiConfig(forceRediscover = false) {
  // If running in embed mode with WIDGET_API_BASE_URL set, use it directly
  if (window.WIDGET_API_BASE_URL) {
    console.log("✅ Using embed-provided API URL:", window.WIDGET_API_BASE_URL);
    API_BASE_URL = window.WIDGET_API_BASE_URL;
    lastSuccessfulUrl = API_BASE_URL;
    return API_BASE_URL;
  }
  
  // If we have a cached successful URL and not forcing rediscovery, try it first
  if (lastSuccessfulUrl && !forceRediscover) {
    const test = await testBackendUrl(lastSuccessfulUrl, 1000);
    if (test.success) {
      API_BASE_URL = lastSuccessfulUrl;
      return API_BASE_URL;
    }
  }
  
  // Build list of possible URLs
  const possibleUrls = [];
  
  // 1. Try current origin first (if accessing via IP/hostname)
  if (typeof window !== 'undefined') {
    const origin = window.location.origin;
    if (origin && !origin.includes('localhost') && !origin.includes('127.0.0.1')) {
      // Replace port with backend port (8000)
      const url = origin.replace(/:\d+$/, ':8000');
      if (!possibleUrls.includes(url)) {
        possibleUrls.push(url);
      }
    }
  }
  
  // 2. Add localhost variants
  if (!possibleUrls.includes('http://localhost:8000')) {
    possibleUrls.push('http://localhost:8000');
  }
  if (!possibleUrls.includes('http://127.0.0.1:8000')) {
    possibleUrls.push('http://127.0.0.1:8000');
  }
  
  // 3. Dynamically discover network IPs
  try {
    const networkIPs = await getNetworkIPs();
    networkIPs.forEach(ip => {
      if (ip !== 'localhost' && ip !== '127.0.0.1') {
        const url = `http://${ip}:8000`;
        if (!possibleUrls.includes(url)) {
          possibleUrls.push(url);
        }
      }
    });
  } catch (e) {
    console.debug('Network IP discovery failed:', e);
  }
  
  // 4. Add default URL if not already present
  if (defaultUrl && !possibleUrls.includes(defaultUrl)) {
    possibleUrls.push(defaultUrl);
  }
  
  console.log(`🔍 Trying ${possibleUrls.length} possible backend URLs...`);
  
  // Try all URLs in parallel with short timeouts for faster discovery
  const testPromises = possibleUrls.map(url => testBackendUrl(url, 1500));
  const results = await Promise.all(testPromises);
  
  // Find first successful URL
  const successful = results.find(r => r.success);
  if (successful) {
    API_BASE_URL = successful.url;
    lastSuccessfulUrl = successful.url;
    console.log("✅ Found backend at:", API_BASE_URL);
    
    // Also try to fetch config from admin endpoint for additional info
    try {
      const configResponse = await fetch(`${API_BASE_URL}/admin/api/config`, {
        method: "GET",
        headers: { "Accept": "application/json" },
        signal: AbortSignal.timeout(2000)
      });
      if (configResponse.ok) {
        const config = await configResponse.json();
        if (config.api_base_url) {
          API_BASE_URL = config.api_base_url;
          lastSuccessfulUrl = API_BASE_URL;
          console.log("✅ Using backend-configured URL:", API_BASE_URL);
        }
      }
    } catch (e) {
      // Config endpoint failed, but we have a working URL
    }
    
    return API_BASE_URL;
  }
  
  // If all attempts failed, use default
  console.warn("⚠️ Could not find backend, using default:", defaultUrl);
  API_BASE_URL = defaultUrl;
  return API_BASE_URL;
}

// Fetch config immediately (but don't block - use default for now)
fetchApiConfig().then(() => {
  console.log("🔧 Final API Configuration:");
  console.log("  Hostname:", typeof window !== 'undefined' ? window.location.hostname : 'N/A');
  console.log("  API Base URL:", API_BASE_URL);
});

// Export the API_BASE_URL and fetchApiConfig
export { API_BASE_URL, fetchApiConfig };
