import React, { useState, useEffect } from 'react';
import LoginPage from './LoginPage';
import Dashboard from './Dashboard';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check for existing authentication on component mount
  useEffect(() => {
    checkAuth();
  }, []);

  // Check if user is already authenticated via sessionStorage
  const checkAuth = () => {
    const authData = sessionStorage.getItem('autoninja_auth');
    if (authData) {
      try {
        const { isAuthenticated, timestamp } = JSON.parse(authData);
        // Check if session is still valid (24 hours)
        const now = Date.now();
        const sessionDuration = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
        
        if (isAuthenticated && (now - timestamp) < sessionDuration) {
          setIsAuthenticated(true);
        } else {
          // Session expired, clear storage
          sessionStorage.removeItem('autoninja_auth');
        }
      } catch (error) {
        // Invalid auth data, clear storage
        sessionStorage.removeItem('autoninja_auth');
      }
    }
  };

  // Handle successful login
  const handleLogin = () => {
    const authData = {
      isAuthenticated: true,
      timestamp: Date.now(),
    };
    sessionStorage.setItem('autoninja_auth', JSON.stringify(authData));
    setIsAuthenticated(true);
  };

  // Handle logout
  const handleLogout = () => {
    sessionStorage.removeItem('autoninja_auth');
    setIsAuthenticated(false);
  };

  return (
    <div>
      {isAuthenticated ? (
        <Dashboard onLogout={handleLogout} />
      ) : (
        <LoginPage onLogin={handleLogin} />
      )}
    </div>
  );
}

export default App;
