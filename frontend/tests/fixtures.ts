import { test as base, Page, APIRequestContext } from '@playwright/test';
import { User, Repository, Scan, Finding, Patch } from '../src/types';

type TestFixtures = {
  authenticatedPage: Page;
  apiRequest: APIRequestContext;
  testUser: User;
  testRepository: Repository;
  testScan: Scan;
  testFinding: Finding;
  testPatch: Patch;
};

export const test = base.extend<TestFixtures>({
  apiRequest: async ({ playwright }, use) => {
    const request = await playwright.request.newContext({
      baseURL: 'http://localhost:8000/api/v1',
      extraHTTPHeaders: {
        'Content-Type': 'application/json',
      },
    });
    await use(request);
    await request.dispose();
  },

  authenticatedPage: async ({ page, apiRequest }, use) => {
    // Register and login a test user
    const timestamp = Date.now();
    const testEmail = `test${timestamp}@example.com`;
    const testPassword = 'TestPassword123!';
    
    await apiRequest.post('/auth/register', {
      data: {
        email: testEmail,
        password: testPassword,
        full_name: 'Test User',
        role: 'developer',
      },
    });
    
    const loginResponse = await apiRequest.post('/auth/login', {
      form: { username: testEmail, password: testPassword },
    });
    const loginData = await loginResponse.json();
    const accessToken = loginData.access_token;
    
    // Set auth token in localStorage
    await page.goto('/');
    await page.evaluate((token) => {
      localStorage.setItem('ai_reviewer_access_token', token);
      localStorage.setItem('ai_reviewer_refresh_token', loginData.refresh_token);
      localStorage.setItem('ai_reviewer_user', JSON.stringify(loginData.user));
    }, accessToken);
    
    await page.reload();
    await page.waitForURL('/dashboard');
    
    await use(page);
  },

  testUser: async ({ apiRequest }, use) => {
    const timestamp = Date.now();
    const response = await apiRequest.post('/auth/register', {
      data: {
        email: `testuser${timestamp}@example.com`,
        password: 'TestPassword123!',
        full_name: 'Test User',
        role: 'developer',
      },
    });
    const user = await response.json();
    await use(user.user);
  },

  testRepository: async ({ apiRequest, testUser }, use) => {
    const loginResponse = await apiRequest.post('/auth/login', {
      form: { username: testUser.email, password: 'TestPassword123!' },
    });
    const loginData = await loginResponse.json();
    const headers = { Authorization: `Bearer ${loginData.access_token}` };
    
    const response = await apiRequest.post('/repositories', {
      headers,
      data: {
        github_url: 'https://github.com/testuser/test-repo',
        github_token: 'ghp_test_token',
      },
    });
    const repo = await response.json();
    await use(repo);
  },

  testScan: async ({ apiRequest, testRepository, testUser }, use) => {
    const loginResponse = await apiRequest.post('/auth/login', {
      form: { username: testUser.email, password: 'TestPassword123!' },
    });
    const loginData = await loginResponse.json();
    const headers = { Authorization: `Bearer ${loginData.access_token}` };
    
    const response = await apiRequest.post('/scans', {
      headers,
      data: {
        repository_id: testRepository.id,
        scan_type: 'full',
      },
    });
    const scan = await response.json();
    await use(scan);
  },

  testFinding: async ({ apiRequest, testScan, testUser }, use) => {
    const loginResponse = await apiRequest.post('/auth/login', {
      form: { username: testUser.email, password: 'TestPassword123!' },
    });
    const loginData = await loginResponse.json();
    const headers = { Authorization: `Bearer ${loginData.access_token}` };
    
    // We'll use a mock finding for UI tests
    const finding = {
      id: 'test-finding-id',
      scan_id: testScan.id,
      scanner: 'semgrep',
      rule_id: 'sql-injection',
      rule_name: 'SQL Injection',
      severity: 'high',
      status: 'open',
      cwe_id: 'CWE-89',
      owasp_category: 'A03:2021',
      file_path: 'app/models.py',
      line_start: 42,
      message: 'Potential SQL injection via string formatting',
      confidence: 0.9,
      created_at: new Date().toISOString(),
    };
    await use(finding);
  },

  testPatch: async ({ apiRequest, testScan, testFinding, testUser }, use) => {
    const loginResponse = await apiRequest.post('/auth/login', {
      form: { username: testUser.email, password: 'TestPassword123!' },
    });
    const loginData = await loginResponse.json();
    const headers = { Authorization: `Bearer ${loginData.access_token}` };
    
    const patch = {
      id: 'test-patch-id',
      scan_id: testScan.id,
      finding_id: testFinding.id,
      status: 'generated',
      diff: '--- a/app/models.py\n+++ b/app/models.py\n@@ -39,7 +39,7 @@\n     def get_user(user_id):\n-        query = f"SELECT * FROM users WHERE id = {user_id}"\n+        query = "SELECT * FROM users WHERE id = %s"\n         cursor.execute(query, (user_id,))',
      file_path: 'app/models.py',
      language: 'python',
      llm_provider: 'openai',
      llm_model: 'gpt-4-turbo-preview',
      created_at: new Date().toISOString(),
    };
    await use(patch);
  },
});

export { expect } from '@playwright/test';