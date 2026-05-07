DECLARE @ThisWeekStart date =
    DATEADD(WEEK, DATEDIFF(WEEK, 0, GETDATE()), 0);

DECLARE @cols nvarchar(max) = N'';
DECLARE @sql  nvarchar(max) = N'';

;WITH Weeks AS (
    SELECT 1 AS WeekNo, DATEADD(WEEK, -1, @ThisWeekStart) AS WeekStart
    UNION ALL
    SELECT WeekNo + 1, DATEADD(WEEK, -(WeekNo + 1), @ThisWeekStart)
    FROM Weeks
    WHERE WeekNo < 26
)
SELECT @cols = @cols + '
    SUM(CASE WHEN tea.WeekStart = ''' + CONVERT(varchar(10), WeekStart, 120) + ''' THEN tea.Logged_Hours ELSE 0 END) AS [Logged_Hours_' + CONVERT(varchar(10), WeekStart, 120) + '],
    SUM(CASE WHEN tea.WeekStart = ''' + CONVERT(varchar(10), WeekStart, 120) + ''' THEN tea.Billable_Hours ELSE 0 END) AS [Billable_Hours_' + CONVERT(varchar(10), WeekStart, 120) + '],
    SUM(CASE WHEN tea.WeekStart = ''' + CONVERT(varchar(10), WeekStart, 120) + ''' THEN tea.Billable_Days ELSE 0 END) AS [Billable_Days_' + CONVERT(varchar(10), WeekStart, 120) + '],
    SUM(CASE WHEN tea.WeekStart = ''' + CONVERT(varchar(10), WeekStart, 120) + ''' THEN tea.Consumed_Days ELSE 0 END) AS [Consumed_Days_' + CONVERT(varchar(10), WeekStart, 120) + '],'
FROM Weeks
ORDER BY WeekNo;

SET @cols = LEFT(@cols, LEN(@cols) - 1);

SET @sql = N'
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
        AND tp.KimbleOne__EndDate__c >= DATEADD(WEEK, -26, ''' + CONVERT(varchar(10), @ThisWeekStart, 120) + ''')
        AND tp.KimbleOne__EndDate__c <  ''' + CONVERT(varchar(10), @ThisWeekStart, 120) + '''
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
' + @cols + '
FROM Base b
LEFT JOIN TimeEntryAgg tea
    ON tea.ActivityAssignment_Id = b.ActivityAssignment_Id
GROUP BY
    b.Consultant_Name,
    b.Level,
    b.Job_Title,
    b.Location,
    b.Project_Name,
    b.Project_Type,
    b.Project_Status,
    b.Assignment_Start,
    b.Assignment_End
ORDER BY
    b.Consultant_Name,
    b.Project_Name;
';

EXEC sp_executesql @sql;