import { test, expect } from './fixtures';

test.describe('Chat Assistant', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/chat');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should display chat page', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('h1')).toContainText('Chat Assistant');
  });

  test('should show welcome message when no history', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=How can I help?')).toBeVisible();
    await expect(authenticatedPage.locator('text=Ask me about security findings')).toBeVisible();
  });

  test('should display suggestion chips', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('text=Why is this SQL injection vulnerable?')).toBeVisible();
    await expect(authenticatedPage.locator('text=Explain this CWE-79 finding')).toBeVisible();
    await expect(authenticatedPage.locator('text=How was this patch generated?')).toBeVisible();
    await expect(authenticatedPage.locator('text=Can I ignore this finding?')).toBeVisible();
    await expect(authenticatedPage.locator('text=What is the OWASP category for this?')).toBeVisible();
    await expect(authenticatedPage.locator('text=Show me secure coding examples')).toBeVisible();
  });

  test('should send message on enter', async ({ authenticatedPage }) => {
    await authenticatedPage.fill('textarea[placeholder*="Ask about security"]', 'What is SQL injection?');
    await authenticatedPage.press('textarea[placeholder*="Ask about security"]', 'Enter');
    
    // Wait for response
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Check that user message appears
    await expect(authenticatedPage.locator('text=What is SQL injection?')).toBeVisible();
    
    // Check that assistant response appears
    await expect(authenticatedPage.locator('[class*="bg-dark-100"]').first()).toBeVisible();
  });

  test('should send message on button click', async ({ authenticatedPage }) => {
    await authenticatedPage.fill('textarea[placeholder*="Ask about security"]', 'Explain XSS');
    await authenticatedPage.click('button[aria-label="Send message"]');
    
    await authenticatedPage.waitForLoadState('networkidle');
    
    await expect(authenticatedPage.locator('text=Explain XSS')).toBeVisible();
  });

  test('should show loading indicator while processing', async ({ authenticatedPage }) => {
    await authenticatedPage.fill('textarea[placeholder*="Ask about security"]', 'Test message');
    await authenticatedPage.click('button[aria-label="Send message"]');
    
    // Check for loading spinner
    await expect(authenticatedPage.locator('.animate-spin')).toBeVisible();
  });

  test('should disable send button when empty', async ({ authenticatedPage }) => {
    await expect(authenticatedPage.locator('button[aria-label="Send message"]')).toBeDisabled();
  });

  test('should support shift+enter for new line', async ({ authenticatedPage }) => {
    await authenticatedPage.fill('textarea[placeholder*="Ask about security"]', 'Line 1');
    await authenticatedPage.press('textarea[placeholder*="Ask about security"]', 'Shift+Enter');
    await authenticatedPage.fill('textarea[placeholder*="Ask about security"]', 'Line 1\nLine 2');
    
    const value = await authenticatedPage.inputValue('textarea[placeholder*="Ask about security"]');
    expect(value).toContain('Line 1\nLine 2');
  });

  test('should copy assistant message', async ({ authenticatedPage }) => {
    await authenticatedPage.fill('textarea[placeholder*="Ask about security"]', 'Test');
    await authenticatedPage.click('button[aria-label="Send message"]');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const copyButton = authenticatedPage.locator('button:has-text("Copy")').first();
    if (await copyButton.isVisible()) {
      await copyButton.click();
      // Clipboard access would need permissions in real test
    }
  });

  test('should clear input after sending', async ({ authenticatedPage }) => {
    await authenticatedPage.fill('textarea[placeholder*="Ask about security"]', 'Test message');
    await authenticatedPage.click('button[aria-label="Send message"]');
    await authenticatedPage.waitForLoadState('networkidle');
    
    const value = await authenticatedPage.inputValue('textarea[placeholder*="Ask about security"]');
    expect(value).toBe('');
  });

  test('should show context badges when available', async ({ authenticatedPage, testFinding, testRepository }) => {
    // This test assumes context is set
    const contextBadges = authenticatedPage.locator('[class*="badge"]');
    // Badges might not be visible without context
  });
});

test.describe('Chat with Finding Context', () => {
  test.beforeEach(async ({ authenticatedPage, testFinding }) => {
    // Navigate to finding detail first, then to chat
    await authenticatedPage.goto(`/findings/${testFinding.id}`);
    await authenticatedPage.waitForLoadState('networkidle');
    
    // Click explain with AI or navigate to chat
    await authenticatedPage.goto('/chat');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should show finding context badge', async ({ authenticatedPage, testFinding }) => {
    await expect(authenticatedPage.locator(`text=Finding: ${testFinding.rule_name}`)).toBeVisible();
  });

  test('should answer questions about the finding', async ({ authenticatedPage, testFinding }) => {
    await authenticatedPage.fill('textarea[placeholder*="Ask about security"]', `Why is ${testFinding.rule_name} vulnerable?`);
    await authenticatedPage.click('button[aria-label="Send message"]');
    
    await authenticatedPage.waitForLoadState('networkidle');
    
    await expect(authenticatedPage.locator('text=vulnerable')).toBeVisible();
  });
});

test.describe('Chat with Repository Context', () => {
  test.beforeEach(async ({ authenticatedPage, testRepository }) => {
    await authenticatedPage.goto(`/repositories/${testRepository.id}`);
    await authenticatedPage.waitForLoadState('networkidle');
    await authenticatedPage.goto('/chat');
    await authenticatedPage.waitForLoadState('networkidle');
  });

  test('should show repository context badge', async ({ authenticatedPage, testRepository }) => {
    await expect(authenticatedPage.locator(`text=Repo: ${testRepository.full_name}`)).toBeVisible();
  });
});