import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { scansApi, findingsApi } from '../services/api';
import { Scan, Finding } from '../types';
import { Card, CardContent, CardHeader, CardTitle, Button, LoadingSpinner } from '../components/ui';
import { 
  ArrowLeft, 
  GitBranch, 
  RefreshCw,
  XOctagon
} from 'lucide-react';
import { cn, getSeverityColor, getStatusColor } from '../utils/cn';
import toast from 'react-hot-toast';

export function ScanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [scan, setScan] = useState<Scan | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchScanData = async () => {
    if (!id) return;
    try {
      const [scanData, findingsData] = await Promise.all([
        scansApi.get(id),
        findingsApi.list({ scan_id: id, page_size: 100 }),
      ]);
      setScan(scanData);
      setFindings(findingsData.items || []);
    } catch (error) {
      toast.error('Failed to load scan details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScanData();
  }, [id]);

  const handleRetry = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      const newScan: any = await scansApi.retry(id);
      toast.success('Scan retry started');
      navigate(`/scans/${newScan.id}`);
    } catch (error) {
      toast.error('Failed to retry scan');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!id) return;
    setActionLoading(true);
    try {
      await scansApi.cancel(id);
      toast.success('Scan cancelled');
      fetchScanData();
    } catch (error) {
      toast.error('Failed to cancel scan');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-dark-900 dark:text-dark-50">Scan not found</h2>
        <Button className="mt-4" onClick={() => navigate('/dashboard')}>Back to Dashboard</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to={`/repositories/${scan.repository_id}`}
            className="p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-700 text-dark-600 dark:text-dark-400"
            aria-label="Back to repository"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-dark-900 dark:text-dark-50">
                Scan Details
              </h1>
              <span className={cn('badge uppercase text-xs', getStatusColor(scan.status))}>
                {scan.status}
              </span>
            </div>
            <p className="text-sm text-dark-500 mt-1">ID: {scan.id}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {['pending', 'running'].includes(scan.status) && (
            <Button variant="destructive" size="sm" onClick={handleCancel} disabled={actionLoading}>
              <XOctagon className="h-4 w-4 mr-2" />
              Cancel Scan
            </Button>
          )}
          {['failed', 'cancelled', 'completed'].includes(scan.status) && (
            <Button variant="outline" size="sm" onClick={handleRetry} disabled={actionLoading}>
              <RefreshCw className={cn('h-4 w-4 mr-2', actionLoading && 'animate-spin')} />
              Retry Scan
            </Button>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-dark-500 font-medium uppercase">Type</p>
            <p className="text-lg font-semibold text-dark-900 dark:text-dark-50 capitalize mt-1">
              {scan.scan_type}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-dark-500 font-medium uppercase">Branch</p>
            <p className="text-lg font-semibold text-dark-900 dark:text-dark-50 mt-1 flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-dark-400" />
              {scan.branch || 'default'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-dark-500 font-medium uppercase">Total Findings</p>
            <p className="text-lg font-semibold text-dark-900 dark:text-dark-50 mt-1">
              {scan.total_findings}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-dark-500 font-medium uppercase">Duration</p>
            <p className="text-lg font-semibold text-dark-900 dark:text-dark-50 mt-1">
              {scan.duration_seconds ? `${scan.duration_seconds.toFixed(1)}s` : 'In progress'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Severity Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Severity Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-4 text-center">
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20">
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{scan.critical_count}</p>
              <p className="text-xs font-medium text-red-700 dark:text-red-300">Critical</p>
            </div>
            <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20">
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">{scan.high_count}</p>
              <p className="text-xs font-medium text-orange-700 dark:text-orange-300">High</p>
            </div>
            <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
              <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{scan.medium_count}</p>
              <p className="text-xs font-medium text-yellow-700 dark:text-yellow-300">Medium</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{scan.low_count}</p>
              <p className="text-xs font-medium text-blue-700 dark:text-blue-300">Low</p>
            </div>
            <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
              <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">{scan.info_count}</p>
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Info</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Findings Table */}
      <Card>
        <CardHeader>
          <CardTitle>Findings ({findings.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {findings.length === 0 ? (
            <div className="text-center py-8 text-dark-500">
              No findings identified for this scan.
            </div>
          ) : (
            <div className="divide-y divide-dark-200 dark:divide-dark-700">
              {findings.map((f) => (
                <div key={f.id} className="py-4 flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={cn('badge text-xs uppercase', getSeverityColor(f.severity))}>
                        {f.severity}
                      </span>
                      <Link
                        to={`/findings/${f.id}`}
                        className="font-medium text-dark-900 dark:text-dark-50 hover:text-primary-600"
                      >
                        {f.rule_name || f.rule_id}
                      </Link>
                    </div>
                    <p className="text-xs text-dark-500 font-mono">
                      {f.file_path}:{f.line_start}
                    </p>
                  </div>
                  <Link to={`/findings/${f.id}`}>
                    <Button variant="outline" size="sm">View</Button>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default ScanDetailPage;
