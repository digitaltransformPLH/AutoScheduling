using FluentValidation;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class StoreConfigService : IStoreConfigService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertStoreConfigRequest> _upsertValidator;
    private readonly StoreConfigExcelService _excel;

    public StoreConfigService(
        WorkforcePlanningDbContext db,
        IValidator<UpsertStoreConfigRequest> upsertValidator)
    {
        _db = db;
        _upsertValidator = upsertValidator;
        _excel = new StoreConfigExcelService(db, upsertValidator);
    }

    public Task<byte[]> ExportExcelAsync(
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default) =>
        _excel.ExportAsync(accessibleStoreCodes, cancellationToken);

    public Task<StoreConfigImportResultDto> ImportExcelAsync(
        Stream content,
        string updatedBy,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default) =>
        _excel.ImportAsync(content, updatedBy, accessibleStoreCodes, cancellationToken);

    public async Task<PagedResult<StoreConfigListItemDto>> ListPagedAsync(
        int page,
        int pageSize,
        string? search,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default)
    {
        page = Math.Max(1, page);
        pageSize = Math.Clamp(pageSize, 5, 100);

        if (accessibleStoreCodes is not null && accessibleStoreCodes.Count == 0)
        {
            return new PagedResult<StoreConfigListItemDto>
            {
                Items = [],
                Total = 0,
                Page = page,
                PageSize = pageSize
            };
        }

        var q = _db.Stores.AsNoTracking().Where(s => s.IsActive);

        if (accessibleStoreCodes is not null)
            q = q.Where(s => accessibleStoreCodes.Contains(s.Code));

        if (!string.IsNullOrWhiteSpace(search))
        {
            var term = search.Trim();
            q = q.Where(s => s.Code.Contains(term) || s.Name.Contains(term));
        }

        var total = await q.CountAsync(cancellationToken);
        var stores = await q
            .OrderBy(s => s.Code)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync(cancellationToken);

        var storeIds = stores.Select(s => s.Id).ToList();
        var configs = storeIds.Count == 0
            ? new Dictionary<int, OpsStoreConfig>()
            : await _db.OpsStoreConfigs.AsNoTracking()
                .Where(c => storeIds.Contains(c.StoreId))
                .ToDictionaryAsync(c => c.StoreId, cancellationToken);

        return new PagedResult<StoreConfigListItemDto>
        {
            Items = stores.Select(s => MapToListItem(s, configs.GetValueOrDefault(s.Id))).ToList(),
            Total = total,
            Page = page,
            PageSize = pageSize
        };
    }

    public async Task<StoreConfigDetailDto?> GetByStoreIdAsync(
        int storeId,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default)
    {
        var store = await FindAccessibleStoreByIdAsync(storeId, accessibleStoreCodes, cancellationToken);
        if (store is null)
            return null;

        var config = await _db.OpsStoreConfigs.AsNoTracking()
            .FirstOrDefaultAsync(c => c.StoreId == storeId, cancellationToken);

        return MapToDetail(store, config);
    }

    public async Task<StoreConfigDetailDto?> GetByStoreCodeAsync(
        string storeCode,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(storeCode))
            return null;

        var code = storeCode.Trim();
        var store = await FindAccessibleStoreByCodeAsync(code, accessibleStoreCodes, cancellationToken);
        if (store is null)
            return null;

        var config = await _db.OpsStoreConfigs.AsNoTracking()
            .FirstOrDefaultAsync(c => c.StoreId == store.Id, cancellationToken);

        return MapToDetail(store, config);
    }

    public async Task<StoreConfigDetailDto?> UpsertAsync(
        int storeId,
        UpsertStoreConfigRequest request,
        string updatedBy,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default)
    {
        await _upsertValidator.ValidateAndThrowAsync(request, cancellationToken);

        var store = await _db.Stores.FirstOrDefaultAsync(s => s.Id == storeId, cancellationToken);
        if (store is null || !store.IsActive)
            return null;

        if (!CanAccessStore(store.Code, accessibleStoreCodes))
            throw new UnauthorizedAccessException("No access to this store.");

        var now = DateTimeOffset.UtcNow;
        var config = await _db.OpsStoreConfigs.FirstOrDefaultAsync(c => c.StoreId == storeId, cancellationToken);
        if (config is null)
        {
            config = new OpsStoreConfig
            {
                StoreId = storeId,
                CreatedAt = now
            };
            _db.OpsStoreConfigs.Add(config);
        }

        config.TcphTarget = request.TcphTarget;
        config.TcphCeilingMult = request.TcphCeilingMult;
        config.OpenStaff = request.OpenStaff;
        config.CloseStaff = request.CloseStaff;
        config.MinStaffPerSlot = request.MinStaffPerSlot;
        config.UpdatedAt = now;
        config.UpdatedBy = string.IsNullOrWhiteSpace(updatedBy) ? "system" : updatedBy.Trim();

        await _db.SaveChangesAsync(cancellationToken);
        return MapToDetail(store, config);
    }

    private async Task<Store?> FindAccessibleStoreByIdAsync(
        int storeId,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken)
    {
        var store = await _db.Stores.AsNoTracking()
            .FirstOrDefaultAsync(s => s.Id == storeId && s.IsActive, cancellationToken);
        if (store is null)
            return null;
        return CanAccessStore(store.Code, accessibleStoreCodes) ? store : null;
    }

    private async Task<Store?> FindAccessibleStoreByCodeAsync(
        string storeCode,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken)
    {
        var store = await _db.Stores.AsNoTracking()
            .FirstOrDefaultAsync(s => s.Code == storeCode && s.IsActive, cancellationToken);
        if (store is null)
            return null;
        return CanAccessStore(store.Code, accessibleStoreCodes) ? store : null;
    }

    private static bool CanAccessStore(string storeCode, IReadOnlyCollection<string>? accessibleStoreCodes)
    {
        if (accessibleStoreCodes is null)
            return true;
        return accessibleStoreCodes.Contains(storeCode, StringComparer.OrdinalIgnoreCase);
    }

    private static StoreConfigListItemDto MapToListItem(Store store, OpsStoreConfig? config)
    {
        var configured = config is not null;
        return new StoreConfigListItemDto
        {
            StoreId = store.Id,
            StoreCode = store.Code,
            StoreName = store.Name,
            IsConfigured = configured,
            TcphTarget = configured ? config!.TcphTarget : null,
            TcphCeilingMult = configured ? config!.TcphCeilingMult : null,
            OpenStaff = configured ? config!.OpenStaff : null,
            CloseStaff = configured ? config!.CloseStaff : null,
            MinStaffPerSlot = configured ? config!.MinStaffPerSlot : null,
            UpdatedAt = configured ? config!.UpdatedAt.ToString("O") : null,
            UpdatedBy = configured ? config!.UpdatedBy : null
        };
    }

    private static StoreConfigDetailDto MapToDetail(Store store, OpsStoreConfig? config)
    {
        var configured = config is not null;
        return new StoreConfigDetailDto
        {
            StoreId = store.Id,
            StoreCode = store.Code,
            StoreName = store.Name,
            IsConfigured = configured,
            TcphTarget = configured ? config!.TcphTarget : 0,
            TcphCeilingMult = configured ? config!.TcphCeilingMult : OpsStoreConfigDefaultsDto.TcphCeilingMult,
            OpenStaff = configured ? config!.OpenStaff : OpsStoreConfigDefaultsDto.OpenStaff,
            CloseStaff = configured ? config!.CloseStaff : OpsStoreConfigDefaultsDto.CloseStaff,
            MinStaffPerSlot = configured ? config!.MinStaffPerSlot : OpsStoreConfigDefaultsDto.MinStaffPerSlot,
            UpdatedAt = configured ? config!.UpdatedAt.ToString("O") : null,
            UpdatedBy = configured ? config!.UpdatedBy : null
        };
    }
}