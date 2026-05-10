# PopCorn Mini App - Deployment Checklist

## Pre-Deployment Preparation

### 1. Environment Setup ✓
- [ ] All environment variables are set and verified
- [ ] `.env` file is properly configured
- [ ] Backup of current production state created
- [ ] All team members notified of deployment

### 2. Code Review ✓
- [ ] All code changes reviewed and approved
- [ ] No merge conflicts in main branch
- [ ] All tests passing locally
- [ ] Documentation updated

### 3. Database Preparation ✓
- [ ] Database backup created
- [ ] Migration scripts tested
- [ ] Database connectivity verified
- [ ] Current content counts documented:
  - Movies: ___
  - Series: ___
  - Episodes: ___

---

## Testing Phase

### 4. Pre-Deployment Tests ✓

#### Environment Variables Check
```bash
./run_tests.sh --test-only --component pre-deployment
```
- [ ] All required environment variables present
- [ ] HuggingFace tokens valid
- [ ] Telegram bot tokens valid
- [ ] Database credentials correct
- [ ] TMDB API key working

#### Database Connectivity
- [ ] Database connection successful
- [ ] Read operations working
- [ ] Write operations working
- [ ] Query performance acceptable

#### File Permissions
- [ ] All critical files readable
- [ ] Log directories writable
- [ ] Backup directories accessible

### 5. HuggingFace Spaces Tests ✓

```bash
./run_tests.sh --test-only --component hf-spaces
```

For each Space (5 total):
- [ ] PopCornMiniApp
  - [ ] Build successful
  - [ ] No `__pycache__` files
  - [ ] requirements.txt correct
  - [ ] Health endpoint responding
  - [ ] Logs clean

- [ ] PopCornMiniApp-Mirror1
  - [ ] Build successful
  - [ ] Health endpoint responding
  - [ ] Load balancing working

- [ ] PopCornMiniApp-Mirror2
  - [ ] Build successful
  - [ ] Health endpoint responding
  - [ ] Load balancing working

- [ ] PopCornMiniApp-Mirror3
  - [ ] Build successful
  - [ ] Health endpoint responding
  - [ ] Load balancing working

- [ ] PopCornMiniApp-Mirror4
  - [ ] Build successful
  - [ ] Health endpoint responding
  - [ ] Load balancing working

### 6. Telegram Synchronization Tests ✓

```bash
./run_tests.sh --test-only --component telegram-sync
```

#### Bot Access (9 groups)
- [ ] PRIVATE_GROUPE_1_ID accessible
- [ ] PRIVATE_GROUPE_2_ID accessible
- [ ] PRIVATE_GROUPE_3_ID accessible
- [ ] PRIVATE_GROUPE_4_ID accessible
- [ ] PRIVATE_GROUPE_5_ID accessible
- [ ] PRIVATE_GROUPE_6_ID accessible
- [ ] PRIVATE_GROUPE_7_ID accessible
- [ ] Group private 8 accessible
- [ ] PUBLIC_CHANNEL_ID accessible

#### Scanner Tests
- [ ] Scanner starts without errors
- [ ] Memory usage stable (no leaks)
- [ ] CPU usage acceptable
- [ ] Message processing working
- [ ] Error handling functional

#### Room Sync Tests
- [ ] No race conditions detected
- [ ] Multi-group sync working
- [ ] Sync status accurate
- [ ] Error recovery working

### 7. Frontend Synchronization Tests ✓

```bash
./run_tests.sh --test-only --component frontend-sync
```

#### Database to Frontend Sync
- [ ] `sync_db_to_frontend.py` runs successfully
- [ ] All JSON files generated:
  - [ ] `movies_data.json`
  - [ ] `series_data.json`
  - [ ] `stats_data.json`
  - [ ] `frontend_data.json`

#### Verification
- [ ] `verify_frontend_sync.py` passes
- [ ] Content counts match database:
  - Movies: DB ___ = Frontend ___
  - Series: DB ___ = Frontend ___
- [ ] JSON files valid
- [ ] File sizes reasonable
- [ ] No data corruption

#### WebSocket Tests
- [ ] WebSocket server starts
- [ ] Connections accepted
- [ ] Notifications sent
- [ ] Real-time updates working

### 8. Integration Tests ✓

```bash
./run_tests.sh --test-only --component integration
```

#### End-to-End Flow
- [ ] New content posted to Telegram
- [ ] Scanner detects new content
- [ ] Database updated correctly
- [ ] Frontend sync triggered
- [ ] Content appears in frontend
- [ ] WebSocket notification sent

#### Load Balancing
- [ ] Requests distributed across Spaces
- [ ] Failover working
- [ ] Performance acceptable

#### Database Sharding
- [ ] Sharding strategy working
- [ ] Data distributed correctly
- [ ] Queries optimized

---

## Deployment Phase

### 9. Dry Run ✓

```bash
./run_tests.sh --dry-run --full
```

- [ ] Dry run completed successfully
- [ ] No critical errors
- [ ] All components ready
- [ ] Deployment plan reviewed

### 10. HuggingFace Spaces Deployment ✓

```bash
./run_tests.sh --deploy-only --component hf-spaces
```

For each Space:
- [ ] Code pushed to repository
- [ ] Build triggered
- [ ] Build completed successfully
- [ ] Space status: RUNNING
- [ ] Health check passing
- [ ] Logs reviewed

**Rollback Plan:**
- Previous version tag: ___________
- Rollback command: `git revert <commit>`
- Estimated rollback time: 5-10 minutes

### 11. Telegram Fixes Deployment ✓

```bash
./run_tests.sh --deploy-only --component telegram-sync
```

- [ ] Scanner updated
- [ ] Room sync updated
- [ ] Multi-group sync deployed
- [ ] Bots restarted
- [ ] Sync status verified

**Rollback Plan:**
- Backup location: ___________
- Restore command: `cp -r backup/* .`
- Estimated rollback time: 2-3 minutes

### 12. Frontend Sync Deployment ✓

- [ ] Sync scripts deployed
- [ ] Cron jobs updated
- [ ] Initial sync completed
- [ ] Verification passed

---

## Post-Deployment Validation

### 13. Immediate Validation (0-15 minutes) ✓

```bash
./run_tests.sh --test-only
```

#### All Spaces Health Check
- [ ] All 5 Spaces responding
- [ ] Response times < 2 seconds
- [ ] No error logs
- [ ] Memory usage normal
- [ ] CPU usage normal

#### Telegram Sync Status
- [ ] Scanner running
- [ ] No memory leaks
- [ ] All groups syncing
- [ ] No race conditions
- [ ] Error rate < 1%

#### Frontend Sync Status
- [ ] Latest content visible
- [ ] Counts accurate
- [ ] WebSocket working
- [ ] No sync delays

### 14. Short-term Monitoring (15-60 minutes) ✓

#### Performance Metrics
- [ ] Average response time: ___ ms
- [ ] Error rate: ___ %
- [ ] Active users: ___
- [ ] Concurrent connections: ___

#### System Health
- [ ] CPU usage: ___ %
- [ ] Memory usage: ___ %
- [ ] Disk usage: ___ %
- [ ] Network traffic: ___ MB/s

#### User Experience
- [ ] No user complaints
- [ ] Search working
- [ ] Streaming working
- [ ] Navigation smooth

### 15. Long-term Monitoring (1-24 hours) ✓

#### Daily Checks
- [ ] Morning check (9 AM): ___
- [ ] Afternoon check (3 PM): ___
- [ ] Evening check (9 PM): ___
- [ ] Night check (3 AM): ___

#### Metrics to Track
- [ ] Total requests: ___
- [ ] Unique users: ___
- [ ] New content synced: ___
- [ ] Error count: ___
- [ ] Uptime: ___ %

---

## Rollback Procedures

### When to Rollback
- Critical errors affecting > 50% of users
- Data corruption detected
- Security vulnerability discovered
- Performance degradation > 50%
- Sync failures > 10%

### Rollback Steps

#### 1. Immediate Actions
```bash
# Stop current deployment
./run_tests.sh --dry-run  # Verify rollback plan

# Restore from backup
cd backups/[TIMESTAMP]
cp -r * ../

# Restart services
systemctl restart popcorn-app
```

#### 2. HuggingFace Spaces Rollback
```bash
# For each Space
git checkout [PREVIOUS_TAG]
git push --force
# Wait for rebuild
```

#### 3. Database Rollback
```bash
# Restore database backup
psql popcorn < backups/[TIMESTAMP]/database.sql
```

#### 4. Verification
```bash
./run_tests.sh --test-only
```

---

## Post-Deployment Tasks

### 16. Documentation ✓
- [ ] Deployment report generated
- [ ] Test results documented
- [ ] Issues logged
- [ ] Lessons learned recorded

### 17. Communication ✓
- [ ] Team notified of success
- [ ] Users informed of updates
- [ ] Stakeholders updated
- [ ] Documentation published

### 18. Cleanup ✓
- [ ] Old backups archived
- [ ] Temporary files removed
- [ ] Logs rotated
- [ ] Cache cleared

---

## Success Criteria

### Deployment is Successful When:
- ✅ All 5 HuggingFace Spaces are RUNNING
- ✅ All 9 Telegram groups syncing
- ✅ Database-to-Frontend sync working
- ✅ 38 movies and 16 series visible
- ✅ No critical errors in logs
- ✅ Response time < 2 seconds
- ✅ Error rate < 1%
- ✅ User experience smooth
- ✅ All tests passing

### Deployment is Failed When:
- ❌ Any Space in ERROR state
- ❌ Telegram sync not working
- ❌ Frontend sync failing
- ❌ Data corruption detected
- ❌ Critical errors in logs
- ❌ Response time > 5 seconds
- ❌ Error rate > 5%
- ❌ User complaints increasing

---

## Emergency Contacts

### Team Members
- **Lead Developer:** ___________
- **DevOps Engineer:** ___________
- **Database Admin:** ___________
- **QA Lead:** ___________

### External Services
- **HuggingFace Support:** support@huggingface.co
- **Telegram Support:** https://telegram.org/support
- **TMDB Support:** https://www.themoviedb.org/talk

---

## Deployment Sign-off

### Pre-Deployment
- [ ] **Developer:** __________ Date: __________
- [ ] **QA Lead:** __________ Date: __________
- [ ] **DevOps:** __________ Date: __________

### Post-Deployment
- [ ] **Developer:** __________ Date: __________
- [ ] **QA Lead:** __________ Date: __________
- [ ] **DevOps:** __________ Date: __________

### Final Approval
- [ ] **Project Manager:** __________ Date: __________

---

## Notes

### Deployment Date: __________
### Deployment Time: __________
### Deployment Duration: __________
### Issues Encountered: 
___________________________________________
___________________________________________
___________________________________________

### Resolutions Applied:
___________________________________________
___________________________________________
___________________________________________

### Lessons Learned:
___________________________________________
___________________________________________
___________________________________________

---

**Last Updated:** 2026-05-09
**Version:** 1.0
**Status:** Ready for Production