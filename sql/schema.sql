
-- SQL Server schema (simplified)
CREATE TABLE Customer (
  CustomerID INT PRIMARY KEY,
  Name NVARCHAR(120),
  Email NVARCHAR(120)
);

CREATE TABLE Claim (
  ClaimID INT PRIMARY KEY,
  CustomerID INT REFERENCES Customer(CustomerID),
  CreatedAt DATETIME2,
  ClosedAt DATETIME2 NULL,
  Status NVARCHAR(30),
  SLA_Hours INT,
  Priority NVARCHAR(20),
  Reason NVARCHAR(60)
);

CREATE TABLE Claim_Event (
  EventID INT IDENTITY PRIMARY KEY,
  ClaimID INT REFERENCES Claim(ClaimID),
  EventType NVARCHAR(40),
  EventAt DATETIME2
);
