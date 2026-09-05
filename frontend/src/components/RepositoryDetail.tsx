import { useEffect, useState } from 'react';
import { repositoriesApi } from '../services/api';
import { Repository } from '../types';
import { Card, CardContent, CardHeader, CardTitle, Badge, LoadingSpinner } from './ui';
import { GitBranch, Globe, Lock, Code, Clock, Calendar } from 'lucide-react';
import { formatRelativeTime } from '../utils/cn';

export function RepositoryDetail({ repositoryId }: { repositoryId: string }) {
  const [repository, setRepository] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRepository = async () => {
      try {
        const data = await repositoriesApi.get(repositoryId);
        setRepository(data);
      } catch (error) {
        console.error('Failed to load repository:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRepository();
  }, [repositoryId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!repository) {
    return <div className="text-center text-red-500">Repository not found</div>;
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-primary-100 dark:bg-primary-900/30">
            <GitBranch className="h-8 w-8 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <CardTitle className="text-2xl">{repository.full_name}</CardTitle>
            <p className="text-dark-500">{repository.description || 'No description'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={repository.is_private ? 'high' : 'default'}>
            {repository.is_private ? 'Private' : 'Public'}
          </Badge>
          <Badge variant={repository.status === 'cloned' ? 'default' : repository.status === 'failed' ? 'high' : 'info'}>
            {repository.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="flex items-center gap-3 p-4 rounded-lg bg-dark-50 dark:bg-dark-800">
            <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <Globe className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-dark-500">URL</p>
              <p className="text-sm font-medium truncate max-w-[200px]">
                <a href={repository.url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
                  {repository.url}
                </a>
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 rounded-lg bg-dark-50 dark:bg-dark-800">
            <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
              <Code className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-sm text-dark-500">Language</p>
              <p className="text-sm font-medium">{repository.language || 'Not detected'}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 rounded-lg bg-dark-50 dark:bg-dark-800">
            <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <Lock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-dark-500">Default Branch</p>
              <p className="text-sm font-medium">{repository.default_branch}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 rounded-lg bg-dark-50 dark:bg-dark-800">
            <div className="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
              <Clock className="h-5 w-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <p className="text-sm text-dark-500">Last Scan</p>
              <p className="text-sm font-medium">
                {repository.last_scan_at ? formatRelativeTime(repository.last_scan_at) : 'Never'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 rounded-lg bg-dark-50 dark:bg-dark-800">
            <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/30">
              <Calendar className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <p className="text-sm text-dark-500">Created</p>
              <p className="text-sm font-medium">{formatRelativeTime(repository.created_at)}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 rounded-lg bg-dark-50 dark:bg-dark-800">
            <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800">
              <Calendar className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            </div>
            <div>
              <p className="text-sm text-dark-500">Updated</p>
              <p className="text-sm font-medium">{formatRelativeTime(repository.updated_at)}</p>
            </div>
          </div>
        </div>

        {repository.languages && repository.languages.length > 1 && (
          <div className="mt-6">
            <h4 className="text-sm font-medium text-dark-700 dark:text-dark-300 mb-2">All Languages</h4>
            <div className="flex flex-wrap gap-2">
              {repository.languages.map((lang) => (
                <Badge key={lang} variant="default">{lang}</Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}