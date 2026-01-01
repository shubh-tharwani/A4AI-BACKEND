# Contributing to AI for Education Platform

Thank you for your interest in contributing to our project! We welcome contributions from developers, educators, researchers, and anyone passionate about improving educational access through technology.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. All contributors are expected to:

- Be respectful and considerate in communications
- Welcome diverse perspectives and experiences
- Accept constructive criticism gracefully
- Focus on what is best for the community and educational impact
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When reporting bugs, include:

- **Description**: Clear and concise description of the bug
- **Steps to Reproduce**: Detailed steps to reproduce the behavior
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: OS, Python version, relevant dependencies
- **Screenshots**: If applicable
- **Logs**: Relevant error messages or stack traces

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use Case**: Why this enhancement would be useful
- **Proposed Solution**: How you envision it working
- **Alternatives**: Other solutions you've considered
- **Impact**: Who would benefit and how

### Code Contributions

1. **Fork the Repository**
   ```bash
   git clone https://github.com/shubh-tharwani/A4AI-BACKEND.git
   cd A4AI-BACKEND
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up Development Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. **Make Your Changes**
   - Write clean, readable code following existing style
   - Add comments for complex logic
   - Update documentation as needed
   - Add tests for new functionality

5. **Test Your Changes**
   ```bash
   # Run existing tests
   pytest tests/
   
   # Test the application locally
   python -m uvicorn main:app --reload
   ```

6. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

   Use conventional commit messages:
   - `feat:` New features
   - `fix:` Bug fixes
   - `docs:` Documentation changes
   - `refactor:` Code refactoring
   - `test:` Adding or updating tests
   - `chore:` Maintenance tasks

7. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   Then create a pull request on GitHub with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots/videos if UI changes
   - Checklist of completed items

### Code Style Guidelines

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and single-purpose
- Maintain consistent naming conventions
- Use meaningful variable and function names

### Documentation Contributions

Documentation improvements are highly valued! You can contribute by:

- Fixing typos or clarifying existing documentation
- Adding examples and tutorials
- Translating documentation to other languages
- Creating video tutorials or guides
- Improving API documentation

### Educational Content Contributions

- Propose new activity templates
- Share pedagogical best practices
- Contribute curriculum alignments
- Suggest assessment formats
- Provide educational research references

## Development Workflow

### Project Structure
```
├── agents/          # AI agent implementations
├── dao/             # Data access layer
├── routes/          # API endpoints
├── services/        # Business logic
├── config/          # Configuration
├── tests/           # Test files
├── scripts/         # Utility scripts
└── docs/            # Documentation
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_content_agent.py

# Run with coverage
pytest --cov=. --cov-report=html
```

### Local Development
```bash
# Start development server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Access API docs
http://localhost:8000/docs
```

## Pull Request Process

1. **Update Documentation**: Ensure all documentation is updated
2. **Add Tests**: Include tests for new functionality
3. **Pass CI/CD**: Ensure all automated checks pass
4. **Code Review**: Address reviewer feedback promptly
5. **Squash Commits**: Maintain clean commit history when merging

## Community

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussions
- **Pull Requests**: For code contributions

## Recognition

Contributors will be recognized in:
- Project README
- Release notes
- Contributors page
- Academic publications (for significant contributions)

## Questions?

If you have questions about contributing, feel free to:
- Open a GitHub Discussion
- Create an issue with the "question" label
- Reach out to project maintainers

Thank you for helping make quality education accessible to everyone!
