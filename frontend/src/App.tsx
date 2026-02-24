import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useParams } from 'react-router-dom';
import './App.css';
import QueryPage from './pages/QueryPage';
import IssueAnalysisPage from './pages/IssueAnalysisPage';
import RAGBuilderPage from './pages/RAGBuilderPage';

type PageType = 'query' | 'issue' | 'rag-builder';

// Component for handling direct issue URL routes
function IssueRouteHandler(): React.ReactElement {
  const { owner, repo, issueId } = useParams<{ owner: string; repo: string; issueId: string }>();
  
  if (!owner || !repo || !issueId) {
    return <div>Invalid URL format</div>;
  }

  return <IssueAnalysisPage initialOwner={owner} initialRepo={repo} initialIssueId={issueId} />;
}

function AppContent(): React.ReactElement {
  const [currentPage, setCurrentPage] = useState<PageType>('query');

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
            <button
              className={`nav-btn ${currentPage === 'rag-builder' ? 'active' : ''}`}
              onClick={() => setCurrentPage('rag-builder')}
            >
              Build RAG
            </button>
          </nav>
        </div>
      </header>

      <main className="main-content">
        {currentPage === 'query' && <QueryPage />}
        {currentPage === 'issue' && <IssueAnalysisPage />}
        {currentPage === 'rag-builder' && <RAGBuilderPage />}
      </main>

      <footer className="footer">
        <p>&copy; 2025 GIAS Frontend. Backend: http://localhost:8000</p>
      </footer>
    </div>
  );
}

function App(): React.ReactElement {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AppContent />} />
        <Route path="/:owner/:repo/issues/:issueId" element={<IssueRouteHandler />} />
      </Routes>
    </Router>
  );
}

export default App;
