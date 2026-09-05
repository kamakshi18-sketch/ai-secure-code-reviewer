import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateString);
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function getSeverityColor(severity: string): string {
  const colors = {
    critical: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
    high: 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30',
    medium: 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
    low: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    info: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
  };
  return colors[severity as keyof typeof colors] || colors.info;
}

export function getStatusColor(status: string): string {
  const colors = {
    pending: 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
    running: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    completed: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    failed: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
    cancelled: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
    open: 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30',
    fixed: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    false_positive: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
    wont_fix: 'text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30',
    ignored: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
    in_progress: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    generating: 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30',
    generated: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    applying: 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30',
    applied: 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30',
    rejected: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
    draft: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
    merged: 'text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30',
    closed: 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800',
  };
  return colors[status as keyof typeof colors] || colors.pending;
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}