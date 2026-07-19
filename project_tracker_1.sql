SET NOCOUNT ON;

DECLARE @ThisWeekStart date =
    DATEADD(WEEK, DATEDIFF(WEEK, 0, GETDATE()), 0);

DECLARE @WindowStart date =
    DATEADD(YEAR, -1, @ThisWeekStart);

DECLARE @SubmissionWindowStart date =
    DATEADD(WEEK, -3, @ThisWeekStart);

WITH Base AS (
    SELECT
        aa.Id AS ActivityAssignment_Id,
        r.Id AS Resource_Id,
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
    WHERE
        e.DISPLAY_NAME IS NOT NULL
        AND p.PROJECT_NAME IS NOT NULL
),

TimeEntryAgg AS (
    SELECT
        te.KimbleOne__ActivityAssignment__c AS ActivityAssignment_Id,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c), 0) AS WeekStart,
        SUM(te.KimbleOne__EntryUnits__c) AS Logged_Hours,
        SUM(te.KimbleOne__EntryUnits__c) / 8.0 AS Consumed_Days
    FROM REPL_SF.[TimeEntry] te
    JOIN REPL_SF.TimePeriod tp
        ON tp.Id = te.KimbleOne__TimePeriod__c
    WHERE
        te.KimbleOne__ActivityAssignment__c IS NOT NULL
        AND tp.KimbleOne__EndDate__c >= @WindowStart
        AND tp.KimbleOne__EndDate__c < @ThisWeekStart
    GROUP BY
        te.KimbleOne__ActivityAssignment__c,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c), 0)
),

SubmissionStatus AS (
    SELECT
        te.KimbleOne__ActivityAssignment__c AS ActivityAssignment_Id,
        CASE
            WHEN COUNT(DISTINCT DATEADD(WEEK, DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c), 0)) = 3
            THEN 'Active'
            ELSE 'Inactive'
        END AS Submission
    FROM REPL_SF.[TimeEntry] te
    JOIN REPL_SF.TimePeriod tp
        ON tp.Id = te.KimbleOne__TimePeriod__c
    WHERE
        te.KimbleOne__ActivityAssignment__c IS NOT NULL
        AND tp.KimbleOne__EndDate__c >= @SubmissionWindowStart
        AND tp.KimbleOne__EndDate__c < @ThisWeekStart
        AND ISNULL(te.KimbleOne__EntryUnits__c, 0) > 0
    GROUP BY
        te.KimbleOne__ActivityAssignment__c
),

LeaveEntryAgg AS (
    SELECT
        r.Id AS Resource_Id,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, CAST(fte.KimbleOne__TimePeriodStartDate__c AS date)), 0) AS WeekStart,
        COALESCE(
            NULLIF(LTRIM(RTRIM(ra.Name)), ''),
            NULLIF(LTRIM(RTRIM(aa.Name)), ''),
            'Leave'
        ) AS Leave_Type,
        SUM(ISNULL(fte.KimbleOne__EntryUnits__c, 0)) AS Leave_Hours
    FROM REPL_SF.ForecastTimeEntry fte
    LEFT JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id = fte.KimbleOne__ActivityAssignment__c
    LEFT JOIN REPL_SF.ResourceActivity ra
        ON ra.Id = aa.KimbleOne__ResourcedActivity__c
    LEFT JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c
    WHERE
        fte.KimbleOne__TimePeriodStartDate__c >= @WindowStart
        AND fte.KimbleOne__TimePeriodStartDate__c < @ThisWeekStart
        AND ISNULL(fte.KimbleOne__EntryUnits__c, 0) <> 0
    GROUP BY
        r.Id,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, CAST(fte.KimbleOne__TimePeriodStartDate__c AS date)), 0),
        COALESCE(
            NULLIF(LTRIM(RTRIM(ra.Name)), ''),
            NULLIF(LTRIM(RTRIM(aa.Name)), ''),
            'Leave'
        )
),

LeaveWeekAgg AS (
    SELECT
        Resource_Id,
        WeekStart,
        CAST(
            STRING_AGG(
                CAST(
                    CONCAT(
                        CAST(CAST(Leave_Hours AS decimal(18,2)) AS varchar(30)),
                        ' hours (',
                        Leave_Type,
                        ')'
                    ) AS nvarchar(4000)
                ),
                ', '
            ) AS nvarchar(4000)
        ) AS Leave_Info
    FROM LeaveEntryAgg
    GROUP BY
        Resource_Id,
        WeekStart
)

SELECT
    b.Consultant_Name,
    b.Level,
    b.Job_Title,
    b.Location,
    b.Project_Name,
    b.Project_Type,
    ISNULL(MAX(ss.Submission), 'Inactive') AS Submission,
    b.Project_Status,
    b.Assignment_Start,
    b.Assignment_End,

    SUM(CASE WHEN tea.WeekStart = CONVERT(date, '2026-06-22') THEN tea.Logged_Hours ELSE 0 END) AS [Logged_Hours_2026-06-22],
    ISNULL(MAX(CASE WHEN lwa.WeekStart = CONVERT(date, '2026-06-22') THEN lwa.Leave_Info END), '0 hours') AS [Leave_2026-06-22],
    SUM(CASE WHEN tea.WeekStart = CONVERT(date, '2026-06-22') THEN tea.Consumed_Days ELSE 0 END) AS [Consumed_Days_2026-06-22],

    SUM(CASE WHEN tea.WeekStart = CONVERT(date, '2026-06-15') THEN tea.Logged_Hours ELSE 0 END) AS [Logged_Hours_2026-06-15],
    ISNULL(MAX(CASE WHEN lwa.WeekStart = CONVERT(date, '2026-06-15') THEN lwa.Leave_Info END), '0 hours') AS [Leave_2026-06-15],
    SUM(CASE WHEN tea.WeekStart = CONVERT(date, '2026-06-15') THEN tea.Consumed_Days ELSE 0 END) AS [Consumed_Days_2026-06-15],

    SUM(CASE WHEN tea.WeekStart = CONVERT(date, '2026-06-08') THEN tea.Logged_Hours ELSE 0 END) AS [Logged_Hours_2026-06-08],
    ISNULL(MAX(CASE WHEN lwa.WeekStart = CONVERT(date, '2026-06-08') THEN lwa.Leave_Info END), '0 hours') AS [Leave_2026-06-08],
    SUM(CASE WHEN tea.WeekStart = CONVERT(date, '2026-06-08') THEN tea.Consumed_Days ELSE 0 END) AS [Consumed_Days_2026-06-08],

    SUM(CASE WHEN tea.WeekStart = CONVERT(date, '2026-06-01') THEN tea.Logged_Hours ELSE 0 END) AS [Logged_Hours_2026-06-01],
    ISNULL(MAX(CASE WHEN lwa.WeekStart = CONVERT(date, '2026-06-01') THEN lwa.Leave_Info END), '0 hours') AS [Leave_2026-06-01],
    SUM(CASE WHEN tea.WeekStart = CONVERT(date, '2026-06-01') THEN tea.Consumed_Days ELSE 0 END) AS [Consumed_Days_2026-06-01]

    -- Add more fixed week columns here if needed.

FROM Base b
LEFT JOIN TimeEntryAgg tea
    ON tea.ActivityAssignment_Id = b.ActivityAssignment_Id
LEFT JOIN SubmissionStatus ss
    ON ss.ActivityAssignment_Id = b.ActivityAssignment_Id
LEFT JOIN LeaveWeekAgg lwa
    ON lwa.Resource_Id = b.Resource_Id

GROUP BY
    b.Resource_Id,
    b.ActivityAssignment_Id,
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