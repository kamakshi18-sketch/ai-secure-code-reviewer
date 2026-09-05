import { test, expect } from './fixtures';

test.describe('Scans', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/scans');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display scans page', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('h1')).toContainText('Scans');
  });

  test('should show new scan button', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=New Scan')).toBeVisible();
  });

  test('should display empty state when no scans', async ({ page }) => {
    await page.goto('/scans');
    await expect(page.locator('text=No scans yet')).toBeVisible();
  });

  test('should show scan cards with status', async ({ authenticatedPage, testScan }) => {
    await expect(authenticatedPage.locator(`text=${testScan.id.slice(0, 8)}`)).toBeVisible();
    await expect(authenticatedPage.locator('text=completed')).toBeVisible();
  });

  test('should show severity badges on scan cards', async ({ authenticatedPage, testScan }) => {
    if (testScan.critical_count > 0) {
      await expect(authenticatedPage.locator(`text=${testScan.critical_count} Critical`)).toBeVisible();
    }
    if (testScan.high_count > 0) {
      await expect(authenticatedPage.locator(`text=${testScan.high_count} High`)).toBeVisible();
    }
  });

  test('should open scan detail on click', async ({ authenticatedPage, testScan }) => {
    await authenticatedPage.click(`text=${testScan.id.slice(0, 8)}`);
    await expect(authenticatedPage).toHaveURL(new RegExp(`/scans/${testScan.id}`));
  });

  test('should show dropdown menu on scan card', async ({ authenticatedPage, testScan }) => {
    await authenticatedPage.hover(`text=${testScan.id.slice(0, 8)} >> nth=0`);
    await authenticatedPage.click('button[aria-label="More options"]');
    await expect(authenticatedPage.locator('text=View Details')).toBeVisible();
    await expect(authenticatedPage.locator('text=Retry')).toBeVisible();
  });
});

test.describe('Scan Detail', () => {
  test.beforeEach(async ({ authenticatedPage, testScan }) => {
    await authenticatedPage.goto(`/scans/${testScan.id}`);
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display scan detail page', async ({ authenticatedPage, testScan }) => {
    await expect(authenticatedPage.locator('text=Scan')).toBeVisible();
  });

  test('should show scan metadata', async ({ authenticatedPage, testScan }) => {
    await expect(authenticatedPage.locator(`text=${testScan.scan_type}`)).toBeVisible();
    await expect(authenticatedPage.locator(`text=${testScan.branch}`)).toBeVisible();
  });

  test('should show findings tabs', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Overview')).toBeVisible();
    await expect(authenticatedPage.locator('text=Scans')).toBeVisible();
    await expect(authenticatedPage.locator('text=Findings')).toBeVisible();
    await expect(authenticatedPage.locator('text=Patches')).toBeVisible();
    await expect(authenticatedPage.locator('text=Reports')).toBeVisible();
  });
});

test.describe('New Scan Creation', () => {
  test.beforeEach(async ({ authenticatedPage, testRepository }) => {
    await authenticatedPage.goto(`/repositories/${testRepository.id}?tab=scans`);
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should show new scan button', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=New Scan')).toBeVisible();
  });
});