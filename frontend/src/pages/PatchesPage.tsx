import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { patchesApi } from '../services/api';
import { Patch, PatchStatus } from '../types';
import { Card, CardContent, Badge, Button, LoadingSpinner } from '../components/ui';
import { FileText, Play, RotateCcw } from 'lucide-react';
import { formatRelativeTime, cn } from '../utils/cn';
import toast from 'react-hot-toast';

export function PatchesPage() {
  const [patches, setPatches] = useState<Patch[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchPatches = async () => {
    try {
      const res = await patchesApi.list({ page_size: 50 });
      setPatches(res.items || []);
    } catch (error) {
      toast.error('Failed to load patches');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatches();
  }, []);

  const handleApply = async (patchId: string) => {
    try {
      await patchesApi.apply(patchId);
      toast.success('Patch application started');
      fetchPatches();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to apply patch');
    }
  };

  const handleRegenerate = async (patchId: string) => {
    try {
      await patchesApi.regenerate(patchId);
      toast.success('Patch regeneration started');
      fetchPatches();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to regenerate patch');
    }
  };

  const statusColors: Record<PatchStatus, string> = {
    pending: 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
    generating: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    generated: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    applying: 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
    applied: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    failed: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
    rejected: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Patches</h1>
        <p className="text-dark-500 mt-1">Generated security patches for vulnerabilities</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : patches.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No patches generated</h3>
            <p className="text-dark-500">Patches will appear here after running security scans</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {patches.map((patch) => (
            <Card key={patch.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <Badge className={cn('text-xs', statusColors[patch.status])}>
                        {patch.status.toUpperCase()}
                      </Badge>
                      <Badge variant="default" className="text-xs">{patch.language}</Badge>
                      <Badge variant="default" className="text-xs">{patch.llm_provider}/{patch.llm_model}</Badge>
                    </div>
                    <p className="font-medium text-dark-900 dark:text-dark-50 truncate max-w-2xl">
                      {patch.file_path}
                    </p>
                    <div className="flex items-center gap-4 mt-2 text-sm text-dark-500">
                      <span>Retry: {patch.retry_count}/3</span>
                      {patch.generation_time_ms && (
                        <span>Generated in {Math.round(patch.generation_time_ms / 1000)}s</span>
                      )}
                      <span>{formatRelativeTime(patch.created_at)}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 shrink-0">
                    {patch.status === 'generated' && (
                      <Button size="sm" onClick={() => handleApply(patch.id)}>
                        <Play className="h-3 w-3 mr-1" /> Apply
                      </Button>
                    )}
                    {(patch.status === 'failed' || patch.status === 'rejected') && patch.retry_count < 3 && (
                      <Button size="sm" variant="outline" onClick={() => handleRegenerate(patch.id)}>
                        <RotateCcw className="h-3 w-3 mr-1" /> Regenerate
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" asChild>
                      <Link to={`/patches/${patch.id}`}>
                        <FileText className="h-4 w-4" />
                      </Link>
                    </Button>
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