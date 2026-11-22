namespace WorkforcePlanning.Application.Common;

public static class WeekdayParser
{
    public static bool TryParse(string? raw, out DayOfWeek dayOfWeek)
    {
        dayOfWeek = DayOfWeek.Monday;
        if (string.IsNullOrWhiteSpace(raw)) return false;

        var r = Normalize(raw);

        if (r is "2" or "t2" or "thu2" or "mon" or "monday" || r.StartsWith("mon") || r.Contains("thuhai"))
        {
            dayOfWeek = DayOfWeek.Monday;
            return true;
        }

        if (r is "3" or "t3" or "thu3" or "tue" or "tuesday" || r.StartsWith("tue") || r.Contains("thuba"))
        {
            dayOfWeek = DayOfWeek.Tuesday;
            return true;
        }

        if (r is "4" or "t4" or "thu4" or "wed" or "wednesday" || r.StartsWith("wed") || r.Contains("thutu"))
        {
            dayOfWeek = DayOfWeek.Wednesday;
            return true;
        }

        if (r is "5" or "t5" or "thu5" or "thu" or "thursday" || r.StartsWith("thur") || r.Contains("thunam"))
        {
            dayOfWeek = DayOfWeek.Thursday;
            return true;
        }

        if (r is "6" or "t6" or "thu6" or "fri" or "friday" || r.StartsWith("fri") || r.Contains("thusau"))
        {
            dayOfWeek = DayOfWeek.Friday;
            return true;
        }

        if (r is "7" or "t7" or "thu7" or "sat" or "saturday" || r.StartsWith("sat") || r.Contains("thubay"))
        {
            dayOfWeek = DayOfWeek.Saturday;
            return true;
        }

        if (r is "8" or "cn" or "sun" or "sunday" || r.StartsWith("sun") || r.Contains("chunhat"))
        {
            dayOfWeek = DayOfWeek.Sunday;
            return true;
        }

        if (Enum.TryParse<DayOfWeek>(raw.Trim(), ignoreCase: true, out var parsed))
        {
            dayOfWeek = parsed;
            return true;
        }

        return false;
    }

    public static DateOnly? ToWorkDate(DayOfWeek dayOfWeek, DateOnly weekStartMonday)
    {
        var mondayDow = DayOfWeek.Monday;
        var offset = ((int)dayOfWeek - (int)mondayDow + 7) % 7;
        var result = weekStartMonday.AddDays(offset);
        return WeekCalendar.IsInWeek(result, weekStartMonday) ? result : null;
    }

    public static bool TryParseToWorkDate(string? raw, DateOnly weekStartMonday, out DateOnly workDate)
    {
        workDate = default;
        if (!TryParse(raw, out var dow)) return false;
        var mapped = ToWorkDate(dow, weekStartMonday);
        if (mapped is null) return false;
        workDate = mapped.Value;
        return true;
    }

    private static string Normalize(string raw)
    {
        var s = raw.Trim().ToLowerInvariant();
        s = s.Normalize(System.Text.NormalizationForm.FormD);
        var chars = s.Where(c => char.GetUnicodeCategory(c) != System.Globalization.UnicodeCategory.NonSpacingMark);
        s = new string(chars.ToArray());
        s = s.Replace("đ", "d").Replace(" ", "");
        return s;
    }
}