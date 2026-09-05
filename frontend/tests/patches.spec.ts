import { test, expect } from './fixtures';

test.describe('Patches', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/patches');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display patches page', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('h1')).toContainText('Patches');
  });

  test('should display empty state when no patches', async ({ page }) => {
    await page.goto('/patches');
    await expect(page.locator('text=No patches generated')).toBeVisible();
  });

  test('should show patch cards with status', async ({ authenticatedPage, testPatch }) => {
    await expect(authenticatedPage.locator(`text=${testPatch.status.toUpperCase()}`)).toBeVisible();
    await expect(authenticatedPage.locator(`text=${testPatch.file_path}`)).toBeVisible();
    await expect(authenticatedPage.locator(`text=${testPatch.language}`)).toBeVisible();
  });

  test('should show provider/model info', async ({ authenticatedPage, testPatch }) => {
    await expect(authenticatedPage.locator(`text=${testPatch.llm_provider}/${testPatch.llm_model}`)).toBeVisible();
  });

  test('should show retry count', async ({ authenticatedPage, testPatch }) => {
    await expect(authenticatedPage.locator(`text=Retry: ${testPatch.retry_count}/3`)).toBeVisible();
  });

  test('should show apply button for generated patches', async ({ authenticatedPage, testPatch }) => {
    if (testPatch.status === 'generated') {
      await expect(authenticatedPage.locator('text=Apply')).toBeVisible();
    }
  });

  test('should show regenerate button for failed patches', async ({ authenticatedPage }) => {
    // This would need a failed patch to test
  });

  test('should open patch detail on click', async ({ authenticatedPage, testPatch }) => {
    await authenticatedPage.click(`text=${testPatch.file_path}`);
    await expect(authenticatedPage).toHaveURL(new RegExp(`/patches/${testPatch.id}`));
  });
});

test.describe('Patch Detail', () => {
  test.beforeEach(async ({ authenticatedPage, testPatch }) => {
    await authenticatedPage.goto(`/patches/${testPatch.id}`);
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display patch detail page', async ({ authenticatedPage, testPatch }) => {
    await expect(authenticatedPage.locator(`text=${testPatch.file_path}`)).toBeVisible();
  });

  test('should display diff', async ({ authenticatedPage, testPatch }) => {
    await expect(authenticatedPage.locator('pre, code')).toBeVisible();
  });

  test('should show patch attempts', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Patch Attempts')).toBeVisible();
  });

  test('should show apply button', async ({ authenticatedPage, testPatch }) => {
    if (testPatch.status === 'generated') {
      await expect(authenticatedPage.locator('text=Apply')).toBeVisible();
    }
  });

  test('should show regenerate button for failed/rejected', async ({ authenticatedPage, testPatch }) => {
    if (testPatch.status === 'failed' || testPatch.status === 'rejected') {
      await expect(authenticatedPage.locator('text=Regenerate')).toBeVisible();
    }
  });
});

test.describe('Patch Actions', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/patches');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should apply patch', async ({ authenticatedPage, testPatch }) => {
    if (testPatch.status === 'generated') {
      await authenticatedPage.click('text=Apply');
      await expect(authenticatedPage.locator('text=Patch application started')).toBeVisible();
    }
  });

  test('should regenerate patch', async ({ authenticatedPage, testPatch }) => {
    if (testPatch.status === 'failed' || testPatch.status === 'rejected') {
      await authenticatedPage.click('text=Regenerate');
      await expect(authenticatedPage.locator('text=Patch regeneration started')).toBeVisible();
    }
  });
});