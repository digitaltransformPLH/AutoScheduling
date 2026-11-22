using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

internal static class EmployeeAvailabilityPlantEligibility
{
    public static async Task<bool> IsEmployeeEligibleAsync(
        WorkforcePlanningDbContext db,
        Employee emp,
        string plantCode,
        DateOnly workDate,
        CancellationToken cancellationToken)
    {
        if (string.Equals(emp.PlantCode, plantCode, StringComparison.OrdinalIgnoreCase))
            return true;

        return await db.EmployeeSecondments.AsNoTracking().AnyAsync(
            s =>
                s.Status == SecondmentStatuses.Active
                && s.EmployeeId == emp.Id
                && s.ReceivingStoreCode == plantCode
                && s.StartDate <= workDate
                && s.EndDate >= workDate,
            cancellationToken);
    }
}