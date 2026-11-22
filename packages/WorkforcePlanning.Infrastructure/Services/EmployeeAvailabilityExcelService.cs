using ClosedXML.Excel;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.Common;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

internal static class EmployeeAvailabilityExcelColumns
{
    public const string SheetName = "Availability";

    public static readonly string[] Headers =
    [
        "Employee Name",
        "Employee ID",
        "Plant",
        "Ngày",
        "Bận từ",
        "Bận đến"
    ];
}

internal sealed class EmployeeAvailabilityExcelService
{
    private readonly WorkforcePlanningDbContext _db;

    public EmployeeAvailabilityExcelService(WorkforcePlanningDbContext db) => _db = db;

    public async Task<byte[]> ExportAsync(
        string plantCode,
        DateOnly weekStartMonday,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken)
    {
        if (accessiblePlantCodes is { Count: 0 })
            return BuildWorkbook([]);

        var q = _db.EmployeeAvailabilitySlots.AsNoTracking()
            .Include(s => s.Employee)
            .Where(s => s.PlantCode == plantCode.Trim() && s.WeekStartMonday == weekStartMonday);

        if (accessiblePlantCodes is not null)
            q = q.Where(s => accessiblePlantCodes.Contains(s.PlantCode));

        var rows = await q
            .OrderBy(s => s.EmployeeNumber)
            .ThenBy(s => s.WorkDate)
            .ToListAsync(cancellationToken);

        return BuildWorkbook(rows);
    }

    public async Task<EmployeeAvailabilityImportResultDto> ImportAsync(
        Stream content,
        DateOnly weekStartMonday,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken)
    {
        var weekEnd = WeekCalendar.WeekEndSunday(weekStartMonday);
        var result = new EmployeeAvailabilityImportResultDto
        {
            WeekStartMonday = weekStartMonday.ToString("yyyy-MM-dd"),
            WeekEndSunday = weekEnd.ToString("yyyy-MM-dd")
        };

        var storeCodes = await _db.Stores.AsNoTracking().Select(s => s.Code).ToListAsync(cancellationToken);
        var storeCodeSet = storeCodes.ToHashSet(StringComparer.OrdinalIgnoreCase);
        var employees = await _db.Employees.AsNoTracking().ToListAsync(cancellationToken);
        var employeeByNumber = employees.ToDictionary(e => e.EmployeeNumber);

        using var wb = new XLWorkbook(content);
        var ws = wb.Worksheets.FirstOrDefault(w =>
            string.Equals(w.Name, EmployeeAvailabilityExcelColumns.SheetName, StringComparison.OrdinalIgnoreCase))
            ?? wb.Worksheets.First();

        var headerMap = ReadHeaderMap(ws);
        if (headerMap.Count == 0)
        {
            result.Failed = 1;
            result.Errors.Add(new EmployeeImportRowErrorDto { Row = 1, Message = "Không tìm thấy dòng tiêu đề." });
            return result;
        }

        if (!headerMap.ContainsKey("employee name") || !headerMap.ContainsKey("employee id") || !headerMap.ContainsKey("plant"))
        {
            result.Failed = 1;
            result.Errors.Add(new EmployeeImportRowErrorDto { Row = 1, Message = "Thiếu cột bắt buộc (Employee Name, Employee ID, Plant)." });
            return result;
        }

        var dayCol = ResolveColumn(headerMap, "ngày", "ngay", "day", "weekday");
        var fromCol = ResolveColumn(headerMap, "bận từ", "ban tu", "busy from", "busy start", "from");
        var toCol = ResolveColumn(headerMap, "bận đến", "ban den", "busy to", "busy end", "to");
        if (dayCol == 0 || fromCol == 0 || toCol == 0)
        {
            result.Failed = 1;
            result.Errors.Add(new EmployeeImportRowErrorDto { Row = 1, Message = "Thiếu cột Ngày / Bận từ / Bận đến." });
            return result;
        }

        var lastRow = ws.LastRowUsed()?.RowNumber() ?? 1;
        var parsedSlots = new List<(int Row, EmployeeAvailabilitySlot Slot)>();
        var plantsInFile = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        for (var row = 2; row <= lastRow; row++)
        {
            var name = GetCellString(ws, row, headerMap["employee name"]);
            if (string.IsNullOrWhiteSpace(name))
                continue;

            try
            {
                if (!TryGetEmployeeId(ws, row, headerMap["employee id"], out var employeeNumber))
                    throw new ArgumentException("Employee ID không hợp lệ.");

                if (!TryResolvePlantCode(ws, row, headerMap["plant"], storeCodeSet, out var plantCode))
                    throw new ArgumentException("Plant không hợp lệ hoặc cửa hàng không tồn tại.");

                if (accessiblePlantCodes is not null && !accessiblePlantCodes.Contains(plantCode, StringComparer.OrdinalIgnoreCase))
                    throw new ArgumentException($"Không có quyền trên Plant {plantCode}.");

                if (!employeeByNumber.TryGetValue(employeeNumber, out var emp))
                    throw new ArgumentException($"Employee ID {employeeNumber} không có trong master.");

                var rawDay = GetCellString(ws, row, dayCol);
                if (!WeekdayParser.TryParseToWorkDate(rawDay, weekStartMonday, out var workDate))
                    throw new ArgumentException($"Ngày không hợp lệ: {rawDay}.");

                if (!await EmployeeAvailabilityPlantEligibility.IsEmployeeEligibleAsync(
                        _db, emp, plantCode, workDate, cancellationToken))
                    throw new ArgumentException(
                        $"Nhân viên {employeeNumber} không thuộc Plant {plantCode} và không mượn vào cửa hàng trong ngày {rawDay}.");

                var rawFrom = GetCellString(ws, row, fromCol);
                var rawTo = GetCellString(ws, row, toCol);
                var isAl = BusyTimeParser.IsPaidLeaveToken(rawFrom) && BusyTimeParser.IsPaidLeaveToken(rawTo);

                TimeOnly? busyFrom = null;
                TimeOnly? busyTo = null;
                if (isAl)
                {
                    if (!string.IsNullOrWhiteSpace(rawFrom) || !string.IsNullOrWhiteSpace(rawTo))
                    {
                        if (!BusyTimeParser.IsPaidLeaveToken(rawFrom) || !BusyTimeParser.IsPaidLeaveToken(rawTo))
                            throw new ArgumentException("Nghỉ phép phải ghi AL ở cả Bận từ và Bận đến.");
                    }
                }
                else
                {
                    if (!BusyTimeParser.TryParse(rawFrom, out busyFrom) || busyFrom is null)
                        throw new ArgumentException("Bận từ không hợp lệ.");
                    if (!BusyTimeParser.TryParse(rawTo, out busyTo) || busyTo is null)
                        throw new ArgumentException("Bận đến không hợp lệ.");
                    if (busyTo <= busyFrom)
                        throw new ArgumentException("Bận đến phải sau Bận từ.");
                }

                var now = DateTimeOffset.UtcNow;
                var slot = new EmployeeAvailabilitySlot
                {
                    PlantCode = plantCode,
                    EmployeeNumber = employeeNumber,
                    EmployeeId = emp.Id,
                    WeekStartMonday = weekStartMonday,
                    WorkDate = workDate,
                    BusyFrom = isAl ? null : busyFrom,
                    BusyTo = isAl ? null : busyTo,
                    IsPaidLeave = isAl,
                    CreatedAt = now,
                    UpdatedAt = now
                };
                parsedSlots.Add((row, slot));
                plantsInFile.Add(plantCode);
            }
            catch (Exception ex)
            {
                result.Failed++;
                result.Errors.Add(new EmployeeImportRowErrorDto { Row = row, Message = ex.Message });
            }
        }

        if (parsedSlots.Count == 0)
            return result;

        await using var tx = await _db.Database.BeginTransactionAsync(cancellationToken);
        foreach (var plant in plantsInFile)
        {
            await _db.EmployeeAvailabilitySlots
                .Where(s => s.PlantCode == plant && s.WeekStartMonday == weekStartMonday)
                .ExecuteDeleteAsync(cancellationToken);
        }

        foreach (var (_, slot) in parsedSlots)
            _db.EmployeeAvailabilitySlots.Add(slot);

        await _db.SaveChangesAsync(cancellationToken);
        await tx.CommitAsync(cancellationToken);
        result.Created = parsedSlots.Count;
        return result;
    }

    private static byte[] BuildWorkbook(IReadOnlyList<EmployeeAvailabilitySlot> rows)
    {
        using var wb = new XLWorkbook();
        var ws = wb.Worksheets.Add(EmployeeAvailabilityExcelColumns.SheetName);

        for (var c = 0; c < EmployeeAvailabilityExcelColumns.Headers.Length; c++)
            ws.Cell(1, c + 1).Value = EmployeeAvailabilityExcelColumns.Headers[c];

        ws.Row(1).Style.Font.Bold = true;
        ws.SheetView.FreezeRows(1);

        var r = 2;
        foreach (var slot in rows)
        {
            var name = slot.Employee?.FullName ?? "";
            ws.Cell(r, 1).Value = name;
            ws.Cell(r, 2).Value = slot.EmployeeNumber;
            ws.Cell(r, 3).Value = slot.PlantCode;
            ws.Cell(r, 4).Value = WeekCalendar.EnglishWeekdayName(slot.WorkDate);
            ws.Cell(r, 5).Value = BusyTimeParser.FormatForExcel(slot.BusyFrom, slot.IsPaidLeave);
            ws.Cell(r, 6).Value = BusyTimeParser.FormatForExcel(slot.BusyTo, slot.IsPaidLeave);
            r++;
        }

        ws.Columns().AdjustToContents();
        ws.Column(2).Style.NumberFormat.Format = "0";

        using var ms = new MemoryStream();
        wb.SaveAs(ms);
        return ms.ToArray();
    }

    private static Dictionary<string, int> ReadHeaderMap(IXLWorksheet ws)
    {
        var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        var lastCol = ws.LastColumnUsed()?.ColumnNumber() ?? 0;
        for (var col = 1; col <= lastCol; col++)
        {
            var raw = ws.Cell(1, col).GetString().Trim();
            if (string.IsNullOrEmpty(raw)) continue;
            map[NormalizeHeader(raw)] = col;
        }

        return map;
    }

    private static string NormalizeHeader(string raw) => raw.Trim().ToLowerInvariant();

    private static int ResolveColumn(Dictionary<string, int> headerMap, params string[] keys)
    {
        foreach (var key in keys)
        {
            if (headerMap.TryGetValue(key, out var col))
                return col;
        }

        return 0;
    }

    private static string GetCellString(IXLWorksheet ws, int row, int col)
    {
        var cell = ws.Cell(row, col);
        if (cell.DataType == XLDataType.DateTime)
            return cell.GetDateTime().ToString("yyyy-MM-dd");
        if (cell.DataType == XLDataType.TimeSpan)
            return TimeOnly.FromTimeSpan(cell.GetTimeSpan()).ToString("HH:mm");
        return cell.GetString().Trim();
    }

    private static bool TryGetEmployeeId(IXLWorksheet ws, int row, int col, out long employeeNumber)
    {
        employeeNumber = 0;
        var cell = ws.Cell(row, col);
        if (cell.DataType == XLDataType.Number)
        {
            var n = cell.GetDouble();
            if (n <= 0 || n != Math.Floor(n)) return false;
            employeeNumber = (long)n;
            return true;
        }

        var s = cell.GetString().Trim();
        return long.TryParse(s, out employeeNumber) && employeeNumber > 0;
    }

    private static bool TryResolvePlantCode(
        IXLWorksheet ws,
        int row,
        int col,
        HashSet<string> storeCodes,
        out string plantCode) =>
        EmployeeExcelPlantHelper.TryResolvePlantCode(ws, row, col, storeCodes, out plantCode);
}

internal static class EmployeeExcelPlantHelper
{
    public static bool TryResolvePlantCode(
        IXLWorksheet ws,
        int row,
        int col,
        HashSet<string> storeCodes,
        out string plantCode)
    {
        plantCode = string.Empty;
        var cell = ws.Cell(row, col);

        if (cell.DataType == XLDataType.Number)
        {
            var n = cell.GetDouble();
            if (n <= 0 || n != Math.Floor(n)) return false;
            return TryMatchStoreCode((long)n, storeCodes, out plantCode);
        }

        var s = cell.GetString().Trim();
        if (string.IsNullOrEmpty(s)) return false;

        if (storeCodes.Contains(s))
        {
            plantCode = storeCodes.First(c => string.Equals(c, s, StringComparison.OrdinalIgnoreCase));
            return true;
        }

        if (long.TryParse(s, out var parsed))
            return TryMatchStoreCode(parsed, storeCodes, out plantCode);

        return false;
    }

    private static bool TryMatchStoreCode(long plant, HashSet<string> storeCodes, out string plantCode)
    {
        plantCode = string.Empty;
        var asString = plant.ToString();
        if (storeCodes.Contains(asString))
        {
            plantCode = storeCodes.First(c => string.Equals(c, asString, StringComparison.OrdinalIgnoreCase));
            return true;
        }

        foreach (var code in storeCodes)
        {
            if (long.TryParse(code, out var n) && n == plant)
            {
                plantCode = code;
                return true;
            }
        }

        return false;
    }
}