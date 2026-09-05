import { forwardRef, useState, useEffect, useRef } from 'react';
import { cn } from '../../utils/cn';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive' | string;
  size?: 'sm' | 'md' | 'lg' | 'icon' | string;
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', asChild = false, disabled, children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';

    const variants: Record<string, string> = {
      primary: 'bg-primary-600 text-white hover:bg-primary-700',
      secondary: 'bg-dark-100 text-dark-900 hover:bg-dark-200 dark:bg-dark-800 dark:text-dark-50 dark:hover:bg-dark-700',
      outline: 'border border-dark-300 bg-transparent hover:bg-dark-100 dark:border-dark-600 dark:hover:bg-dark-800',
      ghost: 'bg-transparent hover:bg-dark-100 dark:hover:bg-dark-800',
      destructive: 'bg-red-600 text-white hover:bg-red-700',
    };

    const sizes: Record<string, string> = {
      sm: 'px-3 py-1.5 text-xs',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
      icon: 'p-2',
    };

    const classes = cn(baseStyles, variants[variant] || variants.primary, sizes[size] || sizes.md, className);

    if (asChild && children && typeof children === 'object' && 'type' in (children as any)) {
      const child = children as React.ReactElement<any>;
      const { className: childClassName, ...childProps } = child.props || {};
      return (
        <>
          {Object.assign({}, child, {
            props: { ...childProps, className: cn(classes, childClassName), ref },
          })}
        </>
      );
    }

    return (
      <button
        ref={ref}
        className={classes}
        disabled={disabled}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helperText, leftIcon, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && <label className="label mb-1.5 block">{label}</label>}
        <div className="relative flex items-center">
          {leftIcon && <div className="absolute left-3 text-dark-400 pointer-events-none">{leftIcon}</div>}
          <input
            ref={ref}
            className={cn('input', leftIcon && 'pl-10', error && 'border-red-500 focus:ring-red-500', className)}
            {...props}
          />
        </div>
        {error && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>}
        {helperText && !error && <p className="mt-1 text-xs text-dark-500">{helperText}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && <label className="label mb-1.5 block">{label}</label>}
        <textarea
          ref={ref}
          className={cn('input min-h-[100px] resize-y', error && 'border-red-500 focus:ring-red-500', className)}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>}
        {helperText && !error && <p className="mt-1 text-xs text-dark-500">{helperText}</p>}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  options?: SelectOption[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, helperText, options = [], children, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && <label className="label mb-1.5 block">{label}</label>}
        <select
          ref={ref}
          className={cn('input', error && 'border-red-500 focus:ring-red-500', className)}
          {...props}
        >
          {options.length > 0
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        {error && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>}
        {helperText && !error && <p className="mt-1 text-xs text-dark-500">{helperText}</p>}
      </div>
    );
  }
);

Select.displayName = 'Select';

export const Label = ({ className, children, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) => {
  return (
    <label className={cn('label', className)} {...props}>
      {children}
    </label>
  );
};

export const Card = ({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <div className={cn('card', className)} {...props}>
      {children}
    </div>
  );
};

export const CardHeader = ({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <div className={cn('px-6 py-4 border-b border-dark-200 dark:border-dark-700', className)} {...props}>
      {children}
    </div>
  );
};

export const CardTitle = ({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => {
  return (
    <h3 className={cn('text-lg font-semibold text-dark-900 dark:text-dark-50', className)} {...props}>
      {children}
    </h3>
  );
};

export const CardContent = ({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <div className={cn('p-6', className)} {...props}>
      {children}
    </div>
  );
};

export const CardFooter = ({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <div className={cn('px-6 py-4 border-t border-dark-200 dark:border-dark-700', className)} {...props}>
      {children}
    </div>
  );
};

export const Badge = ({ className, variant = 'default', children, ...props }: React.HTMLAttributes<HTMLSpanElement> & { variant?: 'default' | 'critical' | 'high' | 'medium' | 'low' | 'info' }) => {
  const variants = {
    default: 'bg-dark-100 text-dark-700 dark:bg-dark-700 dark:text-dark-300',
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    info: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400',
  };
  
  return (
    <span className={cn('badge', variants[variant], className)} {...props}>
      {children}
    </span>
  );
};

export const LoadingSpinner = ({ size = 'md', className }: { size?: 'sm' | 'md' | 'lg'; className?: string }) => {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  };
  
  return (
    <svg
      className={cn('animate-spin text-primary-600', sizes[size], className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
};

export const Avatar = ({ className, src, alt, name, size = 'md' }: { 
  className?: string; 
  src?: string; 
  alt?: string; 
  name?: string; 
  size?: 'sm' | 'md' | 'lg' | 'xl';
}) => {
  const sizes = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-12 w-12 text-base',
    xl: 'h-16 w-16 text-lg',
  };
  
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };
  
  const getColor = (name: string) => {
    const colors = [
      'bg-red-500', 'bg-orange-500', 'bg-amber-500', 'bg-green-500',
      'bg-emerald-500', 'bg-teal-500', 'bg-cyan-500', 'bg-blue-500',
      'bg-indigo-500', 'bg-violet-500', 'bg-purple-500', 'bg-fuchsia-500',
    ];
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };
  
  if (src) {
    return (
      <img
        src={src}
        alt={alt || name || 'Avatar'}
        className={cn('rounded-full object-cover', sizes[size], className)}
      />
    );
  }
  
  return (
    <div
      className={cn('rounded-full flex items-center justify-center font-medium text-white', sizes[size], getColor(name || ''), className)}
      aria-label={name || 'User avatar'}
    >
      {name ? getInitials(name) : '?'}
    </div>
  );
};

export const Dropdown = ({ 
  trigger, 
  items, 
  align = 'end' 
}: { 
  trigger: React.ReactNode; 
  items: Array<{ label: string; onClick: () => void; icon?: React.ReactNode; danger?: boolean; disabled?: boolean }>;
  align?: 'start' | 'end';
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  return (
    <div className="relative" ref={ref}>
      <div onClick={() => setOpen(!open)}>{trigger}</div>
      
      {open && (
        <div
          className={cn(
            'absolute z-50 mt-2 min-w-[160px] rounded-lg border border-dark-200 bg-white py-1 shadow-lg dark:border-dark-700 dark:bg-dark-800',
            align === 'end' ? 'right-0' : 'left-0'
          )}
        >
          {items.map((item, index) => (
            <button
              key={index}
              disabled={item.disabled}
              onClick={() => { if (!item.disabled) { item.onClick(); setOpen(false); } }}
              className={cn(
                'w-full px-4 py-2 text-left text-sm flex items-center gap-2',
                item.danger ? 'text-red-600 dark:text-red-400' : 'text-dark-700 dark:text-dark-300',
                item.disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-dark-100 dark:hover:bg-dark-700'
              )}
            >
              {item.icon && <span>{item.icon}</span>}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};