import React, { useState } from 'react';
import { queryAgent } from '../api';
import '../styles/QueryPage.css';

function QueryPage() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await queryAgent(query);
      setResult(response.result);
    } catch (err) {
      setError(err.detail || 'Failed to process query');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setQuery('');
    setResult(null);
    setError(null);
  };

  return (
    <div className="query-page">
      <div className="query-container">
        <h2>Ask a General Question</h2>
        <p className="description">Ask any question about the repository or codebase</p>

        <form onSubmit={handleSubmit} className="query-form">
          <textarea
            className="query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your question here..."
            rows="6"
          />
          <div className="form-buttons">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Processing...' : 'Ask Question'}
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

        {result && (
          <div className="result-container">
            <h3>Response</h3>
            <div className="result-text">
              {result}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default QueryPage;
