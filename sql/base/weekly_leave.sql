SET NOCOUNT ON;

DECLARE @Today date = CAST(GETDATE() AS date);

DECLARE @CurrentWeekStart date =
    DATEADD(
        WEEK,
        DATEDIFF(WEEK, 0, @Today),
        0
    );

DECLARE @WindowStart date =
    DATEADD(
        YEAR,
        -1,
        @CurrentWeekStart
    );

DECLARE @YearEnd date =
    DATEFROMPARTS(
        YEAR(@Today),
        12,
        31
    );


/*
    Bu sorgu her consultant için haftalık izin bilgisini üretir.

    WeekStart her zaman pazartesidir.
*/

;WITH LeaveByType AS
(
    SELECT
        r.Id AS Resource_Id,

        DATEADD(
            WEEK,
            DATEDIFF(
                WEEK,
                0,
                CAST(
                    fte.KimbleOne__TimePeriodStartDate__c AS date
                )
            ),
            0
        ) AS WeekStart,

        COALESCE(
            NULLIF(LTRIM(RTRIM(ra.Name)), ''),
            NULLIF(LTRIM(RTRIM(aa.Name)), ''),
            'Leave'
        ) AS Leave_Type,

        SUM(
            ISNULL(
                fte.KimbleOne__EntryUnits__c,
                0
            )
        ) AS Leave_Hours

    FROM REPL_SF.ForecastTimeEntry fte

    LEFT JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id = fte.KimbleOne__ActivityAssignment__c

    LEFT JOIN REPL_SF.ResourceActivity ra
        ON ra.Id = aa.KimbleOne__ResourcedActivity__c

    LEFT JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c

    WHERE
        fte.KimbleOne__TimePeriodStartDate__c IS NOT NULL

        AND CAST(
                fte.KimbleOne__TimePeriodStartDate__c AS date
            ) >= @WindowStart

        AND CAST(
                fte.KimbleOne__TimePeriodStartDate__c AS date
            ) <= @YearEnd

        AND ISNULL(
                fte.KimbleOne__EntryUnits__c,
                0
            ) <> 0

    GROUP BY
        r.Id,

        DATEADD(
            WEEK,
            DATEDIFF(
                WEEK,
                0,
                CAST(
                    fte.KimbleOne__TimePeriodStartDate__c AS date
                )
            ),
            0
        ),

        COALESCE(
            NULLIF(LTRIM(RTRIM(ra.Name)), ''),
            NULLIF(LTRIM(RTRIM(aa.Name)), ''),
            'Leave'
        )
)

SELECT
    Resource_Id,

    WeekStart,

    SUM(
        Leave_Hours
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