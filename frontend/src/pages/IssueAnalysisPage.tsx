import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { analyzeIssue, AnalysisResponse, triggerPatchDownload } from '../api';
import '../styles/IssueAnalysisPage.css';

interface IssueAnalysisPageProps {
  initialOwner?: string;
  initialRepo?: string;
  initialIssueId?: string;
}

function IssueAnalysisPage({ 
  initialOwner = '', 
  initialRepo = '', 
  initialIssueId = '' 
}: IssueAnalysisPageProps): React.ReactElement {
  const [owner, setOwner] = useState<string>(initialOwner);
  const [repo, setRepo] = useState<string>(initialRepo);
  const [issueId, setIssueId] = useState<string>(initialIssueId);
  const [customQuery, setCustomQuery] = useState<string>('');
  
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  const hasAnalyzedRef = useRef<boolean>(false);

  // Auto-trigger analysis when route parameters are provided (only once)
  useEffect(() => {
    if (initialOwner && initialRepo && initialIssueId && !hasAnalyzedRef.current) {
      hasAnalyzedRef.current = true;
      handleAnalyzeWithParams(initialOwner, initialRepo, initialIssueId);
    }
  }, []);

  const handleAnalyzeWithParams = async (
    ownerParam: string,
    repoParam: string,
    issueIdParam: string,
    customQueryParam: string = ''
  ): Promise<void> => {
    if (!ownerParam.trim() || !repoParam.trim() || !issueIdParam.trim()) {
      setError('Please fill in all fields (owner, repo, issue ID)');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);
    setAnalysis(null);

    try {
      const response = await analyzeIssue(
        ownerParam,
        repoParam,
        parseInt(issueIdParam),
        customQueryParam.trim() || null
      );
      setAnalysis(response);
      setSuccess('Issue analyzed successfully!');
    } catch (err: unknown) {
      const error = err as any;
      setError(error.detail || 'Failed to analyze issue');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    await handleAnalyzeWithParams(owner, repo, issueId, customQuery);
  };

  const handleClear = (): void => {
    setOwner('');
    setRepo('');
    setIssueId('');
    setCustomQuery('');
    setAnalysis(null);
    setError(null);
    setSuccess(null);
    hasAnalyzedRef.current = false;
  };

  const handleDownloadPatch = (): void => {
    if (analysis?.patch?.patch_content) {
      const patchName = `issue_${issueId}_${repo}_fix.patch`;
      triggerPatchDownload(analysis.patch.patch_content, patchName);
    }
  };

  const renderPatchSection = (): React.ReactElement | null => {
    if (!analysis?.patch) return null;

    const patch = analysis.patch;

    return (
      <div className="patch-section">
        <h4>Generated Patch</h4>
        
        {patch.status === 'success' && (
          <div className="patch-info patch-success">
            <div className="patch-status">✓ Patch Generated Successfully</div>
            
            {patch.files_changed.length > 0 && (
              <div className="patch-files">
                <strong>Files Changed:</strong>
                <ul>
                  {patch.files_changed.map((file, idx) => (
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
            {patch.patch_content && (
              <details className="patch-preview">
                <summary>View Patch Specification</summary>
                <pre className="patch-code">{patch.patch_content}</pre>
              </details>
            )}
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
            <p>Patch generation was not attempted for this analysis.</p>
          </div>
        )}
      </div>
    );
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
              rows={4}
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
                  <ReactMarkdown>{analysis.analysis}</ReactMarkdown>
                </div>
              </div>

              {renderPatchSection()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default IssueAnalysisPage;
