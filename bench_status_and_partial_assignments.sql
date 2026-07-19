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
        WEEK,
        -52,
        @CurrentWeekStart
    );


/* ============================================================
   VARSA ÖNCEKİ GEÇİCİ TABLOLARI TEMİZLE
   ============================================================ */

DROP TABLE IF EXISTS #ConsultantAssignments;
DROP TABLE IF EXISTS #ResourceSummary;
DROP TABLE IF EXISTS #LatestCompletedAssignment;
DROP TABLE IF EXISTS #ActiveAssignments;
DROP TABLE IF EXISTS #WeeklyProjectHours;
DROP TABLE IF EXISTS #PartialAssignmentSummary;


/* ============================================================
   ORTAK CONSULTANT VE ASSIGNMENT VERİSİ
   ============================================================ */

SELECT
    r.Id AS Resource_Id,

    aa.Id AS ActivityAssignment_Id,

    e.DISPLAY_NAME AS Resource_Name,

    e.JOB_LEVEL AS [Level],

    e.DEPARTMENT AS [Group],

    CAST(
        aa.KimbleOne__StartDate__c AS date
    ) AS Assignment_Start,

    CAST(
        aa.KimbleOne__ForecastP2EndDate__c AS date
    ) AS Assignment_End,

    ra.Name AS Activity,

    p.PROJECT_ID,

    p.PROJECT_NAME AS Client,

    p.PROJECT_STATUS

INTO #ConsultantAssignments

FROM REPL_SF.Resource r

LEFT JOIN REPL_SF.[User] u
    ON u.Id = r.KimbleOne__User__c

LEFT JOIN ANALYTICS.DIM_EMPLOYEE e
    ON e.INTEGRATION_ID = u.Username

LEFT JOIN REPL_SF.ActivityAssignment aa
    ON aa.KimbleOne__Resource__c = r.Id

LEFT JOIN REPL_SF.ResourceActivity ra
    ON ra.Id = aa.KimbleOne__ResourcedActivity__c

LEFT JOIN ANALYTICS.DIM_PROJECT p
    ON p.PROJECT_ID = ra.Id

WHERE
    e.DISPLAY_NAME IS NOT NULL;


/* ============================================================
   BENCH STATUS: RESOURCE ÖZETİ
   ============================================================ */

SELECT
    Resource_Id,

    Resource_Name,

    [Level],

    [Group],

    MAX(
        CASE
            WHEN Assignment_End < @Today
                THEN Assignment_End
            ELSE NULL
        END
    ) AS Last_Assignment_End_Date,

    COUNT(
        DISTINCT
        CASE
            WHEN Assignment_Start <= @Today

                 AND ISNULL(
                        Assignment_End,
                        CONVERT(date, '99991231')
                     ) >= @Today

                 AND PROJECT_ID IS NOT NULL

                THEN PROJECT_ID
            ELSE NULL
        END
    ) AS Active_Project_Count

INTO #ResourceSummary

FROM #ConsultantAssignments

GROUP BY
    Resource_Id,
    Resource_Name,
    [Level],
    [Group];


/* ============================================================
   BENCH STATUS: SON TAMAMLANAN ASSIGNMENT
   ============================================================ */

SELECT
    Resource_Id,

    Activity,

    Client,

    Assignment_End,

    Assignment_Start,

    ROW_NUMBER() OVER
    (
        PARTITION BY Resource_Id

        ORDER BY
            Assignment_End DESC,
            Assignment_Start DESC,
            ActivityAssignment_Id DESC
    ) AS RowNo

INTO #LatestCompletedAssignment

FROM #ConsultantAssignments

WHERE
    Assignment_End < @Today;


/* ============================================================
   PARTIAL PROJECT ASSIGNMENTS:
   BUGÜN AKTİF OLAN ASSIGNMENT'LAR
   ============================================================ */

SELECT
    Resource_Id,

    ActivityAssignment_Id,

    Resource_Name,

    [Level],

    [Group],

    Client,

    PROJECT_ID,

    Assignment_Start,

    Assignment_End

INTO #ActiveAssignments

FROM #ConsultantAssignments

WHERE
    ActivityAssignment_Id IS NOT NULL

    AND PROJECT_ID IS NOT NULL

    AND Client IS NOT NULL

    AND Assignment_Start <= @Today

    AND ISNULL(
            Assignment_End,
            CONVERT(date, '99991231')
        ) >= @Today;


/* ============================================================
   PROJE BAZINDA HAFTALIK SAATLER

   Aynı consultant aynı projede birden fazla assignment'a
   sahipse saatleri aynı hafta ve proje altında birleştirir.
   ============================================================ */

SELECT
    aa.Resource_Id,

    aa.Resource_Name,

    aa.[Level],

    aa.[Group],

    aa.Client,

    aa.PROJECT_ID,

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
    ) AS Logged_Hours

INTO #WeeklyProjectHours

FROM #ActiveAssignments aa

JOIN REPL_SF.[TimeEntry] te
    ON te.KimbleOne__ActivityAssignment__c =
       aa.ActivityAssignment_Id

JOIN REPL_SF.TimePeriod tp
    ON tp.Id = te.KimbleOne__TimePeriod__c

WHERE
    tp.KimbleOne__EndDate__c IS NOT NULL

    AND CAST(
            tp.KimbleOne__EndDate__c AS date
        ) >= @WindowStart

    /*
        İçinde bulunduğumuz tamamlanmamış hafta hariç.
    */
    AND CAST(
            tp.KimbleOne__EndDate__c AS date
        ) < @CurrentWeekStart

GROUP BY
    aa.Resource_Id,
    aa.Resource_Name,
    aa.[Level],
    aa.[Group],
    aa.Client,
    aa.PROJECT_ID,

    DATEADD(
        WEEK,
        DATEDIFF(
            WEEK,
            0,
            tp.KimbleOne__EndDate__c
        ),
        0
    );


/* ============================================================
   PARTIAL PROJECT ASSIGNMENT ÖZETİ
   ============================================================ */

SELECT
    Resource_Id,

    Resource_Name,

    [Level],

    [Group],

    Client,

    PROJECT_ID,

    SUM(
        CASE
            WHEN Logged_Hours > 0
                 AND Logged_Hours < 40
                THEN 1
            ELSE 0
        END
    ) AS Partial_Weeks,

    SUM(
        CASE
            WHEN Logged_Hours > 0
                 AND Logged_Hours < 40
                THEN Logged_Hours
            ELSE 0
        END
    ) AS Partial_Hours,

    AVG(
        CASE
            WHEN Logged_Hours > 0
                 AND Logged_Hours < 40
                THEN CAST(
                        Logged_Hours / 40.0
                        AS decimal(10,4)
                     )
            ELSE NULL
        END
    ) AS Average_Partial_Capacity

INTO #PartialAssignmentSummary

FROM #WeeklyProjectHours

GROUP BY
    Resource_Id,
    Resource_Name,
    [Level],
    [Group],
    Client,
    PROJECT_ID;


/* ============================================================
   RESULT SET 1: BENCH STATUS TABLE
   ============================================================ */

SELECT
    rs.Resource_Id AS [Resource ID],

    rs.Resource_Name AS [Resource name],

    rs.[Level],

    rs.[Group],

    CASE
        WHEN rs.Last_Assignment_End_Date IS NULL
            THEN NULL

        ELSE DATEDIFF
        (
            WEEK,

            DATEADD(
                WEEK,
                DATEDIFF(
                    WEEK,
                    0,
                    rs.Last_Assignment_End_Date
                ),
                0
            ),

            @CurrentWeekStart
        )
    END AS [Number of weeks on bench since last assignment],

    lca.Activity AS [Activity],

    CAST(NULL AS varchar(500))
        AS [Possible Next Assignment]

FROM #ResourceSummary rs

LEFT JOIN #LatestCompletedAssignment lca
    ON lca.Resource_Id = rs.Resource_Id
    AND lca.RowNo = 1

WHERE
    rs.Active_Project_Count = 0

ORDER BY
    [Number of weeks on bench since last assignment] DESC,
    rs.Resource_Name;


/* ============================================================
   RESULT SET 2: PARTIALLY PROJECT ASSIGNMENTS TABLE
   ============================================================ */

SELECT
    pas.Resource_Id AS [Resource ID],

    pas.Resource_Name AS [Resource name],

    pas.[Level],

    pas.[Group],

    pas.Client,

    pas.Partial_Weeks
        AS [Weeks assigned to project (<100% billable)],

    CAST(
        pas.Average_Partial_Capacity * 100
        AS decimal(10,2)
    ) AS [Time (%)]

FROM #PartialAssignmentSummary pas

WHERE
    pas.Partial_Weeks > 0

ORDER BY
    pas.Partial_Weeks DESC,
    pas.Resource_Name,
    pas.Client;


/* ============================================================
   GEÇİCİ TABLOLARI TEMİZLE
   ============================================================ */

DROP TABLE IF EXISTS #PartialAssignmentSummary;
DROP TABLE IF EXISTS #WeeklyProjectHours;
DROP TABLE IF EXISTS #ActiveAssignments;
DROP TABLE IF EXISTS #LatestCompletedAssignment;
DROP TABLE IF EXISTS #ResourceSummary;
DROP TABLE IF EXISTS #ConsultantAssignments;