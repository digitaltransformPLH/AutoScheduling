using System.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public static class StoreOrgSeedService
{
    public static async Task EnsureSeedAsync(
        WorkforcePlanningDbContext db,
        ILogger? logger = null,
        CancellationToken cancellationToken = default)
    {
        if (await db.Persons.AnyAsync(cancellationToken))
            return;

        var sqlPath = FindSeedSqlPath();
        if (sqlPath is null)
        {
            logger?.LogWarning("Store org seed SQL not found; skipping import.");
            return;
        }

        logger?.LogInformation("Importing store org seed from {Path}", sqlPath);

        var sql = await File.ReadAllTextAsync(sqlPath, cancellationToken);
        var connection = db.Database.GetDbConnection();
        if (connection.State != ConnectionState.Open)
            await connection.OpenAsync(cancellationToken);

        await using var command = connection.CreateCommand();
        command.CommandText = sql;
        command.CommandTimeout = 180;
        await command.ExecuteNonQueryAsync(cancellationToken);

        var personCount = await db.Persons.CountAsync(cancellationToken);
        var mappingCount = await db.AmOmAssignments.CountAsync(a => a.EffectiveTo == null, cancellationToken);
        logger?.LogInformation(
            "Store org seed completed: {PersonCount} persons, {MappingCount} AM→OM mappings.",
            personCount,
            mappingCount);
    }

    internal static string? FindSeedSqlPath()
    {
        var candidates = new[]
        {
            Path.Combine(AppContext.BaseDirectory, "Data", "006_store_org_seed.sql"),
            Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "database", "006_store_org_seed.sql")),
            Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "database", "006_store_org_seed.sql"))
        };

        return candidates.FirstOrDefault(File.Exists);
    }
}
