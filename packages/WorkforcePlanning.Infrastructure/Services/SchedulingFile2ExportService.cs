using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using ClosedXML.Excel;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
namespace WorkforcePlanning.Infrastructure.Services;

public partial class SchedulingFile2ExportService : ISchedulingFile2ExportService
{
    private static readonly string[] Headers =
    [
        "Mã CH", "Mã nhân viên", "Tên nhân viên", "Template", "Ngày bắt đầu (dd.MM.yyyy)", "Ngày kết thúc (dd.MM.yyyy)",
        "Mã ca làm việc/Loại nghỉ/ công tác (Tr.hợp phân loại nghỉ phép/ công tác thì phải phân ca của 2003 kèm theo, không phân ca OFF)",
        "Giờ vào (HH:mm)", "Giờ ra (HH:mm)"
    ];

    private static readonly double[] ColWidths = [8, 14, 28, 10, 25, 25, 62, 16, 16];
    private const int Template = 2003;
    private static readonly HashSet<string> PaidDayTypes = new(StringComparer.Ordinal)
    {
        "Làm", "Nghỉ phép", "Đi hỗ trợ"
    };

    private readonly ISchedulingReadService _read;

    public SchedulingFile2ExportService(ISchedulingReadService read) => _read = read;

    public async Task<File2ExportResult> ExportAsync(string storeCode, DateOnly weekStart, CancellationToken cancellationToken = default)
    {
        var week = await _read.GetScheduleWeekAsync(storeCode, weekStart, cancellationToken)
            ?? throw new KeyNotFoundException($"chưa có lịch cho store {storeCode} tuần {weekStart:yyyy-MM-dd}");

        var roster = (await _read.GetRosterAsync(storeCode, weekStart, cancellationToken))
            .Where(r => r.HomeStore is null)
            .ToList();

        var missing = roster.Where(r => PaidDayTypes.Contains(r.DayType) && string.IsNullOrWhiteSpace(r.ShiftCode)).ToList();
        if (missing.Count > 0)
        {
            var msg = string.Join("; ", missing.Take(20).Select(r =>
                $"{r.EmployeeId} - {r.EmployeeName} - {r.WorkDate}: {r.StartTime}-{r.EndTime}"));
            throw new InvalidOperationException($"ca không có mã chấm công: {msg}");
        }

        using var wb = new XLWorkbook();
        var ws = wb.Worksheets.Add("Sheet1");
        for (var i = 0; i < Headers.Length; i++)
            ws.Cell(1, i + 1).Value = Headers[i];

        var codeCell = AttendanceStoreCode(storeCode);
        foreach (var r in roster)
        {
            var workDate = DateOnly.Parse(r.WorkDate, CultureInfo.InvariantCulture);
            var ds = workDate.ToString("dd.MM.yyyy", CultureInfo.InvariantCulture);
            var row = ws.LastRowUsed()?.RowNumber() + 1 ?? 2;
            ws.Cell(row, 1).Value = codeCell;
            ws.Cell(row, 2).Value = r.EmployeeId;
            ws.Cell(row, 3).Value = r.EmployeeName;
            ws.Cell(row, 4).Value = Template;
            ws.Cell(row, 5).Value = ds;
            ws.Cell(row, 6).Value = ds;
            if (PaidDayTypes.Contains(r.DayType))
            {
                var code = r.ShiftCode!;
                ws.Cell(row, 7).Value = int.TryParse(code, out var n) ? n : code;
                if (!string.IsNullOrWhiteSpace(r.StartTime))
                {
                    ws.Cell(row, 8).Value = r.StartTime;
                    ws.Cell(row, 8).Style.DateFormat.Format = "HH:mm";
                }
                if (!string.IsNullOrWhiteSpace(r.EndTime))
                {
                    ws.Cell(row, 9).Value = r.EndTime;
                    ws.Cell(row, 9).Style.DateFormat.Format = "HH:mm";
                }
            }
            else
            {
                ws.Cell(row, 7).Value = "OFF";
            }
        }

        for (var i = 0; i < ColWidths.Length; i++)
            ws.Column(i + 1).Width = ColWidths[i];

        await using var buf = new MemoryStream();
        wb.SaveAs(buf);
        var shortName = AsciiSafe(week.StoreName ?? storeCode);
        var weekEnd = weekStart.AddDays(6);
        var fileName =
            $"{storeCode}_{shortName}_Upload_Phan_Cong_{weekStart:yyyyMMdd}-{weekEnd:yyyyMMdd}.xlsx";

        return new File2ExportResult { Content = buf.ToArray(), FileName = fileName };
    }

    private static string AttendanceStoreCode(string storeId)
    {
        var digits = DigitsOnly().Replace(storeId, "");
        return digits.Length >= 4 ? $"PL{digits[^4..]}" : storeId;
    }

    private static string AsciiSafe(string s)
    {
        var normalized = s.Replace("đ", "d").Replace("Đ", "D").Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder();
        foreach (var ch in normalized)
        {
            if (char.GetUnicodeCategory(ch) != UnicodeCategory.NonSpacingMark)
                sb.Append(ch);
        }
        var cleaned = NonAlnum().Replace(sb.ToString(), "_").Trim('_');
        return string.IsNullOrEmpty(cleaned) ? "store" : cleaned;
    }

    [GeneratedRegex(@"\D")]
    private static partial Regex DigitsOnly();

    [GeneratedRegex(@"[^A-Za-z0-9]+")]
    private static partial Regex NonAlnum();
}