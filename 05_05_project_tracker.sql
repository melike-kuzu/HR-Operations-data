DECLARE @ThisWeekStart date =
    DATEADD(WEEK, DATEDIFF(WEEK, 0, GETDATE()), 0);

DECLARE @LastWeekStart date =
    DATEADD(WEEK, -1, @ThisWeekStart);

WITH Base AS (
    SELECT
        aa.Id AS ActivityAssignment_Id,
        e.DISPLAY_NAME AS Consultant_Name,
        e.JOB_LEVEL AS Level,
        e.JOB_TITLE AS Job_Title,
        e.OFFICE_LOCATION AS Location,
        p.PROJECT_NAME AS Project_Name,
        p.PROJECT_TYPE AS Project_Type,
        p.PROJECT_STATUS AS Project_Status,
        aa.KimbleOne__StartDate__c AS Assignment_Start,
        aa.KimbleOne__ForecastP2EndDate__c AS Assignment_End
    FROM REPL_SF.ActivityAssignment aa
    JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c
    LEFT JOIN REPL_SF.[User] u
        ON u.Id = r.KimbleOne__User__c
    LEFT JOIN ANALYTICS.DIM_EMPLOYEE e
        ON e.INTEGRATION_ID = u.Username
    LEFT JOIN REPL_SF.ResourceActivity ra
        ON ra.Id = aa.KimbleOne__ResourcedActivity__c
    LEFT JOIN ANALYTICS.DIM_PROJECT p
        ON p.PROJECT_ID = ra.Id
    WHERE e.DISPLAY_NAME IS NOT NULL
),

TimeEntryAgg AS (
    SELECT
        te.KimbleOne__ActivityAssignment__c AS ActivityAssignment_Id,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c), 0) AS WeekStart,
        SUM(te.KimbleOne__EntryUnits__c) AS Logged_Hours,
        SUM(te.KimbleOne__FactoredEntryUnits__c) AS Billable_Hours,
        SUM(te.KimbleOne__FactoredEntryUnits__c) / 8.0 AS Billable_Days,
        SUM(te.KimbleOne__EntryUnits__c) / 8.0 AS Consumed_Days
    FROM REPL_SF.[TimeEntry] te
    LEFT JOIN REPL_SF.TimePeriod tp
        ON tp.Id = te.KimbleOne__TimePeriod__c
    WHERE
        te.KimbleOne__ActivityAssignment__c IS NOT NULL
        AND tp.KimbleOne__EndDate__c > '2024-01-01'
        AND tp.KimbleOne__EndDate__c <= CAST(GETDATE() AS date)
    GROUP BY
        te.KimbleOne__ActivityAssignment__c,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c), 0)
)

SELECT
    b.Consultant_Name,
    b.Level,
    b.Job_Title,
    b.Location,
    b.Project_Name,
    b.Project_Type,
    b.Project_Status,
    b.Assignment_Start,
    b.Assignment_End,
    tea.WeekStart,
    tea.Logged_Hours,
    tea.Billable_Hours,
    tea.Billable_Days,
    tea.Consumed_Days
FROM Base b
JOIN TimeEntryAgg tea
    ON tea.ActivityAssignment_Id = b.ActivityAssignment_Id
WHERE tea.WeekStart = @LastWeekStart
ORDER BY
    b.Consultant_Name,
    tea.WeekStart,
    b.Project_Name;