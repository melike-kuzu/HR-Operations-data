SET NOCOUNT ON;

DECLARE @YearStart date = '2026-01-05';
DECLARE @YearEnd   date = '2026-12-31';

WITH Weeks AS (
    SELECT v.WeekStart
    FROM (VALUES
        ('2026-01-05'), ('2026-01-12'), ('2026-01-19'), ('2026-01-26'),
        ('2026-02-02'), ('2026-02-09'), ('2026-02-16'), ('2026-02-23'),
        ('2026-03-02'), ('2026-03-09'), ('2026-03-16'), ('2026-03-23'), ('2026-03-30'),
        ('2026-04-06'), ('2026-04-13'), ('2026-04-20'), ('2026-04-27'),
        ('2026-05-04'), ('2026-05-11'), ('2026-05-18'), ('2026-05-25'),
        ('2026-06-01'), ('2026-06-08'), ('2026-06-15'), ('2026-06-22'), ('2026-06-29'),
        ('2026-07-06'), ('2026-07-13'), ('2026-07-20'), ('2026-07-27'),
        ('2026-08-03'), ('2026-08-10'), ('2026-08-17'), ('2026-08-24'), ('2026-08-31'),
        ('2026-09-07'), ('2026-09-14'), ('2026-09-21'), ('2026-09-28'),
        ('2026-10-05'), ('2026-10-12'), ('2026-10-19'), ('2026-10-26'),
        ('2026-11-02'), ('2026-11-09'), ('2026-11-16'), ('2026-11-23'), ('2026-11-30'),
        ('2026-12-07'), ('2026-12-14'), ('2026-12-21'), ('2026-12-28')
    ) v(WeekStart)
),

Base AS (
    SELECT
        r.Id AS Resource_Id,
        e.DISPLAY_NAME AS Consultant_Name,
        e.DEPARTMENT AS Team
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
        AND CAST(aa.KimbleOne__StartDate__c AS date) <= @YearEnd
        AND ISNULL(CAST(aa.KimbleOne__ForecastP2EndDate__c AS date), @YearEnd) >= @YearStart
    GROUP BY
        r.Id,
        e.DISPLAY_NAME,
        e.DEPARTMENT
),

TimeEntryWeekly AS (
    SELECT
        r.Id AS Resource_Id,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c), 0) AS WeekStart,
        CASE
            WHEN SUM(te.KimbleOne__EntryUnits__c) >= 40 THEN '1.00'
            WHEN SUM(te.KimbleOne__EntryUnits__c) > 0
                THEN CAST(CAST(SUM(te.KimbleOne__EntryUnits__c) / 40.0 AS DECIMAL(10,2)) AS varchar(20))
            ELSE '0'
        END AS Capacity
    FROM REPL_SF.TimeEntry te
    JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id = te.KimbleOne__ActivityAssignment__c
    JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c
    JOIN REPL_SF.TimePeriod tp
        ON tp.Id = te.KimbleOne__TimePeriod__c
    WHERE
        te.KimbleOne__ActivityAssignment__c IS NOT NULL
        AND tp.KimbleOne__EndDate__c >= @YearStart
        AND tp.KimbleOne__EndDate__c <= @YearEnd
    GROUP BY
        r.Id,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c), 0)
),

ApprovedLeaveWeekly AS (
    SELECT
        r.Id AS Resource_Id,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, CAST(fte.KimbleOne__TimePeriodStartDate__c AS date)), 0) AS WeekStart
    FROM REPL_SF.ForecastTimeEntry fte
    JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id = fte.KimbleOne__ActivityAssignment__c
    JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c
    JOIN REPL_SF.ResourceActivity ra
        ON ra.Id = aa.KimbleOne__ResourcedActivity__c
    WHERE
        CAST(fte.KimbleOne__TimePeriodStartDate__c AS date) BETWEEN @YearStart AND @YearEnd
        AND ISNULL(fte.KimbleOne__EntryUnits__c,0) > 0
        AND (
            ra.Name LIKE '%leave%'
            OR ra.Name LIKE '%holiday%'
            OR ra.Name LIKE '%vacation%'
            OR ra.Name LIKE '%annual%'
        )
    GROUP BY
        r.Id,
        DATEADD(WEEK, DATEDIFF(WEEK, 0, CAST(fte.KimbleOne__TimePeriodStartDate__c AS date)), 0)
),

CalendarGrid AS (
    SELECT
        b.Team,
        b.Consultant_Name,
        w.WeekStart,
        CASE
            WHEN al.Resource_Id IS NOT NULL THEN 'L'
            WHEN ISNULL(tw.Capacity, '0') <> '0' THEN tw.Capacity
            ELSE 'B'
        END AS CalendarValue
    FROM Base b
    CROSS JOIN Weeks w
    LEFT JOIN TimeEntryWeekly tw
        ON tw.Resource_Id = b.Resource_Id
        AND tw.WeekStart = w.WeekStart
    LEFT JOIN ApprovedLeaveWeekly al
        ON al.Resource_Id = b.Resource_Id
        AND al.WeekStart = w.WeekStart
)

SELECT
    Team,
    Consultant_Name,

    MAX(CASE WHEN cg.WeekStart = '2026-01-05' THEN cg.CalendarValue END) AS [2026-01-05],
    MAX(CASE WHEN cg.WeekStart = '2026-01-12' THEN cg.CalendarValue END) AS [2026-01-12],
    MAX(CASE WHEN cg.WeekStart = '2026-01-19' THEN cg.CalendarValue END) AS [2026-01-19],
    MAX(CASE WHEN cg.WeekStart = '2026-01-26' THEN cg.CalendarValue END) AS [2026-01-26],
    MAX(CASE WHEN cg.WeekStart = '2026-02-02' THEN cg.CalendarValue END) AS [2026-02-02],
    MAX(CASE WHEN cg.WeekStart = '2026-02-09' THEN cg.CalendarValue END) AS [2026-02-09],
    MAX(CASE WHEN cg.WeekStart = '2026-02-16' THEN cg.CalendarValue END) AS [2026-02-16],
    MAX(CASE WHEN cg.WeekStart = '2026-02-23' THEN cg.CalendarValue END) AS [2026-02-23],
    MAX(CASE WHEN cg.WeekStart = '2026-03-02' THEN cg.CalendarValue END) AS [2026-03-02],
    MAX(CASE WHEN cg.WeekStart = '2026-03-09' THEN cg.CalendarValue END) AS [2026-03-09],
    MAX(CASE WHEN cg.WeekStart = '2026-03-16' THEN cg.CalendarValue END) AS [2026-03-16],
    MAX(CASE WHEN cg.WeekStart = '2026-03-23' THEN cg.CalendarValue END) AS [2026-03-23],
    MAX(CASE WHEN cg.WeekStart = '2026-03-30' THEN cg.CalendarValue END) AS [2026-03-30],
    MAX(CASE WHEN cg.WeekStart = '2026-04-06' THEN cg.CalendarValue END) AS [2026-04-06],
    MAX(CASE WHEN cg.WeekStart = '2026-04-13' THEN cg.CalendarValue END) AS [2026-04-13],
    MAX(CASE WHEN cg.WeekStart = '2026-04-20' THEN cg.CalendarValue END) AS [2026-04-20],
    MAX(CASE WHEN cg.WeekStart = '2026-04-27' THEN cg.CalendarValue END) AS [2026-04-27],
    MAX(CASE WHEN cg.WeekStart = '2026-05-04' THEN cg.CalendarValue END) AS [2026-05-04],
    MAX(CASE WHEN cg.WeekStart = '2026-05-11' THEN cg.CalendarValue END) AS [2026-05-11],
    MAX(CASE WHEN cg.WeekStart = '2026-05-18' THEN cg.CalendarValue END) AS [2026-05-18],
    MAX(CASE WHEN cg.WeekStart = '2026-05-25' THEN cg.CalendarValue END) AS [2026-05-25],
    MAX(CASE WHEN cg.WeekStart = '2026-06-01' THEN cg.CalendarValue END) AS [2026-06-01],
    MAX(CASE WHEN cg.WeekStart = '2026-06-08' THEN cg.CalendarValue END) AS [2026-06-08],
    MAX(CASE WHEN cg.WeekStart = '2026-06-15' THEN cg.CalendarValue END) AS [2026-06-15],
    MAX(CASE WHEN cg.WeekStart = '2026-06-22' THEN cg.CalendarValue END) AS [2026-06-22],
    MAX(CASE WHEN cg.WeekStart = '2026-06-29' THEN cg.CalendarValue END) AS [2026-06-29],
    MAX(CASE WHEN cg.WeekStart = '2026-07-06' THEN cg.CalendarValue END) AS [2026-07-06],
    MAX(CASE WHEN cg.WeekStart = '2026-07-13' THEN cg.CalendarValue END) AS [2026-07-13],
    MAX(CASE WHEN cg.WeekStart = '2026-07-20' THEN cg.CalendarValue END) AS [2026-07-20],
    MAX(CASE WHEN cg.WeekStart = '2026-07-27' THEN cg.CalendarValue END) AS [2026-07-27],
    MAX(CASE WHEN cg.WeekStart = '2026-08-03' THEN cg.CalendarValue END) AS [2026-08-03],
    MAX(CASE WHEN cg.WeekStart = '2026-08-10' THEN cg.CalendarValue END) AS [2026-08-10],
    MAX(CASE WHEN cg.WeekStart = '2026-08-17' THEN cg.CalendarValue END) AS [2026-08-17],
    MAX(CASE WHEN cg.WeekStart = '2026-08-24' THEN cg.CalendarValue END) AS [2026-08-24],
    MAX(CASE WHEN cg.WeekStart = '2026-08-31' THEN cg.CalendarValue END) AS [2026-08-31],
    MAX(CASE WHEN cg.WeekStart = '2026-09-07' THEN cg.CalendarValue END) AS [2026-09-07],
    MAX(CASE WHEN cg.WeekStart = '2026-09-14' THEN cg.CalendarValue END) AS [2026-09-14],
    MAX(CASE WHEN cg.WeekStart = '2026-09-21' THEN cg.CalendarValue END) AS [2026-09-21],
    MAX(CASE WHEN cg.WeekStart = '2026-09-28' THEN cg.CalendarValue END) AS [2026-09-28],
    MAX(CASE WHEN cg.WeekStart = '2026-10-05' THEN cg.CalendarValue END) AS [2026-10-05],
    MAX(CASE WHEN cg.WeekStart = '2026-10-12' THEN cg.CalendarValue END) AS [2026-10-12],
    MAX(CASE WHEN cg.WeekStart = '2026-10-19' THEN cg.CalendarValue END) AS [2026-10-19],
    MAX(CASE WHEN cg.WeekStart = '2026-10-26' THEN cg.CalendarValue END) AS [2026-10-26],
    MAX(CASE WHEN cg.WeekStart = '2026-11-02' THEN cg.CalendarValue END) AS [2026-11-02],
    MAX(CASE WHEN cg.WeekStart = '2026-11-09' THEN cg.CalendarValue END) AS [2026-11-09],
    MAX(CASE WHEN cg.WeekStart = '2026-11-16' THEN cg.CalendarValue END) AS [2026-11-16],
    MAX(CASE WHEN cg.WeekStart = '2026-11-23' THEN cg.CalendarValue END) AS [2026-11-23],
    MAX(CASE WHEN cg.WeekStart = '2026-11-30' THEN cg.CalendarValue END) AS [2026-11-30],
    MAX(CASE WHEN cg.WeekStart = '2026-12-07' THEN cg.CalendarValue END) AS [2026-12-07],
    MAX(CASE WHEN cg.WeekStart = '2026-12-14' THEN cg.CalendarValue END) AS [2026-12-14],
    MAX(CASE WHEN cg.WeekStart = '2026-12-21' THEN cg.CalendarValue END) AS [2026-12-21],
    MAX(CASE WHEN cg.WeekStart = '2026-12-28' THEN cg.CalendarValue END) AS [2026-12-28]

FROM CalendarGrid cg
GROUP BY
    Team,
    Consultant_Name
ORDER BY
    Team,
    Consultant_Name;