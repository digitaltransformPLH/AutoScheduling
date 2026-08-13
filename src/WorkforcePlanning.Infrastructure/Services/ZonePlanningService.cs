using System.Globalization;
using System.Linq;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class ZonePlanningService : IZonePlanningService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly ICurrentUserService _currentUser;

    public ZonePlanningService(WorkforcePlanningDbContext db, ICurrentUserService currentUser)
    {
        _db = db;
        _currentUser = currentUser;
    }

    private sealed class MetricsAgg
    {
        public HashSet<string> StoreCodes { get; } = new();
        public decimal Adtc { get; private set; }
        public decimal LaborReg { get; private set; }
        public decimal LaborTrain { get; private set; }
        public decimal LaborNso { get; private set; }

        public void Add(ZonePlanningDailyRow row)
        {
            if (!string.IsNullOrWhiteSpace(row.StoreCode))
                StoreCodes.Add(row.StoreCode);

            Adtc += row.Adtc;
            LaborReg += row.LaborReg;
            LaborTrain += row.LaborTrain;
            LaborNso += row.LaborNso;
        }

        public ZonePlanningMetricsDto ToDto()
        {
            var laborPlan = LaborReg + LaborTrain;
            var laborPlanNso = laborPlan + LaborNso;

            return new ZonePlanningMetricsDto
            {
                Published = StoreCodes.Count,
                Adtc = Adtc,
                LaborReg = LaborReg,
                LaborTrain = LaborTrain,
                LaborNso = LaborNso,
                Tcph = laborPlan > 0 ? Adtc / laborPlan : null,
                TcphNso = laborPlanNso > 0 ? Adtc / laborPlanNso : null
            };
        }
    }

    private sealed class GroupAgg
    {
        public MetricsAgg Weekly { get; } = new();
        public MetricsAgg Monthly { get; } = new();
        public Dictionary<string, AmAgg> Ams { get; } = new();
    }

    private sealed class AmAgg
    {
        public MetricsAgg Weekly { get; } = new();
        public MetricsAgg Monthly { get; } = new();
    }

    private sealed class ZonePlanningDailyRow
    {
        public required string StoreCode { get; init; }
        public required string OperationManager { get; init; }
        public required string AreaManager { get; init; }
        public required string StoreName { get; init; }

        public required DateOnly WeekStart { get; init; }
        public required DateOnly Date { get; init; }
        public required int Month { get; init; }
        public required int Year { get; init; }

        public required decimal Adtc { get; init; }
        public required decimal LaborReg { get; init; }
        public required decimal LaborTrain { get; init; }
        public required decimal LaborNso { get; init; }
    }

    public async Task<ZonePlanningResponseDto> GetZonePlanningAsync(
        int year,
        int month,
        DateOnly weekStartMonday,
        CancellationToken cancellationToken = default)
    {
        if (weekStartMonday.DayOfWeek != DayOfWeek.Monday)
            throw new ArgumentException("weekStart must be a Monday.", nameof(weekStartMonday));

        if (!await _currentUser.HasPermissionAsync(PermissionCodes.ZonePlanningView, cancellationToken))
            throw new UnauthorizedAccessException("Missing Action.ZonePlanning.View.");

        var me = await _currentUser.GetMeAsync(cancellationToken);
        var allowedStoreCodes = (me?.Stores ?? [])
            .Select(s => s.Code)
            .Where(s => !string.IsNullOrWhiteSpace(s))
            .Distinct()
            .ToList();

        if (allowedStoreCodes.Count == 0)
        {
            return new ZonePlanningResponseDto
            {
                Periods = new ZonePlanningPeriodsDto(),
                View = new ZonePlanningViewDto
                {
                    TotalWeekly = new ZonePlanningMetricsDto(),
                    TotalMonthly = new ZonePlanningMetricsDto(),
                    Groups = []
                },
                Summary = new ZonePlanningSummaryDto
                {
                    Week = ISOWeek.GetWeekOfYear(weekStartMonday.ToDateTime(TimeOnly.MinValue)),
                    Month = month,
                    Year = year,
                    AccessibleStores = 0,
                    WeeklyPublished = 0,
                    MonthlyPublished = 0,
                    RowCount = 1
                }
            };
        }

        var weekStarts = MonthMondays(year, month);
        if (!weekStarts.Contains(weekStartMonday))
            weekStarts.Insert(0, weekStartMonday);

        // dim_store_detail is the “source of truth” for names/OM/AM when placeholders are missing.
        var dimRows = await _db.DimStoreDetails
            .AsNoTracking()
            .Where(d => allowedStoreCodes.Contains(d.StoreCode))
            .ToListAsync(cancellationToken);
        var dimByStore = dimRows.ToDictionary(d => d.StoreCode, StringComparer.Ordinal);

        var weeklyTotal = new MetricsAgg();
        var monthlyTotal = new MetricsAgg();

        var omMap = new Dictionary<string, GroupAgg>(StringComparer.Ordinal);

        // Re-fetch/tag all rows once more for correct weekly/monthly AM aggregation.
        // This keeps the “latest per weekStart” logic identical for both totals and groups.
        var allRecords = new List<ZonePlanningDailyRow>();
        foreach (var ws in weekStarts)
        {
            var we = ws.AddDays(6);

            var latestRows = await (
                from m in _db.DailyPlanningMetrics.AsNoTracking()
                where allowedStoreCodes.Contains(m.StoreCode)
                      && m.Date >= ws
                      && m.Date <= we
                join mv in
                    (from m2 in _db.DailyPlanningMetrics.AsNoTracking()
                     where allowedStoreCodes.Contains(m2.StoreCode)
                           && m2.Date >= ws
                           && m2.Date <= we
                     group m2 by m2.StoreCode into g
                     select new { StoreCode = g.Key, PublishVersion = g.Max(x => x.PublishVersion) })
                    on new { m.StoreCode, m.PublishVersion } equals new { mv.StoreCode, mv.PublishVersion }
                select m
            ).ToListAsync(cancellationToken);

            foreach (var row in latestRows)
            {
                var omExisting = row.OperationManager ?? string.Empty;
                var amExisting = row.AreaManager ?? string.Empty;
                var storeNameExisting = row.StoreName ?? string.Empty;

                var omMissingOrPlaceholder = string.IsNullOrWhiteSpace(omExisting) ||
                                              omExisting.Contains("Chưa mapping", StringComparison.OrdinalIgnoreCase);
                var amMissingOrPlaceholder = string.IsNullOrWhiteSpace(amExisting) ||
                                              amExisting.Contains("Chưa mapping", StringComparison.OrdinalIgnoreCase);
                var storeNameMissing = string.IsNullOrWhiteSpace(storeNameExisting);

                var dim = dimByStore.TryGetValue(row.StoreCode, out var d) ? d : null;

                var omResolved = string.IsNullOrWhiteSpace(omExisting) ? "Chưa mapping OM" : omExisting;
                if (omMissingOrPlaceholder && dim?.OperationManager is { Length: > 0 })
                    omResolved = dim.OperationManager;

                var amResolved = string.IsNullOrWhiteSpace(amExisting) ? "Chưa mapping AM" : amExisting;
                if (amMissingOrPlaceholder && dim?.AreaManager is { Length: > 0 })
                    amResolved = dim.AreaManager;

                var storeNameResolved = storeNameExisting;
                if (storeNameMissing && dim?.StoreName is { Length: > 0 })
                    storeNameResolved = dim.StoreName;

                allRecords.Add(new ZonePlanningDailyRow
                {
                    StoreCode = row.StoreCode,
                    OperationManager = omResolved,
                    AreaManager = amResolved,
                    StoreName = storeNameResolved,
                    WeekStart = ws,
                    Date = row.Date,
                    Month = row.Month,
                    Year = row.Year,
                    Adtc = row.ADTC ?? 0,
                    LaborReg = row.LaborReg ?? 0,
                    LaborTrain = row.LaborTrain ?? 0,
                    LaborNso = row.LaborNSO ?? 0
                });
            }
        }

        // Real group aggregation with separate weekly/monthly metrics for AM.
        omMap = new Dictionary<string, GroupAgg>(StringComparer.Ordinal);
        weeklyTotal = new MetricsAgg();
        monthlyTotal = new MetricsAgg();

        foreach (var rec in allRecords)
        {
            if (rec.Year != year || rec.Month != month)
                continue;

            monthlyTotal.Add(rec);

            if (!omMap.TryGetValue(rec.OperationManager, out var g))
            {
                g = new GroupAgg();
                omMap[rec.OperationManager] = g;
            }

            g.Monthly.Add(rec);

            // AM needs two separate aggregates (weekly and monthly), so store as a custom tuple-like container.
            // To avoid creating more nested classes, we treat MetricsAgg for monthly in Ams, and for weekly in a companion dictionary.
            // We'll instead rebuild both MetricsAggs in-line while constructing DTOs.

            if (rec.WeekStart == weekStartMonday)
            {
                weeklyTotal.Add(rec);
                g.Weekly.Add(rec);
            }

            // We'll use nested dictionaries keyed by areaManager to store monthly/weekly separately.
            if (!g.Ams.TryGetValue(rec.AreaManager, out var amMonthlyAgg))
            {
                amMonthlyAgg = new AmAgg();
                g.Ams[rec.AreaManager] = amMonthlyAgg;
            }
            amMonthlyAgg.Monthly.Add(rec);
        }

        // Build DTOs (AM weekly uses filtered metrics from allRecords).
        var culture = new CultureInfo("vi-VN");
        var isoWeek = ISOWeek.GetWeekOfYear(weekStartMonday.ToDateTime(TimeOnly.MinValue));

        var firstDay = new DateOnly(year, month, 1);
        var lastDay = new DateOnly(year, month, DateTime.DaysInMonth(year, month));
        var weeklyPeriod = $"{firstDay.AddDays(-0).ToString("dd/MM/yyyy", culture)}"; // placeholder to keep compilation; overwritten below.
        weeklyPeriod = $"{weekStartMonday.ToString("dd/MM/yyyy", culture)} – {weekStartMonday.AddDays(6).ToString("dd/MM/yyyy", culture)}";
        var monthlyPeriod = $"{firstDay.ToString("dd/MM/yyyy", culture)} – {lastDay.ToString("dd/MM/yyyy", culture)}";

        var groupsDtos = new List<ZonePlanningGroupDto>();
        foreach (var omName in omMap.Keys.OrderBy(k => k, StringComparer.Create(culture, ignoreCase: false)))
        {
            var g = omMap[omName];

            var amDtos = new List<ZonePlanningAmDto>();
            foreach (var amName in g.Ams.Keys.OrderBy(k => k, StringComparer.Create(culture, ignoreCase: false)))
            {
                // For AM weekly: sum only rows whose WeekStart matches selectedWeekMonday.
                var weeklyAgg = new MetricsAgg();
                foreach (var rec in allRecords)
                {
                    if (rec.Year != year || rec.Month != month) continue;
                    if (rec.OperationManager != omName) continue;
                    if (rec.AreaManager != amName) continue;
                    if (rec.WeekStart != weekStartMonday) continue;
                    weeklyAgg.Add(rec);
                }

                var monthlyAgg = g.Ams[amName].Monthly;
                amDtos.Add(new ZonePlanningAmDto
                {
                    Name = amName,
                    Weekly = weeklyAgg.ToDto(),
                    Monthly = monthlyAgg.ToDto()
                });
            }

            groupsDtos.Add(new ZonePlanningGroupDto
            {
                Name = omName,
                Weekly = g.Weekly.ToDto(),
                Monthly = g.Monthly.ToDto(),
                Ams = amDtos
            });
        }

        var periods = new ZonePlanningPeriodsDto
        {
            Weekly = weeklyPeriod,
            Monthly = monthlyPeriod
        };

        var summary = new ZonePlanningSummaryDto
        {
            Week = isoWeek,
            Month = month,
            Year = year,
            AccessibleStores = allowedStoreCodes.Count,
            WeeklyPublished = weeklyTotal.ToDto().Published,
            MonthlyPublished = monthlyTotal.ToDto().Published,
            RowCount = 1 + groupsDtos.Count + groupsDtos.Sum(g => g.Ams.Count)
        };

        return new ZonePlanningResponseDto
        {
            Periods = periods,
            View = new ZonePlanningViewDto
            {
                TotalWeekly = weeklyTotal.ToDto(),
                TotalMonthly = monthlyTotal.ToDto(),
                Groups = groupsDtos
            },
            Summary = summary
        };
    }

    private static List<DateOnly> MonthMondays(int year, int month)
    {
        var first = new DateOnly(year, month, 1);
        var last = new DateOnly(year, month, DateTime.DaysInMonth(year, month));

        var cursor = MondayOf(first);
        var list = new List<DateOnly>();
        while (cursor <= last)
        {
            list.Add(cursor);
            cursor = cursor.AddDays(7);
        }
        return list;
    }

    private static DateOnly MondayOf(DateOnly d)
    {
        // JavaScript: diff=(getDay()+6)%7 (Sunday=0, Monday=1, ...).
        var dow = (int)d.DayOfWeek;
        var diff = (dow + 6) % 7;
        return d.AddDays(-diff);
    }
}

