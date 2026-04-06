# Contributing to Social Agent

First off, thank you for considering contributing to Social Agent! 🎉

## Development Setup

```bash
# Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/social-agent.git
cd social-agent

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## How to Contribute

### Report Bugs

Found a bug? Please open an issue with:
- Bug description
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

### Suggest Features

Have an idea? Open an issue with the `enhancement` label.

### Submit Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest tests/ -v`)
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Add a New Platform Plugin

See the [Plugin Development Guide](#create-your-own-plugin) in README.md.
Follow these steps:

1. Create a new directory under `src/social_agent/plugins/your_platform/`
2. Implement `BasePlatformPlugin` interface
3. Add optional dependencies to `pyproject.toml`
4. Add tests in `tests/plugins/`
5. Update the supported platforms table in README.md
6. Submit a PR!

## Code Style

- Use `black` for formatting
- Use `ruff` for linting
- Type hints are encouraged
- Docstrings for public APIs

## Pull Request Guidelines

- Keep PRs small and focused
- Include tests for new functionality
- Update documentation as needed
- One PR per feature/fix

## Questions?

Feel free to open an issue with the `question` label.
