namespace WorkforcePlanning.Application.Common;

public static class WeekCalendar
{
    public static DateOnly SnapToMonday(DateOnly anchor)
    {
        var dow = (int)anchor.DayOfWeek;
        var daysFromMonday = dow == 0 ? 6 : dow - 1;
        return anchor.AddDays(-daysFromMonday);
    }

    public static DateOnly WeekEndSunday(DateOnly weekStartMonday) => weekStartMonday.AddDays(6);

    public static bool IsInWeek(DateOnly workDate, DateOnly weekStartMonday)
    {
        var end = WeekEndSunday(weekStartMonday);
        return workDate >= weekStartMonday && workDate <= end;
    }

    public static int DayOffsetFromMonday(DateOnly workDate, DateOnly weekStartMonday) =>
        workDate.DayNumber - weekStartMonday.DayNumber;

    public static string EnglishWeekdayName(DateOnly date) =>
        date.DayOfWeek switch
        {
            DayOfWeek.Monday => "Monday",
            DayOfWeek.Tuesday => "Tuesday",
            DayOfWeek.Wednesday => "Wednesday",
            DayOfWeek.Thursday => "Thursday",
            DayOfWeek.Friday => "Friday",
            DayOfWeek.Saturday => "Saturday",
            DayOfWeek.Sunday => "Sunday",
            _ => "Monday"
        };
}