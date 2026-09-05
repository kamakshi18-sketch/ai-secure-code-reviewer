import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Badge } from '../components/ui';
import { User, Lock, Key, Save, Loader2, Bell, Shield } from 'lucide-react';
import toast from 'react-hot-toast';

const profileSchema = z.object({
  full_name: z.string().min(1, 'Full name is required'),
  email: z.string().email('Invalid email address'),
});

const passwordSchema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: z.string().min(8, 'New password must be at least 8 characters'),
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

type ProfileForm = z.infer<typeof profileSchema>;
type PasswordForm = z.infer<typeof passwordSchema>;

export function SettingsPage() {
  const { user, updateUser } = useAuth();
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'notifications'>('profile');
  const [saving, setSaving] = useState(false);

  const profileForm = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user?.full_name || '',
      email: user?.email || '',
    },
  });

  const passwordForm = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  const handleProfileSubmit = async (data: ProfileForm) => {
    setSaving(true);
    try {
      await updateUser(data);
      toast.success('Profile updated successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordSubmit = async (data: PasswordForm) => {
    setSaving(true);
    try {
      await authApi.changePassword(data.current_password, data.new_password);
      toast.success('Password changed successfully');
      passwordForm.reset();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold text-dark-900 dark:text-dark-50">Settings</h1>
        <p className="text-dark-500 mt-1">Manage your account settings</p>
      </div>

      <div className="flex gap-4 border-b border-dark-200 dark:border-dark-700">
        {[
          { id: 'profile', label: 'Profile', icon: User },
          { id: 'security', label: 'Security', icon: Shield },
          { id: 'notifications', label: 'Notifications', icon: Bell },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as any)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === id
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-dark-500 hover:text-dark-700 dark:hover:text-dark-300'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'profile' && (
        <Card>
          <CardHeader>
            <CardTitle>Profile Information</CardTitle>
          </CardHeader>
          <form onSubmit={profileForm.handleSubmit(handleProfileSubmit)} className="p-6 space-y-4">
            <Input
              label="Full Name"
              {...profileForm.register('full_name')}
              error={profileForm.formState.errors.full_name?.message}
            />
            <Input
              label="Email"
              type="email"
              {...profileForm.register('email')}
              error={profileForm.formState.errors.email?.message}
            />
            <div className="flex items-center gap-2 text-sm text-dark-500">
              <Badge variant="default">{user?.role?.replace('_', ' ')}</Badge>
              <span>Role (cannot be changed)</span>
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4 mr-2" />} Save Changes
            </Button>
          </form>
        </Card>
      )}

      {activeTab === 'security' && (
        <Card>
          <CardHeader>
            <CardTitle>Change Password</CardTitle>
          </CardHeader>
          <form onSubmit={passwordForm.handleSubmit(handlePasswordSubmit)} className="p-6 space-y-4">
            <Input
              label="Current Password"
              type="password"
              {...passwordForm.register('current_password')}
              error={passwordForm.formState.errors.current_password?.message}
              leftIcon={<Lock className="h-4 w-4 text-dark-400" />}
            />
            <Input
              label="New Password"
              type="password"
              {...passwordForm.register('new_password')}
              error={passwordForm.formState.errors.new_password?.message}
              leftIcon={<Lock className="h-4 w-4 text-dark-400" />}
              helperText="At least 8 characters"
            />
            <Input
              label="Confirm New Password"
              type="password"
              {...passwordForm.register('confirm_password')}
              error={passwordForm.formState.errors.confirm_password?.message}
              leftIcon={<Lock className="h-4 w-4 text-dark-400" />}
            />
            <Button type="submit" disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4 mr-2" />} Change Password
            </Button>
          </form>
        </Card>
      )}

      {activeTab === 'notifications' && (
        <Card>
          <CardHeader>
            <CardTitle>Notification Preferences</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-dark-500">Notification settings coming soon.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}