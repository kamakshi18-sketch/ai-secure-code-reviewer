import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/Tabs';
import { RepositoryDetail } from '../components/RepositoryDetail';
import { ScansList } from '../components/ScansList';

export function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (!id) navigate('/repositories');
  }, [id, navigate]);

  if (!id) {
    return null;
  }

  return (
    <div className="space-y-6">
      <RepositoryDetail repositoryId={id} />
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="scans">Scans</TabsTrigger>
          <TabsTrigger value="findings">Findings</TabsTrigger>
          <TabsTrigger value="patches">Patches</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview">
          <div className="py-4 text-center text-dark-500">
            Repository overview content
          </div>
        </TabsContent>
        
        <TabsContent value="scans">
          <ScansList repositoryId={id} />
        </TabsContent>
        
        <TabsContent value="findings">
          <div className="py-4 text-center text-dark-500">
            Findings for this repository
          </div>
        </TabsContent>
        
        <TabsContent value="patches">
          <div className="py-4 text-center text-dark-500">
            Patches for this repository
          </div>
        </TabsContent>
        
        <TabsContent value="reports">
          <div className="py-4 text-center text-dark-500">
            Reports for this repository
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}