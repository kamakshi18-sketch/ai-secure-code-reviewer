import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  LayoutDashboard, 
  GitBranch, 
  Search, 
  AlertTriangle, 
  FileText, 
  GitPullRequest, 
  MessageSquare, 
  Settings,
  LogOut,
  Menu,
  X,
  ChevronDown,
  User,
  Shield,
  Github,
} from 'lucide-react';
import { Avatar, Dropdown } from './ui';
import { useState } from 'react';
import { cn } from '../utils/cn';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Repositories', href: '/repositories', icon: GitBranch },
  { name: 'Scans', href: '/scans', icon: Search },
  { name: 'Findings', href: '/findings', icon: AlertTriangle },
  { name: 'Patches', href: '/patches', icon: FileText },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Pull Requests', href: '/pull-requests', icon: GitPullRequest },
  { name: 'Chat Assistant', href: '/chat', icon: MessageSquare },
  { name: 'GitHub', href: '/github', icon: Github },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  
  const handleLogout = async () => {
    await logout();
    setUserMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-dark-50 dark:bg-dark-900">
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-dark-800 border-r border-dark-200 dark:border-dark-700 transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        aria-label="Sidebar"
      >
        <div className="flex h-16 items-center justify-between px-6 border-b border-dark-200 dark:border-dark-700">
          <h1 className="text-xl font-bold text-primary-600">AI Code Reviewer</h1>
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-700"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        
        <nav className="flex-1 overflow-y-auto p-4 space-y-1" aria-label="Main navigation">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href || 
              (item.href !== '/dashboard' && location.pathname.startsWith(item.href));
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                    : 'text-dark-600 hover:bg-dark-100 dark:text-dark-400 dark:hover:bg-dark-700'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <item.icon className="h-5 w-5" aria-hidden="true" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>
        
        <div className="p-4 border-t border-dark-200 dark:border-dark-700">
          <p className="text-xs font-medium text-dark-500 dark:text-dark-400 uppercase tracking-wider mb-2">
            Security Status
          </p>
          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20">
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">0</p>
              <p className="text-xs text-red-700 dark:text-red-400">Critical</p>
            </div>
            <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20">
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">0</p>
              <p className="text-xs text-orange-700 dark:text-orange-400">High</p>
            </div>
            <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
              <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">0</p>
              <p className="text-xs text-yellow-700 dark:text-yellow-400">Medium</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">0</p>
              <p className="text-xs text-blue-700 dark:text-blue-400">Low</p>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-40 h-16 bg-white/80 dark:bg-dark-800/80 backdrop-blur-sm border-b border-dark-200 dark:border-dark-700">
          <div className="flex h-full items-center justify-between px-4 sm:px-6">
            <button
              className="lg:hidden p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-700"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu className="h-6 w-6" />
            </button>
            
            <div className="flex-1 lg:flex-none" />
            
            <div className="flex items-center gap-4">
              <Dropdown
                trigger={
                  <button className="flex items-center gap-2 p-1 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-700" onClick={() => setUserMenuOpen(!userMenuOpen)}>
                    <Avatar name={user?.full_name} size="md" />
                    <span className="hidden sm:block text-sm font-medium text-dark-700 dark:text-dark-300">
                      {user?.full_name}
                    </span>
                    <ChevronDown className="h-4 w-4 text-dark-500" />
                  </button>
                }
                items={[
                  { label: 'Profile', onClick: () => {}, icon: <User className="h-4 w-4" /> },
                  { label: 'Security Settings', onClick: () => {}, icon: <Shield className="h-4 w-4" /> },
                  { label: 'Logout', onClick: handleLogout, icon: <LogOut className="h-4 w-4" />, danger: true },
                ]}
              />
            </div>
          </div>
        </header>
        
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
      
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}
    </div>
  );
}