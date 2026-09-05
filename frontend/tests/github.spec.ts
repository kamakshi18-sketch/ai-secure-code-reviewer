import { test, expect } from './fixtures';

test.describe('GitHub Integration', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/github');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display GitHub integration page', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('h1')).toContainText('GitHub Integration');
  });

  test('should show installations tab', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Installations')).toBeVisible();
    await expect(authenticatedPage.locator('text=Repositories')).toBeVisible();
  });

  test('should show connect GitHub button', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Connect GitHub')).toBeVisible();
  });

  test('should show refresh button', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Refresh')).toBeVisible();
  });
});

test.describe('Installations Tab', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/github');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should show empty state when no installations', async ({ page }) => {
    await page.goto('/github');
    await expect(page.locator('text=No GitHub App installations')).toBeVisible();
  });

  test('should show view repositories button for each installation', async ({ authenticatedPage }) => {
    // This test requires a GitHub App installation
  });

  test('should display installation details', async ({ authenticatedPage }) => {
    // Account login, repository selection, permissions
  });
});

test.describe('Repositories Tab', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/github');
    await authenticatedPage.click('text=Repositories');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should show repositories list', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Available Repositories')).toBeVisible();
  });

  test('should filter repositories by search', async ({ authenticatedPage }) => {
    await authenticatedPage.fill('input[placeholder*="Search repositories"]', 'test');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should show repository details', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Private')).toBeVisible();
    await expect(authenticatedPage.locator('text=Public')).toBeVisible();
  });

  test('should show add repository button', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Add')).toBeVisible();
  });

  test('should show view on GitHub link', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=View')).toBeVisible();
  });
});

test.describe('Repository Detail with GitHub', () => {
  test.beforeEach(async ({ authenticatedPage, testRepository }) => {
    await authenticatedPage.goto(`/repositories/${testRepository.id}`);
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should show GitHub information', async ({ authenticatedPage, testRepository }) => {
    await expect(authenticatedPage.locator(`text=${testRepository.url}`)).toBeVisible();
    await expect(authenticatedPage.locator(`text=${testRepository.default_branch}`)).toBeVisible();
  });

  test('should show scan button when cloned', async ({ authenticatedPage, testRepository }) => {
    if (testRepository.status === 'cloned') {
      await expect(authenticatedPage.locator('text=Scan')).toBeVisible();
    }
  });
});

test.describe('Pull Requests', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/pull-requests');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display pull requests page', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('h1')).toContainText('Pull Requests');
  });

  test('should show empty state when no PRs', async ({ page }) => {
    await page.goto('/pull-requests');
    await expect(page.locator('text=No pull requests')).toBeVisible();
  });

  test('should show PR cards with status', async ({ authenticatedPage }) => {
    // PR status badges: draft, open, merged, closed, failed
  });

  test('should show GitHub link for created PRs', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=View on GitHub')).toBeVisible();
  });

  test('should show sync button', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Sync Status')).toBeVisible();
  });
});

test.describe('Pull Request Detail', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    // Would need a test PR
  });

  test('should display PR details', async ({ authenticatedPage }) => {
    // Title, file changes, additions/deletions, status
  });
});