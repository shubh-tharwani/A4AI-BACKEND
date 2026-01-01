# Documentation

This directory contains comprehensive documentation for the AI for Education platform.

## Documentation Structure

### Architecture & Design
- Technical architecture overview
- System design decisions
- Agent collaboration patterns
- Data flow diagrams

### API Reference
- Endpoint documentation
- Request/response schemas
- Authentication details
- Error codes and handling

### Development Guides
- Setup instructions
- Development workflow
- Testing guidelines
- Deployment procedures

### Migration & Upgrade Notes
- Version upgrade summaries
- Breaking changes
- Migration scripts
- Deprecation notices

## Available Documentation

### Setup & Configuration
- [README.md](../README.md) - Main project documentation
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) - Community standards

### Technical Documentation
- API_DOCUMENTATION.md - Comprehensive API reference
- Architecture diagrams and specifications
- Database schema documentation

### Service-Specific Documentation
- Activities Service upgrade notes
- Assessment Service specifications
- Planning Service architecture
- Personalization Service details
- Visual Aid Service implementation
- Voice Assistant configuration

### Project Management
- PROJECT_STATUS.md - Current project status
- ROUTE_OPTIMIZATION_PLAN.md - API optimization strategy
- DAO_REFACTORING_SUMMARY.md - Data layer improvements

## Contributing to Documentation

We welcome documentation improvements! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### Documentation Standards

**Style Guide:**
- Use clear, concise language
- Include code examples where relevant
- Add diagrams for complex concepts
- Keep documentation up-to-date with code changes

**Formatting:**
- Use Markdown for all documentation
- Follow consistent heading hierarchy
- Include table of contents for long documents
- Use code blocks with language specification

### Documentation Checklist

When adding new features:
- [ ] Update API documentation
- [ ] Add code examples
- [ ] Include error handling documentation
- [ ] Update relevant guides
- [ ] Add to changelog

## Building Documentation

For generating API documentation:
```bash
# Generate OpenAPI documentation
python -m scripts.generate_api_docs

# View API docs locally
python -m uvicorn main:app --reload
# Visit: http://localhost:8000/docs
```

## Documentation Categories

### For Developers
- Setup and installation
- Architecture overview
- API reference
- Testing guidelines
- Deployment guides

### For Educators
- Platform capabilities
- Integration guides
- Best practices
- Use case examples

### For Researchers
- System architecture
- AI agent design
- Evaluation metrics
- Research opportunities

## Version History

Documentation is versioned alongside code releases. See release notes for changes in each version.

## Questions?

If you have questions about the documentation:
- Open a GitHub issue with the "documentation" label
- Start a discussion in GitHub Discussions
- Submit a pull request with improvements

---

**Last Updated:** January 2026
