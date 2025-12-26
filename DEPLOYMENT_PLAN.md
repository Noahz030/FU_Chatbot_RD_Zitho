# 🚀 Arena Deployment Plan

## Phase 1: Production Environment Setup

### 1.1 Server Infrastructure
- [ ] Provision Server/VM (Ubuntu 22.04, 4GB RAM, 20GB SSD)
- [ ] Configure networking (Firewall rules, Port forwarding)
- [ ] Setup SSH access and key-based authentication
- [ ] Install Docker & Docker Compose

### 1.2 Domain & SSL
- [ ] Register domain (e.g., arena.ki-campus.org)
- [ ] Configure DNS
- [ ] Setup Let's Encrypt certificates (auto-renewal)

### 1.3 Environment Preparation
- [ ] Clone repository to server
- [ ] Create `.env.prod` with production secrets from Key Vault
- [ ] Configure backup storage (Azure Blob Storage or S3)

## Phase 2: Docker Stack Configuration

### 2.1 Production docker-compose.yaml
```yaml
Services needed:
- openwebui-api (Port 8001, internal)
- voting-ui (Port 8002, internal)
- nginx (Port 80/443, public)
- postgres (Port 5432, internal, with persistent volume)
- qdrant (external, use remote URL)
- langfuse (optional, for monitoring)
```

### 2.2 Nginx Reverse Proxy
- [ ] Create nginx.conf with:
  - SSL/TLS termination
  - Rate limiting for /arena/vote endpoint
  - Gzip compression
  - Health check probes
- [ ] Setup certificate auto-renewal

### 2.3 API Improvements for Production
- [ ] Fix dynamic comparison loading (reload from JSONL)
- [ ] Add pagination support (limit, offset)
- [ ] Add authentication to voting endpoints
- [ ] Add detailed logging/audit trail
- [ ] Add error handling & graceful degradation

## Phase 3: Data Management

### 3.1 Backup Strategy
- [ ] Daily automated backups of arena_votes.jsonl
- [ ] Store in Azure Blob Storage with retention policy
- [ ] Test restore procedure

### 3.2 Monitoring & Logging
- [ ] Setup ELK stack or Azure Monitor
- [ ] Create dashboards for:
  - Vote volume & trends
  - API response times
  - Error rates
- [ ] Setup alerts for critical issues

### 3.3 Database Setup
- [ ] Initialize PostgreSQL in production
- [ ] Create database schema
- [ ] Setup regular vacuum/maintenance jobs

## Phase 4: Large-Scale Seeding

### 4.1 Prepare Questions
- [ ] Collect 200-500 production questions
- [ ] Translate to German (if needed)
- [ ] Create questions.csv

### 4.2 Batch Seeding
```bash
# Use improved script with:
python scripts/arena_seed_with_llm.py \
  --input questions_prod.csv \
  --api-url https://arena.ki-campus.org \
  --batch-size 50 \
  --max-workers 5
```

### 4.3 Validate Results
- [ ] Check all answers generated
- [ ] Verify citations present
- [ ] Sample random comparisons for quality

## Phase 5: Testing & Validation

### 5.1 Load Testing
- [ ] Test with 1000+ comparisons
- [ ] Simulate 100 concurrent users voting
- [ ] Measure response times

### 5.2 User Acceptance Testing
- [ ] Invite team to vote on comparisons
- [ ] Collect feedback on UI/UX
- [ ] Test mobile responsiveness

### 5.3 Security Testing
- [ ] Penetration test voting endpoints
- [ ] Test CSRF protection
- [ ] Verify rate limiting works

## Phase 6: Launch & Monitoring

### 6.1 Pre-Launch Checklist
- [ ] All tests passing
- [ ] Monitoring setup and verified
- [ ] Backup procedure tested
- [ ] Team trained on system

### 6.2 Launch
- [ ] Deploy to production server
- [ ] Smoke test all endpoints
- [ ] Monitor system closely for 24h

### 6.3 Post-Launch
- [ ] Weekly vote summary reports
- [ ] Monthly model performance analysis
- [ ] Quarterly system optimization

## Timeline Estimate

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| 1. Infrastructure | 2-3 days | Jan 2 | Jan 4 |
| 2. Docker Config | 2-3 days | Jan 5 | Jan 7 |
| 3. Data Management | 1-2 days | Jan 8 | Jan 9 |
| 4. Large Seeding | 1-2 days | Jan 10 | Jan 11 |
| 5. Testing | 2-3 days | Jan 12 | Jan 14 |
| 6. Launch | 1 day | Jan 15 | Jan 15 |

**Total: ~2 weeks from start to production launch**

## Team Responsibilities

- **DevOps**: Infrastructure, Docker, monitoring
- **Backend**: API improvements, authentication
- **QA**: Testing, validation
- **Product**: Questions, user feedback
- **Security**: Penetration testing, data protection

## Success Criteria

- ✅ Arena voting live for team
- ✅ 100+ comparisons available
- ✅ 99.9% API uptime
- ✅ <500ms response times
- ✅ Daily automated backups
- ✅ Team actively voting

## Risks & Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| API performance issues | Medium | Load testing, caching strategy |
| Data loss | Low | 3x redundant backups |
| Security vulnerabilities | Low | Professional penetration test |
| User adoption | Medium | Easy UI, clear instructions |

---

**Next Action**: Confirm Phase 1 infrastructure requirements with team
