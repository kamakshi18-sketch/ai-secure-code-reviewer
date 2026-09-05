import { useEffect, useState } from 'react';
import { reportsApi } from '../services/api';
import { SecurityReport, ReportFormat } from '../types';
import { Card, CardContent, Button, LoadingSpinner } from '../components/ui';
import { FileText, Download, MoreVertical } from 'lucide-react';
import { formatRelativeTime } from '../utils/cn';
import { Dropdown } from '../components/ui';
import toast from 'react-hot-toast';

export function ReportsPage() {
  const [reports, setReports] = useState<SecurityReport[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    try {
      const res = await reportsApi.list({ page_size: 50 });
      setReports(res.items || []);
    } catch (error) {
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleDownload = async (reportId: string, format: ReportFormat) => {
    try {
      const res = await reportsApi.download(reportId);
      const blob = res instanceof Blob ? res : new Blob([res as any]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `security-report-${reportId}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Report downloaded');
    } catch (error) {
      toast.error('Failed to download report');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Reports</h1>
        <p className="text-dark-500 mt-1">Generated security reports</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : reports.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="h-16 w-16 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-dark-900 dark:text-dark-50 mb-2">No reports generated</h3>
            <p className="text-dark-500">Generate reports from scan results</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {reports.map((report) => (
            <Card key={report.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                      <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="font-medium text-dark-900 dark:text-dark-50">{report.title}</p>
                      <p className="text-sm text-dark-500">
                        {report.format.toUpperCase()} • Score: {report.security_score?.toFixed(1) || 'N/A'} • {formatRelativeTime(report.created_at)}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => handleDownload(report.id, report.format)}
                    >
                      <Download className="h-3 w-3 mr-1" /> Download
                    </Button>
                    <Dropdown
                      trigger={
                        <button className="p-1 rounded hover:bg-dark-100 dark:hover:bg-dark-700">
                          <MoreVertical className="h-5 w-5 text-dark-500" />
                        </button>
                      }
                      items={[
                        { label: 'View Report', onClick: () => {}, icon: <FileText className="h-4 w-4" /> },
                        { label: 'Download', onClick: () => handleDownload(report.id, report.format), icon: <Download className="h-4 w-4" /> },
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