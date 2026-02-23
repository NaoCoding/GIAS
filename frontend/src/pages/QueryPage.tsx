import React, { useState } from 'react';
import { queryAgent, triggerPatchDownload } from '../api';
import '../styles/QueryPage.css';

function QueryPage(): React.ReactElement {
  const [query, setQuery] = useState<string>('');
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [patch, setPatch] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setPatch(null);

    try {
      const response = await queryAgent(query);
      setResult(response.result);
      if (response.patch) {
        setPatch(response.patch);
      }
    } catch (err: unknown) {
      const error = err as any;
      setError(error.detail || 'Failed to process query');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = (): void => {
    setQuery('');
    setResult(null);
    setError(null);
    setPatch(null);
  };

  const handleDownloadPatch = (): void => {
    if (patch?.patch_content) {
      triggerPatchDownload(patch.patch_content, 'query_fix.patch');
    }
  };

  const renderPatchSection = (): React.ReactElement | null => {
    if (!patch) return null;

    return (
      <div className="patch-section">
        <h3>Generated Patch</h3>
        
        {patch.status === 'success' && (
          <div className="patch-info patch-success">
            <div className="patch-status">✓ Patch Generated Successfully</div>
            
            {patch.files_changed && patch.files_changed.length > 0 && (
              <div className="patch-files">
                <strong>Files Changed:</strong>
                <ul>
                  {patch.files_changed.map((file: string, idx: number) => (
                    <li key={idx}>{file}</li>
                  ))}
                </ul>
              </div>
            )}

            {patch.commit_message && (
              <div className="patch-commit">
                <strong>Suggested Commit Message:</strong>
                <pre>{patch.commit_message}</pre>
              </div>
            )}

            <div className="patch-actions">
              <button 
                className="btn btn-patch" 
                onClick={handleDownloadPatch}
                title="Download the patch file to your computer"
              >
                📥 Download Patch
              </button>
              {patch.patch_file && (
                <span className="patch-file-info">
                  Saved to: {patch.patch_file}
                </span>
              )}
            </div>

            {patch.patch_content && (
              <details className="patch-preview">
                <summary>View Patch Content</summary>
                <pre className="patch-code">{patch.patch_content}</pre>
              </details>
            )}
          </div>
        )}

        {patch.status === 'warning' && (
          <div className="patch-info patch-warning">
            <div className="patch-status">⚠ Patch Generation Warning</div>
            <p>The patch was generated but may require review before applying.</p>
          </div>
        )}

        {patch.status === 'failed' && (
          <div className="patch-info patch-failed">
            <div className="patch-status">✗ Patch Generation Failed</div>
            <p>Unable to generate patch from the analysis.</p>
          </div>
        )}

        {patch.status === 'not_generated' && (
          <div className="patch-info patch-not-generated">
            <div className="patch-status">ℹ Patch Not Generated</div>
            <p>Include an issue number (e.g., #123) in your query to generate a patch.</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="query-page">
      <div className="query-container">
        <h2>Ask a General Question</h2>
        <p className="description">Ask any question about the repository or codebase. Include an issue number (e.g., #123) to auto-generate patches.</p>

        <form onSubmit={handleSubmit} className="query-form">
          <textarea
            className="query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your question here... (e.g., 'What's wrong with #123?')"
            rows={6}
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

        {renderPatchSection()}
      </div>
    </div>
  );
}

export default QueryPage;
