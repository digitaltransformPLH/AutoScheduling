namespace WorkforcePlanning.Application.Common;

public static class BusyTimeParser
{
    public static bool IsPaidLeaveToken(string? raw) =>
        string.Equals(raw?.Trim(), "AL", StringComparison.OrdinalIgnoreCase);

    public static bool TryParse(string? raw, out TimeOnly? time)
    {
        time = null;
        if (raw is null) return false;
        var s = raw.Trim();
        if (string.IsNullOrEmpty(s)) return false;
        if (IsPaidLeaveToken(s)) return true;

        if (TimeOnly.TryParse(s, out var direct))
        {
            time = direct;
            return true;
        }

        if (DateTime.TryParse(s, out var dt))
        {
            time = TimeOnly.FromDateTime(dt);
            return true;
        }

        if (s.Contains(':') && TimeSpan.TryParse(s, out var ts))
        {
            time = TimeOnly.FromTimeSpan(ts);
            return true;
        }

        return false;
    }

    public static string FormatForExcel(TimeOnly? time, bool isPaidLeave)
    {
        if (isPaidLeave) return "AL";
        if (time is null) return "";
        return time.Value.ToString("HH:mm");
    }
}