# Candidate Application & Status Tracking

## 1. Candidate Application

Candidate job ki public application link open karega.

No account or login will be required.

### Application Form

Candidate will provide:

* Full Name
* Email
* Phone Number
* CV / Resume
* Expected Salary — Optional
* Consent to store application information

After submitting the form:

**Candidate Application → CV Upload → Application Created → Application ID Generated → Confirmation Email**

---

## 2. Application ID

System automatically generates a unique Application ID for every application.

Example:

```text
APP-2026-00421
```

The Application ID will be associated with:

* Candidate
* Job
* CV
* Application status
* Application history
* Interview records
* HR decisions
* Timestamps

The candidate will receive this Application ID in the confirmation email.

---

## 3. Confirmation Email

Immediately after successful application submission, the system will send an automated email.

### Example Email

**Subject:** Application Received – Software Engineer

Hello Ahmed,

Thank you for applying for the **Software Engineer** position.

Your application has been successfully received.

**Application ID:** APP-2026-00421

You can check the current status of your application using the link below:

**Track Your Application**

Your application is currently:

**Application Received**

We will notify you by email when there is an important update to your application.

Regards,
HR Team
Evyol Group of Industries

---

## 4. Tracking Link

The email will contain a unique tracking link.

Example:

```text
https://careers.company.com/application/APP-2026-00421
```

The candidate does not need to create an account.

The tracking page will identify the application using a secure tracking token rather than exposing internal database information.

---

## 5. Candidate Status Page

When the candidate opens the tracking link, they will see:

```text
Application ID
APP-2026-00421

Position
Software Engineer

Application Status

✓ Application Received
✓ Under Review
→ Shortlisted
○ Technical Interview
○ HR Interview
○ Final Review
○ Final Decision
```

Only candidate-facing recruitment stages will be displayed.

---

## 6. Candidate-Facing Statuses

The system will use a simple status flow:

```text
Application Received
        ↓
Under Review
        ↓
Shortlisted
        ↓
Interview Scheduled
        ↓
Technical Interview
        ↓
HR Interview
        ↓
Final Review
        ↓
Selected / Not Selected
```

The candidate will see the current stage and completed stages.

---

## 7. Status Updates

Whenever an important recruitment stage changes, the system can automatically notify the candidate.

### Application Received

Candidate receives confirmation immediately after applying.

### Shortlisted

Candidate receives an email informing them that their application has progressed to the next stage.

### Interview Scheduled

Candidate receives:

* Interview type
* Date
* Time
* Interview instructions
* Meeting link, if applicable

### Next Round

Candidate receives a notification when they progress to another interview stage.

### Selected

Candidate receives a selection/congratulations email after HR's final approval.

### Not Selected

Candidate receives a professionally written rejection email after HR approval.

---

## 8. Internal vs Candidate Information

The system must clearly separate **internal HR information** from **candidate-facing information**.

### Candidate Can See

* Application ID
* Position applied for
* Current application stage
* Completed recruitment stages
* Interview schedule
* Important instructions
* Final application outcome

### Candidate Cannot See

* AI matching score
* AI ranking
* Other candidates
* Internal candidate ranking
* HR notes
* Interviewer comments
* Salary analysis
* Internal rejection reasoning
* AI confidence score
* Internal validation flags
* HR override reasons
* Other internal recruitment data

---

## 9. HR Status Control

HR will control the candidate's recruitment status.

AI agents can provide recommendations, but they cannot directly make the final hiring decision.

Example:

```text
AI Screening
      ↓
AI Recommendation
      ↓
HR Review
      ↓
HR Approves / Overrides
      ↓
Candidate Status Updated
      ↓
Candidate Notification
```

For example:

```text
AI Recommendation:
MATCH

Evidence:
3 years React experience
2 years Node.js experience

HR Decision:
Approve

Candidate Status:
Shortlisted
```

The candidate will only see:

```text
Application Status: Shortlisted
```

---

## 10. Email Notification Workflow

The backend notification workflow will be:

```text
Application Submitted
        ↓
Create Application
        ↓
Generate Application ID
        ↓
Generate Secure Tracking Token
        ↓
Save Application
        ↓
Send Confirmation Email
        ↓
Candidate Opens Tracking Link
        ↓
View Current Status
```

For later updates:

```text
HR Changes Status
        ↓
Validate Status Transition
        ↓
Update Application
        ↓
Create Status History
        ↓
Trigger Notification
        ↓
Send Email
        ↓
Candidate Opens Tracking Link
        ↓
View Updated Status
```

---

## 11. Application Status History

Every important status change should be stored.

Example:

```text
Application History

02 Sep 2026
Application Received

03 Sep 2026
Under Review

04 Sep 2026
Shortlisted

06 Sep 2026
Technical Interview Scheduled
```

This history is useful for HR auditing and recruitment tracking.

The candidate can see a simplified version of this history.

---

## 12. Security

The tracking page must not expose sensitive candidate or company information.

The system should use:

* Secure tracking tokens
* HTTPS
* Expiring or revocable tracking links where appropriate
* Rate limiting
* No internal database IDs in public URLs
* Access validation
* Audit logging

The public tracking page should only return information belonging to that application.

---

## 13. Complete Candidate Journey

The complete candidate experience will be:

```text
Job Published
      ↓
Candidate Opens Job
      ↓
Candidate Fills Application Form
      ↓
Uploads CV
      ↓
Submits Application
      ↓
Application Created
      ↓
Application ID Generated
      ↓
Confirmation Email Sent
      ↓
Candidate Opens Tracking Link
      ↓
Application Received
      ↓
CV Processing
      ↓
AI Screening
      ↓
HR Review
      ↓
Shortlisted
      ↓
Interview Scheduled
      ↓
Technical Interview
      ↓
HR Interview
      ↓
Final HR Review
      ↓
┌───────────────────────┐
│                       │
Selected           Not Selected
│                       │
↓                       ↓
Joining Date       Feedback Draft
│                       ↓
↓                  HR Approval
Congratulations         ↓
Email                Email Sent
```

---

## 14. V1 Implementation

For V1, the following components will be implemented:

### Candidate Portal

* Public job application page
* CV upload
* Application form
* Application submission
* Application ID generation
* Secure tracking link
* Candidate status page

### Backend

* Application API
* Candidate database
* Application status management
* Status history
* Secure tracking token
* Email notification service
* Audit logs

### HR Dashboard

HR will be able to:

* View applications
* Change candidate status
* Schedule interviews
* Review candidate information
* Review AI recommendations
* Approve/override AI recommendations
* Trigger candidate communications

### Email Service

The system will automatically send:

* Application confirmation
* Shortlist notification
* Interview invitation
* Interview schedule/update
* Selection email
* Rejection email

HR approval will be required for sensitive/final communications where appropriate.

---

## 15. Final Principle

The candidate should **never need to contact HR just to ask, "What is the status of my application?"**

The system should provide:

**Apply → Receive Email → Open Tracking Link → Check Status → Receive Updates**

At the same time:

**AI recommends → HR verifies → HR decides → System communicates**
