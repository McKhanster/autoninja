import React from 'react';

function Dashboard({ onLogout }) {
  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>AutoNinja Dashboard</h1>
        <button onClick={onLogout} style={styles.logoutButton}>
          Logout
        </button>
      </header>
      
      <main style={styles.main}>
        <div style={styles.welcomeCard}>
          <h2 style={styles.welcomeTitle}>Welcome to AutoNinja</h2>
          <p style={styles.welcomeText}>
            Your multi-agent Bedrock system is ready to generate production-ready AWS Bedrock Agents.
          </p>
        </div>
        
        <div style={styles.grid}>
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>System Status</h3>
            <p style={styles.cardContent}>All agents operational</p>
            <div style={styles.statusIndicator}>
              <span style={styles.statusDot}></span>
              <span>Active</span>
            </div>
          </div>
          
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Recent Jobs</h3>
            <p style={styles.cardContent}>No recent jobs</p>
          </div>
          
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>Quick Actions</h3>
            <p style={styles.cardContent}>Create new agent deployment</p>
          </div>
        </div>
      </main>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: 'white',
    padding: '20px 40px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    margin: 0,
    fontSize: '24px',
    color: '#333',
  },
  logoutButton: {
    padding: '10px 20px',
    fontSize: '14px',
    backgroundColor: '#f44336',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: '600',
  },
  main: {
    padding: '40px',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  welcomeCard: {
    backgroundColor: 'white',
    padding: '30px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
    marginBottom: '30px',
  },
  welcomeTitle: {
    margin: '0 0 15px 0',
    fontSize: '28px',
    color: '#333',
  },
  welcomeText: {
    margin: 0,
    fontSize: '16px',
    color: '#666',
    lineHeight: '1.6',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '20px',
  },
  card: {
    backgroundColor: 'white',
    padding: '25px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
  },
  cardTitle: {
    margin: '0 0 15px 0',
    fontSize: '18px',
    color: '#333',
    fontWeight: '600',
  },
  cardContent: {
    margin: '0 0 15px 0',
    fontSize: '14px',
    color: '#666',
  },
  statusIndicator: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
    color: '#4caf50',
    fontWeight: '600',
  },
  statusDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: '#4caf50',
    marginRight: '8px',
  },
};

export default Dashboard;
