# Contributing to Prompt Security Guide

Thank you for your interest in contributing to the Prompt Security Guide! This document provides guidelines for contributing to this security research project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and professional environment. We are committed to providing a welcoming experience for everyone.

## Ethical Guidelines

**This is a security research project.** All contributions must adhere to responsible disclosure and ethical security research principles:

###  Acceptable Contributions

- Documentation of publicly known vulnerabilities
- Defensive techniques and mitigation strategies
- Security testing tools for authorized use
- Educational content about AI security
- Bug fixes and improvements to existing tools
- Research papers and academic references

###  Not Acceptable

- Exploits targeting specific commercial systems without disclosure
- Personal data or credentials
- Content intended to enable harassment or harm
- Malicious code or backdoors
- Proprietary information obtained without authorization

## How to Contribute

### 1. Reporting Vulnerabilities in This Project

If you find a security issue in this repository itself:

1. **Do not** open a public issue
2. Email the maintainers directly (see SECURITY.md)
3. Allow reasonable time for response

### 2. Contributing New Attack Vectors

When documenting new attack techniques:

```markdown
## Attack Name

### Description
Brief description of the attack technique

### Mechanism
How the attack works technically

### Example
Sanitized example (do not include working exploits against production systems)

### Detection
How to detect this attack

### Mitigation
How to defend against this attack

### References
Academic papers, responsible disclosures, etc.
```

### 3. Contributing Defensive Techniques

When adding new defenses:

```markdown
## Defense Name

### Description
What this defense protects against

### Implementation
How to implement this defense (with code examples)

### Effectiveness
Against which attack classes and with what limitations

### Trade-offs
Performance, usability, or other considerations

### Testing
How to verify the defense works
```

### 4. Contributing Tools

Security tools must:

- Include clear usage documentation
- Have a `--help` option
- Include example usage
- Be tested before submission
- Not require authentication credentials
- Work in a sandboxed/simulated environment by default

## Submission Process

### Step 1: Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/prompt-security-guide.git
cd prompt-security-guide
```

### Step 2: Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Use prefixes:
- `feature/` - New features or content
- `fix/` - Bug fixes
- `docs/` - Documentation improvements
- `tool/` - New or updated tools

### Step 3: Make Changes

- Follow existing code and documentation style
- Include tests where applicable
- Update relevant documentation

### Step 4: Test Your Changes

```bash
# Install dev dependencies
python3 -m pip install -r requirements-dev.txt

# Run tests
python3 -m pytest tests/ -v

# Basic syntax check
python3 -m compileall tools tests
```

### Step 5: Commit and Push

```bash
git add .
git commit -m "Brief description of changes"
git push origin feature/your-feature-name
```

### Step 6: Open a Pull Request

1. Go to the repository on GitHub
2. Click "New Pull Request"
3. Select your branch
4. Fill in the PR template
5. Submit for review

## Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] New attack documentation
- [ ] New defense documentation
- [ ] New tool
- [ ] Bug fix
- [ ] Documentation improvement
- [ ] Other (please describe)

## Checklist
- [ ] I have read the CONTRIBUTING guidelines
- [ ] This contribution follows ethical guidelines
- [ ] I have tested my changes
- [ ] I have updated relevant documentation
- [ ] My code follows the project style

## Related Issues
Closes #(issue number)

## Additional Notes
Any other context about the contribution
```

## Style Guidelines

### Documentation

- Use clear, concise language
- Include code examples where helpful
- Use proper Markdown formatting
- Add tables for structured information
- Include diagrams for complex concepts

### Code

- Follow PEP 8 for Python
- Include docstrings for functions
- Add type hints where possible
- Comment complex logic
- Use meaningful variable names

### Commit Messages

```
<type>: <brief description>

<detailed description if needed>

<references to issues>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `tool`: Tool changes
- `test`: Test changes
- `refactor`: Code refactoring

## Review Process

1. **Initial Review**: Maintainers check for ethical compliance and basic quality
2. **Technical Review**: Deep review of content accuracy and security implications
3. **Community Input**: For significant changes, community feedback may be requested
4. **Merge**: Once approved, changes are merged to main branch

## Recognition

Contributors are recognized in:

- The project README
- Release notes for their contributions
- The CONTRIBUTORS file

## Questions?

- Open a Discussion on GitHub
- Check existing issues and discussions
- Review the FAQ in documentation

---

Thank you for helping make AI systems more secure!