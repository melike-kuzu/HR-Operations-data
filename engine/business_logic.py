from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from engine.master_dataset import MasterData


WEEKLY_CAPACITY_HOURS = 40.0
DAILY_CAPACITY_HOURS = 8.0


@dataclass(frozen=True)
class CalendarSettings:
    """
    Consultant Tracker ve Utilisation için kullanılan tarih ayarları.
    """

    as_of_date: pd.Timestamp
    year_start: pd.Timestamp
    year_end: pd.Timestamp
    current_week_start: pd.Timestamp
    first_week_start: pd.Timestamp
    last_week_start: pd.Timestamp


def normalise_date(value: str | date | pd.Timestamp | None) -> pd.Timestamp:
    """
    Verilen tarihi normalize eder.

    Saat, dakika ve saniye bilgisini kaldırır.
    Değer verilmezse bugünün tarihini kullanır.
    """

    if value is None:
        result = pd.Timestamp.today()
    else:
        result = pd.Timestamp(value)

    return result.normalize()


def monday_of_week(value: str | date | pd.Timestamp) -> pd.Timestamp:
    """
    Verilen tarihin bulunduğu haftanın pazartesi gününü döndürür.
    """

    timestamp = normalise_date(value)

    return timestamp - pd.Timedelta(days=timestamp.weekday())


def first_monday_on_or_after(value: str | date | pd.Timestamp) -> pd.Timestamp:
    """
    Verilen tarihte veya sonrasındaki ilk pazartesiyi döndürür.
    """

    timestamp = normalise_date(value)
    days_until_monday = (7 - timestamp.weekday()) % 7

    return timestamp + pd.Timedelta(days=days_until_monday)


def last_monday_on_or_before(value: str | date | pd.Timestamp) -> pd.Timestamp:
    """
    Verilen tarihte veya öncesindeki son pazartesiyi döndürür.
    """

    return monday_of_week(value)


def create_calendar_settings(
    as_of_date: str | date | pd.Timestamp | None = None,
) -> CalendarSettings:
    """
    Mevcut takvim yılı için Consultant Tracker tarih ayarlarını üretir.
    """

    current_date = normalise_date(as_of_date)

    year_start = pd.Timestamp(
        year=current_date.year,
        month=1,
        day=1,
    )

    year_end = pd.Timestamp(
        year=current_date.year,
        month=12,
        day=31,
    )

    return CalendarSettings(
        as_of_date=current_date,
        year_start=year_start,
        year_end=year_end,
        current_week_start=monday_of_week(current_date),
        first_week_start=first_monday_on_or_after(year_start),
        last_week_start=last_monday_on_or_before(year_end),
    )


def create_week_list(
    first_week_start: pd.Timestamp,
    last_week_start: pd.Timestamp,
) -> pd.DatetimeIndex:
    """
    İki tarih arasında pazartesi bazlı haftalık tarih listesi oluşturur.
    """

    return pd.date_range(
        start=first_week_start,
        end=last_week_start,
        freq="7D",
    )


def calculate_capacity(logged_hours: pd.Series) -> pd.Series:
    """
    Haftalık girilen saatlerden capacity hesaplar.

    40 saat veya üzeri:
        1.00

    20 saat:
        0.50

    0 saat:
        0.00
    """

    hours = pd.to_numeric(
        logged_hours,
        errors="coerce",
    ).fillna(0)

    capacity = hours / WEEKLY_CAPACITY_HOURS

    return capacity.clip(lower=0, upper=1).round(2)

def get_eligible_assignments(
    assignments: pd.DataFrame,
    as_of_date: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Orijinal Consultant Tracker SQL'iyle aynı consultant population'ını
    oluşturan geçerli proje assignment kayıtlarını döndürür.

    Dahil edilme kuralları:
    - Resource_Id mevcut olmalı.
    - Consultant_Name mevcut olmalı.
    - Project_Name mevcut olmalı.
    - Assignment raporlama yılıyla kesişmeli.
    """

    settings = create_calendar_settings(as_of_date)

    eligible = assignments.copy()

    eligible["Assignment_Start"] = pd.to_datetime(
        eligible["Assignment_Start"],
        errors="coerce",
    ).dt.normalize()

    eligible["Assignment_End"] = pd.to_datetime(
        eligible["Assignment_End"],
        errors="coerce",
    ).dt.normalize()

    has_resource = eligible["Resource_Id"].notna()

    has_consultant_name = (
        eligible["Consultant_Name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    )

    has_project = (
        eligible["Project_Name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    )

    overlaps_reporting_year = (
        eligible["Assignment_Start"].notna()
        & eligible["Assignment_Start"].le(settings.year_end)
        & (
            eligible["Assignment_End"].isna()
            | eligible["Assignment_End"].ge(settings.year_start)
        )
    )

    eligible = eligible.loc[
        has_resource
        & has_consultant_name
        & has_project
        & overlaps_reporting_year
    ].copy()

    return eligible.reset_index(drop=True)

def get_eligible_resource_ids(
    assignments: pd.DataFrame,
    as_of_date: str | date | pd.Timestamp | None = None,
) -> set[object]:
    """
    Geçerli consultant population'ındaki Resource_Id değerlerini döndürür.
    """

    eligible_assignments = get_eligible_assignments(
        assignments=assignments,
        as_of_date=as_of_date,
    )

    return set(
        eligible_assignments["Resource_Id"]
        .dropna()
        .unique()
    )


def is_assignment_active_on_date(
    assignments: pd.DataFrame,
    target_date: str | date | pd.Timestamp,
) -> pd.Series:
    """
    Assignment'ın verilen tarihte aktif olup olmadığını hesaplar.
    """

    target = normalise_date(target_date)

    start = pd.to_datetime(
        assignments["Assignment_Start"],
        errors="coerce",
    )

    end = pd.to_datetime(
        assignments["Assignment_End"],
        errors="coerce",
    )

    has_project = (
        assignments["Project_Name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    )

    return (
        start.notna()
        & start.le(target)
        & (end.isna() | end.ge(target))
        & has_project
    )


def is_assignment_active_in_week(
    assignments: pd.DataFrame,
    week_start: str | date | pd.Timestamp,
) -> pd.Series:
    """
    Assignment'ın verilen pazartesi-pazar haftasıyla kesişip
    kesişmediğini hesaplar.
    """

    week = monday_of_week(week_start)
    week_end = week + pd.Timedelta(days=6)

    start = pd.to_datetime(
        assignments["Assignment_Start"],
        errors="coerce",
    )

    end = pd.to_datetime(
        assignments["Assignment_End"],
        errors="coerce",
    )

    has_project = (
        assignments["Project_Name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    )

    return (
        start.notna()
        & start.le(week_end)
        & (end.isna() | end.ge(week))
        & has_project
    )


def count_active_projects(
    assignments: pd.DataFrame,
    as_of_date: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Her consultant için aktif proje sayısını döndürür.
    """

    target_date = normalise_date(as_of_date)

    active_assignments = assignments.loc[
        is_assignment_active_on_date(
            assignments,
            target_date,
        )
    ].copy()

    if active_assignments.empty:
        return pd.DataFrame(
            columns=[
                "Resource_Id",
                "Active_Projects",
            ]
        )

    result = (
        active_assignments.groupby(
            "Resource_Id",
            dropna=False,
        )["PROJECT_ID"]
        .nunique()
        .rename("Active_Projects")
        .reset_index()
    )

    return result


def calculate_expected_availability(
    assignments: pd.DataFrame,
) -> pd.DataFrame:
    """
    Her consultant için en ileri assignment end tarihini döndürür.
    """

    valid_assignments = assignments.loc[
        assignments["Project_Name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
    ].copy()

    result = (
        valid_assignments.groupby(
            "Resource_Id",
            dropna=False,
        )["Assignment_End"]
        .max()
        .rename("Expected_Availability_Date")
        .reset_index()
    )

    return result


def get_consultant_directory(
    assignments: pd.DataFrame,
) -> pd.DataFrame:
    """
    Her consultant için tek satırlık temel bilgi tablosu oluşturur.
    """

    directory = (
        assignments.sort_values(
            [
                "Resource_Id",
                "Assignment_End",
                "Assignment_Start",
            ],
            na_position="last",
        )
        .groupby(
            "Resource_Id",
            dropna=False,
            as_index=False,
        )
        .agg(
            Consultant_Name=("Consultant_Name", "last"),
            Level=("Level", "last"),
            Group=("Group", "last"),
            Job_Title=("Job_Title", "last"),
            Location=("Location", "last"),
        )
    )

    return directory


def get_resource_weekly_time(
    data: MasterData,
    eligible_assignments: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Assignment seviyesindeki haftalık saatleri resource seviyesinde toplar.
    """


    assignment_source = (
        eligible_assignments
        if eligible_assignments is not None
        else data.assignments
    )

    assignment_map = assignment_source[
        [
            "ActivityAssignment_Id",
            "Resource_Id",
        ]
    ].drop_duplicates()

    weekly = data.time_entries.merge(
        assignment_map,
        on="ActivityAssignment_Id",
        how="inner",
        validate="many_to_one",
    )

    result = (
        weekly.groupby(
            [
                "Resource_Id",
                "WeekStart",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            Logged_Hours=("Logged_Hours", "sum"),
            Consumed_Days=("Consumed_Days", "sum"),
        )
    )

    result["Capacity"] = calculate_capacity(
        result["Logged_Hours"]
    )

    return result


def get_resource_weekly_leave(
    data: MasterData,
) -> pd.DataFrame:
    """
    Resource ve hafta seviyesinde izin verisini hazırlar.
    """

    leave = (
        data.leave.groupby(
            [
                "Resource_Id",
                "WeekStart",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            Leave_Hours=("Leave_Hours", "sum"),
            Leave_Info=("Leave_Info", "first"),
        )
    )

    leave["Is_Leave"] = leave["Leave_Hours"].gt(0)

    return leave


def get_future_assignment_weeks(
    assignments: pd.DataFrame,
    weeks: pd.DatetimeIndex,
    current_week_start: pd.Timestamp,
) -> pd.DataFrame:
    """
    Consultant'ın gelecekte hangi haftalarda aktif assignment'ı
    bulunduğunu hesaplar.

    Bu yöntem consultant'ın minimum başlangıç ve maksimum bitiş tarihi
    arasındaki boş haftaları yanlışlıkla booked göstermez.
    Gerçek assignment-week kesişimini kontrol eder.
    """

    future_weeks = [
        week
        for week in weeks
        if week > current_week_start
    ]

    rows: list[dict[str, object]] = []

    for week_start in future_weeks:
        active_mask = is_assignment_active_in_week(
            assignments,
            week_start,
        )

        active_resources = (
            assignments.loc[
                active_mask,
                "Resource_Id",
            ]
            .dropna()
            .drop_duplicates()
        )

        rows.extend(
            {
                "Resource_Id": resource_id,
                "WeekStart": week_start,
                "Has_Future_Assignment": True,
            }
            for resource_id in active_resources
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Resource_Id",
                "WeekStart",
                "Has_Future_Assignment",
            ]
        )

    return pd.DataFrame(rows)


def build_consultant_calendar_base(
    data: MasterData,
    as_of_date: str | date | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Consultant Tracker ve Utilisation tarafından kullanılacak
    ortak uzun format takvim tablosunu üretir.

    Bir satır:
        bir consultant + bir hafta
    """

    settings = create_calendar_settings(as_of_date)

    weeks = create_week_list(
        settings.first_week_start,
        settings.last_week_start,
    )

    


    eligible_assignments = get_eligible_assignments(
        assignments=data.assignments,
        as_of_date=settings.as_of_date,
    )

    consultants = get_consultant_directory(
        eligible_assignments
    )

    expected_availability = calculate_expected_availability(
        eligible_assignments
    )

    active_projects = count_active_projects(
        eligible_assignments,
        settings.as_of_date,
    )


    consultants = consultants.merge(
        expected_availability,
        on="Resource_Id",
        how="left",
        validate="one_to_one",
    )

    consultants = consultants.merge(
        active_projects,
        on="Resource_Id",
        how="left",
        validate="one_to_one",
    )

    consultants["Active_Projects"] = (
        consultants["Active_Projects"]
        .fillna(0)
        .astype(int)
    )

    week_frame = pd.DataFrame(
        {
            "WeekStart": weeks,
        }
    )

    consultants["_merge_key"] = 1
    week_frame["_merge_key"] = 1

    calendar = consultants.merge(
        week_frame,
        on="_merge_key",
        how="inner",
    ).drop(columns="_merge_key")

    weekly_time = get_resource_weekly_time(
        data=data,
        eligible_assignments=eligible_assignments,
    )
    weekly_leave = get_resource_weekly_leave(data)

    eligible_resource_ids = set(
        eligible_assignments["Resource_Id"]
        .dropna()
        .unique()
    )

    weekly_leave = weekly_leave.loc[
        weekly_leave["Resource_Id"].isin(
            eligible_resource_ids
        )
    ].copy()


    future_assignments = get_future_assignment_weeks(
        assignments=eligible_assignments,
        weeks=weeks,
        current_week_start=settings.current_week_start,
    )

    calendar = calendar.merge(
        weekly_time,
        on=[
            "Resource_Id",
            "WeekStart",
        ],
        how="left",
        validate="one_to_one",
    )

    calendar = calendar.merge(
        weekly_leave,
        on=[
            "Resource_Id",
            "WeekStart",
        ],
        how="left",
        validate="one_to_one",
    )

    calendar = calendar.merge(
        future_assignments,
        on=[
            "Resource_Id",
            "WeekStart",
        ],
        how="left",
        validate="one_to_one",
    )

    calendar["Logged_Hours"] = (
        calendar["Logged_Hours"]
        .fillna(0)
        .astype(float)
    )

    calendar["Consumed_Days"] = (
        calendar["Consumed_Days"]
        .fillna(0)
        .astype(float)
    )

    calendar["Capacity"] = (
        calendar["Capacity"]
        .fillna(0)
        .astype(float)
        .clip(lower=0, upper=1)
        .round(2)
    )

    calendar["Leave_Hours"] = (
        calendar["Leave_Hours"]
        .fillna(0)
        .astype(float)
    )

    calendar["Leave_Info"] = (
        calendar["Leave_Info"]
        .fillna("")
        .astype(str)
    )

    calendar["Is_Leave"] = (
        calendar["Is_Leave"]
        .fillna(False)
        .astype(bool)
    )

    calendar["Has_Future_Assignment"] = (
        calendar["Has_Future_Assignment"]
        .fillna(False)
        .astype(bool)
    )

    calendar["CalendarStatus"] = "BENCH"

    calendar.loc[
        calendar["Has_Future_Assignment"],
        "CalendarStatus",
    ] = "UNCONFIRMED"

    calendar.loc[
        calendar["Capacity"].gt(0)
        & calendar["Capacity"].lt(1),
        "CalendarStatus",
    ] = "PARTLY_BOOKED"

    calendar.loc[
        calendar["Capacity"].ge(1),
        "CalendarStatus",
    ] = "BOOKED"

        # Leave has the highest priority.
    calendar.loc[
        calendar["Is_Leave"],
        "CalendarStatus",
    ] = "ON_LEAVE"

    calendar["CalendarCapacity"] = 0.0

    calendar.loc[
        calendar["CalendarStatus"].eq("UNCONFIRMED"),
        "CalendarCapacity",
    ] = 1.0

    calendar.loc[
        calendar["CalendarStatus"].isin(
            [
                "BOOKED",
                "PARTLY_BOOKED",
            ]
        ),
        "CalendarCapacity",
    ] = calendar["Capacity"]

    calendar["CalendarValue"] = "B"

    calendar.loc[
        calendar["CalendarStatus"].eq("UNCONFIRMED"),
        "CalendarValue",
    ] = "1.00"

    calendar.loc[
        calendar["CalendarStatus"].isin(
            [
                "BOOKED",
                "PARTLY_BOOKED",
            ]
        ),
        "CalendarValue",
    ] = calendar["Capacity"].map(
        lambda value: f"{value:.2f}"
    )

    calendar.loc[
        calendar["CalendarStatus"].eq("ON_LEAVE"),
        "CalendarValue",
    ] = "L"

    return calendar.sort_values(
        [
            "Group",
            "Consultant_Name",
            "WeekStart",
        ]
    ).reset_index(drop=True)


def get_calendar_colour(status: str) -> str:
    """
    Calendar status değerini renk ismine dönüştürür.
    """

    colour_map = {
        "BOOKED": "RED",
        "UNCONFIRMED": "ORANGE",
        "PARTLY_BOOKED": "LIGHT_ORANGE",
        "ON_LEAVE": "YELLOW",
        "BENCH": "PURPLE",
    }

    return colour_map.get(status, "")