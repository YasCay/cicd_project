# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please send an email to the maintainers. All security vulnerabilities will be promptly addressed.

Please do not create public GitHub issues for security vulnerabilities.

## Security Measures

This project implements several security measures:

- **Dependency Scanning**: Automated vulnerability scanning with Trivy
- **Code Analysis**: Static analysis with CodeQL
- **Container Security**: Multi-stage Docker builds with minimal attack surface
- **Secrets Management**: Environment-based configuration
- **Access Control**: Least privilege principle in CI/CD pipelines
