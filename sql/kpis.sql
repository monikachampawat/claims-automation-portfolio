
-- KPI: Average Processing Time (hours)
SELECT AVG(DATEDIFF(hour, CreatedAt, ClosedAt)) AS AvgProcessingHours
FROM Claim
WHERE ClosedAt IS NOT NULL;

-- KPI: SLA Compliance (%)
SELECT 100.0 * SUM(CASE WHEN DATEDIFF(hour, CreatedAt, ClosedAt) <= SLA_Hours THEN 1 ELSE 0 END) / COUNT(*) AS SLACompliancePct
FROM Claim
WHERE ClosedAt IS NOT NULL;

-- KPI: Aging buckets for open claims
SELECT CASE 
         WHEN DATEDIFF(hour, CreatedAt, ISNULL(ClosedAt, SYSUTCDATETIME())) <= 24 THEN '0-24h'
         WHEN DATEDIFF(hour, CreatedAt, ISNULL(ClosedAt, SYSUTCDATETIME())) <= 48 THEN '24-48h'
         ELSE '>48h' END AS AgingBucket,
       COUNT(*) AS Cnt
FROM Claim
WHERE ClosedAt IS NULL OR Status <> 'Closed'
GROUP BY CASE 
         WHEN DATEDIFF(hour, CreatedAt, ISNULL(ClosedAt, SYSUTCDATETIME())) <= 24 THEN '0-24h'
         WHEN DATEDIFF(hour, CreatedAt, ISNULL(ClosedAt, SYSUTCDATETIME())) <= 48 THEN '24-48h'
         ELSE '>48h' END;
