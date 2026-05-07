WITH Base AS (
    SELECT
        e.DISPLAY_NAME AS Consultant_Name,
        e.JOB_LEVEL AS Level,
        e.JOB_TITLE AS Job_Title,
        e.OFFICE_LOCATION AS Location,

        u.Username AS SF_User,
        r.Name AS Resource_Name,

        p.PROJECT_NAME AS Project_Name,
        p.PROJECT_TYPE AS Project_Type,
        p.PROJECT_STATUS AS Project_Status,

        aa.KimbleOne__StartDate__c AS Project_Start_Date,
        aa.KimbleOne__ForecastP2EndDate__c AS Project_End_Date,
        aa.KimbleOne__UtilisationPercentage__c / 100.0 AS UtilPct,

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
        aa.KimbleOne__ForecastP2EndDate__c >= DATEADD(MONTH, -6, GETDATE())
        AND e.DISPLAY_NAME IS NOT NULL
),

Numbers AS (
    SELECT TOP (26)
        ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
    FROM sys.objects
),

Weekly AS (
    SELECT
        b.Consultant_Name,
        b.Level,
        b.Job_Title,
        b.Location,

        b.Project_Name,
        b.Project_Type,
        b.Project_Status,

        b.Project_Start_Date,
        b.Project_End_Date,

        DATEADD(
            WEEK,
            n.n,
            DATEADD(DAY, 1 - DATEPART(WEEKDAY, b.Assignment_Start), b.Assignment_Start)
        ) AS WeekStart,

        b.UtilPct,

        CASE
            WHEN b.Project_End_Date < GETDATE() THEN 'Completed CPAD'
            ELSE 'Active CPAD'
        END AS CPAD_Type

    FROM Base b
    JOIN Numbers n
        ON DATEADD(WEEK, n.n, b.Assignment_Start) <= b.Assignment_End
),

Capacity AS (
    SELECT
        Consultant_Name,
        Level,
        Job_Title,
        Location,
        Project_Name,
        Project_Start_Date,
        Project_End_Date,
        CPAD_Type,
        Project_Type,
        WeekStart,
        UtilPct,

        40 * UtilPct AS Weekly_Assigned_Hours

    FROM Weekly
),

Aggregated AS (
    SELECT
        Consultant_Name,
        Level,
        Job_Title,
        Location,
        Project_Name,
        Project_Start_Date,
        Project_End_Date,
        CPAD_Type,
        Project_Type,
        WeekStart,

        SUM(Weekly_Assigned_Hours) AS Assigned_Hours,
        40 AS Capacity_Hours,

        CASE
            WHEN SUM(Weekly_Assigned_Hours) = 0 THEN 0
            ELSE SUM(Weekly_Assigned_Hours) / 40.0
        END AS Utilisation_Pct

    FROM Capacity
    WHERE WeekStart >= DATEADD(MONTH, -6, GETDATE())
    GROUP BY
        Consultant_Name,
        Level,
        Job_Title,
        Location,
        Project_Name,
        Project_Start_Date,
        Project_End_Date,
        CPAD_Type,
        Project_Type,
        WeekStart
)

SELECT *
FROM Aggregated
ORDER BY
    Consultant_Name,
    WeekStart,
    Project_Name;