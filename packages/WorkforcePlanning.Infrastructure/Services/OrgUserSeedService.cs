using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using WorkforcePlanning.Application.Options;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public static class OrgUserSeedService
{
    private static readonly string[] SkipEmailPrefixes = ["pl.gskv@", "pl.qlch@"];
    private static readonly Dictionary<string, string> RomNameAliases = new(StringComparer.OrdinalIgnoreCase)
    {
        ["Anna Nguyen"] = "Nguyễn Thị Yến Tuyết (Anna Nguyễn)",
        ["Nguyễn Thị Yến Tuyết (Anna Nguyễn)"] = "Anna Nguyen",
        ["Nguyễn Thị Trúc Linh"] = "Nguyễn Thị Trúc Linh",
        ["Trần Ngọc Thanh Nhân"] = "Trần Ngọc Thanh Nhân"
    };

    public static async Task EnsureSeedAsync(
        WorkforcePlanningDbContext db,
        IOptions<AuthOptions> authOptions,
        ILogger? logger = null,
        CancellationToken cancellationToken = default)
    {
        if (!await db.Persons.AnyAsync(cancellationToken))
            return;

        var managerRole = await db.Roles.FirstOrDefaultAsync(r => r.Name == "Manager", cancellationToken);
        if (managerRole is null)
        {
            logger?.LogWarning("Manager role not found; skipping org user seed.");
            return;
        }

        var password = string.IsNullOrWhiteSpace(authOptions.Value.OrgUserDefaultPassword)
            ? "PLH@2026"
            : authOptions.Value.OrgUserDefaultPassword.Trim();
        var hasher = new PasswordHasher<User>();

        var persons = await db.Persons.AsNoTracking()
            .Where(p => p.IsActive && (p.Role == PersonRoles.Am || p.Role == PersonRoles.Rom))
            .Where(p => p.Email != null && p.Email != "")
            .OrderBy(p => p.Role).ThenBy(p => p.FullName)
            .ToListAsync(cancellationToken);

        var existingEmails = await db.Users
            .Select(u => u.Email)
            .ToListAsync(cancellationToken);
        var emailSet = existingEmails.ToHashSet(StringComparer.OrdinalIgnoreCase);

        var amStoreLookup = (await db.Stores.AsNoTracking()
            .Where(s => s.IsActive && s.AreaManagerId != null)
            .Select(s => new { AmId = s.AreaManagerId!.Value, s.Id })
            .ToListAsync(cancellationToken))
            .GroupBy(s => s.AmId)
            .ToDictionary(g => g.Key, g => g.Select(x => x.Id).ToList());

        var assignments = await db.AmOmAssignments.AsNoTracking()
            .Include(a => a.OperationManager)
            .Where(a => a.EffectiveTo == null)
            .ToListAsync(cancellationToken);

        var created = 0;
        var skipped = 0;

        foreach (var person in persons)
        {
            var email = person.Email!.Trim().ToLowerInvariant();
            if (ShouldSkipPerson(person, email))
            {
                skipped++;
                continue;
            }

            if (emailSet.Contains(email))
            {
                skipped++;
                continue;
            }

            var storeIds = ResolveStoreIds(person, assignments, amStoreLookup);

            var user = new User
            {
                Email = email,
                DisplayName = person.FullName,
                RoleId = managerRole.Id,
                AllStores = false,
                IsActive = true
            };
            user.PasswordHash = hasher.HashPassword(user, password);
            db.Users.Add(user);
            await db.SaveChangesAsync(cancellationToken);

            foreach (var storeId in storeIds)
                db.UserStores.Add(new UserStore { UserId = user.Id, StoreId = storeId });

            await db.SaveChangesAsync(cancellationToken);
            emailSet.Add(email);
            created++;
            logger?.LogInformation(
                "Created org user {Email} ({Role}, {StoreCount} stores).",
                email,
                person.Role,
                storeIds.Count);
        }

        if (created > 0 || skipped > 0)
            logger?.LogInformation("Org user seed: {Created} created, {Skipped} skipped.", created, skipped);
    }

    private static bool ShouldSkipPerson(Person person, string email)
    {
        if (person.FullName.Contains("Group mail", StringComparison.OrdinalIgnoreCase))
            return true;

        return SkipEmailPrefixes.Any(prefix => email.StartsWith(prefix, StringComparison.OrdinalIgnoreCase));
    }

    private static List<int> ResolveStoreIds(
        Person person,
        List<AmOmAssignment> assignments,
        Dictionary<int, List<int>> amStoreLookup)
    {
        if (person.Role == PersonRoles.Am)
            return amStoreLookup.GetValueOrDefault(person.Id) ?? [];

        if (person.Role != PersonRoles.Rom)
            return [];

        var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { person.FullName };
        if (RomNameAliases.TryGetValue(person.FullName, out var alias))
            names.Add(alias);

        var amIds = assignments
            .Where(a => a.OperationManagerId == person.Id || names.Contains(a.OperationManager.FullName))
            .Select(a => a.AreaManagerId)
            .Distinct()
            .ToList();

        var storeIds = new HashSet<int>();
        foreach (var amId in amIds)
        {
            if (amStoreLookup.TryGetValue(amId, out var ids))
            {
                foreach (var id in ids)
                    storeIds.Add(id);
            }
        }

        return storeIds.OrderBy(x => x).ToList();
    }
}
