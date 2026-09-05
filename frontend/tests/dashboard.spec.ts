import { test, expect } from './fixtures';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/dashboard');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display dashboard with stats cards', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('h1')).toContainText('Dashboard');
    await expect(authenticatedPage.locator('text=Repositories')).toBeVisible();
    await expect(authenticatedPage.locator('text=Total Scans')).toBeVisible();
    await expect(authenticatedPage.locator('text=Open Findings')).toBeVisible();
    await expect(authenticatedPage.locator('text=Pull Requests')).toBeVisible();
  });

  test('should display recent scans section', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Recent Scans')).toBeVisible();
  });

  test('should display recent repositories section', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Recent Repositories')).toBeVisible();
  });

  test('should display severity distribution', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Finding Severity Distribution')).toBeVisible();
    await expect(authenticatedPage.locator('text=Critical')).toBeVisible();
    await expect(authenticatedPage.locator('text=High')).toBeVisible();
    await expect(authenticatedPage.locator('text=Medium')).toBeVisible();
    await expect(authenticatedPage.locator('text=Low')).toBeVisible();
    await expect(authenticatedPage.locator('text=Info')).toBeVisible();
  });

  test('should have add repository button', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Add Repository')).toBeVisible();
  });
});

test.describe('Repositories Page', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/repositories');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display repositories list', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('h1')).toContainText('Repositories');
  });

  test('should show add repository button', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Add Repository')).toBeVisible();
  });

  test('should open add repository modal', async ({ authenticatedPage }) => {
    await authenticatedPage.click('text=Add Repository');
    await expect(authenticatedPage.locator('text=Add Repository')).toBeVisible();
    await expect(authenticatedPage.locator('input[placeholder*="github.com"]')).toBeVisible();
  });

  test('should close modal on cancel', async ({ authenticatedPage }) => {
    await authenticatedPage.click('text=Add Repository');
    await authenticatedPage.click('text=Cancel');
    await expect(authenticatedPage.locator('text=Add Repository')).not.toBeVisible();
  });

  test('should show empty state when no repositories', async ({ authenticatedPage, page }) => {
    // This test assumes no repositories exist for the test user
    await page.goto('/repositories');
    await expect(page.locator('text=No repositories yet')).toBeVisible();
  });

  test('should navigate to repository detail on click', async ({ authenticatedPage, testRepository }) => {
    await authenticatedPage.click(`text=${testRepository.full_name}`);
    await expect(authenticatedPage).toHaveURL(new RegExp(`/repositories/${testRepository.id}`));
  });
});

test.describe('Add Repository Flow', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/repositories');
  });

  test('should validate GitHub URL format', async ({ authenticatedPage }) => {
    await authenticatedPage.click('text=Add Repository');
    await authenticatedPage.fill('input[placeholder*="github.com"]', 'not-a-url');
    await authenticatedPage.click('text=Add Repository');
    await expect(authenticatedPage.locator('text=Invalid GitHub URL')).toBeVisible();
  });

  test('should validate GitHub domain', async ({ authenticatedPage }) => {
    await authenticatedPage.click('text=Add Repository');
    await authenticatedPage.fill('input[placeholder*="github.com"]', 'https://gitlab.com/user/repo');
    await authenticatedPage.click('text=Add Repository');
    await expect(authenticatedPage.locator('text=Must be a GitHub repository URL')).toBeVisible();
  });
});