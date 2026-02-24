import React, { useState } from 'react';
import { buildRag } from '../api';
import '../styles/RAGBuilderPage.css';

function RAGBuilderPage(): React.ReactElement {
  const [owner, setOwner] = useState<string>('');
  const [repo, setRepo] = useState<string>('');
  const [saveCode, setSaveCode] = useState<boolean>(true);
  
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [buildResult, setBuildResult] = useState<any>(null);

  const handleBuild = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    
    if (!owner.trim() || !repo.trim()) {
      setError('Please fill in both repository owner and name');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);
    setBuildResult(null);

    try {
      const response = await buildRag(owner, repo, saveCode);
      setBuildResult(response);
      setSuccess(`RAG knowledge base built successfully for ${owner}/${repo}`);
    } catch (err: unknown) {
      const error = err as any;
      setError(error.detail || 'Failed to build RAG knowledge base');
      setBuildResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = (): void => {
    setOwner('');
    setRepo('');
    setSaveCode(true);
    setBuildResult(null);
    setError(null);
    setSuccess(null);
  };

  return (
    <div className="rag-builder-page">
      <div className="rag-builder-container">
        <h2>Build RAG Knowledge Base</h2>
        <p className="description">
          Create or rebuild a RAG (Retrieval-Augmented Generation) knowledge base from a GitHub repository. 
          This will process all code files and create embeddings for semantic search.
        </p>

        <form onSubmit={handleBuild} className="rag-form">
          <div className="form-group">
            <label>Repository Owner</label>
            <input
              type="text"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="e.g., facebook, torvalds, python"
              className="form-input"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label>Repository Name</label>
            <input
              type="text"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="e.g., react, linux, cpython"
              className="form-input"
              disabled={loading}
            />
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={saveCode}
                onChange={(e) => setSaveCode(e.target.checked)}
                disabled={loading}
              />
              Save repository code to disk for reference
            </label>
            <p className="checkbox-help">
              When enabled, the repository files will be saved locally for easy reference and testing.
            </p>
          </div>

          <div className="form-buttons">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Building RAG...' : 'Build RAG Knowledge Base'}
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleClear} disabled={loading}>
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

        {buildResult && (
          <div className="build-result">
            <div className="result-header">
              <h3>Build Result</h3>
              <span className={`status-badge ${buildResult.status}`}>
                {buildResult.status.toUpperCase()}
              </span>
            </div>

            <div className="result-details">
              <div className="result-item">
                <strong>Message:</strong>
                <p>{buildResult.message}</p>
              </div>

              <div className="result-item">
                <strong>Documents Processed:</strong>
                <p className="document-count">{buildResult.document_count}</p>
              </div>

              {buildResult.saved_repo_path && (
                <div className="result-item">
                  <strong>Repository Saved To:</strong>
                  <p className="repo-path">{buildResult.saved_repo_path}</p>
                </div>
              )}
            </div>

            <div className="result-info">
              <p>
                ✓ The RAG knowledge base has been successfully created. 
                You can now use the Query and Issue Analysis features with this repository.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default RAGBuilderPage;
