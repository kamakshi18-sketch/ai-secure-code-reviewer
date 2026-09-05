import { Page, Locator, expect } from '@playwright/test';

export async function login(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL('/dashboard');
}

export async function register(page: Page, userData: {
  email: string;
  password: string;
  fullName: string;
  role?: string;
}) {
  await page.goto('/register');
  await page.fill('input[placeholder="John Doe"]', userData.fullName);
  await page.fill('input[type="email"]', userData.email);
  await page.fill('input[type="password"]', userData.password);
  await page.fill('input[placeholder="••••••••"] >> nth=1', userData.password);
  if (userData.role) {
    await page.selectOption('select', userData.role);
  }
  await page.click('button[type="submit"]');
  await page.waitForURL('/dashboard');
}

export async function addRepository(page: Page, githubUrl: string, githubToken?: string) {
  await page.goto('/repositories');
  await page.click('text=Add Repository');
  await page.fill('input[placeholder*="github.com"]', githubUrl);
  if (githubToken) {
    await page.fill('input[placeholder="For private repositories"]', githubToken);
  }
  await page.click('text=Add Repository');
  await page.waitForURL(/\/repositories\/[a-f0-9-]+/);
}

export async function createScan(page: Page, repositoryId: string) {
  await page.goto(`/repositories/${repositoryId}?tab=scans`);
  await page.click('text=New Scan');
  await page.waitForURL(/\/scans\/[a-f0-9-]+/);
}

export async function getAuthToken(page: Page): Promise<string | null> {
  return page.evaluate(() => localStorage.getItem('ai_reviewer_access_token'));
}

export async function setAuthToken(page: Page, token: string) {
  await page.evaluate((t) => localStorage.setItem('ai_reviewer_access_token', t), token);
}

export async function clearAuth(page: Page) {
  await page.evaluate(() => {
    localStorage.removeItem('ai_reviewer_access_token');
    localStorage.removeItem('ai_reviewer_refresh_token');
    localStorage.removeItem('ai_reviewer_user');
  });
}

export async function waitForToast(page: Page, message: string, timeout = 5000) {
  await page.waitForSelector(`[role="alert"]:has-text("${message}")`, { timeout });
}

export function generateTestEmail(): string {
  return `test${Date.now()}@example.com`;
}

export function generateTestPassword(): string {
  return `TestPass${Date.now()}!`;
}

export async function waitForElement(page: Page, selector: string, timeout = 10000) {
  await page.waitForSelector(selector, { timeout });
}

export async function fillForm(page: Page, fields: Record<string, string>) {
  for (const [selector, value] of Object.entries(fields)) {
    await page.fill(selector, value);
  }
}

export async function clickAndWait(page: Page, selector: string, waitForUrl?: string) {
  await page.click(selector);
  if (waitForUrl) {
    await page.waitForURL(waitForUrl);
  }
}

export async function selectOption(page: Page, selector: string, value: string) {
  await page.selectOption(selector, value);
}

export async function checkCheckbox(page: Page, selector: string, check = true) {
  const checkbox = page.locator(selector);
  const isChecked = await checkbox.isChecked();
  if (isChecked !== check) {
    await checkbox.click();
  }
}

export async function uploadFile(page: Page, selector: string, filePath: string) {
  await page.setInputFiles(selector, filePath);
}

export async function downloadFile(page: Page, triggerSelector: string) {
  const downloadPromise = page.waitForEvent('download');
  await page.click(triggerSelector);
  const download = await downloadPromise;
  return download;
}

export function createTestUser(overrides: Partial<{
  email: string;
  password: string;
  fullName: string;
  role: string;
}> = {}) {
  return {
    email: `test${Date.now()}@example.com`,
    password: 'TestPassword123!',
    fullName: 'Test User',
    role: 'developer',
    ...overrides,
  };
}

export async function takeScreenshot(page: Page, name: string) {
  await page.screenshot({ path: `test-results/screenshots/${name}.png`, fullPage: true });
}

export async function waitForNetworkIdle(page: Page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}

export async function waitForApiResponse(page: Page, urlPattern: string | RegExp, timeout = 30000) {
  return page.waitForResponse(response => {
    const url = response.url();
    return typeof urlPattern === 'string' ? url.includes(urlPattern) : urlPattern.test(url);
  }, { timeout });
}

export async function expectNoConsoleErrors(page: Page) {
  const errors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return () => {
    if (errors.length > 0) {
      throw new Error(`Console errors: ${errors.join(', ')}`);
    }
  };
}