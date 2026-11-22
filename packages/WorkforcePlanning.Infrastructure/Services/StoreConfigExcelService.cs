using ClosedXML.Excel;
using FluentValidation;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

internal static class StoreConfigExcelColumns
{
    public const string SheetName = "Store Config";

    public static readonly string[] Headers =
    [
        "Mã Plant",
        "TCPH target",
        "Hệ số trần TCPH",
        "Open staff",
        "Close staff",
        "Min staff / slot"
    ];

    public static readonly string[] PlantAliases =
    [
        "mã plant", "ma plant", "plant", "mã cửa hàng", "ma cua hang", "plant code"
    ];

    public static readonly string[] TcphTargetAliases = ["tcph target", "tcph_target", "tcphtarget"];

    public static readonly string[] CeilingAliases =
    [
        "hệ số trần tcp",
        "he so tran tcp",
        "tcph ceiling mult",
        "tcph_ceiling_mult",
        "ceiling mult"
    ];

    public static readonly string[] OpenAliases = ["open staff", "open_staff"];
    public static readonly string[] CloseAliases = ["close staff", "close_staff"];
    public static readonly string[] MinAliases = ["min staff / slot", "min staff per slot", "min_staff_per_slot"];
}

internal sealed class StoreConfigExcelService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertStoreConfigRequest> _validator;

    public StoreConfigExcelService(
        WorkforcePlanningDbContext db,
        IValidator<UpsertStoreConfigRequest> validator)
    {
        _db = db;
        _validator = validator;
    }

    public async Task<byte[]> ExportAsync(
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken)
    {
        var q = _db.Stores.AsNoTracking().Where(s => s.IsActive);

        if (accessibleStoreCodes is not null)
        {
            if (accessibleStoreCodes.Count == 0)
                return BuildWorkbook([]);
            q = q.Where(s => accessibleStoreCodes.Contains(s.Code));
        }

        var stores = await q.OrderBy(s => s.Code).ToListAsync(cancellationToken);
        var storeIds = stores.Select(s => s.Id).ToList();
        var configs = storeIds.Count == 0
            ? new Dictionary<int, OpsStoreConfig>()
            : await _db.OpsStoreConfigs.AsNoTracking()
                .Where(c => storeIds.Contains(c.StoreId))
                .ToDictionaryAsync(c => c.StoreId, cancellationToken);

        var rows = stores.Select(s =>
        {
            configs.TryGetValue(s.Id, out var cfg);
            return (Store: s, Config: cfg);
        }).ToList();

        return BuildWorkbook(rows);
    }

    public async Task<StoreConfigImportResultDto> ImportAsync(
        Stream content,
        string updatedBy,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken)
    {
        var result = new StoreConfigImportResultDto();
        var storeRows = await _db.Stores.AsNoTracking()
            .Where(s => s.IsActive)
            .Select(s => new { s.Id, s.Code })
            .ToListAsync(cancellationToken);

        var storeByCode = storeRows.ToDictionary(
            s => s.Code,
            s => s,
            StringComparer.OrdinalIgnoreCase);
        var storeCodes = storeRows.Select(s => s.Code).ToHashSet(StringComparer.OrdinalIgnoreCase);

        using var wb = new XLWorkbook(content);
        var ws = wb.Worksheets.FirstOrDefault(w =>
            string.Equals(w.Name, StoreConfigExcelColumns.SheetName, StringComparison.OrdinalIgnoreCase))
            ?? wb.Worksheets.First();

        var headerMap = ReadHeaderMap(ws);
        if (headerMap.Count == 0)
        {
            result.Failed = 1;
            result.Errors.Add(new StoreConfigImportRowErrorDto { Row = 1, Message = "Không tìm thấy dòng tiêu đề." });
            return result;
        }

        if (!TryResolveColumn(headerMap, StoreConfigExcelColumns.PlantAliases, out var plantCol))
        {
            result.Failed = 1;
            result.Errors.Add(new StoreConfigImportRowErrorDto
            {
                Row = 1,
                Message = "Thiếu cột Mã Plant."
            });
            return result;
        }

        if (!TryResolveColumn(headerMap, StoreConfigExcelColumns.TcphTargetAliases, out var tcphCol))
        {
            result.Failed = 1;
            result.Errors.Add(new StoreConfigImportRowErrorDto
            {
                Row = 1,
                Message = "Thiếu cột TCPH target."
            });
            return result;
        }

        TryResolveColumn(headerMap, StoreConfigExcelColumns.CeilingAliases, out var ceilingCol);
        TryResolveColumn(headerMap, StoreConfigExcelColumns.OpenAliases, out var openCol);
        TryResolveColumn(headerMap, StoreConfigExcelColumns.CloseAliases, out var closeCol);
        TryResolveColumn(headerMap, StoreConfigExcelColumns.MinAliases, out var minCol);

        var existingConfigs = await _db.OpsStoreConfigs.ToDictionaryAsync(c => c.StoreId, cancellationToken);
        var now = DateTimeOffset.UtcNow;
        var actor = string.IsNullOrWhiteSpace(updatedBy) ? "import" : updatedBy.Trim();

        var lastRow = ws.LastRowUsed()?.RowNumber() ?? 1;
        for (var row = 2; row <= lastRow; row++)
        {
            var plantRaw = GetCellString(ws, row, plantCol);
            if (string.IsNullOrWhiteSpace(plantRaw))
                continue;

            string? plantCode = null;
            try
            {
                if (!TryResolvePlantCode(ws, row, plantCol, storeCodes, out var resolvedPlant))
                    throw new ArgumentException("Mã Plant không hợp lệ hoặc cửa hàng không tồn tại / không active.");

                plantCode = resolvedPlant;

                if (accessibleStoreCodes is not null
                    && !accessibleStoreCodes.Contains(resolvedPlant, StringComparer.OrdinalIgnoreCase))
                    throw new ArgumentException($"Không có quyền trên Plant {resolvedPlant}.");

                if (!storeByCode.TryGetValue(resolvedPlant, out var store))
                    throw new ArgumentException($"Cửa hàng {resolvedPlant} không tồn tại.");

                if (!TryGetDecimal(ws, row, tcphCol, out var tcphTarget) || tcphTarget <= 0)
                    throw new ArgumentException("TCPH target phải > 0.");

                var request = new UpsertStoreConfigRequest
                {
                    TcphTarget = tcphTarget,
                    TcphCeilingMult = ceilingCol > 0 && TryGetDecimal(ws, row, ceilingCol, out var ceiling)
                        ? ceiling
                        : OpsStoreConfigDefaultsDto.TcphCeilingMult,
                    OpenStaff = openCol > 0 && TryGetInt(ws, row, openCol, out var openStaff)
                        ? openStaff
                        : OpsStoreConfigDefaultsDto.OpenStaff,
                    CloseStaff = closeCol > 0 && TryGetInt(ws, row, closeCol, out var closeStaff)
                        ? closeStaff
                        : OpsStoreConfigDefaultsDto.CloseStaff,
                    MinStaffPerSlot = minCol > 0 && TryGetInt(ws, row, minCol, out var minStaff)
                        ? minStaff
                        : OpsStoreConfigDefaultsDto.MinStaffPerSlot
                };

                await _validator.ValidateAndThrowAsync(request, cancellationToken);

                if (existingConfigs.TryGetValue(store.Id, out var entity))
                {
                    entity.TcphTarget = request.TcphTarget;
                    entity.TcphCeilingMult = request.TcphCeilingMult;
                    entity.OpenStaff = request.OpenStaff;
                    entity.CloseStaff = request.CloseStaff;
                    entity.MinStaffPerSlot = request.MinStaffPerSlot;
                    entity.UpdatedAt = now;
                    entity.UpdatedBy = actor;
                    result.Updated++;
                }
                else
                {
                    entity = new OpsStoreConfig
                    {
                        StoreId = store.Id,
                        TcphTarget = request.TcphTarget,
                        TcphCeilingMult = request.TcphCeilingMult,
                        OpenStaff = request.OpenStaff,
                        CloseStaff = request.CloseStaff,
                        MinStaffPerSlot = request.MinStaffPerSlot,
                        CreatedAt = now,
                        UpdatedAt = now,
                        UpdatedBy = actor
                    };
                    _db.OpsStoreConfigs.Add(entity);
                    existingConfigs[store.Id] = entity;
                    result.Created++;
                }
            }
            catch (Exception ex)
            {
                result.Failed++;
                result.Errors.Add(new StoreConfigImportRowErrorDto
                {
                    Row = row,
                    PlantCode = plantCode ?? plantRaw.Trim(),
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

    private static byte[] BuildWorkbook(IReadOnlyList<(Store Store, OpsStoreConfig? Config)> rows)
    {
        using var wb = new XLWorkbook();
        var ws = wb.Worksheets.Add(StoreConfigExcelColumns.SheetName);

        for (var c = 0; c < StoreConfigExcelColumns.Headers.Length; c++)
            ws.Cell(1, c + 1).Value = StoreConfigExcelColumns.Headers[c];

        ws.Row(1).Style.Font.Bold = true;
        ws.SheetView.FreezeRows(1);

        var r = 2;
        foreach (var (store, cfg) in rows)
        {
            if (TryParsePlantCodeAsInt(store.Code, out var plantInt))
                ws.Cell(r, 1).Value = plantInt;
            else
                ws.Cell(r, 1).Value = store.Code;

            if (cfg is not null)
            {
                ws.Cell(r, 2).Value = cfg.TcphTarget;
                ws.Cell(r, 3).Value = cfg.TcphCeilingMult;
                ws.Cell(r, 4).Value = cfg.OpenStaff;
                ws.Cell(r, 5).Value = cfg.CloseStaff;
                ws.Cell(r, 6).Value = cfg.MinStaffPerSlot;
            }

            r++;
        }

        ws.Columns().AdjustToContents();
        ws.Column(1).Style.NumberFormat.Format = "@";
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

    private static bool TryResolveColumn(Dictionary<string, int> headerMap, string[] aliases, out int col)
    {
        col = 0;
        foreach (var alias in aliases)
        {
            if (headerMap.TryGetValue(NormalizeHeader(alias), out col))
                return true;
        }

        return false;
    }

    private static string NormalizeHeader(string raw) => raw.Trim().ToLowerInvariant();

    private static string GetCellString(IXLWorksheet ws, int row, int col) =>
        ws.Cell(row, col).GetString().Trim();

    private static bool TryGetDecimal(IXLWorksheet ws, int row, int col, out decimal value)
    {
        value = 0;
        var cell = ws.Cell(row, col);
        if (cell.IsEmpty()) return false;

        if (cell.DataType == XLDataType.Number)
        {
            value = (decimal)cell.GetDouble();
            return true;
        }

        var s = cell.GetString().Trim();
        return decimal.TryParse(s, System.Globalization.NumberStyles.Any,
            System.Globalization.CultureInfo.InvariantCulture, out value)
            || decimal.TryParse(s, out value);
    }

    private static bool TryGetInt(IXLWorksheet ws, int row, int col, out int value)
    {
        value = 0;
        if (!TryGetDecimal(ws, row, col, out var d)) return false;
        if (d != Math.Floor(d)) return false;
        value = (int)d;
        return true;
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
            plantCode = s;
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
            plantCode = asString;
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

    private static bool TryParsePlantCodeAsInt(string plantCode, out int value) =>
        int.TryParse(plantCode, out value);
}