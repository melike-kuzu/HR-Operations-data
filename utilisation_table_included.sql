SET NOCOUNT ON;


/* ============================================================
   CURRENT CALENDAR YEAR
   ============================================================ */

DECLARE @Today date = CAST(GETDATE() AS date);

DECLARE @YearStart date =
    DATEFROMPARTS(YEAR(@Today), 1, 1);

DECLARE @YearEnd date =
    DATEFROMPARTS(YEAR(@Today), 12, 31);


/*
    Monday of the current week.

    This uses the same week calculation as the original SQL.
*/
DECLARE @CurrentWeekStart date =
    DATEADD(
        WEEK,
        DATEDIFF(WEEK, 0, @Today),
        0
    );


/*
    First Monday on or after 1 January.
*/
DECLARE @FirstWeekStart date =
    DATEADD(
        DAY,
        (
            7
            - (
                DATEDIFF(
                    DAY,
                    CONVERT(date, '19000101'),
                    @YearStart
                ) % 7
            )
        ) % 7,
        @YearStart
    );


/*
    Last Monday on or before 31 December.
*/
DECLARE @LastWeekStart date =
    DATEADD(
        DAY,
        -(
            DATEDIFF(
                DAY,
                CONVERT(date, '19000101'),
                @YearEnd
            ) % 7
        ),
        @YearEnd
    );


DECLARE @CalendarColumns nvarchar(max) = N'';
DECLARE @ColourColumns nvarchar(max) = N'';
DECLARE @UtilisationColumns nvarchar(max) = N'';
DECLARE @sql nvarchar(max) = N'';


/* ============================================================
   CREATE DYNAMIC WEEK COLUMNS
   ============================================================ */

;WITH Weeks AS
(
    SELECT @FirstWeekStart AS WeekStart

    UNION ALL

    SELECT DATEADD(WEEK, 1, WeekStart)
    FROM Weeks
    WHERE DATEADD(WEEK, 1, WeekStart) <= @LastWeekStart
)
SELECT
    @CalendarColumns =
    (
        SELECT
            N',
    MAX(
        CASE
            WHEN cg.WeekStart = CONVERT(date, '''
            + CONVERT(varchar(10), WeekStart, 120)
            + N''')
            THEN cg.CalendarValue
        END
    ) AS [' + CONVERT(varchar(10), WeekStart, 120) + N']'

        FROM Weeks

        ORDER BY WeekStart

        FOR XML PATH(''), TYPE
    ).value('.', 'nvarchar(max)'),


    @ColourColumns =
    (
        SELECT
            N',
    MAX(
        CASE
            WHEN cg.WeekStart = CONVERT(date, '''
            + CONVERT(varchar(10), WeekStart, 120)
            + N''')
            THEN cg.CalendarColour
        END
    ) AS [' + CONVERT(varchar(10), WeekStart, 120) + N']'

        FROM Weeks

        ORDER BY WeekStart

        FOR XML PATH(''), TYPE
    ).value('.', 'nvarchar(max)'),


    @UtilisationColumns =
    (
        SELECT
            N',
    MAX(
        CASE
            WHEN ul.WeekStart = CONVERT(date, '''
            + CONVERT(varchar(10), WeekStart, 120)
            + N''')
            THEN ul.MetricValue
        END
    ) AS [' + CONVERT(varchar(10), WeekStart, 120) + N']'

        FROM Weeks

        ORDER BY WeekStart

        FOR XML PATH(''), TYPE
    ).value('.', 'nvarchar(max)')

OPTION (MAXRECURSION 60);


/* ============================================================
   MAIN DYNAMIC SQL
   ============================================================ */

SET @sql = N'

;WITH Weeks AS
(
    SELECT @FirstWeekStart AS WeekStart

    UNION ALL

    SELECT DATEADD(WEEK, 1, WeekStart)
    FROM Weeks
    WHERE DATEADD(WEEK, 1, WeekStart) <= @LastWeekStart
),


/* ============================================================
   CONSULTANT AND PROJECT BASE

   This retains the original joins and original project filter.
   ============================================================ */

Base AS
(
    SELECT
        r.Id AS Resource_Id,

        e.DISPLAY_NAME AS Consultant_Name,

        e.DEPARTMENT AS Team,

        MIN(
            CAST(
                aa.KimbleOne__StartDate__c AS date
            )
        ) AS Assignment_Start,

        /*
            Expected availability date:
            latest forecast project assignment end date.
        */
        MAX(
            CAST(
                aa.KimbleOne__ForecastP2EndDate__c AS date
            )
        ) AS Expected_Availability_Date,

        /*
            Number of distinct projects active today.
        */
        COUNT(
            DISTINCT
            CASE
                WHEN CAST(
                        aa.KimbleOne__StartDate__c AS date
                     ) <= @Today

                     AND ISNULL(
                            CAST(
                                aa.KimbleOne__ForecastP2EndDate__c
                                AS date
                            ),
                            @YearEnd
                         ) >= @Today

                THEN p.PROJECT_ID
            END
        ) AS Active_Projects

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

        /*
            Assignment overlaps the current calendar year.
        */
        AND CAST(
                aa.KimbleOne__StartDate__c AS date
            ) <= @YearEnd

        AND ISNULL(
                CAST(
                    aa.KimbleOne__ForecastP2EndDate__c AS date
                ),
                @YearEnd
            ) >= @YearStart

    GROUP BY
        r.Id,
        e.DISPLAY_NAME,
        e.DEPARTMENT
),


/* ============================================================
   WEEKLY SUBMITTED HOURS

   This retains the exact original Monday week calculation.
   ============================================================ */

TimeEntryWeekly AS
(
    SELECT
        r.Id AS Resource_Id,

        DATEADD(
            WEEK,
            DATEDIFF(
                WEEK,
                0,
                tp.KimbleOne__EndDate__c
            ),
            0
        ) AS WeekStart,

        SUM(
            ISNULL(
                te.KimbleOne__EntryUnits__c,
                0
            )
        ) AS Logged_Hours,

        CASE
            WHEN SUM(
                    ISNULL(
                        te.KimbleOne__EntryUnits__c,
                        0
                    )
                 ) >= 40
                THEN CAST(1.00 AS decimal(10,2))

            WHEN SUM(
                    ISNULL(
                        te.KimbleOne__EntryUnits__c,
                        0
                    )
                 ) > 0
                THEN CAST(
                        SUM(
                            ISNULL(
                                te.KimbleOne__EntryUnits__c,
                                0
                            )
                        ) / 40.0
                        AS decimal(10,2)
                     )

            ELSE CAST(0 AS decimal(10,2))
        END AS Capacity

    FROM REPL_SF.TimeEntry te

    JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id = te.KimbleOne__ActivityAssignment__c

    JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c

    LEFT JOIN REPL_SF.TimePeriod tp
        ON tp.Id = te.KimbleOne__TimePeriod__c

    WHERE
        te.KimbleOne__ActivityAssignment__c IS NOT NULL

        AND tp.KimbleOne__EndDate__c IS NOT NULL

        AND CAST(
                tp.KimbleOne__EndDate__c AS date
            ) >= @YearStart

        AND CAST(
                tp.KimbleOne__EndDate__c AS date
            ) <= @YearEnd

    GROUP BY
        r.Id,

        DATEADD(
            WEEK,
            DATEDIFF(
                WEEK,
                0,
                tp.KimbleOne__EndDate__c
            ),
            0
        )
),


/* ============================================================
   APPROVED LEAVE

   This retains the original Monday week calculation.
   ============================================================ */

ApprovedLeaveWeekly AS
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

        SUM(
            ISNULL(
                fte.KimbleOne__EntryUnits__c,
                0
            )
        ) AS Leave_Hours

    FROM REPL_SF.ForecastTimeEntry fte

    LEFT JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id = fte.KimbleOne__ActivityAssignment__c

    LEFT JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c

    LEFT JOIN REPL_SF.ResourceActivity ra
        ON ra.Id = aa.KimbleOne__ResourcedActivity__c

    WHERE
        CAST(
            fte.KimbleOne__TimePeriodStartDate__c AS date
        ) BETWEEN @YearStart AND @YearEnd

        AND ISNULL(
                fte.KimbleOne__EntryUnits__c,
                0
            ) > 0

        AND
        (
            ra.Name LIKE ''%leave%''
            OR ra.Name LIKE ''%holiday%''
            OR ra.Name LIKE ''%vacation%''
            OR ra.Name LIKE ''%annual%''
        )

    GROUP BY
        r.Id,

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
        )
)


/* ============================================================
   CALENDAR GRID
   ============================================================ */

SELECT
    b.Resource_Id,

    b.Team,

    b.Consultant_Name,

    b.Expected_Availability_Date,

    b.Active_Projects,

    b.Assignment_Start,

    w.WeekStart,


    /* ========================================================
       VALUE DISPLAYED IN THE TRACKER
       ======================================================== */

    CASE
        /*
            Leave takes priority.
        */
        WHEN al.Resource_Id IS NOT NULL
            THEN ''L''

        /*
            Actual submitted hours.
        */
        WHEN ISNULL(tw.Capacity, 0) > 0
            THEN CONVERT(
                    varchar(20),
                    CAST(
                        tw.Capacity AS decimal(10,2)
                    )
                 )

        /*
            Future unconfirmed allocation.

            A future week is shown as 1.00 when:
            - the week is after the current week;
            - the assignment has started;
            - the expected availability date has not passed.
        */
        WHEN w.WeekStart > @CurrentWeekStart

             AND b.Expected_Availability_Date IS NOT NULL

             AND w.WeekStart <=
                 DATEADD(
                     WEEK,
                     DATEDIFF(
                         WEEK,
                         0,
                         b.Expected_Availability_Date
                     ),
                     0
                 )

             AND
             (
                 b.Assignment_Start IS NULL

                 OR w.WeekStart >=
                    DATEADD(
                        WEEK,
                        DATEDIFF(
                            WEEK,
                            0,
                            b.Assignment_Start
                        ),
                        0
                    )
             )
            THEN ''1.00''

        ELSE ''B''
    END AS CalendarValue,


    /* ========================================================
       NUMERIC CAPACITY
       ======================================================== */

    CASE
        WHEN al.Resource_Id IS NOT NULL
            THEN CAST(0 AS decimal(10,2))

        WHEN ISNULL(tw.Capacity, 0) > 0
            THEN CAST(
                    tw.Capacity AS decimal(10,2)
                 )

        WHEN w.WeekStart > @CurrentWeekStart

             AND b.Expected_Availability_Date IS NOT NULL

             AND w.WeekStart <=
                 DATEADD(
                     WEEK,
                     DATEDIFF(
                         WEEK,
                         0,
                         b.Expected_Availability_Date
                     ),
                     0
                 )

             AND
             (
                 b.Assignment_Start IS NULL

                 OR w.WeekStart >=
                    DATEADD(
                        WEEK,
                        DATEDIFF(
                            WEEK,
                            0,
                            b.Assignment_Start
                        ),
                        0
                    )
             )
            THEN CAST(1.00 AS decimal(10,2))

        ELSE CAST(0 AS decimal(10,2))
    END AS CalendarCapacity,


    /* ========================================================
       BUSINESS STATUS
       ======================================================== */

    CASE
        WHEN al.Resource_Id IS NOT NULL
            THEN ''ON_LEAVE''

        WHEN ISNULL(tw.Capacity, 0) >= 1
            THEN ''BOOKED''

        WHEN ISNULL(tw.Capacity, 0) > 0
             AND ISNULL(tw.Capacity, 0) < 1
            THEN ''PARTLY_BOOKED''

        WHEN w.WeekStart > @CurrentWeekStart

             AND b.Expected_Availability_Date IS NOT NULL

             AND w.WeekStart <=
                 DATEADD(
                     WEEK,
                     DATEDIFF(
                         WEEK,
                         0,
                         b.Expected_Availability_Date
                     ),
                     0
                 )

             AND
             (
                 b.Assignment_Start IS NULL

                 OR w.WeekStart >=
                    DATEADD(
                        WEEK,
                        DATEDIFF(
                            WEEK,
                            0,
                            b.Assignment_Start
                        ),
                        0
                    )
             )
            THEN ''UNCONFIRMED''

        ELSE ''BENCH''
    END AS CalendarStatus,


    /* ========================================================
       COLOUR CATEGORY
       ======================================================== */

    CASE
        WHEN al.Resource_Id IS NOT NULL
            THEN ''YELLOW''

        WHEN ISNULL(tw.Capacity, 0) >= 1
            THEN ''RED''

        WHEN ISNULL(tw.Capacity, 0) > 0
             AND ISNULL(tw.Capacity, 0) < 1
            THEN ''LIGHT_ORANGE''

        WHEN w.WeekStart > @CurrentWeekStart

             AND b.Expected_Availability_Date IS NOT NULL

             AND w.WeekStart <=
                 DATEADD(
                     WEEK,
                     DATEDIFF(
                         WEEK,
                         0,
                         b.Expected_Availability_Date
                     ),
                     0
                 )

             AND
             (
                 b.Assignment_Start IS NULL

                 OR w.WeekStart >=
                    DATEADD(
                        WEEK,
                        DATEDIFF(
                            WEEK,
                            0,
                            b.Assignment_Start
                        ),
                        0
                    )
             )
            THEN ''ORANGE''

        ELSE ''PURPLE''
    END AS CalendarColour

INTO #CalendarGrid

FROM Base b

CROSS JOIN Weeks w

LEFT JOIN TimeEntryWeekly tw
    ON tw.Resource_Id = b.Resource_Id
    AND tw.WeekStart = w.WeekStart

LEFT JOIN ApprovedLeaveWeekly al
    ON al.Resource_Id = b.Resource_Id
    AND al.WeekStart = w.WeekStart

OPTION (MAXRECURSION 60);


/* ============================================================
   RESULT 1: CONSULTANT TRACKER
   ============================================================ */

SELECT
    Team,

    Consultant_Name,

    Expected_Availability_Date,

    Active_Projects

' + @CalendarColumns + N'

FROM #CalendarGrid cg

GROUP BY
    Team,
    Consultant_Name,
    Expected_Availability_Date,
    Active_Projects

ORDER BY
    Team,
    Consultant_Name;


/* ============================================================
   RESULT 2: COLOUR TRACKER

   RED          = booked 1.00
   ORANGE       = future unconfirmed 1.00
   LIGHT_ORANGE = partially booked
   YELLOW       = leave
   PURPLE       = bench
   ============================================================ */

SELECT
    Team,

    Consultant_Name,

    Expected_Availability_Date,

    Active_Projects

' + @ColourColumns + N'

FROM #CalendarGrid cg

GROUP BY
    Team,
    Consultant_Name,
    Expected_Availability_Date,
    Active_Projects

ORDER BY
    Team,
    Consultant_Name;


/* ============================================================
   WEEKLY UTILISATION
   ============================================================ */

SELECT
    WeekStart,

    SUM(
        CASE
            WHEN CalendarStatus = ''BOOKED''
            THEN 1
            ELSE 0
        END
    ) AS Booked,

    SUM(
        CASE
            WHEN CalendarStatus = ''UNCONFIRMED''
            THEN 1
            ELSE 0
        END
    ) AS Unconfirmed,

    SUM(
        CASE
            WHEN CalendarStatus = ''PARTLY_BOOKED''
            THEN 1
            ELSE 0
        END
    ) AS Partly_Booked,

    SUM(
        CASE
            WHEN CalendarStatus = ''ON_LEAVE''
            THEN 1
            ELSE 0
        END
    ) AS On_Leave,

    SUM(
        CASE
            WHEN CalendarStatus = ''BENCH''
            THEN 1
            ELSE 0
        END
    ) AS Bench,

    /*
        Booked Capacity includes:
        - confirmed fully booked capacity;
        - partially booked capacity.

        Unconfirmed future bookings are not included.
    */
    SUM(
        CASE
            WHEN CalendarStatus IN
                 (
                     ''BOOKED'',
                     ''PARTLY_BOOKED''
                 )
            THEN CalendarCapacity
            ELSE 0
        END
    ) AS Booked_Capacity,

    /*
        Maximum Capacity includes:
        - booked;
        - unconfirmed;
        - partly booked;
        - bench.

        Leave is excluded.
    */
    SUM(
        CASE
            WHEN CalendarStatus <> ''ON_LEAVE''
            THEN 1
            ELSE 0
        END
    ) AS Maximum_Capacity

INTO #UtilisationWeekly

FROM #CalendarGrid

GROUP BY
    WeekStart;


/* ============================================================
   CREATE UTILISATION ROWS
   ============================================================ */

CREATE TABLE #UtilisationLong
(
    MetricOrder int NOT NULL,
    MetricName varchar(50) NOT NULL,
    WeekStart date NOT NULL,
    MetricValue varchar(50) NULL
);


/* Booked */
INSERT INTO #UtilisationLong
SELECT
    1,
    ''Booked'',
    WeekStart,
    CONVERT(varchar(50), Booked)
FROM #UtilisationWeekly;


/* Unconfirmed */
INSERT INTO #UtilisationLong
SELECT
    2,
    ''Unconfirmed'',
    WeekStart,
    CONVERT(varchar(50), Unconfirmed)
FROM #UtilisationWeekly;


/* Partly Booked */
INSERT INTO #UtilisationLong
SELECT
    3,
    ''Partly Booked'',
    WeekStart,
    CONVERT(varchar(50), Partly_Booked)
FROM #UtilisationWeekly;


/* On Leave */
INSERT INTO #UtilisationLong
SELECT
    4,
    ''On Leave'',
    WeekStart,
    CONVERT(varchar(50), On_Leave)
FROM #UtilisationWeekly;


/* Bench */
INSERT INTO #UtilisationLong
SELECT
    5,
    ''Bench'',
    WeekStart,
    CONVERT(varchar(50), Bench)
FROM #UtilisationWeekly;


/* Booked Capacity */
INSERT INTO #UtilisationLong
SELECT
    6,
    ''Booked Capacity'',
    WeekStart,

    CONVERT(
        varchar(50),
        CAST(
            Booked_Capacity AS decimal(10,2)
        )
    )

FROM #UtilisationWeekly;


/* Maximum Capacity */
INSERT INTO #UtilisationLong
SELECT
    7,
    ''Maximum Capacity'',
    WeekStart,

    CONVERT(
        varchar(50),
        CAST(
            Maximum_Capacity AS decimal(10,2)
        )
    )

FROM #UtilisationWeekly;


/* Forecasted Allocation */
INSERT INTO #UtilisationLong
SELECT
    8,
    ''Forecasted Allocation'',
    WeekStart,

    CONVERT(
        varchar(50),

        CAST(
            Booked_Capacity
            /
            NULLIF(
                CAST(
                    Maximum_Capacity AS decimal(10,6)
                ),
                0
            )
            AS decimal(10,6)
        )
    )

FROM #UtilisationWeekly;


/* ============================================================
   RESULT 3: UTILISATION SUMMARY
   ============================================================ */

SELECT
    MetricName AS Utilisation

' + @UtilisationColumns + N'

FROM #UtilisationLong ul

GROUP BY
    MetricOrder,
    MetricName

ORDER BY
    MetricOrder;


/* ============================================================
   CLEAN-UP
   ============================================================ */

DROP TABLE #UtilisationLong;
DROP TABLE #UtilisationWeekly;
DROP TABLE #CalendarGrid;

';


/* ============================================================
   EXECUTE
   ============================================================ */

EXEC sp_executesql
    @sql,

    N'
        @Today date,
        @YearStart date,
        @YearEnd date,
        @FirstWeekStart date,
        @LastWeekStart date,
        @CurrentWeekStart date
    ',

    @Today = @Today,
    @YearStart = @YearStart,
    @YearEnd = @YearEnd,
    @FirstWeekStart = @FirstWeekStart,
    @LastWeekStart = @LastWeekStart,
    @CurrentWeekStart = @CurrentWeekStart;