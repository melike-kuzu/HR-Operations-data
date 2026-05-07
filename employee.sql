WITH MaxDate AS (
    SELECT
        MAX(CAST(te.KimbleOne__StartTime__c AS DATE)) AS Max_Time_Entry_Date
    FROM REPL_SF.TimeEntry te
    WHERE te.KimbleOne__StartTime__c IS NOT NULL
),

CurrentWeek AS (
    SELECT
        DATEADD(
            DAY,
            1 - DATEPART(WEEKDAY, Max_Time_Entry_Date),
            Max_Time_Entry_Date
        ) AS Current_Week_Start
    FROM MaxDate
),

TimeEntryBase AS (
    SELECT
        COALESCE(e.DISPLAY_NAME, r.Name, u.Name, u.Username) AS Consultant_Name,
        e.JOB_LEVEL AS Level,
        e.JOB_TITLE AS Job_Title,
        e.OFFICE_LOCATION AS Location,

        u.Username AS SF_User,
        r.Name AS Resource_Name,

        p.PROJECT_NAME AS Project_Name,
        p.PROJECT_TYPE AS Project_Type,
        p.PROJECT_STATUS AS Project_Status,

        CAST(te.KimbleOne__StartTime__c AS DATE) AS Time_Entry_Date,
        te.KimbleOne__EntryUnitsInHours__c AS Hours_Entered,

        DATEADD(
            DAY,
            1 - DATEPART(WEEKDAY, CAST(te.KimbleOne__StartTime__c AS DATE)),
            CAST(te.KimbleOne__StartTime__c AS DATE)
        ) AS WeekStart

    FROM REPL_SF.TimeEntry te

    LEFT JOIN REPL_SF.ActivityAssignment aa
        ON aa.Id = te.KimbleOne__ActivityAssignment__c

    LEFT JOIN REPL_SF.Resource r
        ON r.Id = aa.KimbleOne__Resource__c

    LEFT JOIN REPL_SF.[User] u
        ON u.Id = r.KimbleOne__User__c

    LEFT JOIN ANALYTICS.DIM_EMPLOYEE e
        ON e.INTEGRATION_ID = u.Username

    LEFT JOIN REPL_SF.ResourceActivity ra
        ON ra.Id = aa.KimbleOne__ResourcedActivity__c

    LEFT JOIN ANALYTICS.DIM_PROJECT p
        ON p.PROJECT_ID = ra.Id

    CROSS JOIN CurrentWeek cw

    WHERE
        te.KimbleOne__StartTime__c IS NOT NULL
        AND te.KimbleOne__EntryUnitsInHours__c IS NOT NULL
        AND CAST(te.KimbleOne__StartTime__c AS DATE) >= DATEADD(WEEK, -25, cw.Current_Week_Start)
),

WeeklyHours AS (
    SELECT
        Consultant_Name,
        Level,
        Job_Title,
        Location,
        SF_User,
        Resource_Name,
        Project_Name,
        Project_Type,
        Project_Status,
        WeekStart,
        SUM(Hours_Entered) AS Hours_Entered
    FROM TimeEntryBase
    GROUP BY
        Consultant_Name,
        Level,
        Job_Title,
        Location,
        SF_User,
        Resource_Name,
        Project_Name,
        Project_Type,
        Project_Status,
        WeekStart
)

SELECT
    wh.Consultant_Name,
    wh.Level,
    wh.Job_Title,
    wh.Location,
    wh.SF_User,
    wh.Resource_Name,
    wh.Project_Name,
    wh.Project_Type,
    wh.Project_Status,

    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -25, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_25,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -24, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_24,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -23, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_23,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -22, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_22,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -21, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_21,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -20, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_20,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -19, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_19,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -18, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_18,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -17, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_17,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -16, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_16,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -15, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_15,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -14, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_14,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -13, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_13,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -12, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_12,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -11, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_11,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -10, cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_10,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -9,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_9,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -8,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_8,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -7,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_7,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -6,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_6,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -5,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_5,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -4,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_4,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -3,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_3,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -2,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_2,
    SUM(CASE WHEN wh.WeekStart = DATEADD(WEEK, -1,  cw.Current_Week_Start) THEN wh.Hours_Entered ELSE 0 END) AS Week_Minus_1,
    SUM(CASE WHEN wh.WeekStart = cw.Current_Week_Start THEN wh.Hours_Entered ELSE 0 END) AS Current_Week,

    SUM(wh.Hours_Entered) AS Total_Hours_Last_26_Weeks

FROM WeeklyHours wh
CROSS JOIN CurrentWeek cw

GROUP BY
    wh.Consultant_Name,
    wh.Level,
    wh.Job_Title,
    wh.Location,
    wh.SF_User,
    wh.Resource_Name,
    wh.Project_Name,
    wh.Project_Type,
    wh.Project_Status

ORDER BY
    wh.Consultant_Name,
    wh.Project_Name;