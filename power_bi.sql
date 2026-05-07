WITH Base AS (
    SELECT
        e.DISPLAY_NAME AS employee_name,
        e.JOB_LEVEL AS employee_level,
        e.JOB_TITLE AS job_title,
        e.OFFICE_LOCATION AS office_location,
        e.INTEGRATION_ID AS employee_integration_id,

        u.Username AS sf_user,
        r.Id AS resource_id,
        r.Name AS resource_name,

        p.PROJECT_ID AS project_id,
        p.PROJECT_NAME AS project_name,
        p.PROJECT_TYPE AS project_type,
        p.PROJECT_STATUS AS project_status,

        CAST(aa.KimbleOne__StartDate__c AS DATE) AS assignment_start_date,
        CAST(aa.KimbleOne__ForecastP2EndDate__c AS DATE) AS assignment_end_date,

        CAST(aa.KimbleOne__StartDate__c AS DATE) AS project_start_date,
        CAST(aa.KimbleOne__ForecastP2EndDate__c AS DATE) AS project_end_date,

        COALESCE(aa.KimbleOne__UtilisationPercentage__c, 0) / 100.0 AS utilisation_rate

    FROM REPL_SF.ActivityAssignment aa

    INNER JOIN REPL_SF.Resource r
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
        aa.KimbleOne__StartDate__c IS NOT NULL
        AND aa.KimbleOne__ForecastP2EndDate__c IS NOT NULL
        AND aa.KimbleOne__ForecastP2EndDate__c >= DATEADD(MONTH, -6, CAST(GETDATE() AS DATE))
        AND e.DISPLAY_NAME IS NOT NULL
),

Numbers AS (
    SELECT TOP (104)
        ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
    FROM sys.objects
),

Weekly AS (
    SELECT
        b.employee_name,
        b.employee_level,
        b.job_title,
        b.office_location,
        b.employee_integration_id,
        b.sf_user,
        b.resource_id,
        b.resource_name,

        b.project_id,
        b.project_name,
        b.project_type,
        b.project_status,

        b.project_start_date,
        b.project_end_date,
        b.assignment_start_date,
        b.assignment_end_date,

        CAST(
            DATEADD(
                WEEK,
                n.n,
                DATEADD(DAY, 1 - DATEPART(WEEKDAY, b.assignment_start_date), b.assignment_start_date)
            ) AS DATE
        ) AS week_start_date,

        b.utilisation_rate

    FROM Base b

    INNER JOIN Numbers n
        ON DATEADD(WEEK, n.n, b.assignment_start_date) <= b.assignment_end_date
),

FactEmployeeProjectWeekly AS (
    SELECT
        employee_name,
        employee_level,
        job_title,
        office_location,
        employee_integration_id,
        sf_user,
        resource_id,
        resource_name,

        project_id,
        project_name,
        project_type,
        project_status,

        project_start_date,
        project_end_date,
        assignment_start_date,
        assignment_end_date,

        week_start_date,
        DATEADD(DAY, 6, week_start_date) AS week_end_date,

        YEAR(week_start_date) AS year_number,
        MONTH(week_start_date) AS month_number,
        DATENAME(MONTH, week_start_date) AS month_name,
        DATEPART(ISO_WEEK, week_start_date) AS iso_week_number,

        CASE
            WHEN project_end_date < CAST(GETDATE() AS DATE) THEN 'Completed CPAD'
            ELSE 'Active CPAD'
        END AS cpad_type,

        SUM(40 * utilisation_rate) AS assigned_hours,
        CAST(40 AS DECIMAL(10,2)) AS capacity_hours,

        SUM(40 * utilisation_rate) / 40.0 AS utilisation_pct,

        CASE
            WHEN SUM(40 * utilisation_rate) = 0 THEN 'Bench'
            WHEN SUM(40 * utilisation_rate) < 40 THEN 'Partially Allocated'
            WHEN SUM(40 * utilisation_rate) = 40 THEN 'Fully Allocated'
            WHEN SUM(40 * utilisation_rate) > 40 THEN 'Overallocated'
        END AS allocation_status

    FROM Weekly

    WHERE week_start_date >= DATEADD(MONTH, -6, CAST(GETDATE() AS DATE))

    GROUP BY
        employee_name,
        employee_level,
        job_title,
        office_location,
        employee_integration_id,
        sf_user,
        resource_id,
        resource_name,
        project_id,
        project_name,
        project_type,
        project_status,
        project_start_date,
        project_end_date,
        assignment_start_date,
        assignment_end_date,
        week_start_date
)

SELECT
    employee_name,
    employee_level,
    job_title,
    office_location,
    employee_integration_id,
    sf_user,
    resource_id,
    resource_name,

    project_id,
    project_name,
    project_type,
    project_status,

    project_start_date,
    project_end_date,
    assignment_start_date,
    assignment_end_date,

    week_start_date,
    week_end_date,
    year_number,
    month_number,
    month_name,
    iso_week_number,

    cpad_type,
    allocation_status,

    assigned_hours,
    capacity_hours,
    utilisation_pct

FROM FactEmployeeProjectWeekly

ORDER BY
    employee_name,
    week_start_date,
    project_name;