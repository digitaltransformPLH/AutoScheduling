using FluentValidation;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class StoreOrgServiceHelper
{
    private readonly WorkforcePlanningDbContext _db;

    public StoreOrgServiceHelper(WorkforcePlanningDbContext db) => _db = db;

    public async Task<string?> ResolveOperationManagerNameAsync(int? areaManagerId, CancellationToken cancellationToken)
    {
        if (areaManagerId is null) return null;

        var assignment = await _db.AmOmAssignments
            .AsNoTracking()
            .Include(a => a.OperationManager)
            .Where(a => a.AreaManagerId == areaManagerId && a.EffectiveTo == null)
            .OrderByDescending(a => a.EffectiveFrom)
            .FirstOrDefaultAsync(cancellationToken);

        return assignment?.OperationManager.FullName;
    }

    public async Task<StoreDetailDto> MapStoreDetailAsync(Store store, CancellationToken cancellationToken)
    {
        var omName = await ResolveOperationManagerNameAsync(store.AreaManagerId, cancellationToken);
        return new StoreDetailDto
        {
            Id = store.Id,
            Code = store.Code,
            Name = store.Name,
            City = store.City,
            Concept = store.Concept,
            OpenDate = store.OpenDate?.ToString("yyyy-MM-dd"),
            CloseDate = store.CloseDate?.ToString("yyyy-MM-dd"),
            Email = store.Email,
            AreaManagerId = store.AreaManagerId,
            AreaManagerName = store.AreaManager?.FullName,
            OperationManagerName = omName,
            IsActive = store.IsActive
        };
    }
}

public class StoreQueryService : IStoreQueryService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertStoreRequest> _validator;
    private readonly StoreOrgServiceHelper _helper;

    public StoreQueryService(
        WorkforcePlanningDbContext db,
        IValidator<UpsertStoreRequest> validator,
        StoreOrgServiceHelper helper)
    {
        _db = db;
        _validator = validator;
        _helper = helper;
    }

    public async Task<List<StoreDto>> ListActiveAsync(CancellationToken cancellationToken = default)
    {
        return await _db.Stores.AsNoTracking()
            .Where(s => s.IsActive)
            .OrderBy(s => s.Code)
            .Select(s => new StoreDto { Id = s.Id, Code = s.Code, Name = s.Name, IsActive = s.IsActive })
            .ToListAsync(cancellationToken);
    }

    public async Task<List<StoreDetailDto>> ListAllAsync(CancellationToken cancellationToken = default)
    {
        var stores = await _db.Stores.AsNoTracking()
            .Include(s => s.AreaManager)
            .OrderBy(s => s.Code)
            .ToListAsync(cancellationToken);

        return await MapStoreDetailsBatchAsync(stores, cancellationToken);
    }

    public async Task<PagedResult<StoreDetailDto>> ListPagedAsync(
        int page,
        int pageSize,
        string? search,
        CancellationToken cancellationToken = default)
    {
        page = Math.Max(1, page);
        pageSize = Math.Clamp(pageSize, 5, 100);

        var q = _db.Stores.AsNoTracking().Include(s => s.AreaManager).AsQueryable();
        if (!string.IsNullOrWhiteSpace(search))
        {
            var term = search.Trim();
            q = q.Where(s =>
                s.Code.Contains(term)
                || s.Name.Contains(term)
                || (s.City != null && s.City.Contains(term))
                || (s.AreaManager != null && s.AreaManager.FullName.Contains(term)));
        }

        var total = await q.CountAsync(cancellationToken);
        var stores = await q
            .OrderBy(s => s.Code)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync(cancellationToken);

        var items = await MapStoreDetailsBatchAsync(stores, cancellationToken);
        return new PagedResult<StoreDetailDto>
        {
            Items = items,
            Total = total,
            Page = page,
            PageSize = pageSize
        };
    }

    private async Task<List<StoreDetailDto>> MapStoreDetailsBatchAsync(
        List<Store> stores,
        CancellationToken cancellationToken)
    {
        var amIds = stores
            .Where(s => s.AreaManagerId != null)
            .Select(s => s.AreaManagerId!.Value)
            .Distinct()
            .ToList();

        var omByAm = new Dictionary<int, string>();
        if (amIds.Count > 0)
        {
            var assignments = await _db.AmOmAssignments.AsNoTracking()
                .Include(a => a.OperationManager)
                .Where(a => a.EffectiveTo == null && amIds.Contains(a.AreaManagerId))
                .ToListAsync(cancellationToken);

            omByAm = assignments
                .GroupBy(a => a.AreaManagerId)
                .ToDictionary(
                    g => g.Key,
                    g => g.OrderByDescending(a => a.EffectiveFrom).First().OperationManager.FullName);
        }

        return stores.Select(store => new StoreDetailDto
        {
            Id = store.Id,
            Code = store.Code,
            Name = store.Name,
            City = store.City,
            Concept = store.Concept,
            OpenDate = store.OpenDate?.ToString("yyyy-MM-dd"),
            CloseDate = store.CloseDate?.ToString("yyyy-MM-dd"),
            Email = store.Email,
            AreaManagerId = store.AreaManagerId,
            AreaManagerName = store.AreaManager?.FullName,
            OperationManagerName = store.AreaManagerId is int amId && omByAm.TryGetValue(amId, out var om)
                ? om
                : null,
            IsActive = store.IsActive
        }).ToList();
    }

    public async Task<StoreDetailDto?> GetAsync(int id, CancellationToken cancellationToken = default)
    {
        var store = await _db.Stores.AsNoTracking()
            .Include(s => s.AreaManager)
            .FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
        return store is null ? null : await _helper.MapStoreDetailAsync(store, cancellationToken);
    }

    public async Task<StoreDetailDto?> GetByCodeAsync(string code, CancellationToken cancellationToken = default)
    {
        var store = await _db.Stores.AsNoTracking()
            .Include(s => s.AreaManager)
            .FirstOrDefaultAsync(s => s.Code == code.Trim(), cancellationToken);
        return store is null ? null : await _helper.MapStoreDetailAsync(store, cancellationToken);
    }

    public async Task<StoreOrgResponse?> GetOrgByCodeAsync(string code, CancellationToken cancellationToken = default)
    {
        // Source of truth: dim_store_detail (StoreCode -> AreaManager / OperationManager / StoreName)
        // This avoids failures when store.AreaManagerId / AmOmAssignments mapping is incomplete.
        var trimmed = code.Trim();
        var detail = await _db.DimStoreDetails.AsNoTracking()
            .FirstOrDefaultAsync(d => d.StoreCode == trimmed, cancellationToken);
        if (detail is null) return null;

        return new StoreOrgResponse
        {
            StoreCode = detail.StoreCode,
            StoreName = detail.StoreName,
            AreaManager = detail.AreaManager,
            OperationManager = detail.OperationManager
        };
    }

    public async Task<StoreDetailDto> CreateAsync(UpsertStoreRequest request, CancellationToken cancellationToken = default)
    {
        await ValidateAsync(request, cancellationToken);
        var code = request.Code.Trim();
        if (await _db.Stores.AnyAsync(s => s.Code == code, cancellationToken))
            throw new ArgumentException($"Mã cửa hàng {code} đã tồn tại.");

        await EnsureAreaManagerAsync(request.AreaManagerId, cancellationToken);

        var store = MapNewStore(request);
        _db.Stores.Add(store);
        await _db.SaveChangesAsync(cancellationToken);
        return (await GetAsync(store.Id, cancellationToken))!;
    }

    public async Task<StoreDetailDto?> UpdateAsync(int id, UpsertStoreRequest request, CancellationToken cancellationToken = default)
    {
        await ValidateAsync(request, cancellationToken);
        var store = await _db.Stores.FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
        if (store is null) return null;

        var code = request.Code.Trim();
        if (await _db.Stores.AnyAsync(s => s.Code == code && s.Id != id, cancellationToken))
            throw new ArgumentException($"Mã cửa hàng {code} đã tồn tại.");

        await EnsureAreaManagerAsync(request.AreaManagerId, cancellationToken);

        store.Code = code;
        store.Name = request.Name.Trim();
        store.City = NullIfWhiteSpace(request.City);
        store.Concept = NullIfWhiteSpace(request.Concept);
        store.Email = NullIfWhiteSpace(request.Email);
        store.OpenDate = ParseDate(request.OpenDate);
        store.CloseDate = ParseDate(request.CloseDate);
        store.AreaManagerId = request.AreaManagerId;
        store.IsActive = request.IsActive;
        await _db.SaveChangesAsync(cancellationToken);
        return await GetAsync(store.Id, cancellationToken);
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default)
    {
        var store = await _db.Stores
            .Include(s => s.UserStores)
            .FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
        if (store is null) return false;

        _db.UserStores.RemoveRange(store.UserStores);
        _db.Stores.Remove(store);
        await _db.SaveChangesAsync(cancellationToken);
        return true;
    }

    private async Task ValidateAsync(UpsertStoreRequest request, CancellationToken cancellationToken)
    {
        var result = await _validator.ValidateAsync(request, cancellationToken);
        if (!result.IsValid)
            throw new ArgumentException(string.Join(" | ", result.Errors.Select(e => e.ErrorMessage)));
    }

    private static Store MapNewStore(UpsertStoreRequest request) => new()
    {
        Code = request.Code.Trim(),
        Name = request.Name.Trim(),
        City = NullIfWhiteSpace(request.City),
        Concept = NullIfWhiteSpace(request.Concept),
        Email = NullIfWhiteSpace(request.Email),
        OpenDate = ParseDate(request.OpenDate),
        CloseDate = ParseDate(request.CloseDate),
        AreaManagerId = request.AreaManagerId,
        IsActive = request.IsActive
    };

    private async Task EnsureAreaManagerAsync(int? areaManagerId, CancellationToken cancellationToken)
    {
        if (areaManagerId is null) return;
        var ok = await _db.Persons.AnyAsync(
            p => p.Id == areaManagerId && p.Role == PersonRoles.Am && p.IsActive,
            cancellationToken);
        if (!ok) throw new ArgumentException("Area Manager không hợp lệ.");
    }

    private static string? NullIfWhiteSpace(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value.Trim();

    private static DateOnly? ParseDate(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : DateOnly.Parse(value.Trim());
}

public class PersonQueryService : IPersonQueryService
{
    private readonly WorkforcePlanningDbContext _db;

    public PersonQueryService(WorkforcePlanningDbContext db) => _db = db;

    public async Task<List<PersonDto>> ListAsync(string? role, CancellationToken cancellationToken = default)
    {
        var q = _db.Persons.AsNoTracking().Where(p => p.IsActive);
        if (!string.IsNullOrWhiteSpace(role))
            q = q.Where(p => p.Role == role.Trim().ToUpperInvariant());
        return await q.OrderBy(p => p.FullName)
            .Select(p => new PersonDto
            {
                Id = p.Id,
                FullName = p.FullName,
                Email = p.Email,
                Phone = p.Phone,
                Role = p.Role,
                IsActive = p.IsActive
            })
            .ToListAsync(cancellationToken);
    }
}

public class AmOmAssignmentService : IAmOmAssignmentService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertAmOmAssignmentRequest> _validator;
    private readonly IValidator<CreateAmOmAssignmentRequest> _createValidator;

    public AmOmAssignmentService(
        WorkforcePlanningDbContext db,
        IValidator<UpsertAmOmAssignmentRequest> validator,
        IValidator<CreateAmOmAssignmentRequest> createValidator)
    {
        _db = db;
        _validator = validator;
        _createValidator = createValidator;
    }

    public async Task<List<AmOmAssignmentDto>> ListCurrentAsync(CancellationToken cancellationToken = default)
    {
        return await _db.AmOmAssignments.AsNoTracking()
            .Include(a => a.AreaManager)
            .Include(a => a.OperationManager)
            .Where(a => a.EffectiveTo == null)
            .OrderBy(a => a.AreaManager.FullName)
            .Select(a => new AmOmAssignmentDto
            {
                Id = a.Id,
                AreaManagerId = a.AreaManagerId,
                AreaManagerName = a.AreaManager.FullName,
                OperationManagerId = a.OperationManagerId,
                OperationManagerName = a.OperationManager.FullName,
                EffectiveFrom = a.EffectiveFrom.ToString("yyyy-MM-dd"),
                EffectiveTo = a.EffectiveTo != null ? a.EffectiveTo.Value.ToString("yyyy-MM-dd") : null
            })
            .ToListAsync(cancellationToken);
    }

    public async Task<OperationManagerLookupResponse?> GetOmByAmIdAsync(int areaManagerId, CancellationToken cancellationToken = default)
    {
        var assignment = await _db.AmOmAssignments.AsNoTracking()
            .Include(a => a.OperationManager)
            .Where(a => a.AreaManagerId == areaManagerId && a.EffectiveTo == null)
            .OrderByDescending(a => a.EffectiveFrom)
            .FirstOrDefaultAsync(cancellationToken);

        if (assignment is null) return null;
        return new OperationManagerLookupResponse
        {
            OperationManagerId = assignment.OperationManagerId,
            OperationManagerName = assignment.OperationManager.FullName
        };
    }

    public async Task<AmOmAssignmentDto?> UpdateCurrentAsync(
        int areaManagerId,
        UpsertAmOmAssignmentRequest request,
        CancellationToken cancellationToken = default)
    {
        var result = await _validator.ValidateAsync(request, cancellationToken);
        if (!result.IsValid)
            throw new ArgumentException(string.Join(" | ", result.Errors.Select(e => e.ErrorMessage)));

        var am = await _db.Persons.FirstOrDefaultAsync(
            p => p.Id == areaManagerId && p.Role == PersonRoles.Am && p.IsActive,
            cancellationToken);
        if (am is null) throw new ArgumentException("Area Manager không tồn tại.");

        var om = await _db.Persons.FirstOrDefaultAsync(
            p => p.Id == request.OperationManagerId && p.Role == PersonRoles.Rom && p.IsActive,
            cancellationToken);
        if (om is null) throw new ArgumentException("Operation Manager không hợp lệ.");

        var effectiveFrom = string.IsNullOrWhiteSpace(request.EffectiveFrom)
            ? DateOnly.FromDateTime(DateTime.UtcNow)
            : DateOnly.Parse(request.EffectiveFrom.Trim());

        var current = await _db.AmOmAssignments
            .Where(a => a.AreaManagerId == areaManagerId && a.EffectiveTo == null)
            .ToListAsync(cancellationToken);

        foreach (var item in current)
        {
            if (item.OperationManagerId == request.OperationManagerId) continue;
            item.EffectiveTo = effectiveFrom.AddDays(-1);
        }

        if (!current.Any(c => c.OperationManagerId == request.OperationManagerId && c.EffectiveTo == null))
        {
            _db.AmOmAssignments.Add(new AmOmAssignment
            {
                AreaManagerId = areaManagerId,
                OperationManagerId = request.OperationManagerId,
                EffectiveFrom = effectiveFrom
            });
        }

        await _db.SaveChangesAsync(cancellationToken);

        return (await ListCurrentAsync(cancellationToken))
            .FirstOrDefault(a => a.AreaManagerId == areaManagerId);
    }

    public async Task<AmOmAssignmentDto?> CreateAsync(
        CreateAmOmAssignmentRequest request,
        CancellationToken cancellationToken = default)
    {
        var result = await _createValidator.ValidateAsync(request, cancellationToken);
        if (!result.IsValid)
            throw new ArgumentException(string.Join(" | ", result.Errors.Select(e => e.ErrorMessage)));

        var hasCurrent = await _db.AmOmAssignments.AnyAsync(
            a => a.AreaManagerId == request.AreaManagerId && a.EffectiveTo == null,
            cancellationToken);
        if (hasCurrent)
            throw new ArgumentException("Area Manager này đã có mapping. Hãy dùng Sửa OM.");

        return await UpdateCurrentAsync(
            request.AreaManagerId,
            new UpsertAmOmAssignmentRequest
            {
                OperationManagerId = request.OperationManagerId,
                EffectiveFrom = request.EffectiveFrom
            },
            cancellationToken);
    }
}
