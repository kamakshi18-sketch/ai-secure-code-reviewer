import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { scansApi } from '../services/api';
import { Scan } from '../types';
import { Card, CardContent, CardTitle, Badge, Button, LoadingSpinner } from './ui';
import { Search, Play, RotateCcw, X, MoreVertical, Loader2 } from 'lucide-react';
import { cn, formatRelativeTime, getStatusColor } from '../utils/cn';
import { Dropdown } from './ui';
import toast from 'react-hot-toast';

export function ScansList({ repositoryId }: { repositoryId: string }) {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchScans = async () => {
    try {
      const res = await scansApi.list({ repository_id: repositoryId, page_size: 50 });
      setScans(res.items || []);
    } catch (error) {
      toast.error('Failed to load scans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScans();
  }, [repositoryId]);

  const handleRetry = async (scanId: string) => {
    try {
      await scansApi.retry(scanId);
      toast.success('Scan retry started');
      fetchScans();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to retry scan');
    }
  };

  const handleCancel = async (scanId: string) => {
    try {
      await scansApi.cancel(scanId);
      toast.success('Scan cancelled');
      fetchScans();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to cancel scan');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <CardTitle>Scans</CardTitle>
        <Button asChild>
          <Link to={`/repositories/${repositoryId}/scan/new`}>
            <Play className="h-4 w-4 mr-2" /> New Scan
          </Link>
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : scans.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No scans yet</h3>
            <p className="text-dark-500 mb-6">Start your first security scan</p>
            <Button asChild>
              <Link to={`/repositories/${repositoryId}/scan/new`}>
                <Play className="h-4 w-4 mr-2" /> New Scan
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {scans.map((scan) => (
            <Card key={scan.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={cn('p-2 rounded-lg', getStatusColor(scan.status))}>
                      {scan.status === 'completed' && <span className="text-green-600">✓</span>}
                      {scan.status === 'running' && <Loader2 className="h-5 w-5 animate-spin" />}
                      {scan.status === 'failed' && <X className="h-5 w-5 text-red-600" />}
                      {scan.status === 'pending' && <span className="text-yellow-600">⏳</span>}
                      {scan.status === 'cancelled' && <RotateCcw className="h-5 w-5 text-gray-600" />}
                    </div>
                    <div>
                      <Link to={`/scans/${scan.id}`} className="font-medium text-dark-900 dark:text-dark-50 hover:text-primary-600">
                        Scan #{scan.id.slice(0, 8)}
                      </Link>
                      <p className="text-sm text-dark-500 flex items-center gap-2">
                        <span>{scan.scan_type}</span>
                        <span>•</span>
                        <span>{scan.branch || 'main'}</span>
                        {scan.commit_sha && (
                          <>
                            <span>•</span>
                            <code className="text-xs bg-dark-100 dark:bg-dark-800 px-1 rounded">
                              {scan.commit_sha.slice(0, 8)}
                            </code>
                          </>
                        )}
                        <span>•</span>
                        <span>{formatRelativeTime(scan.created_at)}</span>
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Badge variant={scan.critical_count > 0 ? 'critical' : 'default'}>
                        {scan.critical_count} Critical
                      </Badge>
                      <Badge variant={scan.high_count > 0 ? 'high' : 'default'}>
                        {scan.high_count} High
                      </Badge>
                      <Badge variant={scan.medium_count > 0 ? 'medium' : 'default'}>
                        {scan.medium_count} Medium
                      </Badge>
                      <Badge variant={scan.low_count > 0 ? 'low' : 'default'}>
                        {scan.low_count} Low
                      </Badge>
                    </div>
                    
                    <Dropdown
                      trigger={
                        <button className="p-1 rounded hover:bg-dark-100 dark:hover:bg-dark-700">
                          <MoreVertical className="h-5 w-5 text-dark-500" />
                        </button>
                      }
                      items={[
                        { label: 'View Details', onClick: () => {}, icon: <Search className="h-4 w-4" /> },
                        { label: 'Retry', onClick: () => handleRetry(scan.id), icon: <RotateCcw className="h-4 w-4" />, disabled: scan.status !== 'failed' && scan.status !== 'completed' },
                        { label: 'Cancel', onClick: () => handleCancel(scan.id), icon: <X className="h-4 w-4" />, disabled: scan.status !== 'pending' && scan.status !== 'running' },
                      ]}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}