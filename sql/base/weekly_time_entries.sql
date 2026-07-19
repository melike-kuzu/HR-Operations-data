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
    Bu sorgu her Activity Assignment için haftalık toplam saatleri üretir.

    WeekStart her zaman Monday'dir.
    Bu tarih mantığı mevcut çalışan SQL'lerinle aynıdır.
*/

SELECT
    te.KimbleOne__ActivityAssignment__c
        AS ActivityAssignment_Id,

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

    SUM(
        ISNULL(
            te.KimbleOne__EntryUnits__c,
            0
        )
    ) / 8.0 AS Consumed_Days,

    CAST(
        CASE
            WHEN SUM(
                    ISNULL(
                        te.KimbleOne__EntryUnits__c,
                        0
                    )
                 ) >= 40
                THEN 1.00

            WHEN SUM(
                    ISNULL(
                        te.KimbleOne__EntryUnits__c,
                        0
                    )
                 ) > 0
                THEN SUM(
                        ISNULL(
                            te.KimbleOne__EntryUnits__c,
                            0
                        )
                     ) / 40.0

            ELSE 0
        END
        AS decimal(10,2)
    ) AS Capacity

FROM REPL_SF.[TimeEntry] te

JOIN REPL_SF.TimePeriod tp
    ON tp.Id = te.KimbleOne__TimePeriod__c

WHERE
    te.KimbleOne__ActivityAssignment__c IS NOT NULL

    AND tp.KimbleOne__EndDate__c IS NOT NULL

    /*
        Son bir yıllık Project Tracker geçmişi
        ve mevcut yılın ileri tarih kayıtları için yeterli pencere.
    */
    AND CAST(
            tp.KimbleOne__EndDate__c AS date
        ) >= @WindowStart

    AND CAST(
            tp.KimbleOne__EndDate__c AS date
        ) <= @YearEnd

GROUP BY
    te.KimbleOne__ActivityAssignment__c,

    DATEADD(
        WEEK,
        DATEDIFF(
            WEEK,
            0,
            tp.KimbleOne__EndDate__c
        ),
        0
    )

ORDER BY
    ActivityAssignment_Id,
    WeekStart;