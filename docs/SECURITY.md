# Security Policy

## Overview

Security is a top priority for the Odiseo AI platform. We appreciate the security community's efforts to responsibly disclose vulnerabilities and work with us to protect our users.

This document outlines our security policies, vulnerability disclosure process, and bug bounty program.

---

## 🔒 Security Practices

### Current Security Posture

Our platform implements comprehensive security controls across all layers:

**Phase 1 - CRITICAL (✅ Complete)**
- ✅ Broken Access Control (CWE-862) - Enforced Clerk authentication
- ✅ SQL Injection Prevention (CWE-89) - Parameterized queries
- ✅ Credential Exposure Prevention (CWE-532) - Secure logging
- ✅ JWT Token Reuse Prevention (CWE-347) - Single-use tokens
- ✅ Webhook Signature Verification (CWE-345) - Svix integration

**Phase 2 - HIGH (✅ Complete)**
- ✅ ReDoS Prevention (CWE-1333) - Safe regex patterns
- ✅ IP Spoofing Prevention (CWE-290) - Trusted proxy validation
- ✅ Sensitive Data Logging (CWE-532) - PII redaction
- ✅ Time-of-Check to Time-of-Use (CWE-367) - Atomic operations
- ✅ Timing Attack Prevention (CWE-208) - Constant-time comparisons
- ✅ Server Information Disclosure (CWE-209) - Header obfuscation

**Phase 3 - MEDIUM (✅ Complete)**
- ✅ XSS Prevention (CWE-79) - HTML escaping, CSP headers
- ✅ Race Condition Prevention (CWE-362) - Atomic SQL queries
- ✅ Information Disclosure (CWE-209) - Error sanitization
- ✅ Session Fixation Prevention (CWE-384) - UUID v4 validation
- ✅ Input Validation (CWE-20) - Pydantic validators, length limits
- ✅ Rate Limiting (CWE-770) - Token bucket algorithm

**Phase 4 - LOW (✅ Complete)**
- ✅ Security Response Headers - HSTS, CSP, X-Frame-Options, etc.
- ✅ Rate Limit Headers - X-RateLimit-* transparency
- ✅ Request Size Limits - DoS prevention (10-100 KB limits)
- ✅ API Versioning - Deprecation management
- ✅ Security Audit Logging - Comprehensive event tracking

**OWASP Top 10 2021 Compliance**: ✅ FULL COMPLIANCE

---

## 🐛 Vulnerability Disclosure Policy

### Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

**📧 Email**: security@odiseo.ai
**🔐 PGP Key**: Available on request
**⏱️ Response Time**: Within 48 hours (business days)

### What to Include in Your Report

Please provide as much detail as possible:

1. **Type of Vulnerability**
   - OWASP category (e.g., A01:2021 – Broken Access Control)
   - CWE number (e.g., CWE-89: SQL Injection)
   - CVSS v3.1 score (if applicable)

2. **Affected Component**
   - API endpoint (e.g., `POST /v1/demo`)
   - Service (e.g., demo_agent, booking_agent, auth_service)
   - Version number (check `X-API-Version` header)

3. **Reproduction Steps**
   - Clear step-by-step instructions
   - Proof-of-concept code (if applicable)
   - Screenshots or logs (redact sensitive data)

4. **Impact Assessment**
   - Who is affected (users, admins, specific roles)
   - What data is at risk
   - Potential attack scenarios

5. **Suggested Fix** (optional)
   - Proposed remediation
   - Code patches (if available)

### Example Report Template

```markdown
**Vulnerability Type**: SQL Injection (CWE-89)
**Severity**: HIGH (CVSS 8.6)
**Affected Endpoint**: POST /v1/demo
**API Version**: 1.0.0

**Description**:
The /v1/demo endpoint does not properly sanitize the `input` parameter...

**Reproduction Steps**:
1. Send POST request to /v1/demo
2. Set `input` parameter to: `' OR 1=1--`
3. Observe SQL error in response

**Impact**:
- Attackers can bypass authentication
- Sensitive user data may be exposed
- Database integrity at risk

**Suggested Fix**:
Use parameterized queries instead of string concatenation.
```

---

## 🚫 Out of Scope

The following issues are **NOT** eligible for rewards and should not be reported:

### Non-Issues
- ❌ Clickjacking on pages without sensitive actions
- ❌ Missing security headers with no demonstrated impact
- ❌ Presence of autocomplete on forms
- ❌ Lack of CSRF tokens on logout endpoints
- ❌ Version disclosure in headers (we use `X-API-Version` intentionally)
- ❌ Rate limit response times (timing attacks without PoC)

### Known Limitations
- ❌ Demo account quotas (this is intended behavior)
- ❌ CAPTCHA on registration (intentionally disabled for demo)
- ❌ Email verification timing (not a security issue)

### Testing Restrictions
- ❌ **DO NOT** perform automated scanning without permission
- ❌ **DO NOT** test against production data (use test/staging environments)
- ❌ **DO NOT** attempt Denial of Service (DoS) attacks
- ❌ **DO NOT** perform social engineering attacks
- ❌ **DO NOT** access other users' data without permission

---

## 💰 Bug Bounty Program

We offer rewards for valid, high-quality vulnerability reports:

### Reward Tiers

| Severity | CVSS Score | Reward (USD) | Examples |
|----------|------------|--------------|----------|
| **CRITICAL** | 9.0-10.0 | $500-$2,000 | Remote code execution, authentication bypass |
| **HIGH** | 7.0-8.9 | $250-$500 | SQL injection, privilege escalation |
| **MEDIUM** | 4.0-6.9 | $100-$250 | XSS, CSRF, information disclosure |
| **LOW** | 0.1-3.9 | $50-$100 | Security misconfigurations, weak crypto |

### Bonus Multipliers

- **🔥 First to Report**: +25% bonus
- **📄 Detailed PoC**: +20% bonus
- **🛠️ Working Patch**: +30% bonus
- **🏆 Multiple Findings**: +10% per additional issue (same session)

### Eligibility Requirements

To qualify for a reward:

1. ✅ Be the first to report the vulnerability
2. ✅ Provide clear reproduction steps
3. ✅ Allow reasonable time for remediation (90 days minimum)
4. ✅ Do not publicly disclose before fix is deployed
5. ✅ Follow responsible disclosure guidelines
6. ✅ Not be an employee, contractor, or affiliate of Odiseo AI
7. ✅ Comply with all local laws and regulations

### Payment Process

1. **Report Submission**: Submit via email (security@odiseo.ai)
2. **Initial Triage**: We respond within 48 hours
3. **Validation**: We verify and reproduce the issue (1-2 weeks)
4. **Reward Determination**: Severity assessment and reward calculation
5. **Remediation**: We fix the vulnerability (30-90 days)
6. **Payment**: Reward sent via PayPal, bank transfer, or cryptocurrency

---

## 🛡️ Secure Development Practices

### Code Security

- ✅ All code undergoes security review before deployment
- ✅ Automated security scanning (SAST/DAST) on every commit
- ✅ Dependency vulnerability scanning (GitHub Dependabot)
- ✅ Google-style docstrings with security notes

### Infrastructure Security

- ✅ Docker container security (non-root users, minimal base images)
- ✅ PostgreSQL with SSL/TLS connections
- ✅ Environment variable secrets management
- ✅ Network segmentation (VPC, security groups)
- ✅ Regular security updates and patch management

### API Security

- ✅ Clerk authentication (OAuth 2.0 / OpenID Connect)
- ✅ Token bucket rate limiting (5,000 tokens/day per user)
- ✅ Input validation (Pydantic v2 models)
- ✅ Output sanitization (HTML escaping, error redaction)
- ✅ CORS policies (whitelist-only origins)
- ✅ Content Security Policy (CSP)
- ✅ HTTP Strict Transport Security (HSTS)

### Data Protection

- ✅ Passwords hashed with bcrypt (cost factor 12)
- ✅ OTP codes secure random generation (6 digits, 5-minute expiry)
- ✅ PII redaction in logs (IP addresses, emails)
- ✅ Secure database connections (SSL/TLS)
- ✅ Soft delete (data retention for compliance)

---

## 📞 Security Contact

**Primary Contact**: security@odiseo.ai
**Response Time**: Within 48 hours (business days)
**Office Hours**: Monday-Friday, 9:00-17:00 GMT-5
**Urgent Issues**: Include "[URGENT]" in subject line

**Escalation Path**:
1. Security Team (security@odiseo.ai)
2. Engineering Lead (engineering@odiseo.ai)
3. CTO (cto@odiseo.ai)

---

## 📜 Disclosure Timeline

We follow industry-standard coordinated disclosure practices:

1. **Day 0**: Vulnerability reported
2. **Day 1-2**: Initial triage and acknowledgment
3. **Day 7-14**: Validation and impact assessment
4. **Day 30-90**: Remediation and testing
5. **Day 90+**: Public disclosure (coordinated with reporter)

We request that researchers:
- ⏰ Allow 90 days for remediation before public disclosure
- 📢 Coordinate disclosure timing with our security team
- 🏅 Receive credit in our security acknowledgments (if desired)

---

## 🏆 Security Hall of Fame

We publicly acknowledge security researchers who have responsibly disclosed vulnerabilities:

*No researchers to acknowledge yet. Be the first!*

To be listed:
1. Report a valid vulnerability
2. Follow responsible disclosure guidelines
3. Opt-in to public acknowledgment (we respect privacy)

---

## 📚 Security Resources

### For Developers

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Google Secure Development Guidelines](https://cloud.google.com/security/secure-development)

### For Users

- [API Security Best Practices](./docs/API_SECURITY_BEST_PRACTICES.md) *(coming soon)*
- [Clerk Authentication Guide](./docs/CLERK_SETUP_GUIDE.md)
- [Rate Limiting Documentation](./docs/RATE_LIMITING.md) *(coming soon)*

### Security Audits

- **Phase 1 (CRITICAL)**: Completed 2025-11-07 ✅
- **Phase 2 (HIGH)**: Completed 2025-11-07 ✅
- **Phase 3 (MEDIUM)**: Completed 2025-11-07 ✅
- **Phase 4 (LOW)**: Completed 2025-11-07 ✅
- **External Penetration Test**: Scheduled Q1 2026

---

## 📖 Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-07 | 1.0.0 | Initial security policy |

---

## ⚖️ Legal

By submitting a vulnerability report, you agree to:

1. Not exploit the vulnerability beyond what is necessary for demonstration
2. Keep the vulnerability confidential until it is resolved
3. Not demand or negotiate a reward before the issue is validated
4. Act in good faith to avoid privacy violations and service disruption

We commit to:

1. Respond to your report within 48 hours
2. Provide an estimated timeline for remediation
3. Credit you in our security acknowledgments (if desired)
4. Not pursue legal action against researchers acting in good faith

---

**Last Updated**: November 7, 2025
**Contact**: security@odiseo.ai
**Version**: 1.0.0
