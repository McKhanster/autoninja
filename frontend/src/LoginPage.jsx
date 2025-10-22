import React, { useState } from 'react';

function LoginPage({ onLogin }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Clear any previous errors
    setError('');
    
    // Validate password is not empty
    if (!password.trim()) {
      setError('Password is required.');
      return;
    }
    
    // Hardcoded password for MVP (stored locally in component)
    const DASHBOARD_PASSWORD = 'autoninja2024';
    
    // Validate password
    if (password === DASHBOARD_PASSWORD) {
      onLogin();
    } else {
      setError('Invalid password. Please try again.');
      setPassword('');
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.loginBox}>
        <h1 style={styles.title}>AutoNinja Dashboard</h1>
        <p style={styles.subtitle}>Enter password to access the dashboard</p>
        
        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            style={styles.input}
            autoFocus
          />
          
          {error && (
            <div style={styles.error}>
              {error}
            </div>
          )}
          
          <button type="submit" style={styles.button}>
            Login
          </button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
  },
  loginBox: {
    backgroundColor: 'white',
    padding: '40px',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
    width: '100%',
    maxWidth: '400px',
  },
  title: {
    margin: '0 0 10px 0',
    fontSize: '28px',
    color: '#333',
    textAlign: 'center',
  },
  subtitle: {
    margin: '0 0 30px 0',
    fontSize: '14px',
    color: '#666',
    textAlign: 'center',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
  },
  input: {
    padding: '12px',
    fontSize: '16px',
    border: '1px solid #ddd',
    borderRadius: '4px',
    marginBottom: '10px',
    outline: 'none',
  },
  error: {
    color: '#d32f2f',
    fontSize: '14px',
    marginBottom: '15px',
    padding: '10px',
    backgroundColor: '#ffebee',
    borderRadius: '4px',
    border: '1px solid #ffcdd2',
  },
  button: {
    padding: '12px',
    fontSize: '16px',
    backgroundColor: '#1976d2',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: '600',
  },
};

export default LoginPage;
