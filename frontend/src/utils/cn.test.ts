import { describe, it, expect } from 'vitest';
import { cn, getSeverityColor, getStatusColor, truncate, formatBytes } from './cn';

describe('cn utility', () => {
  it('merges class names correctly', () => {
    expect(cn('btn', 'btn-primary')).toBe('btn btn-primary');
    expect(cn('p-4', { 'bg-red-500': true, 'bg-blue-500': false })).toBe('p-4 bg-red-500');
  });
});

describe('getSeverityColor', () => {
  it('returns proper colors for known severities', () => {
    expect(getSeverityColor('critical')).toContain('red');
    expect(getSeverityColor('high')).toContain('orange');
    expect(getSeverityColor('medium')).toContain('yellow');
    expect(getSeverityColor('low')).toContain('blue');
    expect(getSeverityColor('info')).toContain('gray');
  });

  it('handles unknown severity gracefully', () => {
    expect(getSeverityColor('unknown')).toContain('gray');
  });
});

describe('getStatusColor', () => {
  it('returns proper colors for known statuses', () => {
    expect(getStatusColor('completed')).toContain('green');
    expect(getStatusColor('running')).toContain('blue');
    expect(getStatusColor('failed')).toContain('red');
  });
});

describe('truncate', () => {
  it('truncates strings exceeding max length', () => {
    expect(truncate('Hello, world!', 5)).toBe('Hello...');
    expect(truncate('Hi', 5)).toBe('Hi');
  });
});

describe('formatBytes', () => {
  it('formats byte sizes accurately', () => {
    expect(formatBytes(0)).toBe('0 Bytes');
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(1048576)).toBe('1 MB');
  });
});
