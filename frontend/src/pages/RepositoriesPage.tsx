import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { 
  GitBranch, 
  Search, 
  Plus, 
  Loader2, 
  MoreVertical,
  Edit,
  Trash2,
  Play,
  Code,
} from 'lucide-react';
import { repositoriesApi } from '../services/api';
import { Repository } from '../types';
import { Card, CardContent, CardHeader, CardTitle, Badge, Button, Input, Dropdown, LoadingSpinner } from '../components/ui';
import { formatRelativeTime } from '../utils/cn';
import toast from 'react-hot-toast';

const createRepoSchema = z.object({
  github_url: z.string().url('Invalid GitHub URL').refine(
    (url) => url.includes('github.com/'),
    'Must be a GitHub repository URL'
  ),
  github_token: z.string().optional(),
});

type CreateRepoForm = z.infer<typeof createRepoSchema>;

export function RepositoriesPage() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CreateRepoForm>({
    resolver: zodResolver(createRepoSchema),
    defaultValues: { github_url: '', github_token: '' },
  });

  const fetchRepositories = async () => {
    try {
      const res = await repositoriesApi.list({ page_size: 50 });
      setRepositories(res.items || []);
    } catch (error) {
      toast.error('Failed to load repositories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  const onSubmit = async (data: CreateRepoForm) => {
    setCreating(true);
    try {
      await repositoriesApi.create(data);
      toast.success('Repository added successfully');
      setShowModal(false);
      reset();
      fetchRepositories();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add repository');
    } finally {
      setCreating(false);
    }
  };

  const handleClone = async (id: string) => {
    try {
      await repositoriesApi.clone(id);
      toast.success('Clone started');
      fetchRepositories();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to start clone');
    }
  };

  const handleDetectLanguage = async (id: string) => {
    try {
      await repositoriesApi.detectLanguage(id);
      toast.success('Language detection started');
      fetchRepositories();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to start language detection');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this repository?')) return;
    try {
      await repositoriesApi.delete(id);
      toast.success('Repository deleted');
      fetchRepositories();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete repository');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Repositories</h1>
          <p className="text-dark-500 mt-1">Manage your GitHub repositories</p>
        </div>
        <Button onClick={() => setShowModal(true)}>
          <Plus className="h-4 w-4 mr-2" /> Add Repository
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : repositories.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <GitBranch className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No repositories yet</h3>
            <p className="text-dark-500 mb-6">Add your first GitHub repository to start scanning</p>
            <Button onClick={() => setShowModal(true)}>
              <Plus className="h-4 w-4 mr-2" /> Add Repository
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {repositories.map((repo) => (
            <Card key={repo.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
                      <GitBranch className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div>
                      <Link to={`/repositories/${repo.id}`} className="font-medium text-dark-900 dark:text-dark-50 hover:text-primary-600">
                        {repo.full_name}
                      </Link>
                      <p className="text-sm text-dark-500">{repo.description || 'No description'}</p>
                    </div>
                  </div>
                  <Dropdown
                    trigger={
                      <button className="p-1 rounded hover:bg-dark-100 dark:hover:bg-dark-700">
                        <MoreVertical className="h-5 w-5 text-dark-500" />
                      </button>
                    }
                    items={[
                      { label: 'View Details', onClick: () => navigate(`/repositories/${repo.id}`), icon: <Search className="h-4 w-4" /> },
                      { label: 'Start Scan', onClick: () => navigate(`/repositories/${repo.id}?tab=scans`), icon: <Play className="h-4 w-4" /> },
                      { label: 'Clone', onClick: () => handleClone(repo.id), icon: <Code className="h-4 w-4" />, disabled: repo.status !== 'cloned' },
                      { label: 'Detect Language', onClick: () => handleDetectLanguage(repo.id), icon: <Edit className="h-4 w-4" />, disabled: repo.status !== 'cloned' },
                      { label: 'Delete', onClick: () => handleDelete(repo.id), icon: <Trash2 className="h-4 w-4" />, danger: true },
                    ]}
                  />
                </div>

                <div className="flex items-center justify-between text-sm text-dark-500 mb-4">
                  <span className="flex items-center gap-1">
                    {repo.language && (
                      <>
                        <span className="px-2 py-0.5 rounded bg-dark-100 dark:bg-dark-700">{repo.language}</span>
                      </>
                    )}
                    <span>Updated {formatRelativeTime(repo.updated_at)}</span>
                  </span>
                  <Badge variant={repo.status === 'cloned' ? 'default' : repo.status === 'failed' ? 'high' : repo.status === 'cloning' ? 'info' : 'default'}>
                    {repo.status}
                  </Badge>
                </div>

                <div className="flex items-center gap-2">
                  <Button asChild variant="outline" size="sm" className="flex-1">
                    <Link to={`/repositories/${repo.id}`}>View Details</Link>
                  </Button>
                  {repo.status === 'cloned' && (
                    <Button asChild variant="primary" size="sm">
                      <Link to={`/repositories/${repo.id}?tab=scans`}>
                        <Play className="h-3 w-3 mr-1" /> Scan
                      </Link>
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-md mx-4">
            <CardHeader>
              <CardTitle>Add Repository</CardTitle>
            </CardHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4">
              <Input
                label="GitHub Repository URL"
                placeholder="https://github.com/owner/repo"
                {...register('github_url')}
                error={errors.github_url?.message}
                disabled={creating}
              />
              <Input
                label="GitHub Token (Optional)"
                type="password"
                placeholder="For private repositories"
                {...register('github_token')}
                disabled={creating}
                helperText="Required for private repositories"
              />
              <div className="flex gap-2 pt-2">
                <Button type="button" variant="secondary" onClick={() => { setShowModal(false); reset(); }} className="flex-1">
                  Cancel
                </Button>
                <Button type="submit" disabled={creating} className="flex-1">
                  {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Add Repository'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}