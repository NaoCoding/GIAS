import React, { useState } from 'react';
import { analyzeIssue } from '../api';
import '../styles/IssueAnalysisPage.css';

function IssueAnalysisPage() {
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');
  const [issueId, setIssueId] = useState('');
  const [customQuery, setCustomQuery] = useState('');
  
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    
    if (!owner.trim() || !repo.trim() || !issueId.trim()) {
      setError('Please fill in all fields (owner, repo, issue ID)');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);
    setAnalysis(null);

    try {
      const response = await analyzeIssue(
        owner,
        repo,
        parseInt(issueId),
        customQuery.trim() || null
      );
      setAnalysis(response);
      setSuccess('Issue analyzed successfully!');
    } catch (err) {
      setError(err.detail || 'Failed to analyze issue');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setOwner('');
    setRepo('');
    setIssueId('');
    setCustomQuery('');
    setAnalysis(null);
    setError(null);
    setSuccess(null);
  };

  return (
    <div className="issue-analysis-page">
      <div className="issue-container">
        <h2>Analyze GitHub Issue</h2>
        <p className="description">Enter repository and issue details to analyze</p>

        <form onSubmit={handleAnalyze} className="issue-form">
          <div className="form-group">
            <label>Repository Owner</label>
            <input
              type="text"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="e.g., facebook, torvalds"
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label>Repository Name</label>
            <input
              type="text"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="e.g., react, linux"
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label>Issue ID</label>
            <input
              type="number"
              value={issueId}
              onChange={(e) => setIssueId(e.target.value)}
              placeholder="e.g., 12345"
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label>Custom Query (Optional)</label>
            <textarea
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              placeholder="Leave empty to use issue content, or enter a custom question..."
              rows="4"
              className="form-input"
            />
          </div>

          <div className="form-buttons">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Analyzing...' : 'Analyze Issue'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleClear}>
              Clear
            </button>
          </div>
        </form>

        {error && (
          <div className="alert alert-error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {success && (
          <div className="alert alert-success">
            <strong>Success:</strong> {success}
          </div>
        )}

        {analysis && (
          <div className="analysis-result">
            <div className="result-header">
              <h3>Analysis Result</h3>
              <a href={analysis.issue_url} target="_blank" rel="noopener noreferrer" className="issue-link">
                View on GitHub
              </a>
            </div>

            <div className="issue-details">
              <div className="detail-section">
                <h4>Issue Title</h4>
                <p>{analysis.issue_title}</p>
              </div>

              <div className="detail-section">
                <h4>Issue Description</h4>
                <p>{analysis.issue_body}</p>
              </div>

              <div className="detail-section">
                <h4>Analysis</h4>
                <div className="analysis-text">
                  {analysis.analysis}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default IssueAnalysisPage;
