using FluentValidation;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;
using WorkforcePlanning.Domain.Entities;
using WorkforcePlanning.Infrastructure.Persistence;

namespace WorkforcePlanning.Infrastructure.Services;

public class UserAdminService : IUserAdminService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertUserRequest> _validator;
    private readonly PasswordHasher<User> _hasher = new();

    public UserAdminService(WorkforcePlanningDbContext db, IValidator<UpsertUserRequest> validator)
    {
        _db = db;
        _validator = validator;
    }

    public async Task<List<UserListItemDto>> ListAsync(CancellationToken cancellationToken = default)
    {
        var users = await _db.Users
            .AsNoTracking()
            .Include(u => u.Role)
            .Include(u => u.UserStores).ThenInclude(us => us.Store)
            .OrderBy(u => u.DisplayName)
            .ToListAsync(cancellationToken);

        return users.Select(MapList).ToList();
    }

    public async Task<UserDetailDto?> GetAsync(int id, CancellationToken cancellationToken = default)
    {
        var user = await _db.Users
            .AsNoTracking()
            .Include(u => u.Role)
            .Include(u => u.UserStores).ThenInclude(us => us.Store)
            .FirstOrDefaultAsync(u => u.Id == id, cancellationToken);
        return user is null ? null : MapDetail(user);
    }

    public async Task<UserDetailDto> CreateAsync(UpsertUserRequest request, CancellationToken cancellationToken = default)
    {
        await ValidateAsync(request, requirePassword: true, cancellationToken);
        var email = request.Email.Trim().ToLowerInvariant();
        if (await _db.Users.AnyAsync(u => u.Email == email, cancellationToken))
            throw new ArgumentException("Email đã tồn tại.");

        await EnsureRoleExists(request.RoleId, cancellationToken);
        var storeIds = await ResolveStoreIds(request, cancellationToken);

        var user = new User
        {
            Email = email,
            DisplayName = request.DisplayName.Trim(),
            RoleId = request.RoleId,
            AllStores = request.AllStores,
            IsActive = request.IsActive
        };
        user.PasswordHash = _hasher.HashPassword(user, request.Password!);

        _db.Users.Add(user);
        await _db.SaveChangesAsync(cancellationToken);

        if (!user.AllStores)
        {
            foreach (var sid in storeIds)
                _db.UserStores.Add(new UserStore { UserId = user.Id, StoreId = sid });
            await _db.SaveChangesAsync(cancellationToken);
        }

        return (await GetAsync(user.Id, cancellationToken))!;
    }

    public async Task<UserDetailDto?> UpdateAsync(int id, UpsertUserRequest request, CancellationToken cancellationToken = default)
    {
        await ValidateAsync(request, requirePassword: false, cancellationToken);
        var user = await _db.Users
            .Include(u => u.UserStores)
            .FirstOrDefaultAsync(u => u.Id == id, cancellationToken);
        if (user is null) return null;

        var email = request.Email.Trim().ToLowerInvariant();
        if (await _db.Users.AnyAsync(u => u.Email == email && u.Id != id, cancellationToken))
            throw new ArgumentException("Email đã tồn tại.");

        await EnsureRoleExists(request.RoleId, cancellationToken);
        var storeIds = await ResolveStoreIds(request, cancellationToken);

        user.Email = email;
        user.DisplayName = request.DisplayName.Trim();
        user.RoleId = request.RoleId;
        user.AllStores = request.AllStores;
        user.IsActive = request.IsActive;
        if (!string.IsNullOrWhiteSpace(request.Password))
            user.PasswordHash = _hasher.HashPassword(user, request.Password);

        _db.UserStores.RemoveRange(user.UserStores);
        if (!user.AllStores)
        {
            foreach (var sid in storeIds)
                _db.UserStores.Add(new UserStore { UserId = user.Id, StoreId = sid });
        }

        await _db.SaveChangesAsync(cancellationToken);
        return await GetAsync(user.Id, cancellationToken);
    }

    public async Task<bool> DeactivateAsync(int id, CancellationToken cancellationToken = default)
    {
        var user = await _db.Users.FirstOrDefaultAsync(u => u.Id == id, cancellationToken);
        if (user is null) return false;
        user.IsActive = false;
        await _db.SaveChangesAsync(cancellationToken);
        return true;
    }

    private async Task ValidateAsync(UpsertUserRequest request, bool requirePassword, CancellationToken ct)
    {
        var result = await _validator.ValidateAsync(request, ct);
        if (!result.IsValid)
            throw new ArgumentException(string.Join(" | ", result.Errors.Select(e => e.ErrorMessage)));
        if (requirePassword && string.IsNullOrWhiteSpace(request.Password))
            throw new ArgumentException("Password là bắt buộc khi tạo user.");
    }

    private async Task EnsureRoleExists(int roleId, CancellationToken ct)
    {
        if (!await _db.Roles.AnyAsync(r => r.Id == roleId, ct))
            throw new ArgumentException("Role không tồn tại.");
    }

    private async Task<List<int>> ResolveStoreIds(UpsertUserRequest request, CancellationToken ct)
    {
        if (request.AllStores) return [];
        var ids = (request.StoreIds ?? []).Distinct().ToList();
        var valid = await _db.Stores.Where(s => ids.Contains(s.Id) && s.IsActive).Select(s => s.Id).ToListAsync(ct);
        if (valid.Count != ids.Count)
            throw new ArgumentException("Một hoặc nhiều StoreId không hợp lệ.");
        return valid;
    }

    private static UserListItemDto MapList(User u) => new()
    {
        Id = u.Id,
        Email = u.Email,
        DisplayName = u.DisplayName,
        RoleId = u.RoleId,
        RoleName = u.Role?.Name ?? string.Empty,
        AllStores = u.AllStores,
        IsActive = u.IsActive,
        Stores = u.AllStores
            ? []
            : u.UserStores.Where(us => us.Store.IsActive)
                .Select(us => new StoreAccessDto { Id = us.Store.Id, Code = us.Store.Code, Name = us.Store.Name })
                .OrderBy(s => s.Code).ToList()
    };

    private static UserDetailDto MapDetail(User u)
    {
        var list = MapList(u);
        return new UserDetailDto
        {
            Id = list.Id,
            Email = list.Email,
            DisplayName = list.DisplayName,
            RoleId = list.RoleId,
            RoleName = list.RoleName,
            AllStores = list.AllStores,
            IsActive = list.IsActive,
            Stores = list.Stores,
            StoreIds = list.Stores.Select(s => s.Id).ToList()
        };
    }
}

public class RoleAdminService : IRoleAdminService
{
    private readonly WorkforcePlanningDbContext _db;
    private readonly IValidator<UpsertRoleRequest> _upsertValidator;
    private readonly IValidator<SetRolePermissionsRequest> _permValidator;

    public RoleAdminService(
        WorkforcePlanningDbContext db,
        IValidator<UpsertRoleRequest> upsertValidator,
        IValidator<SetRolePermissionsRequest> permValidator)
    {
        _db = db;
        _upsertValidator = upsertValidator;
        _permValidator = permValidator;
    }

    public async Task<List<RoleDto>> ListAsync(CancellationToken cancellationToken = default)
    {
        var roles = await Query().OrderBy(r => r.Id).ToListAsync(cancellationToken);
        return roles.Select(Map).ToList();
    }

    public async Task<RoleDto?> GetAsync(int id, CancellationToken cancellationToken = default)
    {
        var role = await Query().FirstOrDefaultAsync(r => r.Id == id, cancellationToken);
        return role is null ? null : Map(role);
    }

    public async Task<RoleDto> CreateAsync(UpsertRoleRequest request, CancellationToken cancellationToken = default)
    {
        await ValidateUpsert(request, cancellationToken);
        if (await _db.Roles.AnyAsync(r => r.Name == request.Name.Trim(), cancellationToken))
            throw new ArgumentException("Tên role đã tồn tại.");

        var role = new Role
        {
            Name = request.Name.Trim(),
            Description = request.Description?.Trim(),
            IsSystem = false
        };
        _db.Roles.Add(role);
        await _db.SaveChangesAsync(cancellationToken);
        await ReplacePermissions(role.Id, request.PermissionIds, allowEmpty: true, cancellationToken);
        return (await GetAsync(role.Id, cancellationToken))!;
    }

    public async Task<RoleDto?> UpdateAsync(int id, UpsertRoleRequest request, CancellationToken cancellationToken = default)
    {
        await ValidateUpsert(request, cancellationToken);
        var role = await _db.Roles.FirstOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (role is null) return null;

        if (await _db.Roles.AnyAsync(r => r.Name == request.Name.Trim() && r.Id != id, cancellationToken))
            throw new ArgumentException("Tên role đã tồn tại.");

        role.Name = request.Name.Trim();
        role.Description = request.Description?.Trim();
        await _db.SaveChangesAsync(cancellationToken);

        if (!role.IsSystem || !string.Equals(role.Name, "Administrator", StringComparison.OrdinalIgnoreCase))
            await ReplacePermissions(role.Id, request.PermissionIds, allowEmpty: true, cancellationToken);
        else
            await ReplacePermissions(role.Id, await _db.Permissions.Select(p => p.Id).ToListAsync(cancellationToken), allowEmpty: false, cancellationToken);

        return await GetAsync(role.Id, cancellationToken);
    }

    public async Task<RoleDto?> SetPermissionsAsync(int id, SetRolePermissionsRequest request, CancellationToken cancellationToken = default)
    {
        var result = await _permValidator.ValidateAsync(request, cancellationToken);
        if (!result.IsValid)
            throw new ArgumentException(string.Join(" | ", result.Errors.Select(e => e.ErrorMessage)));

        var role = await _db.Roles.FirstOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (role is null) return null;

        if (role.IsSystem && string.Equals(role.Name, "Administrator", StringComparison.OrdinalIgnoreCase))
        {
            var all = await _db.Permissions.Select(p => p.Id).ToListAsync(cancellationToken);
            await ReplacePermissions(id, all, allowEmpty: false, cancellationToken);
        }
        else
        {
            await ReplacePermissions(id, request.PermissionIds, allowEmpty: true, cancellationToken);
        }

        return await GetAsync(id, cancellationToken);
    }

    public async Task<RoleDto?> CloneAsync(int id, CancellationToken cancellationToken = default)
    {
        var source = await Query().FirstOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (source is null) return null;

        var baseName = source.Name + " (copy)";
        var name = baseName;
        var i = 2;
        while (await _db.Roles.AnyAsync(r => r.Name == name, cancellationToken))
        {
            name = $"{baseName} {i++}";
        }

        var role = new Role
        {
            Name = name,
            Description = source.Description,
            IsSystem = false
        };
        _db.Roles.Add(role);
        await _db.SaveChangesAsync(cancellationToken);
        await ReplacePermissions(role.Id, source.RolePermissions.Select(rp => rp.PermissionId).ToList(), allowEmpty: true, cancellationToken);
        return await GetAsync(role.Id, cancellationToken);
    }

    public async Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default)
    {
        var role = await _db.Roles.FirstOrDefaultAsync(r => r.Id == id, cancellationToken);
        if (role is null) return false;
        if (role.IsSystem)
            throw new ArgumentException("Không thể xóa role hệ thống.");
        if (await _db.Users.AnyAsync(u => u.RoleId == id, cancellationToken))
            throw new ArgumentException("Role đang được gán cho user.");

        var links = await _db.RolePermissions.Where(rp => rp.RoleId == id).ToListAsync(cancellationToken);
        _db.RolePermissions.RemoveRange(links);
        _db.Roles.Remove(role);
        await _db.SaveChangesAsync(cancellationToken);
        return true;
    }

    public async Task<List<PermissionDto>> ListPermissionsAsync(CancellationToken cancellationToken = default)
    {
        return await _db.Permissions.AsNoTracking()
            .OrderBy(p => p.Id)
            .Select(p => new PermissionDto { Id = p.Id, Code = p.Code, Name = p.Name })
            .ToListAsync(cancellationToken);
    }

    private IQueryable<Role> Query() =>
        _db.Roles.AsNoTracking()
            .Include(r => r.RolePermissions).ThenInclude(rp => rp.Permission);

    private async Task ValidateUpsert(UpsertRoleRequest request, CancellationToken ct)
    {
        var result = await _upsertValidator.ValidateAsync(request, ct);
        if (!result.IsValid)
            throw new ArgumentException(string.Join(" | ", result.Errors.Select(e => e.ErrorMessage)));
    }

    private async Task ReplacePermissions(int roleId, IEnumerable<int> permissionIds, bool allowEmpty, CancellationToken ct)
    {
        var ids = permissionIds.Distinct().ToList();
        if (!allowEmpty && ids.Count == 0)
            throw new ArgumentException("Administrator phải có đầy đủ permission.");

        var valid = await _db.Permissions.Where(p => ids.Contains(p.Id)).Select(p => p.Id).ToListAsync(ct);
        if (valid.Count != ids.Count)
            throw new ArgumentException("PermissionId không hợp lệ.");

        var existing = await _db.RolePermissions.Where(rp => rp.RoleId == roleId).ToListAsync(ct);
        _db.RolePermissions.RemoveRange(existing);
        foreach (var pid in valid)
            _db.RolePermissions.Add(new RolePermission { RoleId = roleId, PermissionId = pid });
        await _db.SaveChangesAsync(ct);
    }

    private static RoleDto Map(Role r) => new()
    {
        Id = r.Id,
        Name = r.Name,
        Description = r.Description,
        IsSystem = r.IsSystem,
        PermissionIds = r.RolePermissions.Select(rp => rp.PermissionId).OrderBy(x => x).ToList(),
        Permissions = r.RolePermissions.Select(rp => rp.Permission.Code).OrderBy(x => x).ToList()
    };
}
