using System.Globalization;

namespace WorkforcePlanning.Infrastructure.Services;

internal static class SchedulingValueFormatter
{
    public static string? DateToString(object? value) => value switch
    {
        null => null,
        DateOnly d => d.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
        DateTime dt => dt.Date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
        string s => s,
        _ => value.ToString()
    };

    public static string? DateTimeToString(object? value) => value switch
    {
        null => null,
        DateTime dt => dt.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture),
        string s => s,
        _ => value.ToString()
    };

    public static string? TimeToString(object? value) => value switch
    {
        null => null,
        TimeSpan t => $"{(int)t.TotalHours:D2}:{t.Minutes:D2}",
        DateTime dt => dt.ToString("HH:mm", CultureInfo.InvariantCulture),
        string s => s.Length > 5 ? s[..5] : s,
        _ => value.ToString()
    };

    public static double? ToDouble(object? value) => value switch
    {
        null => null,
        double d => d,
        float f => f,
        decimal m => (double)m,
        int i => i,
        long l => l,
        _ => double.TryParse(value.ToString(), NumberStyles.Any, CultureInfo.InvariantCulture, out var x) ? x : null
    };

    public static int ToInt(object? value) => value switch
    {
        int i => i,
        long l => (int)l,
        short s => s,
        byte b => b,
        _ => int.TryParse(value?.ToString(), out var x) ? x : 0
    };

    public static bool ToBool(object? value) => value switch
    {
        bool b => b,
        byte by => by != 0,
        short s => s != 0,
        int i => i != 0,
        _ => bool.TryParse(value?.ToString(), out var x) && x
    };
}