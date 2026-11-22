using FluentValidation;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class PublishService : IPublishService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly ICurrentUserService _currentUser;
    private readonly IStoreQueryService _stores;
    private readonly IValidator<PublishScheduleRequest> _validator;

    public PublishService(
        WorkforcePlanningDbContext db,
        ICurrentUserService currentUser,
        IStoreQueryService stores,
        IValidator<PublishScheduleRequest> validator)
    {
        _db = db;
        _currentUser = currentUser;
        _stores = stores;
        _validator = validator;
    }

    public async Task<PublishScheduleResponse> PublishAsync(
        PublishScheduleRequest request,
        CancellationToken cancellationToken = default)
    {
        var validation = await _validator.ValidateAsync(request, cancellationToken);
        if (!validation.IsValid)
        {
            return new PublishScheduleResponse
            {
                Success = false,
                Message = string.Join(" | ", validation.Errors.Select(e => e.ErrorMessage)),
                PublishId = request.PublishId,
                PublishVersion = request.PublishVersion
            };
        }

        if (!await _currentUser.HasPermissionAsync(PermissionCodes.PublishSchedule, cancellationToken))
        {
            return new PublishScheduleResponse
            {
                Success = false,
                Message = "Forbidden: missing Action.Publish.Schedule.",
                PublishId = request.PublishId,
                PublishVersion = request.PublishVersion
            };
        }

        var storeCode = request.StoreCode.Trim();
        if (!await _currentUser.CanAccessStoreAsync(storeCode, cancellationToken))
        {
            return new PublishScheduleResponse
            {
                Success = false,
                Message = $"Forbidden: no access to store {storeCode}.",
                PublishId = request.PublishId,
                PublishVersion = request.PublishVersion
            };
        }

        var storeExists = await _db.Stores.AnyAsync(
            s => s.Code == storeCode && s.IsActive, cancellationToken);
        if (!storeExists)
        {
            return new PublishScheduleResponse
            {
                Success = false,
                Message = $"Store {storeCode} is not registered.",
                PublishId = request.PublishId,
                PublishVersion = request.PublishVersion
            };
        }

        var weekStart = DateOnly.Parse(request.WeekStart);
        var weekEnd = weekStart.AddDays(6);
        var duplicate = await _db.DailyPlanningMetrics.AnyAsync(
            m => m.StoreCode == storeCode
                 && m.PublishVersion == request.PublishVersion
                 && m.Date >= weekStart
                 && m.Date <= weekEnd,
            cancellationToken);

        if (duplicate)
        {
            return new PublishScheduleResponse
            {
                Success = false,
                Message = $"Publish version {request.PublishVersion} already exists for store {storeCode} in this week.",
                PublishId = request.PublishId,
                PublishVersion = request.PublishVersion
            };
        }

        if (!DateTimeOffset.TryParse(request.PublishedAt, out var publishedAt))
            publishedAt = DateTimeOffset.UtcNow;

        var publishedBy = string.IsNullOrWhiteSpace(_currentUser.Email)
            ? _currentUser.DisplayName
            : _currentUser.Email;

        var org = await _stores.GetOrgByCodeAsync(storeCode, cancellationToken);

        var entities = request.Records.Select(r => new DailyPlanningMetric
        {
            StoreCode = storeCode,
            StoreName = r.StoreName,
            AreaManager = string.IsNullOrWhiteSpace(r.AreaManager) ? org?.AreaManager : r.AreaManager,
            OperationManager = string.IsNullOrWhiteSpace(r.OperationManager) ? org?.OperationManager : r.OperationManager,
            Date = DateOnly.Parse(r.Date),
            Day = r.Day,
            Month = r.Month,
            Year = r.Year,
            ADTC = r.ADTC,
            LaborReg = r.LaborReg,
            LaborTrain = r.LaborTrain,
            LaborNSO = r.LaborNSO,
            TCPH = r.TCPH,
            TcphNSO = r.TcphNSO,
            PublishId = request.PublishId,
            PublishVersion = request.PublishVersion,
            PublishedAt = publishedAt,
            PublishedBy = publishedBy
        }).ToList();

        await using var tx = await _db.Database.BeginTransactionAsync(cancellationToken);
        _db.DailyPlanningMetrics.AddRange(entities);
        await _db.SaveChangesAsync(cancellationToken);
        await tx.CommitAsync(cancellationToken);

        return new PublishScheduleResponse
        {
            Success = true,
            RowsInserted = entities.Count,
            PublishId = request.PublishId,
            PublishVersion = request.PublishVersion,
            Message = $"{entities.Count} daily records inserted."
        };
    }

    public async Task<DailyMetricsWeekResponse> GetLatestWeekAsync(
        string storeCode,
        DateOnly weekStart,
        CancellationToken cancellationToken = default)
    {
        if (!await _currentUser.HasPermissionAsync(PermissionCodes.PublishedView, cancellationToken))
            throw new UnauthorizedAccessException("Missing Action.Published.View.");

        if (!await _currentUser.CanAccessStoreAsync(storeCode, cancellationToken))
            throw new UnauthorizedAccessException($"No access to store {storeCode}.");

        if (weekStart.DayOfWeek != DayOfWeek.Monday)
            throw new ArgumentException("weekStart must be a Monday.", nameof(weekStart));

        var weekEnd = weekStart.AddDays(6);
        var code = storeCode.Trim();

        var rows = await _db.DailyPlanningMetrics
            .AsNoTracking()
            .Where(m => m.StoreCode == code && m.Date >= weekStart && m.Date <= weekEnd)
            .ToListAsync(cancellationToken);

        if (rows.Count == 0)
        {
            return new DailyMetricsWeekResponse
            {
                StoreCode = code,
                WeekStart = weekStart.ToString("yyyy-MM-dd"),
                Records = []
            };
        }

        var maxVersion = rows.Max(r => r.PublishVersion);
        var latest = rows
            .Where(r => r.PublishVersion == maxVersion)
            .OrderBy(r => r.Date)
            .ToList();

        return new DailyMetricsWeekResponse
        {
            StoreCode = code,
            WeekStart = weekStart.ToString("yyyy-MM-dd"),
            PublishVersion = maxVersion,
            PublishId = latest.First().PublishId,
            Records = latest.Select(ToDto).ToList()
        };
    }

    private static DailyRecordDto ToDto(DailyPlanningMetric m) => new()
    {
        StoreCode = m.StoreCode,
        StoreName = m.StoreName,
        AreaManager = m.AreaManager,
        OperationManager = m.OperationManager,
        Date = m.Date.ToString("yyyy-MM-dd"),
        Day = m.Day,
        Month = m.Month,
        Year = m.Year,
        ADTC = m.ADTC,
        LaborReg = m.LaborReg,
        LaborTrain = m.LaborTrain,
        LaborNSO = m.LaborNSO,
        TCPH = m.TCPH,
        TcphNSO = m.TcphNSO,
        PublishId = m.PublishId,
        PublishVersion = m.PublishVersion,
        PublishedAt = m.PublishedAt.ToString("O")
    };
}
