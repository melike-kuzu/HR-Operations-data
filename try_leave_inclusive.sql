DECLARE @ThisWeekStart date =
    DATEADD(WEEK, DATEDIFF(WEEK, 0, GETDATE()), 0);

DECLARE @WindowStart date =
    DATEADD(WEEK, -26, @ThisWeekStart);

DECLARE @cols nvarchar(max) = N'';
DECLARE @sql  nvarchar(max) = N'';

;WITH Weeks AS (
    SELECT 1 AS WeekNo, DATEADD(WEEK, -1, @ThisWeekStart) AS WeekStart
    UNION ALL
    SELECT WeekNo + 1,
           DATEADD(WEEK, -(WeekNo + 1), @ThisWeekStart)
    FROM Weeks
    WHERE WeekNo < 26
)
SELECT @cols = @cols + N'
    SUM(CASE WHEN tea.WeekStart = CONVERT(date, ''' + CONVERT(varchar(10), WeekStart, 120) + N''')
             THEN tea.Logged_Hours ELSE 0 END) AS [Logged_Hours_' + CONVERT(varchar(10), WeekStart, 120) + N'],

    ISNULL(
        CAST(
            MAX(CASE WHEN lwa.WeekStart = CONVERT(date, ''' + CONVERT(varchar(10), WeekStart, 120) + N''')
                     THEN lwa.Leave_Info END)
            AS nvarchar(4000)
        ),
        ''0 hours''
    ) AS [Leave_' + CONVERT(varchar(10), WeekStart, 120) + N'],

    SUM(CASE WHEN tea.WeekStart = CONVERT(date, ''' + CONVERT(varchar(10), WeekStart, 120) + N''')
             THEN tea.Consumed_Days ELSE 0 END) AS [Consumed_Days_' + CONVERT(varchar(10), WeekStart, 120) + N'],'
FROM Weeks
ORDER BY WeekNo;

SET @cols = LEFT(@cols, LEN(@cols) - 1);

SET @sql = N'
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

        DATEADD(WEEK,
                DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c),
                0) AS WeekStart,

        SUM(te.KimbleOne__EntryUnits__c) AS Logged_Hours,

        SUM(te.KimbleOne__EntryUnits__c) / 8.0 AS Consumed_Days

    FROM REPL_SF.[TimeEntry] te

    LEFT JOIN REPL_SF.TimePeriod tp
        ON tp.Id = te.KimbleOne__TimePeriod__c

    WHERE
        te.KimbleOne__ActivityAssignment__c IS NOT NULL
        AND tp.KimbleOne__EndDate__c >= @WindowStart
        AND tp.KimbleOne__EndDate__c < @ThisWeekStart

    GROUP BY
        te.KimbleOne__ActivityAssignment__c,
        DATEADD(WEEK,
                DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c),
                0)
),

LeaveEntryAgg AS (
    SELECT
        r.Id AS Resource_Id,

        DATEADD(WEEK,
                DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c),
                0) AS WeekStart,

        CAST(
            COALESCE(
                NULLIF(LTRIM(RTRIM(ra.Name)), ''''),
                NULLIF(LTRIM(RTRIM(aa.Name)), ''''),
                ''Leave''
            ) AS nvarchar(200)
        ) AS Leave_Type,

        SUM(te.KimbleOne__EntryUnits__c) AS Leave_Hours

    FROM REPL_SF.[TimeEntry] te

    JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id = te.KimbleOne__ActivityAssignment__c

    JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c

    LEFT JOIN REPL_SF.ResourceActivity ra
        ON ra.Id = aa.KimbleOne__ResourcedActivity__c

    LEFT JOIN REPL_SF.TimePeriod tp
        ON tp.Id = te.KimbleOne__TimePeriod__c

    WHERE
        tp.KimbleOne__EndDate__c >= @WindowStart
        AND tp.KimbleOne__EndDate__c < @ThisWeekStart

        AND (
            LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%leave%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%vacation%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%holiday%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%unpaid%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%maternity%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%paternity%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%sick%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%absence%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%time off%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%toil%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%bereavement%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%jury%''
            OR LOWER(COALESCE(ra.Name, aa.Name, '''')) LIKE ''%compassionate%''
        )

    GROUP BY
        r.Id,
        DATEADD(WEEK,
                DATEDIFF(WEEK, 0, tp.KimbleOne__EndDate__c),
                0),
        CAST(
            COALESCE(
                NULLIF(LTRIM(RTRIM(ra.Name)), ''''),
                NULLIF(LTRIM(RTRIM(aa.Name)), ''''),
                ''Leave''
            ) AS nvarchar(200)
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
                        '' hours ('',
                        LEFT(Leave_Type, 200),
                        '')''
                    ) AS nvarchar(4000)
                ),
                '', ''
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
    b.Project_Status,
    b.Assignment_Start,
    b.Assignment_End,

' + @cols + N'

FROM Base b

LEFT JOIN TimeEntryAgg tea
    ON tea.ActivityAssignment_Id = b.ActivityAssignment_Id

LEFT JOIN LeaveWeekAgg lwa
    ON lwa.Resource_Id = b.Resource_Id

GROUP BY
    b.Resource_Id,
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

EXEC sp_executesql
    @sql,
    N'@WindowStart date, @ThisWeekStart date',
    @WindowStart = @WindowStart,
    @ThisWeekStart = @ThisWeekStart;