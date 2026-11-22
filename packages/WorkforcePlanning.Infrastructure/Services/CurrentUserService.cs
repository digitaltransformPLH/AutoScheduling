using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Constants;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class CurrentUserService : ICurrentUserService
{
    private readonly IHttpContextAccessor _http;
    private readonly WorkforcePlanningDbContext _db;

    public CurrentUserService(IHttpContextAccessor http, WorkforcePlanningDbContext db)
    {
        _http = http;
        _db = db;
    }

    public int? UserId
    {
        get
        {
            var raw = _http.HttpContext?.User?.FindFirstValue(ClaimTypes.NameIdentifier);
            return int.TryParse(raw, out var id) ? id : null;
        }
    }

    public string Email =>
        _http.HttpContext?.User?.FindFirstValue(ClaimTypes.Email)
        ?? _http.HttpContext?.User?.Identity?.Name
        ?? string.Empty;

    public string DisplayName =>
        _http.HttpContext?.User?.FindFirstValue(ClaimTypes.GivenName)
        ?? Email;

    public async Task<MeResponse?> GetMeAsync(CancellationToken cancellationToken = default)
    {
        var id = UserId;
        if (id is null) return null;

        try
        {
            // Optimize: avoid Include() chains (RolePermissions/Permission/UserStores/Store)
            // to prevent heavy join graphs and make `/api/v1/me` respond quickly.
            var user = await _db.Users
                .AsNoTracking()
                .Where(u => u.Id == id.Value && u.IsActive)
                .Select(u => new
                {
                    u.Id,
                    u.Email,
                    u.DisplayName,
                    u.RoleId,
                    u.AllStores,
                    IsActive = u.IsActive
                })
                .FirstOrDefaultAsync(cancellationToken);

            if (user is null) return null;

            // AM/OM role is stored in `Persons`, not in `Users.RoleId`.
            // Use email linkage (OrgUserSeedService creates Users from Persons by email).
            var person = await _db.Persons
                .AsNoTracking()
                .Where(p => p.Email != null && p.Email == user.Email && p.IsActive)
                .Select(p => new { p.Id, p.Role })
                .FirstOrDefaultAsync(cancellationToken);

            var permissionCodes = await _db.RolePermissions
                .AsNoTracking()
                .Where(rp => rp.RoleId == user.RoleId)
                .Select(rp => rp.Permission.Code)
                .Distinct()
                .OrderBy(c => c)
                .ToListAsync(cancellationToken);

            List<StoreAccessDto> stores;
            if (user.AllStores)
            {
                stores = await _db.Stores.AsNoTracking()
                    .Where(s => s.IsActive)
                    .OrderBy(s => s.Code)
                    .Select(s => new StoreAccessDto { Id = s.Id, Code = s.Code, Name = s.Name })
                    .ToListAsync(cancellationToken);
            }
            else if (person?.Role == PersonRoles.Am)
            {
                // AM can only see stores they manage.
                stores = await _db.Stores.AsNoTracking()
                    .Where(s => s.IsActive && s.AreaManagerId == person.Id)
                    .OrderBy(s => s.Code)
                    .Select(s => new StoreAccessDto { Id = s.Id, Code = s.Code, Name = s.Name })
                    .ToListAsync(cancellationToken);
            }
            else if (person?.Role == PersonRoles.Rom)
            {
                // OM can see stores from AMs mapped to them (current mappings only).
                var amIds = await _db.AmOmAssignments.AsNoTracking()
                    .Where(a => a.EffectiveTo == null && a.OperationManagerId == person.Id)
                    .Select(a => a.AreaManagerId)
                    .Distinct()
                    .ToListAsync(cancellationToken);

                stores = await _db.Stores.AsNoTracking()
                    .Where(s => s.IsActive
                                && s.AreaManagerId != null
                                && amIds.Contains(s.AreaManagerId.Value))
                    .OrderBy(s => s.Code)
                    .Select(s => new StoreAccessDto { Id = s.Id, Code = s.Code, Name = s.Name })
                    .ToListAsync(cancellationToken);
            }
            else
            {
                // Fallback to UserStores (e.g. admin/staff/viewer models).
                stores = await _db.UserStores.AsNoTracking()
                    .Where(us => us.UserId == user.Id && us.Store.IsActive)
                    .Select(us => new StoreAccessDto
                    {
                        Id = us.Store.Id,
                        Code = us.Store.Code,
                        Name = us.Store.Name
                    })
                    .Distinct()
                    .OrderBy(s => s.Code)
                    .ToListAsync(cancellationToken);
            }

            // Role name can be loaded lazily with a lightweight query; avoids including the full permission graph.
            var roleName = await _db.Roles.AsNoTracking()
                .Where(r => r.Id == user.RoleId)
                .Select(r => r.Name)
                .FirstOrDefaultAsync(cancellationToken) ?? string.Empty;

            // System admin should see all menu-level permissions.
            // This avoids being blocked by DB seed/permission sync timing.
            if (string.Equals(roleName, "Administrator", StringComparison.OrdinalIgnoreCase))
                permissionCodes = PermissionCodes.All.ToList();

            return new MeResponse
            {
                Id = user.Id,
                Email = user.Email,
                DisplayName = user.DisplayName,
                Role = roleName,
                RoleId = user.RoleId,
                AllStores = user.AllStores,
                IsActive = user.IsActive,
                Permissions = permissionCodes,
                Stores = stores
            };
        }
        catch
        {
            return null;
        }
    }

    public async Task<bool> HasPermissionAsync(string permissionCode, CancellationToken cancellationToken = default)
    {
        var id = UserId;
        if (id is null) return false;

        var userRole = await _db.Users
            .AsNoTracking()
            .Where(u => u.Id == id.Value && u.IsActive)
            .Select(u => new { RoleName = u.Role.Name })
            .FirstOrDefaultAsync(cancellationToken);

        if (userRole is null) return false;

        // Keep consistent with GetMeAsync: Administrator has all permissions even if
        // RolePermissions rows are missing/outdated in an existing database.
        if (string.Equals(userRole.RoleName, "Administrator", StringComparison.OrdinalIgnoreCase))
            return true;

        return await _db.Users
            .AsNoTracking()
            .Where(u => u.Id == id.Value && u.IsActive)
            .SelectMany(u => u.Role.RolePermissions)
            .AnyAsync(rp => rp.Permission.Code == permissionCode, cancellationToken);
    }

    public async Task EnsurePermissionAsync(string permissionCode, CancellationToken cancellationToken = default)
    {
        if (!await HasPermissionAsync(permissionCode, cancellationToken))
            throw new UnauthorizedAccessException($"Missing permission: {permissionCode}");
    }

    public async Task<bool> CanAccessStoreAsync(string storeCode, CancellationToken cancellationToken = default)
    {
        var id = UserId;
        if (id is null || string.IsNullOrWhiteSpace(storeCode)) return false;

        var code = storeCode.Trim();
        var user = await _db.Users
            .AsNoTracking()
            .Where(u => u.Id == id.Value && u.IsActive)
            .Select(u => new { u.Id, u.Email, u.AllStores, u.RoleId })
            .FirstOrDefaultAsync(cancellationToken);

        if (user is null) return false;
        if (user.AllStores)
            return await _db.Stores.AnyAsync(s => s.Code == code && s.IsActive, cancellationToken);

        // Resolve Person role from email.
        var person = await _db.Persons
            .AsNoTracking()
            .Where(p => p.Email != null && p.Email == user.Email && p.IsActive)
            .Select(p => new { p.Id, p.Role })
            .FirstOrDefaultAsync(cancellationToken);

        if (person?.Role == PersonRoles.Am)
        {
            return await _db.Stores.AnyAsync(s =>
                s.IsActive &&
                s.Code == code &&
                s.AreaManagerId == person.Id, cancellationToken);
        }

        if (person?.Role == PersonRoles.Rom)
        {
            var amIds = await _db.AmOmAssignments.AsNoTracking()
                .Where(a => a.EffectiveTo == null && a.OperationManagerId == person.Id)
                .Select(a => a.AreaManagerId)
                .Distinct()
                .ToListAsync(cancellationToken);

            if (amIds.Count == 0) return false;

            return await _db.Stores.AnyAsync(s =>
                s.IsActive &&
                s.Code == code &&
                s.AreaManagerId != null &&
                amIds.Contains(s.AreaManagerId.Value), cancellationToken);
        }

        // Fallback to explicit UserStores.
        return await _db.UserStores.AnyAsync(us =>
            us.UserId == user.Id &&
            us.Store.IsActive &&
            us.Store.Code == code, cancellationToken);
    }

    internal static MeResponse MapMe(User user)
    {
        var stores = user.AllStores
            ? new List<StoreAccessDto>()
            : user.UserStores
                .Where(us => us.Store.IsActive)
                .Select(us => new StoreAccessDto
                {
                    Id = us.Store.Id,
                    Code = us.Store.Code,
                    Name = us.Store.Name
                })
                .OrderBy(s => s.Code)
                .ToList();

        var roleName = user.Role?.Name ?? string.Empty;
        var permissionCodes = roleName.Equals("Administrator", StringComparison.OrdinalIgnoreCase)
            ? PermissionCodes.All.ToList()
            : (user.Role?.RolePermissions
                    .Select(rp => rp.Permission.Code)
                    .Distinct()
                    .OrderBy(c => c)
                    .ToList() ?? new List<string>());

        return new MeResponse
        {
            Id = user.Id,
            Email = user.Email,
            DisplayName = user.DisplayName,
            Role = roleName,
            RoleId = user.RoleId,
            AllStores = user.AllStores,
            IsActive = user.IsActive,
            Permissions = permissionCodes,
            Stores = stores
        };
    }
}

public class AuthService : IAuthService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IHttpContextAccessor _http;
    private readonly PasswordHasher<User> _hasher = new();

    public AuthService(WorkforcePlanningDbContext db, IHttpContextAccessor http)
    {
        _db = db;
        _http = http;
    }

    public async Task<MeResponse?> LoginAsync(LoginRequest request, CancellationToken cancellationToken = default)
    {
        var email = request.Email.Trim().ToLowerInvariant();
        var user = await _db.Users
            .Include(u => u.Role).ThenInclude(r => r.RolePermissions).ThenInclude(rp => rp.Permission)
            .Include(u => u.UserStores).ThenInclude(us => us.Store)
            .FirstOrDefaultAsync(u => u.Email == email, cancellationToken);

        if (user is null || !user.IsActive)
            return null;

        var result = _hasher.VerifyHashedPassword(user, user.PasswordHash, request.Password);
        if (result == PasswordVerificationResult.Failed)
            return null;

        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, user.Id.ToString()),
            new(ClaimTypes.Email, user.Email),
            new(ClaimTypes.Name, user.Email),
            new(ClaimTypes.GivenName, user.DisplayName),
            new(ClaimTypes.Role, user.Role.Name)
        };
        foreach (var code in user.Role.RolePermissions.Select(rp => rp.Permission.Code).Distinct())
            claims.Add(new Claim("permission", code));

        var identity = new ClaimsIdentity(claims, CookieAuthenticationDefaults.AuthenticationScheme);
        var principal = new ClaimsPrincipal(identity);
        var ctx = _http.HttpContext ?? throw new InvalidOperationException("No HttpContext");
        await ctx.SignInAsync(
            CookieAuthenticationDefaults.AuthenticationScheme,
            principal,
            new AuthenticationProperties
            {
                IsPersistent = true,
                AllowRefresh = true
            });

        var me = CurrentUserService.MapMe(user);
        if (user.AllStores)
        {
            me.Stores = await _db.Stores.AsNoTracking()
                .Where(s => s.IsActive)
                .OrderBy(s => s.Code)
                .Select(s => new StoreAccessDto { Id = s.Id, Code = s.Code, Name = s.Name })
                .ToListAsync(cancellationToken);
        }
        return me;
    }

    public async Task LogoutAsync()
    {
        var ctx = _http.HttpContext;
        if (ctx is null) return;
        await ctx.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme);
    }
}
