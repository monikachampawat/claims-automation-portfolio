
# System Design

## High-Level Architecture
```mermaid
flowchart LR
  A[Client (Web/Form/API)] -->|REST| G(API Gateway)
  G --> V[Validation Service]
  V --> C[Claims Service (.NET)]
  C --> D[(SQL Server)]
  C --> Q[(Queue/Events)]
  Q --> P[Processing Workers]
  D --> E[ETL]
  E --> BI[Power BI]
```

## Data Flow (Level 0)
```mermaid
sequenceDiagram
  participant User
  participant API as Intake API
  participant Rules as Validation Rules
  participant DB as Claims DB
  participant BI as Power BI
  User->>API: Submit Claim
  API->>Rules: Validate
  Rules-->>DB: Insert/Update
  DB-->>BI: ETL to Analytics Store
  BI-->>User: KPIs & Dashboards
```

## Simplified ER Model
```mermaid
classDiagram
  class Customer {
    +int CustomerID
    +string Name
    +string Email
  }
  class Claim {
    +int ClaimID
    +int CustomerID
    +datetime CreatedAt
    +datetime ClosedAt
    +string Status
    +int SLA_Hours
    +string Priority
    +string Reason
  }
  class Claim_Event {
    +int EventID
    +int ClaimID
    +string EventType
    +datetime EventAt
  }
  Customer <|-- Claim
  Claim <|-- Claim_Event
```
