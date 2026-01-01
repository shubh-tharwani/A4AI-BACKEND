# Tests Directory

This directory contains all test files for the AI for Education platform.

## Test Structure

```
tests/
├── test_agents/           # Agent-specific tests
├── test_routes/           # API endpoint tests
├── test_services/         # Service layer tests
├── test_dao/             # Data access tests
└── test_integration/     # Integration tests
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_content_agent.py
```

### Run Tests with Coverage
```bash
pytest --cov=. --cov-report=html
```

### Run Tests with Verbose Output
```bash
pytest -v
```

## Writing Tests

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test functions: `test_<functionality_description>`
- Test classes: `Test<ClassName>`

### Example Test Structure
```python
import pytest
from agents.content_agent import ContentAgent

class TestContentAgent:
    """Tests for Content Agent functionality"""
    
    @pytest.fixture
    def content_agent(self):
        """Fixture to create ContentAgent instance"""
        return ContentAgent()
    
    def test_generate_activity_success(self, content_agent):
        """Test successful activity generation"""
        result = content_agent.generate_activity(
            topic="Math",
            grade_level="5"
        )
        assert result is not None
        assert "content" in result
```

## Test Categories

### Unit Tests
Test individual functions and methods in isolation.

### Integration Tests
Test interaction between multiple components.

### API Tests
Test API endpoints and request/response handling.

### Performance Tests
Test system performance under various loads.

## Test Fixtures

Common fixtures are available in `conftest.py`:
- Mock credentials
- Test database connections
- Sample data generators

## Continuous Integration

Tests are automatically run on:
- Every pull request
- Commits to main branch
- Before deployment

## Coverage Goals

- Maintain >80% code coverage
- 100% coverage for critical paths
- All public APIs must have tests

## Mock Data

Use mock services from `mock_services.py` for testing without real API calls.

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Use Fixtures**: Share setup code via fixtures
3. **Mock External Services**: Don't rely on external APIs in tests
4. **Clear Test Names**: Test names should describe what they test
5. **Test Edge Cases**: Include tests for error conditions
6. **Keep Tests Fast**: Mock slow operations

## Running Specific Test Groups

```bash
# Run only agent tests
pytest tests/test_agents/

# Run only API tests
pytest tests/test_routes/

# Run tests matching pattern
pytest -k "content"
```

For more information, see CONTRIBUTING.md.
