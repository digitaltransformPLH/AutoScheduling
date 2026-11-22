using FluentValidation;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class EmployeeAdminService : IEmployeeAdminService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertEmployeeRequest> _validator;
    private readonly EmployeeExcelService _excel;

    public EmployeeAdminService(
        WorkforcePlanningDbContext db,
        IValidator<UpsertEmployeeRequest> validator)
    {
        _db = db;
        _validator = validator;
        _excel = new EmployeeExcelService(db, validator);
    }

    public EmployeeLookupsDto GetLookups() =>
        new()
        {
            Positions = EmployeeCatalog.Positions,
            EmploymentTypes = EmployeeCatalog.EmploymentTypes,
            LaborGroups = EmployeeCatalog.LaborGroups,
            Statuses = EmployeeCatalog.Statuses
        };

    public Task<byte[]> ExportExcelAsync(
        string? plantCode,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default) =>
        _excel.ExportAsync(plantCode, accessiblePlantCodes, cancellationToken);

    public Task<EmployeeImportResultDto> ImportExcelAsync(
        Stream content,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default) =>
        _excel.ImportAsync(content, accessiblePlantCodes, cancellationToken);

    public async Task<PagedResult<EmployeeListItemDto>> ListPagedAsync(
        int page,
        int pageSize,
        string? search,
        string? plantCode,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default)
    {
        page = Math.Max(1, page);
        pageSize = Math.Clamp(pageSize, 5, 100);

        var q = _db.Employees.AsNoTracking().Include(e => e.Plant).AsQueryable();

        if (accessiblePlantCodes is not null)
        {
            if (accessiblePlantCodes.Count == 0)
            {
                return new PagedResult<EmployeeListItemDto>
                {
                    Items = [],
                    Total = 0,
                    Page = page,
                    PageSize = pageSize
                };
            }

            q = q.Where(e => accessiblePlantCodes.Contains(e.PlantCode));
        }

        if (!string.IsNullOrWhiteSpace(plantCode))
        {
            var code = plantCode.Trim();
            q = q.Where(e => e.PlantCode == code);
        }

        if (!string.IsNullOrWhiteSpace(search))
        {
            var term = search.Trim();
            q = q.Where(e =>
                e.FullName.Contains(term)
                || e.PlantCode.Contains(term)
                || e.EmployeeNumber.ToString().Contains(term)
                || (e.Plant != null && e.Plant.Name.Contains(term)));
        }

        var total = await q.CountAsync(cancellationToken);
        var rows = await q
            .OrderBy(e => e.PlantCode)
            .ThenBy(e => e.FullName)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync(cancellationToken);

        return new PagedResult<EmployeeListItemDto>
        {
            Items = rows.Select(MapToListItem).ToList(),
            Total = total,
            Page = page,
            PageSize = pageSize
        };
    }

    public async Task<EmployeeDetailDto?> GetAsync(int id, CancellationToken cancellationToken = default)
    {
        var entity = await _db.Employees.AsNoTracking()
            .Include(e => e.Plant)
            .FirstOrDefaultAsync(e => e.Id == id, cancellationToken);
        return entity is null ? null : MapToDetail(entity);
    }

    public async Task<EmployeeDetailDto> CreateAsync(UpsertEmployeeRequest request, CancellationToken cancellationToken = default)
    {
        await _validator.ValidateAndThrowAsync(request, cancellationToken);
        await EnsurePlantExistsAsync(request.PlantCode, cancellationToken);
        await EnsureEmployeeNumberUniqueAsync(request.EmployeeNumber, excludeId: null, cancellationToken);

        var now = DateTimeOffset.UtcNow;
        var entity = new Employee
        {
            FullName = request.FullName.Trim(),
            EmployeeNumber = request.EmployeeNumber,
            PlantCode = request.PlantCode.Trim(),
            Position = request.Position.Trim(),
            EmploymentType = request.EmploymentType.Trim(),
            LaborGroup = request.LaborGroup.Trim(),
            Status = request.Status.Trim(),
            CreatedAt = now,
            UpdatedAt = now
        };

        _db.Employees.Add(entity);
        await _db.SaveChangesAsync(cancellationToken);

        await _db.Entry(entity).Reference(e => e.Plant).LoadAsync(cancellationToken);
        return MapToDetail(entity);
    }

    public async Task<EmployeeDetailDto?> UpdateAsync(int id, UpsertEmployeeRequest request, CancellationToken cancellationToken = default)
    {
        await _validator.ValidateAndThrowAsync(request, cancellationToken);

        var entity = await _db.Employees.FirstOrDefaultAsync(e => e.Id == id, cancellationToken);
        if (entity is null) return null;

        await EnsurePlantExistsAsync(request.PlantCode, cancellationToken);
        await EnsureEmployeeNumberUniqueAsync(request.EmployeeNumber, excludeId: id, cancellationToken);

        entity.FullName = request.FullName.Trim();
        entity.EmployeeNumber = request.EmployeeNumber;
        entity.PlantCode = request.PlantCode.Trim();
        entity.Position = request.Position.Trim();
        entity.EmploymentType = request.EmploymentType.Trim();
        entity.LaborGroup = request.LaborGroup.Trim();
        entity.Status = request.Status.Trim();
        entity.UpdatedAt = DateTimeOffset.UtcNow;

        await _db.SaveChangesAsync(cancellationToken);

        await _db.Entry(entity).Reference(e => e.Plant).LoadAsync(cancellationToken);
        return MapToDetail(entity);
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default)
    {
        var entity = await _db.Employees.FirstOrDefaultAsync(e => e.Id == id, cancellationToken);
        if (entity is null) return false;

        _db.Employees.Remove(entity);
        await _db.SaveChangesAsync(cancellationToken);
        return true;
    }

    private static EmployeeListItemDto MapToListItem(Employee e) =>
        new()
        {
            Id = e.Id,
            FullName = e.FullName,
            EmployeeNumber = e.EmployeeNumber,
            PlantCode = e.PlantCode,
            PlantName = e.Plant?.Name,
            Position = e.Position,
            EmploymentType = e.EmploymentType,
            LaborGroup = e.LaborGroup,
            Status = e.Status,
            CreatedAt = e.CreatedAt,
            UpdatedAt = e.UpdatedAt
        };

    private static EmployeeDetailDto MapToDetail(Employee e) =>
        new()
        {
            Id = e.Id,
            FullName = e.FullName,
            EmployeeNumber = e.EmployeeNumber,
            PlantCode = e.PlantCode,
            PlantName = e.Plant?.Name,
            Position = e.Position,
            EmploymentType = e.EmploymentType,
            LaborGroup = e.LaborGroup,
            Status = e.Status,
            CreatedAt = e.CreatedAt,
            UpdatedAt = e.UpdatedAt
        };

    private async Task EnsurePlantExistsAsync(string plantCode, CancellationToken cancellationToken)
    {
        var code = plantCode.Trim();
        if (!await _db.Stores.AnyAsync(s => s.Code == code, cancellationToken))
            throw new ArgumentException($"Plant (mã cửa hàng) '{code}' không tồn tại.");
    }

    private async Task EnsureEmployeeNumberUniqueAsync(long employeeNumber, int? excludeId, CancellationToken cancellationToken)
    {
        var exists = await _db.Employees.AnyAsync(
            e => e.EmployeeNumber == employeeNumber && (excludeId == null || e.Id != excludeId),
            cancellationToken);
        if (exists)
            throw new ArgumentException($"Employee ID {employeeNumber} đã tồn tại.");
    }
}