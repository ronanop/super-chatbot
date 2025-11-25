import { useState, useEffect } from "react";
import ChatWidget from "./components/ChatWidget";
import LandingPage from "./components/LandingPage";
import { storageKeys as authStorageKeys } from "./components/LoginForm";

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check if user is already authenticated
    const authToken = localStorage.getItem(authStorageKeys.authToken);
    if (authToken) {
      setIsAuthenticated(true);
      setShowLanding(false);
    }
  }, []);

  const handleGetStarted = () => {
    setShowLanding(false);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    // Don't show landing page on logout, let ChatWidget handle it
  };

  // Show landing page if not authenticated and landing flag is true
  if (showLanding && !isAuthenticated) {
    return <LandingPage onGetStarted={handleGetStarted} />;
  }

  // Show chatbot (which includes login form if not authenticated)
  return <ChatWidget />;
}
