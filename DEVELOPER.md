# Developer Guide

## Quick Start for Contributors

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-org/singularity.git
cd singularity

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install PyGithub github-copilot-sdk python-dotenv

# Install development dependencies
pip install pytest pytest-asyncio black mypy
```

### Code Quality Standards

#### 1. Type Hints
Always add type hints to new functions:

```python
from typing import List, Dict, Any, Optional

def my_function(param: str, count: int = 5) -> Dict[str, Any]:
    """Function with proper type hints."""
    return {"result": param * count}
```

#### 2. Error Handling
Use specific exceptions and add proper logging:

```python
import logging
logger = logging.getLogger(__name__)

try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise CustomError(f"Failed to complete operation: {e}")
```

#### 3. Documentation
Add comprehensive docstrings:

```python
def create_branch(self, prompt: str) -> str:
    """
    Create a new branch for the changes.
    
    Args:
        prompt: The improvement prompt (used to generate branch name).
        
    Returns:
        The branch name.
        
    Raises:
        ReleaseFlowError: If branch creation fails.
    """
    # Implementation
```

#### 4. Constants
Extract magic numbers to module-level constants:

```python
# At module level
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30

# In function
for attempt in range(MAX_RETRIES):
    try:
        return make_request(timeout=TIMEOUT_SECONDS)
    except TimeoutError:
        continue
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pytest --cov=. tests/

# Run specific test
pytest tests/test_config.py::TestGitConfig::test_default_values -v
```

### Code Style

The project follows these conventions:

1. **Line Length**: Maximum 100 characters (configurable in pyproject.toml)
2. **Imports**: Use absolute imports, group by standard library, third-party, local
3. **Naming**:
   - Classes: `PascalCase`
   - Functions/Methods: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Private: `_leading_underscore`
4. **Docstrings**: Google style (as shown above)

### Logging Levels

Use appropriate log levels:

```python
logger.debug("Detailed information for debugging")
logger.info("General informational messages")
logger.warning("Warning messages for potentially harmful situations")
logger.error("Error messages for serious problems")
```

### Common Patterns

#### 1. Configuration Validation

```python
def __post_init__(self) -> None:
    """Validate configuration after initialization."""
    if not self.required_field:
        raise ValueError("required_field must be set")
```

#### 2. Resource Cleanup

```python
async def operation(self):
    """Ensure proper cleanup with try-finally."""
    resource = await acquire_resource()
    try:
        await process(resource)
    finally:
        await release(resource)
```

#### 3. Callback Error Handling

```python
if self.callback:
    try:
        self.callback(data)
    except Exception as e:
        logger.warning(f"Callback failed: {e}")
```

### Project Structure

```
singularity/
├── __init__.py           # Package exports
├── __main__.py          # CLI entry point
├── cli.py               # Command-line interface
├── config.py            # Configuration classes
├── core.py              # Main implementation
├── tests/               # Test suite
│   ├── __init__.py
│   ├── test_config.py
│   └── test_cli.py
├── pyproject.toml       # Project metadata
├── README.md            # User documentation
├── CHANGELOG.md         # Version history
├── IMPROVEMENTS.md      # Code improvement log
├── LICENSE              # MIT License
└── .gitignore          # Git ignore rules
```

### Adding New Features

1. **Create Issue**: Document the feature request
2. **Write Tests First**: TDD approach
3. **Implement Feature**: Follow code quality standards
4. **Update Documentation**: README, docstrings, CHANGELOG
5. **Run Tests**: Ensure all tests pass
6. **Submit PR**: With clear description

### Debugging Tips

#### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Test Configuration

```python
from config import ReleaseFlowConfig

config = ReleaseFlowConfig(
    repo="test/repo",
    local_path=".",
)
print(f"Config valid: {config.repo}")
```

#### Test CLI Parsing

```python
from cli import create_parser

parser = create_parser()
args = parser.parse_args(["--repo", "owner/repo", "--prompt", "test"])
print(f"Parsed: {args}")
```

### Common Issues and Solutions

#### Issue: Import Errors
**Solution**: Ensure you're in the project root and virtual environment is activated

```bash
cd /path/to/singularity
source .venv/bin/activate
python3 -c "import config; print('OK')"
```

#### Issue: Type Hint Errors
**Solution**: Use `typing` module for compatibility

```python
from typing import List, Dict, Optional
# Use List[str] not list[str] for Python 3.10
```

#### Issue: Tests Not Found
**Solution**: Ensure pytest is installed and you're in project root

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

### Performance Considerations

1. **Async/Await**: Use for I/O-bound operations
2. **Batch Operations**: Group similar operations when possible
3. **Timeouts**: Always set timeouts for external calls
4. **Resource Cleanup**: Use try-finally or context managers

### Security Best Practices

1. **Never Log Secrets**: Don't log tokens, passwords, or sensitive data
2. **Validate Input**: Always validate user input
3. **Use Timeouts**: Prevent hanging operations
4. **Handle Exceptions**: Don't expose internal errors to users

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `__init__.py` and `pyproject.toml`
- [ ] No breaking changes (or documented)
- [ ] Type hints added
- [ ] Error handling complete
- [ ] Logging appropriate

### Getting Help

- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions
- **Documentation**: Check README.md and code docstrings
- **Tests**: Look at test files for usage examples

### Contributing Guidelines

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes following code quality standards
4. Add tests for new functionality
5. Run tests: `pytest tests/ -v`
6. Commit with clear messages: `git commit -m "feat: add new feature"`
7. Push to your fork: `git push origin feature/my-feature`
8. Open a Pull Request with description

### Commit Message Format

```
<type>: <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or changes
- `refactor`: Code refactoring
- `chore`: Maintenance tasks

Example:
```
feat: add retry logic for API calls

Added exponential backoff retry mechanism for failed API requests.
Configurable via RetryConfig class.

Closes #123
```

---

**Happy Coding! 🚀**
