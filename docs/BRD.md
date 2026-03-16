
# Business Requirements Document (BRD)

## Business Problem
The current claims process is slow and manual, with limited visibility into status and SLA performance.

## Objectives
- Automate intake and validation
- Improve SLA adherence
- Provide real-time KPI dashboards
- Reduce manual effort and errors

## Scope
**In:** Claims submission, validations, data store, dashboard, SLA alerts

**Out:** Payment gateway, mobile apps

## Stakeholders
Operations, Claims Team, IT Development, QA, Compliance

## AS-IS Workflow
1) Email/PDF intake → 2) Manual entry → 3) Manual validations → 4) Agent processing → 5) Excel reports

## TO-BE Workflow
1) Form/API intake → 2) Auto validations → 3) Auto assignment → 4) Real‑time status → 5) KPI dashboards

## Functional Requirements
- FR1 Intake via form/API
- FR2 Validation rules
- FR3 SLA alerts
- FR4 Real‑time status updates
- FR5 Daily KPI generation

## Non‑Functional Requirements
- Availability 99%
- Response time <2s for lookups
- Data accuracy on validated fields = 100%
