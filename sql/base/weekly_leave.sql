SET NOCOUNT ON;

DECLARE @Today date = CAST(GETDATE() AS date);

DECLARE @YearStart date =
    DATEFROMPARTS(YEAR(@Today), 1, 1);

DECLARE @YearEnd date =
    DATEFROMPARTS(YEAR(@Today), 12, 31);

;WITH LeaveEntryBase AS
(
    SELECT
        r.Id AS Resource_Id,

        DATEADD(
            WEEK,
            DATEDIFF(
                WEEK,
                0,
                CAST(
                    fte.KimbleOne__TimePeriodStartDate__c
                    AS date
                )
            ),
            0
        ) AS WeekStart,

        COALESCE(
            NULLIF(LTRIM(RTRIM(ra.Name)), ''),
            NULLIF(LTRIM(RTRIM(aa.Name)), ''),
            'Leave'
        ) AS Leave_Type,

        ISNULL(
            fte.KimbleOne__EntryUnits__c,
            0
        ) AS Leave_Hours

    FROM REPL_SF.ForecastTimeEntry fte

    LEFT JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id =
            fte.KimbleOne__ActivityAssignment__c

    LEFT JOIN REPL_SF.Resource r
        ON r.Id =
            aa.KimbleOne__Resource__c

    LEFT JOIN REPL_SF.ResourceActivity ra
        ON ra.Id =
            aa.KimbleOne__ResourcedActivity__c

    WHERE
        CAST(
            fte.KimbleOne__TimePeriodStartDate__c
            AS date
        ) BETWEEN @YearStart AND @YearEnd

        AND ISNULL(
            fte.KimbleOne__EntryUnits__c,
            0
        ) > 0

        AND
        (
               LOWER(ISNULL(ra.Name, '')) LIKE '%leave%'
            OR LOWER(ISNULL(ra.Name, '')) LIKE '%holiday%'
            OR LOWER(ISNULL(ra.Name, '')) LIKE '%vacation%'
            OR LOWER(ISNULL(ra.Name, '')) LIKE '%annual%'
            OR LOWER(ISNULL(aa.Name, '')) LIKE '%leave%'
            OR LOWER(ISNULL(aa.Name, '')) LIKE '%holiday%'
            OR LOWER(ISNULL(aa.Name, '')) LIKE '%vacation%'
            OR LOWER(ISNULL(aa.Name, '')) LIKE '%annual%'
        )
),

LeaveByType AS
(
    SELECT
        Resource_Id,
        WeekStart,
        Leave_Type,
        SUM(Leave_Hours) AS Leave_Hours

    FROM LeaveEntryBase

    GROUP BY
        Resource_Id,
        WeekStart,
        Leave_Type
)

SELECT
    Resource_Id,

    CAST(
        WeekStart AS date
    ) AS WeekStart,

    CAST(
        SUM(Leave_Hours)
        AS decimal(18,2)
    ) AS Leave_Hours,

    CAST(
        STRING_AGG(
            CAST(
                CONCAT(
                    CAST(
                        CAST(
                            Leave_Hours AS decimal(18,2)
                        ) AS varchar(30)
                    ),
                    ' hours (',
                    Leave_Type,
                    ')'
                ) AS nvarchar(4000)
            ),
            ', '
        ) AS nvarchar(4000)
    ) AS Leave_Info

FROM LeaveByType

GROUP BY
    Resource_Id,
    WeekStart

ORDER BY
    Resource_Id,
    WeekStart;