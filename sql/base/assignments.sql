SET NOCOUNT ON;

DECLARE @Today date = CAST(GETDATE() AS date);

/*
    Bu sorgu consultant, project ve assignment bilgilerini getirir.

    Her satır:
    bir consultant'ın bir activity assignment kaydıdır.
*/

SELECT
    r.Id AS Resource_Id,

    aa.Id AS ActivityAssignment_Id,

    e.DISPLAY_NAME AS Consultant_Name,

    e.JOB_LEVEL AS [Level],

    e.JOB_TITLE AS Job_Title,

    e.DEPARTMENT AS [Group],

    e.OFFICE_LOCATION AS Location,

    ra.Id AS ResourceActivity_Id,

    ra.Name AS Activity,

    p.PROJECT_ID,

    p.PROJECT_NAME AS Project_Name,

    p.PROJECT_TYPE AS Project_Type,

    p.PROJECT_STATUS AS Project_Status,

    CAST(
        aa.KimbleOne__StartDate__c AS date
    ) AS Assignment_Start,

    CAST(
        aa.KimbleOne__ForecastP2EndDate__c AS date
    ) AS Assignment_End,

    CASE
        WHEN CAST(
                aa.KimbleOne__StartDate__c AS date
             ) <= @Today

             AND ISNULL(
                    CAST(
                        aa.KimbleOne__ForecastP2EndDate__c
                        AS date
                    ),
                    CONVERT(date, '99991231')
                 ) >= @Today

             AND p.PROJECT_ID IS NOT NULL

            THEN 1

        ELSE 0
    END AS Is_Active_Assignment

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
    e.DISPLAY_NAME IS NOT NULL

ORDER BY
    e.DISPLAY_NAME,
    aa.KimbleOne__StartDate__c,
    p.PROJECT_NAME;