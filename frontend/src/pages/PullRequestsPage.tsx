import { useEffect, useState } from 'react';
import { pullRequestsApi } from '../services/api';
import { PullRequest, PullRequestStatus } from '../types';
import { Card, CardContent, Badge, Button, LoadingSpinner } from '../components/ui';
import { GitPullRequest, MoreVertical, ExternalLink } from 'lucide-react';
import { cn, formatRelativeTime } from '../utils/cn';
import { Dropdown } from '../components/ui';
import toast from 'react-hot-toast';

export function PullRequestsPage() {
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPRs = async () => {
    try {
      const res = await pullRequestsApi.list({ page_size: 50 });
      setPrs(res.items || []);
    } catch (error) {
      toast.error('Failed to load pull requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPRs();
  }, []);

  const statusColors: Record<PullRequestStatus, string> = {
    draft: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
    open: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    merged: 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30',
    closed: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
    failed: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Pull Requests</h1>
        <p className="text-dark-500 mt-1">Security fix pull requests</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : prs.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <GitPullRequest className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No pull requests</h3>
            <p className="text-dark-500">Create pull requests from applied patches</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {prs.map((pr) => (
            <Card key={pr.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <Badge className={cn('text-xs', statusColors[pr.status])}>
                        {pr.status.toUpperCase()}
                      </Badge>
                      {pr.github_pr_number && (
                        <Badge variant="default" className="text-xs">#{pr.github_pr_number}</Badge>
                      )}
                    </div>
                    <p className="font-medium text-dark-900 dark:text-dark-50 truncate max-w-2xl">
                      {pr.title}
                    </p>
                    <div className="flex items-center gap-4 mt-2 text-sm text-dark-500">
                      <span>{pr.files_changed} files</span>
                      <span>+{pr.additions} -{pr.deletions}</span>
                      <span>{formatRelativeTime(pr.created_at)}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 shrink-0">
                    {pr.github_pr_id && (
                      <Button size="sm" variant="outline" asChild>
                        <a href={`https://github.com/pull/${pr.github_pr_id}`} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-3 w-3 mr-1" /> View on GitHub
                        </a>
                      </Button>
                    )}
                    <Dropdown
                      trigger={
                        <button className="p-1 rounded hover:bg-dark-100 dark:hover:bg-dark-700">
                          <MoreVertical className="h-5 w-5 text-dark-500" />
                        </button>
                      }
                      items={[
                        { label: 'Sync Status', onClick: () => pullRequestsApi.sync(pr.id), icon: <GitPullRequest className="h-4 w-4" /> },
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