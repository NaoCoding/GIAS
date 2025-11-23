import React, { useState } from 'react';
import './App.css';
import QueryPage from './pages/QueryPage';
import IssueAnalysisPage from './pages/IssueAnalysisPage';

function App() {
  const [currentPage, setCurrentPage] = useState('query');

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>GIAS - GitHub Issue Analysis System</h1>
          <nav className="nav">
            <button
              className={`nav-btn ${currentPage === 'query' ? 'active' : ''}`}
              onClick={() => setCurrentPage('query')}
            >
              Query
            </button>
            <button
              className={`nav-btn ${currentPage === 'issue' ? 'active' : ''}`}
              onClick={() => setCurrentPage('issue')}
            >
              Analyze Issue
            </button>
          </nav>
        </div>
      </header>

      <main className="main-content">
        {currentPage === 'query' && <QueryPage />}
        {currentPage === 'issue' && <IssueAnalysisPage />}
      </main>

      <footer className="footer">
        <p>&copy; 2024 GIAS Frontend. Backend: http://localhost:8000</p>
      </footer>
    </div>
  );
}

export default App;
