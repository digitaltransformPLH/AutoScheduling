using ClosedXML.Excel;
using FluentValidation;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

/// <summary>
/// Excel layout aligned with Availability File sheet "Employee Master" + column Plant (integer).
/// </summary>
internal static class EmployeeExcelColumns
{
    public const string SheetName = "Employee Master";

    public static readonly string[] Headers =
    [
        "Employee Name",
        "Employee ID",
        "Position",
        "Employment Type",
        "Labor group",
        "Status",
        "Plant"
    ];
}

internal sealed class EmployeeExcelService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertEmployeeRequest> _validator;

    public EmployeeExcelService(
        WorkforcePlanningDbContext db,
        IValidator<UpsertEmployeeRequest> validator)
    {
        _db = db;
        _validator = validator;
    }

    public async Task<byte[]> ExportAsync(
        string? plantCode,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken)
    {
        var rows = await QueryForExportAsync(plantCode, accessiblePlantCodes, cancellationToken);

        using var wb = new XLWorkbook();
        var ws = wb.Worksheets.Add(EmployeeExcelColumns.SheetName);

        for (var c = 0; c < EmployeeExcelColumns.Headers.Length; c++)
            ws.Cell(1, c + 1).Value = EmployeeExcelColumns.Headers[c];

        var headerRow = ws.Row(1);
        headerRow.Style.Font.Bold = true;
        ws.SheetView.FreezeRows(1);

        var r = 2;
        foreach (var e in rows)
        {
            ws.Cell(r, 1).Value = e.FullName;
            ws.Cell(r, 2).Value = e.EmployeeNumber;
            ws.Cell(r, 3).Value = e.Position;
            ws.Cell(r, 4).Value = e.EmploymentType;
            ws.Cell(r, 5).Value = e.LaborGroup;
            ws.Cell(r, 6).Value = e.Status;
            if (TryParsePlantCodeAsInt(e.PlantCode, out var plantInt))
                ws.Cell(r, 7).Value = plantInt;
            else
                ws.Cell(r, 7).Value = e.PlantCode;
            r++;
        }

        ws.Columns().AdjustToContents();
        ws.Column(2).Style.NumberFormat.Format = "0";
        ws.Column(7).Style.NumberFormat.Format = "0";

        using var ms = new MemoryStream();
        wb.SaveAs(ms);
        return ms.ToArray();
    }

    public async Task<EmployeeImportResultDto> ImportAsync(
        Stream content,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken)
    {
        var result = new EmployeeImportResultDto();
        var storeCodes = await _db.Stores.AsNoTracking().Select(s => s.Code).ToListAsync(cancellationToken);
        var storeCodeSet = storeCodes.ToHashSet(StringComparer.OrdinalIgnoreCase);

        using var wb = new XLWorkbook(content);
        var ws = wb.Worksheets.FirstOrDefault(w =>
            string.Equals(w.Name, EmployeeExcelColumns.SheetName, StringComparison.OrdinalIgnoreCase))
            ?? wb.Worksheets.First();

        var headerMap = ReadHeaderMap(ws);
        if (headerMap.Count == 0)
        {
            result.Failed = 1;
            result.Errors.Add(new EmployeeImportRowErrorDto { Row = 1, Message = "Không tìm thấy dòng tiêu đề." });
            return result;
        }

        var required = new[]
        {
            "employee name", "employee id", "position", "employment type", "labor group", "status", "plant"
        };
        foreach (var key in required)
        {
            if (!headerMap.ContainsKey(key))
            {
                result.Failed = 1;
                result.Errors.Add(new EmployeeImportRowErrorDto
                {
                    Row = 1,
                    Message = $"Thiếu cột bắt buộc: {key}."
                });
                return result;
            }
        }

        var lastRow = ws.LastRowUsed()?.RowNumber() ?? 1;
        var seenEmployeeIds = new HashSet<long>();
        var existingByNumber = await _db.Employees.ToDictionaryAsync(e => e.EmployeeNumber, cancellationToken);

        for (var row = 2; row <= lastRow; row++)
        {
            var name = GetCellString(ws, row, headerMap["employee name"]);
            if (string.IsNullOrWhiteSpace(name))
                continue;

            try
            {
                if (!TryGetEmployeeId(ws, row, headerMap["employee id"], out var employeeNumber))
                    throw new ArgumentException("Employee ID không hợp lệ.");

                if (!seenEmployeeIds.Add(employeeNumber))
                    throw new ArgumentException($"Employee ID {employeeNumber} trùng trong file.");

                if (!TryResolvePlantCode(ws, row, headerMap["plant"], storeCodeSet, out var plantCode))
                    throw new ArgumentException("Plant không hợp lệ hoặc cửa hàng không tồn tại.");

                if (accessiblePlantCodes is not null && !accessiblePlantCodes.Contains(plantCode, StringComparer.OrdinalIgnoreCase))
                    throw new ArgumentException($"Không có quyền trên Plant {plantCode}.");

                var request = new UpsertEmployeeRequest
                {
                    FullName = name.Trim(),
                    EmployeeNumber = employeeNumber,
                    PlantCode = plantCode,
                    Position = GetCellString(ws, row, headerMap["position"]).Trim(),
                    EmploymentType = GetCellString(ws, row, headerMap["employment type"]).Trim(),
                    LaborGroup = GetCellString(ws, row, headerMap["labor group"]).Trim(),
                    Status = NormalizeStatus(GetCellString(ws, row, headerMap["status"]))
                };

                await _validator.ValidateAndThrowAsync(request, cancellationToken);

                if (existingByNumber.TryGetValue(employeeNumber, out var entity))
                {
                    entity.FullName = request.FullName;
                    entity.PlantCode = request.PlantCode;
                    entity.Position = request.Position;
                    entity.EmploymentType = request.EmploymentType;
                    entity.LaborGroup = request.LaborGroup;
                    entity.Status = request.Status;
                    entity.UpdatedAt = DateTimeOffset.UtcNow;
                    result.Updated++;
                }
                else
                {
                    var now = DateTimeOffset.UtcNow;
                    var created = new Employee
                    {
                        FullName = request.FullName,
                        EmployeeNumber = request.EmployeeNumber,
                        PlantCode = request.PlantCode,
                        Position = request.Position,
                        EmploymentType = request.EmploymentType,
                        LaborGroup = request.LaborGroup,
                        Status = request.Status,
                        CreatedAt = now,
                        UpdatedAt = now
                    };
                    _db.Employees.Add(created);
                    existingByNumber[employeeNumber] = created;
                    result.Created++;
                }
            }
            catch (Exception ex)
            {
                result.Failed++;
                result.Errors.Add(new EmployeeImportRowErrorDto
                {
                    Row = row,
                    Message = ex is ValidationException ve
                        ? string.Join("; ", ve.Errors.Select(e => e.ErrorMessage))
                        : ex.Message
                });
            }
        }

        if (result.Created > 0 || result.Updated > 0)
            await _db.SaveChangesAsync(cancellationToken);

        return result;
    }

    private async Task<List<Employee>> QueryForExportAsync(
        string? plantCode,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken)
    {
        var q = _db.Employees.AsNoTracking().AsQueryable();

        if (accessiblePlantCodes is not null)
        {
            if (accessiblePlantCodes.Count == 0) return [];
            q = q.Where(e => accessiblePlantCodes.Contains(e.PlantCode));
        }

        if (!string.IsNullOrWhiteSpace(plantCode))
            q = q.Where(e => e.PlantCode == plantCode.Trim());

        return await q
            .OrderBy(e => e.PlantCode)
            .ThenBy(e => e.FullName)
            .ToListAsync(cancellationToken);
    }

    private static Dictionary<string, int> ReadHeaderMap(IXLWorksheet ws)
    {
        var map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        var lastCol = ws.LastColumnUsed()?.ColumnNumber() ?? 0;
        for (var col = 1; col <= lastCol; col++)
        {
            var raw = ws.Cell(1, col).GetString().Trim();
            if (string.IsNullOrEmpty(raw)) continue;
            var key = NormalizeHeader(raw);
            map[key] = col;
        }

        return map;
    }

    private static string NormalizeHeader(string raw) =>
        raw.Trim().ToLowerInvariant();

    private static string GetCellString(IXLWorksheet ws, int row, int col)
    {
        var cell = ws.Cell(row, col);
        if (cell.DataType == XLDataType.DateTime)
            return cell.GetDateTime().ToString("yyyy-MM-dd");
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

    private static bool TryParsePlantCodeAsInt(string plantCode, out int value)
    {
        value = 0;
        if (int.TryParse(plantCode, out value)) return true;
        return false;
    }

    private static string NormalizeStatus(string raw)
    {
        var s = raw.Trim();
        if (string.IsNullOrEmpty(s)) return "Active";
        if (EmployeeCatalog.Statuses.Contains(s, StringComparer.OrdinalIgnoreCase))
            return EmployeeCatalog.Statuses.First(x => string.Equals(x, s, StringComparison.OrdinalIgnoreCase));
        return s;
    }
}