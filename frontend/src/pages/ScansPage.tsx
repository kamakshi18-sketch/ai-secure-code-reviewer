import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { scansApi } from '../services/api';
import { Scan } from '../types';
import { Card, CardContent, Badge, Button, Input, Select, LoadingSpinner, Dropdown } from '../components/ui';
import { Search, RotateCcw, X, MoreVertical, ShieldAlert, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import { cn, formatRelativeTime, getStatusColor } from '../utils/cn';
import toast from 'react-hot-toast';

export function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchScans = async () => {
    try {
      setLoading(true);
      const res = await scansApi.list({ page_size: 50 });
      setScans(res.items || []);
    } catch {
      toast.error('Failed to load security scans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScans();
  }, []);

  const handleRetry = async (scanId: string) => {
    try {
      await scansApi.retry(scanId);
      toast.success('Scan restarted');
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

  const filteredScans = scans.filter((scan) => {
    const matchesStatus = !statusFilter || scan.status === statusFilter;
    const matchesSearch = !searchQuery || 
      (scan.branch && scan.branch.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (scan.commit_sha && scan.commit_sha.toLowerCase().includes(searchQuery.toLowerCase())) ||
      scan.scanners_used.some(s => s.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  const totalCompleted = scans.filter(s => s.status === 'completed').length;
  const totalRunning = scans.filter(s => s.status === 'running' || s.status === 'pending').length;
  const totalFailed = scans.filter(s => s.status === 'failed').length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Security Scans</h1>
          <p className="text-dark-500 mt-1">Audit runs and vulnerability scan histories across your repositories</p>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
              <Search className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-dark-500 font-medium">Total Scans</p>
              <p className="text-2xl font-bold text-dark-900 dark:text-dark-50">{scans.length}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-dark-500 font-medium">Completed</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">{totalCompleted}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-dark-500 font-medium">In Progress</p>
              <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{totalRunning}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-dark-500 font-medium">Failed</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{totalFailed}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Toolbar */}
      <Card>
        <CardContent className="p-4 flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="w-full md:w-80">
            <Input
              placeholder="Search branch, commit, scanner..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<Search className="h-4 w-4 text-dark-400" />}
            />
          </div>
          <div className="flex gap-3 w-full md:w-auto">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full md:w-44"
            >
              <option value="">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="running">Running</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </Select>
            <Button variant="outline" onClick={fetchScans} disabled={loading}>
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Scans List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : filteredScans.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <ShieldAlert className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No scans found</h3>
            <p className="text-dark-500 mb-6">
              {statusFilter || searchQuery ? 'No scans matched your search criteria.' : 'Start a security scan from your repositories page.'}
            </p>
            <Button asChild>
              <Link to="/repositories">Go to Repositories</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredScans.map((scan) => (
            <Card key={scan.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <Badge className={cn('text-xs capitalize', getStatusColor(scan.status))}>
                        {scan.status}
                      </Badge>
                      <Badge variant="default" className="text-xs uppercase">{scan.scan_type}</Badge>
                      {scan.branch && (
                        <span className="text-xs font-mono bg-dark-100 dark:bg-dark-800 px-2 py-0.5 rounded text-dark-600 dark:text-dark-300">
                          {scan.branch}
                        </span>
                      )}
                      {scan.commit_sha && (
                        <span className="text-xs font-mono text-dark-400">
                          {scan.commit_sha.slice(0, 7)}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 flex-wrap">
                      <Link 
                        to={`/scans/${scan.id}`} 
                        className="font-medium text-dark-900 dark:text-dark-50 hover:text-primary-600"
                      >
                        Scan #{scan.id.slice(0, 8)}
                      </Link>
                      <span className="text-sm text-dark-400">•</span>
                      <span className="text-sm text-dark-500">
                        {scan.scanners_used.join(', ') || 'Default Scanners'}
                      </span>
                    </div>

                    {scan.status === 'completed' && (
                      <div className="flex items-center gap-3 mt-2 text-xs flex-wrap">
                        <span className="text-red-600 dark:text-red-400 font-medium">
                          {scan.critical_count} Critical
                        </span>
                        <span className="text-orange-600 dark:text-orange-400 font-medium">
                          {scan.high_count} High
                        </span>
                        <span className="text-yellow-600 dark:text-yellow-400 font-medium">
                          {scan.medium_count} Medium
                        </span>
                        <span className="text-blue-600 dark:text-blue-400 font-medium">
                          {scan.low_count} Low
                        </span>
                        <span className="text-dark-400">
                          ({scan.total_findings} total findings)
                        </span>
                      </div>
                    )}

                    {scan.error_message && (
                      <p className="text-xs text-red-500 mt-2 truncate">
                        {scan.error_message}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-3 shrink-0 self-end lg:self-center">
                    <span className="text-xs text-dark-400">
                      {formatRelativeTime(scan.created_at)}
                    </span>
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/scans/${scan.id}`}>View</Link>
                    </Button>
                    <Dropdown
                      trigger={
                        <button className="p-1 rounded hover:bg-dark-100 dark:hover:bg-dark-700">
                          <MoreVertical className="h-4 w-4 text-dark-500" />
                        </button>
                      }
                      items={[
                        { label: 'View Details', onClick: () => {}, icon: <Search className="h-4 w-4" /> },
                        ...(scan.status === 'running' ? [
                          { label: 'Cancel Scan', onClick: () => handleCancel(scan.id), icon: <X className="h-4 w-4 text-red-500" /> }
                        ] : [
                          { label: 'Retry Scan', onClick: () => handleRetry(scan.id), icon: <RotateCcw className="h-4 w-4" /> }
                        ]),
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
