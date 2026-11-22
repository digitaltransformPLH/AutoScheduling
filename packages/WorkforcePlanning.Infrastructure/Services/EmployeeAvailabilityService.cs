using FluentValidation;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.Common;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class EmployeeAvailabilityService : IEmployeeAvailabilityService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertEmployeeAvailabilitySlotRequest> _validator;
    private readonly EmployeeAvailabilityExcelService _excel;

    public EmployeeAvailabilityService(
        WorkforcePlanningDbContext db,
        IValidator<UpsertEmployeeAvailabilitySlotRequest> validator)
    {
        _db = db;
        _validator = validator;
        _excel = new EmployeeAvailabilityExcelService(db);
    }

    public async Task<EmployeeAvailabilityWeekResponse> GetWeekAsync(
        string plantCode,
        DateOnly anchorDate,
        int page,
        int pageSize,
        string? search,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(plantCode))
            throw new ArgumentException("plantCode is required.");

        plantCode = plantCode.Trim();
        var weekStart = WeekCalendar.SnapToMonday(anchorDate);
        var weekEnd = WeekCalendar.WeekEndSunday(weekStart);

        page = Math.Max(1, page);
        pageSize = Math.Clamp(pageSize, 5, 200);

        if (accessiblePlantCodes is not null && accessiblePlantCodes.Count == 0)
        {
            return EmptyWeek(plantCode, weekStart, weekEnd, page, pageSize);
        }

        var q = _db.EmployeeAvailabilitySlots.AsNoTracking()
            .Include(s => s.Employee)
            .Include(s => s.Plant)
            .Where(s => s.PlantCode == plantCode && s.WeekStartMonday == weekStart);

        if (accessiblePlantCodes is not null)
            q = q.Where(s => accessiblePlantCodes.Contains(s.PlantCode));

        if (!string.IsNullOrWhiteSpace(search))
        {
            var term = search.Trim();
            q = q.Where(s =>
                s.EmployeeNumber.ToString().Contains(term)
                || (s.Employee != null && s.Employee.FullName.Contains(term)));
        }

        var total = await q.CountAsync(cancellationToken);
        var rows = await q
            .OrderBy(s => s.WorkDate)
            .ThenBy(s => s.EmployeeNumber)
            .Skip((page - 1) * pageSize)
            .Take(pageSize)
            .ToListAsync(cancellationToken);

        return new EmployeeAvailabilityWeekResponse
        {
            WeekStartMonday = weekStart.ToString("yyyy-MM-dd"),
            WeekEndSunday = weekEnd.ToString("yyyy-MM-dd"),
            PlantCode = plantCode,
            Items = rows.Select(MapToListItem).ToList(),
            Total = total,
            Page = page,
            PageSize = pageSize,
            TotalPages = pageSize > 0 ? (int)Math.Ceiling(total / (double)pageSize) : 0
        };
    }

    public async Task<EmployeeAvailabilitySlotListItemDto> CreateAsync(
        DateOnly anchorDate,
        UpsertEmployeeAvailabilitySlotRequest request,
        CancellationToken cancellationToken = default)
    {
        await _validator.ValidateAndThrowAsync(request, cancellationToken);
        var weekStart = WeekCalendar.SnapToMonday(anchorDate);
        var entity = await BuildEntityAsync(weekStart, request, cancellationToken);

        var exists = await _db.EmployeeAvailabilitySlots.AnyAsync(
            s => s.PlantCode == entity.PlantCode
                && s.EmployeeNumber == entity.EmployeeNumber
                && s.WorkDate == entity.WorkDate,
            cancellationToken);
        if (exists)
            throw new ArgumentException("Đã có lịch bận cho nhân viên trong ngày này.");

        _db.EmployeeAvailabilitySlots.Add(entity);
        await _db.SaveChangesAsync(cancellationToken);

        await _db.Entry(entity).Reference(e => e.Employee).LoadAsync(cancellationToken);
        await _db.Entry(entity).Reference(e => e.Plant).LoadAsync(cancellationToken);
        return MapToListItem(entity);
    }

    public async Task<EmployeeAvailabilitySlotListItemDto?> UpdateAsync(
        int id,
        DateOnly anchorDate,
        UpsertEmployeeAvailabilitySlotRequest request,
        CancellationToken cancellationToken = default)
    {
        await _validator.ValidateAndThrowAsync(request, cancellationToken);
        var weekStart = WeekCalendar.SnapToMonday(anchorDate);

        var entity = await _db.EmployeeAvailabilitySlots
            .Include(s => s.Employee)
            .Include(s => s.Plant)
            .FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
        if (entity is null) return null;

        var updated = await BuildEntityAsync(weekStart, request, cancellationToken);
        entity.PlantCode = updated.PlantCode;
        entity.EmployeeNumber = updated.EmployeeNumber;
        entity.EmployeeId = updated.EmployeeId;
        entity.WeekStartMonday = updated.WeekStartMonday;
        entity.WorkDate = updated.WorkDate;
        entity.BusyFrom = updated.BusyFrom;
        entity.BusyTo = updated.BusyTo;
        entity.IsPaidLeave = updated.IsPaidLeave;
        entity.UpdatedAt = DateTimeOffset.UtcNow;

        await _db.SaveChangesAsync(cancellationToken);
        return MapToListItem(entity);
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default)
    {
        var entity = await _db.EmployeeAvailabilitySlots.FirstOrDefaultAsync(s => s.Id == id, cancellationToken);
        if (entity is null) return false;
        _db.EmployeeAvailabilitySlots.Remove(entity);
        await _db.SaveChangesAsync(cancellationToken);
        return true;
    }

    public Task<byte[]> ExportExcelAsync(
        string plantCode,
        DateOnly anchorDate,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default)
    {
        var weekStart = WeekCalendar.SnapToMonday(anchorDate);
        return _excel.ExportAsync(plantCode, weekStart, accessiblePlantCodes, cancellationToken);
    }

    public Task<EmployeeAvailabilityImportResultDto> ImportExcelAsync(
        Stream content,
        DateOnly anchorDate,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default)
    {
        var weekStart = WeekCalendar.SnapToMonday(anchorDate);
        return _excel.ImportAsync(content, weekStart, accessiblePlantCodes, cancellationToken);
    }

    public async Task<IReadOnlyList<EmployeeAvailabilityEmployeePickDto>> ListEmployeePicksAsync(
        string plantCode,
        DateOnly anchorDate,
        string? search,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(plantCode))
            throw new ArgumentException("plantCode is required.");

        plantCode = plantCode.Trim();
        var weekStart = WeekCalendar.SnapToMonday(anchorDate);
        var weekEnd = WeekCalendar.WeekEndSunday(weekStart);
        var term = search?.Trim();

        var homeQ = _db.Employees.AsNoTracking()
            .Where(e => e.PlantCode == plantCode && e.Status == "Active");

        if (!string.IsNullOrEmpty(term))
        {
            homeQ = homeQ.Where(e =>
                e.FullName.Contains(term)
                || e.EmployeeNumber.ToString().Contains(term));
        }

        var home = await homeQ
            .OrderBy(e => e.FullName)
            .ThenBy(e => e.EmployeeNumber)
            .Select(e => new EmployeeAvailabilityEmployeePickDto
            {
                EmployeeNumber = e.EmployeeNumber,
                FullName = e.FullName,
                Position = e.Position,
                Source = "store",
                HomePlantCode = e.PlantCode,
            })
            .ToListAsync(cancellationToken);

        var borrowedQ = _db.EmployeeSecondments.AsNoTracking()
            .Where(s =>
                s.Status == SecondmentStatuses.Active
                && s.ReceivingStoreCode == plantCode
                && s.StartDate <= weekEnd
                && s.EndDate >= weekStart);

        if (!string.IsNullOrEmpty(term))
        {
            borrowedQ = borrowedQ.Where(s =>
                s.Employee != null
                && s.Employee.Status == "Active"
                && (s.Employee.FullName.Contains(term)
                    || s.Employee.EmployeeNumber.ToString().Contains(term)));
        }
        else
        {
            borrowedQ = borrowedQ.Where(s => s.Employee != null && s.Employee.Status == "Active");
        }

        var borrowedRows = await borrowedQ
            .Include(s => s.Employee)
            .OrderBy(s => s.Employee!.FullName)
            .ThenBy(s => s.Employee!.EmployeeNumber)
            .ToListAsync(cancellationToken);

        var homeIds = home.Select(h => h.EmployeeNumber).ToHashSet();
        var borrowed = new List<EmployeeAvailabilityEmployeePickDto>();
        foreach (var s in borrowedRows)
        {
            if (s.Employee is null || homeIds.Contains(s.Employee.EmployeeNumber))
                continue;
            if (borrowed.Any(b => b.EmployeeNumber == s.Employee.EmployeeNumber))
                continue;

            borrowed.Add(new EmployeeAvailabilityEmployeePickDto
            {
                EmployeeNumber = s.Employee.EmployeeNumber,
                FullName = s.Employee.FullName,
                Position = s.Employee.Position,
                Source = "borrowed",
                HomePlantCode = s.HomePlantCode,
                SecondmentStart = s.StartDate.ToString("yyyy-MM-dd"),
                SecondmentEnd = s.EndDate.ToString("yyyy-MM-dd"),
            });
        }

        return home.Concat(borrowed).OrderBy(p => p.FullName).ThenBy(p => p.EmployeeNumber).ToList();
    }

    private async Task<EmployeeAvailabilitySlot> BuildEntityAsync(
        DateOnly weekStart,
        UpsertEmployeeAvailabilitySlotRequest request,
        CancellationToken cancellationToken)
    {
        if (!DateOnly.TryParse(request.WorkDate.Trim(), out var workDate))
            throw new ArgumentException("WorkDate không hợp lệ.");

        if (!WeekCalendar.IsInWeek(workDate, weekStart))
            throw new ArgumentException("WorkDate phải nằm trong tuần đã chọn.");

        var plantCode = request.PlantCode.Trim();
        var storeExists = await _db.Stores.AsNoTracking().AnyAsync(s => s.Code == plantCode, cancellationToken);
        if (!storeExists)
            throw new ArgumentException($"Plant {plantCode} không tồn tại.");

        var emp = await _db.Employees.AsNoTracking()
            .FirstOrDefaultAsync(e => e.EmployeeNumber == request.EmployeeNumber, cancellationToken);
        if (emp is null)
            throw new ArgumentException($"Employee ID {request.EmployeeNumber} không có trong master.");
        if (!await EmployeeAvailabilityPlantEligibility.IsEmployeeEligibleAsync(
                _db, emp, plantCode, workDate, cancellationToken))
        {
            throw new ArgumentException(
                $"Nhân viên {request.EmployeeNumber} không thuộc Plant {plantCode} và không có điều động còn hạn tại cửa hàng này trong ngày đã chọn.");
        }

        TimeOnly? busyFrom = null;
        TimeOnly? busyTo = null;
        if (request.IsPaidLeave)
        {
            if (!string.IsNullOrWhiteSpace(request.BusyFrom) || !string.IsNullOrWhiteSpace(request.BusyTo))
                throw new ArgumentException("Nghỉ phép (AL) không cần nhập giờ.");
        }
        else
        {
            if (!BusyTimeParser.TryParse(request.BusyFrom, out busyFrom) || busyFrom is null)
                throw new ArgumentException("Bận từ không hợp lệ.");
            if (!BusyTimeParser.TryParse(request.BusyTo, out busyTo) || busyTo is null)
                throw new ArgumentException("Bận đến không hợp lệ.");
        }

        var now = DateTimeOffset.UtcNow;
        return new EmployeeAvailabilitySlot
        {
            PlantCode = plantCode,
            EmployeeNumber = request.EmployeeNumber,
            EmployeeId = emp.Id,
            WeekStartMonday = weekStart,
            WorkDate = workDate,
            BusyFrom = request.IsPaidLeave ? null : busyFrom,
            BusyTo = request.IsPaidLeave ? null : busyTo,
            IsPaidLeave = request.IsPaidLeave,
            CreatedAt = now,
            UpdatedAt = now
        };
    }

    private static EmployeeAvailabilitySlotListItemDto MapToListItem(EmployeeAvailabilitySlot s) =>
        new()
        {
            Id = s.Id,
            PlantCode = s.PlantCode,
            PlantName = s.Plant?.Name,
            EmployeeNumber = s.EmployeeNumber,
            EmployeeId = s.EmployeeId,
            EmployeeName = s.Employee?.FullName ?? "",
            WeekStartMonday = s.WeekStartMonday.ToString("yyyy-MM-dd"),
            WorkDate = s.WorkDate.ToString("yyyy-MM-dd"),
            WeekdayLabel = WeekCalendar.EnglishWeekdayName(s.WorkDate),
            BusyFrom = s.IsPaidLeave ? "AL" : s.BusyFrom?.ToString("HH:mm"),
            BusyTo = s.IsPaidLeave ? "AL" : s.BusyTo?.ToString("HH:mm"),
            IsPaidLeave = s.IsPaidLeave
        };

    private static EmployeeAvailabilityWeekResponse EmptyWeek(
        string plantCode,
        DateOnly weekStart,
        DateOnly weekEnd,
        int page,
        int pageSize) =>
        new()
        {
            WeekStartMonday = weekStart.ToString("yyyy-MM-dd"),
            WeekEndSunday = weekEnd.ToString("yyyy-MM-dd"),
            PlantCode = plantCode,
            Items = [],
            Total = 0,
            Page = page,
            PageSize = pageSize,
            TotalPages = 0
        };
}