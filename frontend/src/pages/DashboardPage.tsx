import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  GitBranch, 
  Search, 
  AlertTriangle, 
  GitPullRequest,
  Clock,
  CheckCircle,
  XCircle,
  Plus,
  Loader2,
} from 'lucide-react';
import { repositoriesApi, scansApi, findingsApi } from '../services/api';
import { Repository, Scan } from '../types';
import { Card, CardContent, CardHeader, CardTitle, Badge, Button, LoadingSpinner } from '../components/ui';
import { formatRelativeTime, getStatusColor, cn } from '../utils/cn';
import toast from 'react-hot-toast';

interface FindingsStats {
  total: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
}

export function DashboardPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [recentScans, setRecentScans] = useState<Scan[]>([]);
  const [findingsStats, setFindingsStats] = useState<FindingsStats>({ total: 0, by_severity: {}, by_status: {} });
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [reposRes, scansRes, statsRes] = await Promise.all([
        repositoriesApi.list({ page_size: 5 }),
        scansApi.list({ page_size: 10 }),
        findingsApi.stats(),
      ]);
      setRepositories(reposRes.items || []);
      setRecentScans(scansRes.items || []);
      setFindingsStats(statsRes);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const stats = [
    {
      name: 'Repositories',
      value: repositories.length,
      icon: GitBranch,
      color: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
      href: '/repositories',
    },
    {
      name: 'Total Scans',
      value: recentScans.length,
      icon: Search,
      color: 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30',
      href: '/scans',
    },
    {
      name: 'Open Findings',
      value: (findingsStats.by_severity?.critical || 0) + (findingsStats.by_severity?.high || 0) + (findingsStats.by_severity?.medium || 0) + (findingsStats.by_severity?.low || 0),
      icon: AlertTriangle,
      color: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
      href: '/findings',
    },
    {
      name: 'Pull Requests',
      value: 0,
      icon: GitPullRequest,
      color: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
      href: '/pull-requests',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Dashboard</h1>
          <p className="text-dark-500 mt-1">Overview of your security posture</p>
        </div>
        <Button asChild>
          <Link to="/repositories">
            <Plus className="h-4 w-4 mr-2" /> Add Repository
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Link key={stat.name} to={stat.href} className="card hover:shadow-md transition-shadow">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-dark-500 dark:text-dark-400">{stat.name}</p>
                  <p className="text-3xl font-bold text-dark-900 dark:text-dark-50 mt-1">{stat.value}</p>
                </div>
                <div className={cn('p-3 rounded-xl', stat.color)}>
                  <stat.icon className="h-6 w-6" aria-hidden="true" />
                </div>
              </div>
            </CardContent>
          </Link>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Scans</CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link to="/scans">View all</Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentScans.length === 0 ? (
                <p className="text-dark-500 text-center py-8">No scans yet. Add a repository to get started.</p>
              ) : (
                recentScans.map((scan) => (
                  <Link key={scan.id} to={`/scans/${scan.id}`} className="flex items-center justify-between p-3 rounded-lg hover:bg-dark-50 dark:hover:bg-dark-800 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className={cn('p-2 rounded-lg', getStatusColor(scan.status))}>
                        {scan.status === 'completed' && <CheckCircle className="h-5 w-5" />}
                        {scan.status === 'running' && <Loader2 className="h-5 w-5 animate-spin" />}
                        {scan.status === 'failed' && <XCircle className="h-5 w-5" />}
                        {scan.status === 'pending' && <Clock className="h-5 w-5" />}
                      </div>
                      <div>
                        <p className="font-medium text-dark-900 dark:text-dark-50 truncate max-w-[200px]">
                          {scan.repository_id}
                        </p>
                        <p className="text-sm text-dark-500">
                          {scan.scan_type} • {formatRelativeTime(scan.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={scan.critical_count > 0 ? 'critical' : 'default'}>
                        {scan.critical_count} Critical
                      </Badge>
                      <Badge variant={scan.high_count > 0 ? 'high' : 'default'}>
                        {scan.high_count} High
                      </Badge>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Repositories</CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link to="/repositories">View all</Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {repositories.length === 0 ? (
                <p className="text-dark-500 text-center py-8">No repositories added yet.</p>
              ) : (
                repositories.map((repo) => (
                  <Link key={repo.id} to={`/repositories/${repo.id}`} className="flex items-center justify-between p-3 rounded-lg hover:bg-dark-50 dark:hover:bg-dark-800 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
                        <GitBranch className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                      </div>
                      <div>
                        <p className="font-medium text-dark-900 dark:text-dark-50 truncate max-w-[200px]">
                          {repo.full_name}
                        </p>
                        <p className="text-sm text-dark-500">
                          {repo.language || 'Unknown'} • {formatRelativeTime(repo.updated_at)}
                        </p>
                      </div>
                    </div>
                    <Badge variant={repo.status === 'cloned' ? 'default' : repo.status === 'failed' ? 'high' : 'info'}>
                      {repo.status}
                    </Badge>
                  </Link>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Finding Severity Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { key: 'critical', label: 'Critical', colorClass: 'text-red-600 dark:text-red-400' },
              { key: 'high', label: 'High', colorClass: 'text-orange-600 dark:text-orange-400' },
              { key: 'medium', label: 'Medium', colorClass: 'text-yellow-600 dark:text-yellow-400' },
              { key: 'low', label: 'Low', colorClass: 'text-blue-600 dark:text-blue-400' },
              { key: 'info', label: 'Info', colorClass: 'text-gray-600 dark:text-gray-400' },
            ].map(({ key, label, colorClass }) => (
              <div key={key} className="text-center p-4 rounded-lg bg-dark-50 dark:bg-dark-800">
                <p className={cn('text-3xl font-bold', colorClass)}>
                  {findingsStats.by_severity?.[key] || 0}
                </p>
                <p className="text-sm text-dark-500 mt-1">{label}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}