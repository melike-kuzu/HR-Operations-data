SELECT 
    eg.name AS engagement_name,
    am.Name AS Account_Manager_Name,
    am.Email AS Account_Manager_Email,
    ra.KimbleOne__FullName__c AS project_name,

    MAX(pmn.Name) AS Project_Managers_Names,
    MAX(pme.email) AS Project_Managers_emails,

    MAX(CAST(aa.KimbleOne__ForecastP3EndDate__c AS DATE)) AS Project_Expected_Delivery_Date,
    ra.id AS project_id,
    p.name AS project_type,
    ac.name AS account,
    eg.id AS engagement_id,

    CASE 
        WHEN ac.name = 'ATC Operations LLC' THEN 'pol.oliva@clearpeaks.com'
        WHEN ac.name = 'ADNOC' THEN 'wilinton.tenorio@clearpeaks.com'
        WHEN ac.name = 'Abu Dhabi Department of Government Enablement' THEN 'pere.vegas@clearpeaks.com'
        WHEN ac.name = 'NOATUM HOLDINGS SL' THEN 'jordi.sota@clearpeaks.com'
        WHEN ac.name = 'ClearPeaks SL' AND ee.name = 'Observation Deck' THEN 'natanael.hidalgo@clearpeaks.com'
        ELSE NULL 
    END AS Program_Manager_Email

FROM repl_sf.ActivityAssignment aa
LEFT JOIN repl_sf.ResourceActivity ra 
    ON aa.KimbleOne__ResourcedActivity__c = ra.Id
LEFT JOIN repl_sf.EngagementElement ee 
    ON ra.KimbleOne__DeliveryElement__c = ee.id
LEFT JOIN repl_sf.Engagement eg 
    ON ra.KimbleOne__DeliveryGroup__c = eg.id
LEFT JOIN repl_sf.Account ac 
    ON eg.KimbleOne__Account__c = ac.Id
LEFT JOIN repl_sf.[User] am 
    ON am.Id = ac.OwnerId
LEFT JOIN repl_sf.ActivityRole ar 
    ON ar.Id = aa.KimbleOne__ActivityRole__c
LEFT JOIN repl_sf.Resource re 
    ON re.Id = aa.KimbleOne__Resource__c
LEFT JOIN repl_sf.[User] u 
    ON u.Id = re.KimbleOne__User__c
LEFT JOIN repl_sf.Product p 
    ON p.Id = ee.KimbleOne__Product__c
LEFT JOIN repl_sf.Proposal ps 
    ON ps.Id = eg.KimbleOne__Proposal__c
LEFT JOIN repl_sf.ForecastStatus fs 
    ON fs.Id = ps.KimbleOne__ForecastStatus__c

LEFT JOIN (
    SELECT
        ProjectName,
        STRING_AGG(names, ', ') AS Name
    FROM (
        SELECT
            RA.KimbleOne__FullName__c AS ProjectName,
            PM.Name AS names,
            RANK() OVER(
                PARTITION BY RA.KimbleOne__FullName__c 
                ORDER BY AA.KimbleOne__ForecastP1EndDate__c DESC
            ) AS rnk
        FROM REPL_SF.ResourceActivity RA
        LEFT JOIN REPL_SF.ActivityAssignment AA 
            ON RA.Id = AA.KimbleOne__ResourcedActivity__c
        LEFT JOIN REPL_SF.ActivityRole AR 
            ON AA.KimbleOne__ActivityRole__c = AR.Id
        LEFT JOIN REPL_SF.Resource R 
            ON AA.KimbleOne__Resource__c = R.Id
        LEFT JOIN REPL_SF.[User] PM 
            ON R.KimbleOne__User__c = PM.Id
        LEFT JOIN ANALYTICS.DIM_EMPLOYEE DE 
            ON DE.MAIL = PM.Username
        WHERE
            DE.ACTIVE_FLG = 'Yes'
            AND AR.Name = 'Project Manager'
    ) aux
    WHERE rnk = 1
    GROUP BY ProjectName
) pmn 
    ON ra.KimbleOne__FullName__c = pmn.ProjectName

LEFT JOIN (
    SELECT
        ProjectName,
        STRING_AGG(emails, ';') AS email
    FROM (
        SELECT
            RA.KimbleOne__FullName__c AS ProjectName,
            PM.Email AS emails,
            RANK() OVER(
                PARTITION BY RA.KimbleOne__FullName__c 
                ORDER BY AA.KimbleOne__ForecastP1EndDate__c DESC
            ) AS rnk
        FROM REPL_SF.ResourceActivity RA
        LEFT JOIN REPL_SF.ActivityAssignment AA 
            ON RA.Id = AA.KimbleOne__ResourcedActivity__c
        LEFT JOIN REPL_SF.ActivityRole AR 
            ON AA.KimbleOne__ActivityRole__c = AR.Id
        LEFT JOIN REPL_SF.Resource R 
            ON AA.KimbleOne__Resource__c = R.Id
        LEFT JOIN REPL_SF.[User] PM 
            ON R.KimbleOne__User__c = PM.Id
        LEFT JOIN ANALYTICS.DIM_EMPLOYEE DE 
            ON DE.MAIL = PM.Username
        WHERE
            DE.ACTIVE_FLG = 'Yes'
            AND AR.Name = 'Project Manager'
    ) aux
    WHERE rnk = 1
    GROUP BY ProjectName
) pme 
    ON ra.KimbleOne__FullName__c = pme.ProjectName

WHERE fs.name = '100%'

GROUP BY 
    eg.Name,
    am.Name,
    am.Email,
    ra.Name,
    ra.KimbleOne__FullName__c,
    ra.id,
    p.name,
    ac.name,
    eg.id,
    CASE 
        WHEN ac.name = 'ATC Operations LLC' THEN 'pol.oliva@clearpeaks.com'
        WHEN ac.name = 'ADNOC' THEN 'wilinton.tenorio@clearpeaks.com'
        WHEN ac.name = 'Abu Dhabi Department of Government Enablement' THEN 'pere.vegas@clearpeaks.com'
        WHEN ac.name = 'NOATUM HOLDINGS SL' THEN 'jordi.sota@clearpeaks.com'
        WHEN ac.name = 'ClearPeaks SL' AND ee.name = 'Observation Deck' THEN 'natanael.hidalgo@clearpeaks.com'
        ELSE NULL 
    END;
