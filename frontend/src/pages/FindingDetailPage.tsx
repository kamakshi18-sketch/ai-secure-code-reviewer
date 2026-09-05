import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { findingsApi, patchesApi } from '../services/api';
import { Finding, FindingStatus } from '../types';
import { Card, CardContent, CardHeader, CardTitle, Button, LoadingSpinner } from '../components/ui';
import { 
  ArrowLeft, 
  Wrench, 
  Sparkles,
} from 'lucide-react';
import { cn, formatRelativeTime, getSeverityColor, getStatusColor } from '../utils/cn';
import toast from 'react-hot-toast';

export function FindingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [patchLoading, setPatchLoading] = useState(false);
  const [explainLoading, setExplainLoading] = useState(false);

  const fetchFinding = async () => {
    if (!id) return;
    try {
      const data = await findingsApi.get(id);
      setFinding(data);
    } catch (error) {
      toast.error('Failed to load finding details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFinding();
  }, [id]);

  const handleStatusChange = async (newStatus: FindingStatus) => {
    if (!id) return;
    try {
      const updated = await findingsApi.update(id, { status: newStatus });
      setFinding(updated);
      toast.success('Status updated');
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const handleGeneratePatch = async () => {
    if (!finding) return;
    setPatchLoading(true);
    try {
      await patchesApi.create(finding.scan_id, finding.id);
      toast.success('Patch generation started');
      navigate('/patches');
    } catch (error) {
      toast.error('Failed to generate patch');
    } finally {
      setPatchLoading(false);
    }
  };

  const handleRequestExplanation = async () => {
    if (!id) return;
    setExplainLoading(true);
    try {
      await findingsApi.explain(id);
      toast.success('AI explanation requested');
      fetchFinding();
    } catch (error) {
      toast.error('Failed to request explanation');
    } finally {
      setExplainLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!finding) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-dark-900 dark:text-dark-50">Finding not found</h2>
        <Button className="mt-4" onClick={() => navigate('/findings')}>Back to Findings</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/findings"
            className="p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-700 text-dark-600 dark:text-dark-400"
            aria-label="Back to findings"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <span className={cn('badge text-xs uppercase', getSeverityColor(finding.severity))}>
                {finding.severity}
              </span>
              <h1 className="text-2xl font-bold text-dark-900 dark:text-dark-50">
                {finding.rule_name || finding.rule_id}
              </h1>
            </div>
            <p className="text-sm text-dark-500 mt-1 font-mono">
              {finding.file_path}:{finding.line_start}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRequestExplanation}
            disabled={explainLoading}
          >
            <Sparkles className={cn('h-4 w-4 mr-2', explainLoading && 'animate-spin')} />
            AI Explain
          </Button>
          <Button
            size="sm"
            onClick={handleGeneratePatch}
            disabled={patchLoading}
          >
            <Wrench className={cn('h-4 w-4 mr-2', patchLoading && 'animate-spin')} />
            Generate Patch
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Finding Details */}
          <Card>
            <CardHeader>
              <CardTitle>Vulnerability Description</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-dark-800 dark:text-dark-200">{finding.message}</p>

              {finding.code_snippet && (
                <div>
                  <p className="text-xs font-semibold text-dark-500 uppercase mb-2">Code Snippet</p>
                  <pre className="p-4 rounded-lg bg-dark-900 text-dark-100 font-mono text-xs overflow-x-auto">
                    {finding.code_snippet}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI Analysis Section */}
          {(finding.ai_explanation || finding.ai_root_cause || finding.ai_recommended_fix) && (
            <Card className="border-primary-200 dark:border-primary-900/50 bg-primary-50/20 dark:bg-primary-950/10">
              <CardHeader className="flex flex-row items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary-600" />
                <CardTitle>AI Security Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {finding.ai_explanation && (
                  <div>
                    <h4 className="text-sm font-semibold text-dark-900 dark:text-dark-100 mb-1">Explanation</h4>
                    <p className="text-sm text-dark-700 dark:text-dark-300 whitespace-pre-wrap">{finding.ai_explanation}</p>
                  </div>
                )}
                {finding.ai_root_cause && (
                  <div>
                    <h4 className="text-sm font-semibold text-dark-900 dark:text-dark-100 mb-1">Root Cause</h4>
                    <p className="text-sm text-dark-700 dark:text-dark-300 whitespace-pre-wrap">{finding.ai_root_cause}</p>
                  </div>
                )}
                {finding.ai_recommended_fix && (
                  <div>
                    <h4 className="text-sm font-semibold text-dark-900 dark:text-dark-100 mb-1">Recommended Fix</h4>
                    <p className="text-sm text-dark-700 dark:text-dark-300 whitespace-pre-wrap">{finding.ai_recommended_fix}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        {/* Metadata Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Metadata & Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs text-dark-500 font-medium uppercase">Current Status</p>
                <div className="mt-1">
                  <span className={cn('badge uppercase text-xs', getStatusColor(finding.status))}>
                    {finding.status}
                  </span>
                </div>
              </div>

              <div>
                <p className="text-xs text-dark-500 font-medium uppercase mb-1">Update Status</p>
                <select
                  className="input text-sm"
                  value={finding.status}
                  onChange={(e) => handleStatusChange(e.target.value as FindingStatus)}
                >
                  <option value="open">Open</option>
                  <option value="fixed">Fixed</option>
                  <option value="false_positive">False Positive</option>
                  <option value="wont_fix">Won't Fix</option>
                  <option value="ignored">Ignored</option>
                  <option value="in_progress">In Progress</option>
                </select>
              </div>

              <div>
                <p className="text-xs text-dark-500 font-medium uppercase">Scanner</p>
                <p className="text-sm font-semibold text-dark-900 dark:text-dark-50 capitalize mt-1">
                  {finding.scanner}
                </p>
              </div>

              <div>
                <p className="text-xs text-dark-500 font-medium uppercase">Rule ID</p>
                <p className="text-sm font-mono text-dark-900 dark:text-dark-50 mt-1">
                  {finding.rule_id}
                </p>
              </div>

              {finding.cwe_id && (
                <div>
                  <p className="text-xs text-dark-500 font-medium uppercase">CWE</p>
                  <p className="text-sm text-primary-600 dark:text-primary-400 mt-1 font-mono">
                    {finding.cwe_id}
                  </p>
                </div>
              )}

              {finding.owasp_category && (
                <div>
                  <p className="text-xs text-dark-500 font-medium uppercase">OWASP Category</p>
                  <p className="text-sm text-dark-900 dark:text-dark-50 mt-1">
                    {finding.owasp_category}
                  </p>
                </div>
              )}

              <div>
                <p className="text-xs text-dark-500 font-medium uppercase">Discovered</p>
                <p className="text-sm text-dark-700 dark:text-dark-300 mt-1">
                  {formatRelativeTime(finding.created_at)}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default FindingDetailPage;
