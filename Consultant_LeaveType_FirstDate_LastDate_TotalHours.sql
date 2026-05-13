DECLARE @StartMonday date =
    DATEADD(
        DAY,
        -((DATEPART(WEEKDAY, CAST(GETDATE() AS date)) + @@DATEFIRST - 2) % 7),
        CAST(GETDATE() AS date)
    );

DECLARE @FromDate date = DATEADD(MONTH, -6, @StartMonday);

SELECT
    RA.Name AS ResourceActivityName,
    AA.Name AS ActivityAssignmentName,
    COUNT(*) AS EntryCount,
    MIN(CAST(FTE.KimbleOne__TimePeriodStartDate__c AS date)) AS FirstDate,
    MAX(CAST(FTE.KimbleOne__TimePeriodStartDate__c AS date)) AS LastDate,
    SUM(FTE.KimbleOne__EntryUnits__c) AS TotalHours,
    SUM(FTE.EntryUnits__c) AS TotalDays
FROM REPL_SF.ForecastTimeEntry FTE
LEFT JOIN REPL_SF.ActivityAssignment AA
    ON AA.ID = FTE.KimbleOne__ActivityAssignment__c
LEFT JOIN REPL_SF.ResourceActivity RA
    ON RA.Id = AA.KimbleOne__ResourcedActivity__c
LEFT JOIN REPL_SF.Resource R
    ON R.Id = AA.KimbleOne__Resource__c
LEFT JOIN REPL_SF.[User] U
    ON U.Id = R.KimbleOne__User__c
WHERE CAST(FTE.KimbleOne__TimePeriodStartDate__c AS date)
      BETWEEN @FromDate AND @StartMonday
  AND U.Name IS NOT NULL
GROUP BY
    RA.Name,
    AA.Name
ORDER BY
    ResourceActivityName,
    ActivityAssignmentName;