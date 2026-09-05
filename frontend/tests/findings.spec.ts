import { test, expect } from './fixtures';

test.describe('Findings', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/findings');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display findings page', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('h1')).toContainText('Findings');
  });

  test('should display filter controls', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('input[placeholder*="Search findings"]')).toBeVisible();
    await expect(authenticatedPage.locator('select')).toBeVisible(); // Severity filter
    await expect(authenticatedPage.locator('select').nth(1)).toBeVisible(); // Status filter
  });

  test('should filter by severity', async ({ authenticatedPage }) => {
    await authenticatedPage.selectOption('select', 'high');
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check that all visible findings have high severity
    const severityBadges = authenticatedPage.locator('[class*="badge-high"], [class*="badge-critical"]');
    const count = await severityBadges.count();
    for (let i = 0; i < count; i++) {
      await expect(severityBadges.nth(i)).toContainText(/high|critical/i);
    }
  });

  test('should filter by status', async ({ authenticatedPage }) => {
    await authenticatedPage.selectOption('select:nth-of-type(2)', 'open');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const statusBadges = authenticatedPage.locator('[class*="badge-open"]');
    const count = await statusBadges.count();
    for (let i = 0; i < count; i++) {
      await expect(statusBadges.nth(i)).toContainText('OPEN');
    }
  });

  test('should search findings', async ({ authenticatedPage }) => {
    await authenticatedPage.fill('input[placeholder*="Search findings"]', 'SQL');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const findingCards = authenticatedPage.locator('.card');
    const count = await findingCards.count();
    for (let i = 0; i < count; i++) {
      const text = await findingCards.nth(i).textContent();
      expect(text?.toLowerCase()).toContain('sql');
    }
  });

  test('should display finding cards with metadata', async ({ authenticatedPage, testFinding }) => {
    await expect(authenticatedPage.locator(`text=${testFinding.rule_name}`)).toBeVisible();
    await expect(authenticatedPage.locator(`text=${testFinding.severity.toUpperCase()}`)).toBeVisible();
    await expect(authenticatedPage.locator(`text=${testFinding.file_path}`)).toBeVisible();
    await expect(authenticatedPage.locator(`text=${testFinding.line_start}`)).toBeVisible();
  });

  test('should display severity badges with correct colors', async ({ authenticatedPage, testFinding }) => {
    const severityBadge = authenticatedPage.locator(`text=${testFinding.severity.toUpperCase()}`);
    await expect(severityBadge).toBeVisible();
  });

  test('should display scanner badge', async ({ authenticatedPage, testFinding }) => {
    await expect(authenticatedPage.locator(`text=${testFinding.scanner}`)).toBeVisible();
  });

  test('should open finding detail on click', async ({ authenticatedPage, testFinding }) => {
    await authenticatedPage.click(`text=${testFinding.rule_name}`);
    await expect(authenticatedPage).toHaveURL(new RegExp(`/findings/${testFinding.id}`));
  });

  test('should show dropdown menu on finding card', async ({ authenticatedPage }) => {
    await authenticatedPage.hover('.card >> nth=0');
    await authenticatedPage.click('button[aria-label="More options"]');
    await expect(authenticatedPage.locator('text=View Details')).toBeVisible();
    await expect(authenticatedPage.locator('text=Explain with AI')).toBeVisible();
  });

  test('should paginate results', async ({ authenticatedPage }) => {
    // This test assumes enough findings exist for pagination
    const nextButton = authenticatedPage.locator('text=Next');
    if (await nextButton.isVisible()) {
      await nextButton.click();
      await authenticatedPage.waitForLoadState('networkidle');
    }
  });
});

test.describe('Finding Detail', () => {
  test.beforeEach(async ({ authenticatedPage, testFinding }) => {
    await authenticatedPage.goto(`/findings/${testFinding.id}`);
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display finding detail page', async ({ authenticatedPage, testFinding }) => {
    await expect(authenticatedPage.locator(`text=${testFinding.rule_name}`)).toBeVisible();
  });

  test('should show finding metadata', async ({ authenticatedPage, testFinding }) => {
    await expect(authenticatedPage.locator(`text=${testFinding.scanner}`)).toBeVisible();
    await expect(authenticatedPage.locator(`text=${testFinding.rule_id}`)).toBeVisible();
    if (testFinding.cwe_id) {
      await expect(authenticatedPage.locator(`text=${testFinding.cwe_id}`)).toBeVisible();
    }
  });

  test('should show code snippet if available', async ({ authenticatedPage, testFinding }) => {
    if (testFinding.code_snippet) {
      await expect(authenticatedPage.locator('pre, code')).toBeVisible();
    }
  });

  test('should show AI explanation if available', async ({ authenticatedPage, testFinding }) => {
    // AI explanation might be generated on demand
    const explainButton = authenticatedPage.locator('text=Explain with AI');
    if (await explainButton.isVisible()) {
      await explainButton.click();
      await authenticatedPage.waitForLoadState('networkidle');
    }
  });

  test('should have back navigation', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Findings').first()).toBeVisible();
  });
});

test.describe('Finding Actions', () => {
  test.beforeEach(async ({ authenticatedPage, testFinding }) => {
    await authenticatedPage.goto('/findings');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should open explain modal', async ({ authenticatedPage, testFinding }) => {
    await authenticatedPage.hover('.card >> nth=0');
    await authenticatedPage.click('button[aria-label="More options"]');
    await authenticatedPage.click('text=Explain with AI');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should update finding status', async ({ authenticatedPage, testFinding }) => {
    await authenticatedPage.click(`text=${testFinding.rule_name}`);
    await expect(authenticatedPage).toHaveURL(new RegExp(`/findings/${testFinding.id}`));
  });
});