import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, repositoriesApi } from '../services/api';
import { Button, Card, CardContent, Badge, Input, Tabs, TabsContent, TabsList, TabsTrigger, LoadingSpinner } from '../components/ui';
import { Github, Plus, Search, RefreshCw, ExternalLink, Loader2 } from 'lucide-react';
import { formatRelativeTime } from '../utils/cn';
import toast from 'react-hot-toast';

export function GitHubIntegrationPage() {
  const [installations, setInstallations] = useState<any[]>([]);
  const [repos, setRepos] = useState<any[]>([]);
  const [selectedInstallation, setSelectedInstallation] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [repoLoading, setRepoLoading] = useState(false);
  const [search, setSearch] = useState('');

  const fetchInstallations = async () => {
    try {
      setLoading(true);
      const res = await api.get<any[]>('/auth/github/installations');
      setInstallations(res || []);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to load installations');
    } finally {
      setLoading(false);
    }
  };

  const fetchRepositories = async (installationId: number) => {
    try {
      setRepoLoading(true);
      const res = await api.get<any[]>(`/auth/github/installations/${installationId}/repositories`);
      setRepos(res || []);
      setSelectedInstallation(installationId);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to load repositories');
    } finally {
      setRepoLoading(false);
    }
  };

  const addRepository = async (repoId: number) => {
    try {
      await repositoriesApi.create({
        github_url: `https://github.com/${repos.find(r => r.id === repoId)?.full_name}`,
        github_token: undefined,
      });
      toast.success('Repository added successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add repository');
    }
  };

  const handleConnectGitHub = async () => {
    try {
      const res = await api.get<{ auth_url: string }>('/auth/github/url');
      if (res?.auth_url) {
        window.location.href = res.auth_url;
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to get GitHub authorization URL');
    }
  };

  useEffect(() => {
    fetchInstallations();
  }, []);

  const filteredRepos = repos.filter(r => 
    r.full_name.toLowerCase().includes(search.toLowerCase()) ||
    r.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">GitHub Integration</h1>
          <p className="text-dark-500 mt-1">Connect your GitHub account and manage repositories</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchInstallations} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={handleConnectGitHub}>
            <Github className="h-4 w-4 mr-2" />
            Connect GitHub
          </Button>
        </div>
      </div>

      <Tabs defaultValue="installations" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="installations">Installations ({installations.length})</TabsTrigger>
          <TabsTrigger value="repositories">Repositories ({repos.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="installations">
          <div className="space-y-4 mt-6">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <LoadingSpinner size="lg" />
              </div>
            ) : installations.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Github className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No GitHub App installations</h3>
                  <p className="text-dark-500 mb-6">Install the GitHub App to access repositories</p>
                  <Button asChild>
                    <a href="https://github.com/apps" target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Browse GitHub Apps
                    </a>
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {installations.map(installation => (
                  <Card key={installation.id} className="hover:shadow-md transition-shadow">
                    <CardContent className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
                            <Github className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                          </div>
                          <div>
                            <p className="font-medium text-dark-900 dark:text-dark-50">
                              {installation.account?.login}
                            </p>
                            <p className="text-sm text-dark-500 capitalize">
                              {installation.account?.type}
                            </p>
                          </div>
                        </div>
                        <Badge variant={installation.repository_selection === 'all' ? 'default' : 'info'}>
                          {installation.repository_selection}
                        </Badge>
                      </div>
                      
                      <div className="flex items-center gap-2 text-sm text-dark-500 mb-4">
                        <span>Installed: {formatRelativeTime(installation.created_at)}</span>
                      </div>
                      
                      <Button 
                        className="w-full" 
                        onClick={() => fetchRepositories(installation.id)}
                        disabled={repoLoading}
                      >
                        {repoLoading && selectedInstallation === installation.id ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Search className="h-4 w-4 mr-2" />
                        )}
                        View Repositories
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="repositories">
          <div className="space-y-4 mt-6">
            {selectedInstallation ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium">Available Repositories</h3>
                  <Input
                    placeholder="Search repositories..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-64"
                    leftIcon={<Search className="h-4 w-4 text-dark-400" />}
                  />
                </div>
                
                {repoLoading ? (
                  <div className="flex items-center justify-center h-64">
                    <LoadingSpinner size="lg" />
                  </div>
                ) : filteredRepos.length === 0 ? (
                  <Card>
                    <CardContent className="py-12 text-center">
                      <Search className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No repositories found</h3>
                      <p className="text-dark-500">Try adjusting your search or installation</p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="space-y-3">
                    {filteredRepos.map(repo => (
                      <Card key={repo.id} className="hover:shadow-md transition-shadow">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
                                <Github className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                              </div>
                              <div>
                                <Link to={`/repositories/new?repo=${repo.full_name}`} className="font-medium text-dark-900 dark:text-dark-50 hover:text-primary-600">
                                  {repo.full_name}
                                </Link>
                                <p className="text-sm text-dark-500 flex items-center gap-2">
                                  {repo.language && <Badge variant="default" className="text-xs">{repo.language}</Badge>}
                                  <Badge variant={repo.private ? 'high' : 'default'} className="text-xs">
                                    {repo.private ? 'Private' : 'Public'}
                                  </Badge>
                                </p>
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <Button 
                                variant="outline" 
                                size="sm" 
                                asChild
                              >
                                <a href={repo.html_url} target="_blank" rel="noopener noreferrer">
                                  <ExternalLink className="h-3 w-3 mr-1" /> View
                                </a>
                              </Button>
                              <Button 
                                size="sm" 
                                onClick={() => addRepository(repo.id)}
                              >
                                <Plus className="h-3 w-3 mr-1" /> Add
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <Github className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">Select an installation</h3>
                  <p className="text-dark-500">Choose a GitHub App installation to view its repositories</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}