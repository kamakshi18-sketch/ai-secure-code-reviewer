import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { findingsApi } from '../services/api';
import { Finding } from '../types';
import { Card, CardContent, Badge, Button, Input, Select, LoadingSpinner, Dropdown } from '../components/ui';
import { Search, AlertTriangle, MoreVertical } from 'lucide-react';
import { cn, formatRelativeTime, getSeverityColor, getStatusColor } from '../utils/cn';
import toast from 'react-hot-toast';

export function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    page: 1,
    page_size: 20,
    severity: '',
    status: '',
    scanner: '',
    search: '',
  });
  const [total, setTotal] = useState(0);
  const navigate = useNavigate();

  const fetchFindings = async () => {
    setLoading(true);
    try {
      const res = await findingsApi.list(filters);
      setFindings(res.items || []);
      setTotal(res.total || 0);
    } catch (error) {
      toast.error('Failed to load findings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFindings();
  }, [filters]);

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
  };

  const severityOptions = [
    { value: '', label: 'All Severities' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
    { value: 'info', label: 'Info' },
  ];

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'open', label: 'Open' },
    { value: 'fixed', label: 'Fixed' },
    { value: 'false_positive', label: 'False Positive' },
    { value: 'wont_fix', label: 'Won\'t Fix' },
    { value: 'ignored', label: 'Ignored' },
    { value: 'in_progress', label: 'In Progress' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Findings</h1>
          <p className="text-dark-500 mt-1">Security vulnerabilities discovered in your code</p>
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-dark-400" />
              <Input
                placeholder="Search findings..."
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={filters.severity}
              onChange={(e) => handleFilterChange('severity', e.target.value)}
              options={severityOptions}
              className="w-full sm:w-40"
            />
            <Select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              options={statusOptions}
              className="w-full sm:w-40"
            />
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : findings.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No findings</h3>
            <p className="text-dark-500">No security vulnerabilities found matching your criteria</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="space-y-3">
            {findings.map((finding) => (
              <Card key={finding.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <Badge 
                          className={cn('text-xs', getSeverityColor(finding.severity))}
                        >
                          {finding.severity.toUpperCase()}
                        </Badge>
                        <Badge 
                          className={cn('text-xs', getStatusColor(finding.status))}
                        >
                          {finding.status.replace('_', ' ').toUpperCase()}
                        </Badge>
                        <Badge variant="default" className="text-xs">{finding.scanner}</Badge>
                      </div>
                      <Link to={`/findings/${finding.id}`} className="font-medium text-dark-900 dark:text-dark-50 hover:text-primary-600 truncate block">
                        {finding.rule_name}
                      </Link>
                      <p className="text-sm text-dark-500 mt-1 truncate max-w-2xl">{finding.message}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm text-dark-500">
                        <span className="flex items-center gap-1">
                          <code className="bg-dark-100 dark:bg-dark-800 px-1.5 py-0.5 rounded text-xs">
                            {finding.file_path}
                          </code>
                          <span>:{finding.line_start}</span>
                        </span>
                        {finding.cwe_id && (
                          <span className="flex items-center gap-1">
                            CWE: <code className="bg-dark-100 dark:bg-dark-800 px-1.5 py-0.5 rounded text-xs">{finding.cwe_id}</code>
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          {formatRelativeTime(finding.created_at)}
                        </span>
                      </div>
                    </div>
                    
                    <Dropdown
                      trigger={
                        <button className="p-1 rounded hover:bg-dark-100 dark:hover:bg-dark-700 shrink-0">
                          <MoreVertical className="h-5 w-5 text-dark-500" />
                        </button>
                      }
                      items={[
                        { label: 'View Details', onClick: () => navigate(`/findings/${finding.id}`), icon: <Search className="h-4 w-4" /> },
                        { label: 'Explain with AI', onClick: () => findingsApi.explain(finding.id), icon: <AlertTriangle className="h-4 w-4" /> },
                      ]}
                    />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {total > filters.page_size && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-dark-500">
                Showing {((filters.page - 1) * filters.page_size) + 1} to {Math.min(filters.page * filters.page_size, total)} of {total} findings
              </p>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  disabled={filters.page === 1}
                  onClick={() => setFilters(prev => ({ ...prev, page: prev.page - 1 }))}
                >
                  Previous
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  disabled={filters.page * filters.page_size >= total}
                  onClick={() => setFilters(prev => ({ ...prev, page: prev.page + 1 }))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}