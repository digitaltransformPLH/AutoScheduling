using FluentValidation;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class EmployeeSecondmentService : IEmployeeSecondmentService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<CreateEmployeeSecondmentRequest> _createValidator;
    private readonly IValidator<UpdateEmployeeSecondmentRequest> _updateValidator;

    public EmployeeSecondmentService(
        WorkforcePlanningDbContext db,
        IValidator<CreateEmployeeSecondmentRequest> createValidator,
        IValidator<UpdateEmployeeSecondmentRequest> updateValidator)
    {
        _db = db;
        _createValidator = createValidator;
        _updateValidator = updateValidator;
    }

    public async Task<PagedResult<EmployeeSecondmentListItemDto>> ListPagedAsync(
        int page,
        int pageSize,
        string? search,
        string? plantCode,
        string? status,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default)
    {
        page = Math.Max(1, page);
        pageSize = Math.Clamp(pageSize, 5, 100);

        var q = _db.EmployeeSecondments.AsNoTracking()
            .Include(s => s.Employee)
            .ThenInclude(e => e!.Plant)
            .Include(s => s.ReceivingStore)
            .AsQueryable();

        if (accessiblePlantCodes is not null)
        {
            if (accessiblePlantCodes.Count == 0)
            {
                return new PagedResult<EmployeeSecondmentListItemDto>
                {
                    Items = [],
                    Total = 0,
                    Page = page,
                    PageSize = pageSize
                };
            }

            q = q.Where(s => accessiblePlantCodes.Contains(s.HomePlantCode));
        }

        if (!string.IsNullOrWhiteSpace(plantCode))
        {
            var code = plantCode.Trim();
            q = q.Where(s => s.HomePlantCode == code || s.ReceivingStoreCode == code);
        }

        if (!string.IsNullOrWhiteSpace(status))
        {
            var st = status.Trim();
            q = q.Where(s => s.Status == st);
        }

        if (!string.IsNullOrWhiteSpace(search))
        {
            var term = search.Trim();
            q = q.Where(s =>
                s.Employee != null && (
                    s.Employee.FullName.Contains(term)
                    || s.Employee.EmployeeNumber.ToString().Contains(term)
                    || s.HomePlantCode.Contains(term)
                    || s.ReceivingStoreCode.Contains(term)
                    || (s.ReceivingStore != null && s.ReceivingStore.Name.Contains(term))));
        }

        var total = await q.CountAsync(cancellationToken);
        var rows = await q
            .OrderByDescending(s => s.StartDate)
            .ThenByDescending(s => s.Id)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync(cancellationToken);

        return new PagedResult<EmployeeSecondmentListItemDto>
        {
            Items = rows.Select(MapToListItem).ToList(),
            Total = total,
            Page = page,
            PageSize = pageSize
        };
    }

    public Task<EmployeeSecondmentListItemDto?> GetAsync(int id, CancellationToken cancellationToken = default) =>
        LoadListItemAsync(id, cancellationToken);

    public async Task<EmployeeSecondmentListItemDto> CreateAsync(
        int employeeId,
        CreateEmployeeSecondmentRequest request,
        string updatedBy,
        CancellationToken cancellationToken = default)
    {
        await _createValidator.ValidateAndThrowAsync(request, cancellationToken);

        var employee = await _db.Employees.AsNoTracking()
            .FirstOrDefaultAsync(e => e.Id == employeeId, cancellationToken)
            ?? throw new InvalidOperationException("Không tìm thấy nhân viên.");

        var start = DateOnly.Parse(request.StartDate);
        var end = DateOnly.Parse(request.EndDate);
        var storeCode = request.ReceivingStoreCode.Trim();

        await EnsureReceivingStoreAsync(storeCode, cancellationToken);

        if (string.Equals(storeCode, employee.PlantCode, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Store nhận phải khác plant gốc của nhân viên.");

        await EnsureNoOverlappingActiveAsync(employeeId, start, end, excludeId: null, cancellationToken);

        var now = DateTimeOffset.UtcNow;
        var entity = new EmployeeSecondment
        {
            EmployeeId = employeeId,
            HomePlantCode = employee.PlantCode,
            ReceivingStoreCode = storeCode,
            StartDate = start,
            EndDate = end,
            Status = SecondmentStatuses.Active,
            CreatedAt = now,
            UpdatedAt = now,
            UpdatedBy = updatedBy
        };

        _db.EmployeeSecondments.Add(entity);
        await _db.SaveChangesAsync(cancellationToken);

        return await LoadListItemAsync(entity.Id, cancellationToken)
            ?? throw new InvalidOperationException("Không tải được bản ghi sau khi tạo.");
    }

    public async Task<EmployeeSecondmentListItemDto?> UpdateAsync(
        int id,
        UpdateEmployeeSecondmentRequest request,
        string updatedBy,
        CancellationToken cancellationToken = default)
    {
        await _updateValidator.ValidateAndThrowAsync(request, cancellationToken);

        var entity = await _db.EmployeeSecondments
            .Include(s => s.Employee)
            .FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
        if (entity is null) return null;

        if (entity.Status != SecondmentStatuses.Active)
            throw new InvalidOperationException("Chỉ có thể sửa điều động đang Active.");

        var start = DateOnly.Parse(request.StartDate);
        var end = DateOnly.Parse(request.EndDate);
        var storeCode = request.ReceivingStoreCode.Trim();

        await EnsureReceivingStoreAsync(storeCode, cancellationToken);

        if (entity.Employee is not null
            && string.Equals(storeCode, entity.Employee.PlantCode, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Store nhận phải khác plant gốc của nhân viên.");

        await EnsureNoOverlappingActiveAsync(entity.EmployeeId, start, end, excludeId: id, cancellationToken);

        entity.ReceivingStoreCode = storeCode;
        entity.StartDate = start;
        entity.EndDate = end;
        entity.UpdatedAt = DateTimeOffset.UtcNow;
        entity.UpdatedBy = updatedBy;

        await _db.SaveChangesAsync(cancellationToken);
        return await LoadListItemAsync(id, cancellationToken);
    }

    public async Task<EmployeeSecondmentListItemDto?> CancelAsync(
        int id,
        string updatedBy,
        CancellationToken cancellationToken = default)
    {
        var entity = await _db.EmployeeSecondments.FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
        if (entity is null) return null;

        if (entity.Status == SecondmentStatuses.Cancelled)
            return await LoadListItemAsync(id, cancellationToken);

        entity.Status = SecondmentStatuses.Cancelled;
        entity.UpdatedAt = DateTimeOffset.UtcNow;
        entity.UpdatedBy = updatedBy;
        await _db.SaveChangesAsync(cancellationToken);

        return await LoadListItemAsync(id, cancellationToken);
    }

    private async Task EnsureReceivingStoreAsync(string storeCode, CancellationToken cancellationToken)
    {
        var store = await _db.Stores.AsNoTracking()
            .FirstOrDefaultAsync(s => s.Code == storeCode, cancellationToken);
        if (store is null)
            throw new InvalidOperationException("Store nhận không tồn tại.");
        if (!store.IsActive)
            throw new InvalidOperationException("Store nhận không còn hoạt động.");
    }

    private async Task EnsureNoOverlappingActiveAsync(
        int employeeId,
        DateOnly start,
        DateOnly end,
        int? excludeId,
        CancellationToken cancellationToken)
    {
        var q = _db.EmployeeSecondments.AsNoTracking()
            .Where(s =>
                s.EmployeeId == employeeId
                && s.Status == SecondmentStatuses.Active
                && s.StartDate <= end
                && s.EndDate >= start);

        if (excludeId is not null)
            q = q.Where(s => s.Id != excludeId.Value);

        if (await q.AnyAsync(cancellationToken))
            throw new InvalidOperationException("Nhân viên đã có điều động Active trùng khoảng ngày.");
    }

    private async Task<EmployeeSecondmentListItemDto?> LoadListItemAsync(int id, CancellationToken cancellationToken)
    {
        var entity = await _db.EmployeeSecondments.AsNoTracking()
            .Include(s => s.Employee)
            .ThenInclude(e => e!.Plant)
            .Include(s => s.ReceivingStore)
            .FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
        return entity is null ? null : MapToListItem(entity);
    }

    private static EmployeeSecondmentListItemDto MapToListItem(EmployeeSecondment s) =>
        new()
        {
            Id = s.Id,
            EmployeeId = s.EmployeeId,
            EmployeeNumber = s.Employee?.EmployeeNumber ?? 0,
            FullName = s.Employee?.FullName ?? string.Empty,
            HomePlantCode = s.HomePlantCode,
            HomePlantName = s.Employee?.Plant?.Name,
            ReceivingStoreCode = s.ReceivingStoreCode,
            ReceivingStoreName = s.ReceivingStore?.Name,
            StartDate = s.StartDate.ToString("O"),
            EndDate = s.EndDate.ToString("O"),
            Status = s.Status,
            CreatedAt = s.CreatedAt,
            UpdatedAt = s.UpdatedAt,
            UpdatedBy = s.UpdatedBy
        };
}