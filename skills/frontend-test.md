# Frontend Testing Skill

## Description
Frontend testing with Jest, Cypress, or Playwright for the Item Management System.

## Trigger Phrases
- "test frontend"
- "frontend tests"
- "test UI"
- "run frontend tests"
- "frontend testing"

## When to Use
When you need to:
- Set up frontend testing infrastructure
- Write unit tests for JavaScript/TypeScript components
- Write end-to-end (E2E) tests for user flows
- Test responsive design
- Test PWA functionality
- Debug frontend test failures

## Available Tools
- Bash (for running test commands)
- Grep (for finding test patterns)
- Glob (for finding test files)
- Read (for reading test files)

## MUST DO
1. Identify the testing framework being used (Jest, Cypress, Playwright, or other)
2. Check existing test structure in `tests/` directory
3. Ensure tests cover critical user flows:
   - Item CRUD operations
   - Search and filter functionality
   - User authentication
   - Location management
   - Email notification settings
   - PWA offline functionality
4. Use proper test assertions and matchers
5. Ensure tests are isolated and don't depend on external state
6. Mock API calls appropriately
7. Test edge cases and error handling
8. Follow existing code style and patterns

## MUST NOT DO
- Do NOT create tests without understanding the component structure
- Do NOT ignore test failures
- Do NOT use brittle selectors that depend on implementation details
- Do NOT skip critical user flows
- Do NOT write tests that depend on real database data
- Do NOT write tests with hardcoded values that might change

## Context
- Project uses Bootstrap 5 for UI
- Frontend is vanilla JavaScript (no React/Vue)
- PWA support with service workers
- Dynamic loading of items via API endpoints
- Responsive design breakpoints tested

## Workflow
1. Check existing test setup (if any)
2. Determine appropriate testing framework
3. Identify components to test
4. Write tests following patterns:
   - Arrange: Set up test data/state
   - Act: Perform the user action
   - Assert: Verify expected outcome
5. Run tests and verify they pass
6. Report test coverage if possible

## Example Test Structure
```javascript
describe('Item Management', () => {
  beforeEach(() => {
    // Setup before each test
  });

  afterEach(() => {
    // Cleanup after each test
  });

  test('should create a new item', async () => {
    // Arrange
    const itemData = { ... };

    // Act
    await createItem(itemData);

    // Assert
    expect(itemExists(itemData)).toBe(true);
  });
});
```

## Testing Checklist
- [ ] Unit tests for utility functions
- [ ] Integration tests for API interactions
- [ ] E2E tests for critical user flows
- [ ] Mobile responsiveness tests
- [ ] PWA offline functionality tests
- [ ] Form validation tests
- [ ] Error handling tests
- [ ] Accessibility tests (basic)
