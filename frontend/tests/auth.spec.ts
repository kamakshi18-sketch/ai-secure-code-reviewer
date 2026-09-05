import { test, expect } from './fixtures';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Sign in');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Invalid email address')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });

  test('should show error for invalid email format', async ({ page }) => {
    await page.fill('input[type="email"]', 'invalid-email');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Invalid email address')).toBeVisible();
  });

  test('should toggle password visibility', async ({ page }) => {
    await page.fill('input[type="password"]', 'password123');
    await expect(page.locator('input[type="password"]')).toBeVisible();
    
    await page.click('button[aria-label="Toggle password visibility"]');
    await expect(page.locator('input[type="text"]')).toBeVisible();
    
    await page.click('button[aria-label="Toggle password visibility"]');
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('should navigate to register page', async ({ page }) => {
    await page.click('text=Sign up');
    await expect(page).toHaveURL(/.*register/);
    await expect(page.locator('h1')).toContainText('Create Account');
  });
});

test.describe('Registration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register');
  });

  test('should display registration form', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Create Account');
    await expect(page.locator('input[type="text"]')).toBeVisible(); // Full name
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('select')).toBeVisible(); // Role select
  });

  test('should validate password length', async ({ page }) => {
    await page.fill('input[placeholder="John Doe"]', 'Test User');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'short');
    await page.fill('input[placeholder="••••••••"] >> nth=1', 'short');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Password must be at least 8 characters')).toBeVisible();
  });

  test('should validate password match', async ({ page }) => {
    await page.fill('input[placeholder="John Doe"]', 'Test User');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'Password123!');
    await page.fill('input[placeholder="••••••••"] >> nth=1', 'DifferentPass123!');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Passwords do not match')).toBeVisible();
  });

  test('should navigate to login page', async ({ page }) => {
    await page.click('text=Sign in');
    await expect(page).toHaveURL(/.*login/);
  });
});

test.describe('Protected Routes', () => {
  test('should redirect to login when accessing dashboard without auth', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/.*login/);
  });

  test('should redirect to login when accessing repositories without auth', async ({ page }) => {
    await page.goto('/repositories');
    await expect(page).toHaveURL(/.*login/);
  });

  test('should redirect to login when accessing findings without auth', async ({ page }) => {
    await page.goto('/findings');
    await expect(page).toHaveURL(/.*login/);
  });
});