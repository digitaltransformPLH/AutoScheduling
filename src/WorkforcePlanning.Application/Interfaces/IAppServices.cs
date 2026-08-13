using WorkforcePlanning.Application.DTOs;

namespace WorkforcePlanning.Application.Interfaces;

public interface ICurrentUserService
{
    int? UserId { get; }
    string Email { get; }
    string DisplayName { get; }
    Task<MeResponse?> GetMeAsync(CancellationToken cancellationToken = default);
    Task<bool> HasPermissionAsync(string permissionCode, CancellationToken cancellationToken = default);
    Task<bool> CanAccessStoreAsync(string storeCode, CancellationToken cancellationToken = default);
    Task EnsurePermissionAsync(string permissionCode, CancellationToken cancellationToken = default);
}

public interface IPublishService
{
    Task<PublishScheduleResponse> PublishAsync(PublishScheduleRequest request, CancellationToken cancellationToken = default);
    Task<DailyMetricsWeekResponse> GetLatestWeekAsync(string storeCode, DateOnly weekStart, CancellationToken cancellationToken = default);
}

public interface IAuthService
{
    Task<MeResponse?> LoginAsync(LoginRequest request, CancellationToken cancellationToken = default);
    Task LogoutAsync();
}

public interface IUserAdminService
{
    Task<List<UserListItemDto>> ListAsync(CancellationToken cancellationToken = default);
    Task<UserDetailDto?> GetAsync(int id, CancellationToken cancellationToken = default);
    Task<UserDetailDto> CreateAsync(UpsertUserRequest request, CancellationToken cancellationToken = default);
    Task<UserDetailDto?> UpdateAsync(int id, UpsertUserRequest request, CancellationToken cancellationToken = default);
    Task<bool> DeactivateAsync(int id, CancellationToken cancellationToken = default);
}

public interface IRoleAdminService
{
    Task<List<RoleDto>> ListAsync(CancellationToken cancellationToken = default);
    Task<RoleDto?> GetAsync(int id, CancellationToken cancellationToken = default);
    Task<RoleDto> CreateAsync(UpsertRoleRequest request, CancellationToken cancellationToken = default);
    Task<RoleDto?> UpdateAsync(int id, UpsertRoleRequest request, CancellationToken cancellationToken = default);
    Task<RoleDto?> SetPermissionsAsync(int id, SetRolePermissionsRequest request, CancellationToken cancellationToken = default);
    Task<RoleDto?> CloneAsync(int id, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default);
    Task<List<PermissionDto>> ListPermissionsAsync(CancellationToken cancellationToken = default);
}

public interface IStoreQueryService
{
    Task<List<StoreDto>> ListActiveAsync(CancellationToken cancellationToken = default);
    Task<List<StoreDetailDto>> ListAllAsync(CancellationToken cancellationToken = default);
    Task<PagedResult<StoreDetailDto>> ListPagedAsync(int page, int pageSize, string? search, CancellationToken cancellationToken = default);
    Task<StoreDetailDto?> GetAsync(int id, CancellationToken cancellationToken = default);
    Task<StoreDetailDto?> GetByCodeAsync(string code, CancellationToken cancellationToken = default);
    Task<StoreOrgResponse?> GetOrgByCodeAsync(string code, CancellationToken cancellationToken = default);
    Task<StoreDetailDto> CreateAsync(UpsertStoreRequest request, CancellationToken cancellationToken = default);
    Task<StoreDetailDto?> UpdateAsync(int id, UpsertStoreRequest request, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default);
}

public interface IPersonQueryService
{
    Task<List<PersonDto>> ListAsync(string? role, CancellationToken cancellationToken = default);
}

public interface IAmOmAssignmentService
{
    Task<List<AmOmAssignmentDto>> ListCurrentAsync(CancellationToken cancellationToken = default);
    Task<OperationManagerLookupResponse?> GetOmByAmIdAsync(int areaManagerId, CancellationToken cancellationToken = default);
    Task<AmOmAssignmentDto?> UpdateCurrentAsync(int areaManagerId, UpsertAmOmAssignmentRequest request, CancellationToken cancellationToken = default);
    Task<AmOmAssignmentDto?> CreateAsync(CreateAmOmAssignmentRequest request, CancellationToken cancellationToken = default);
}

public interface IZonePlanningService
{
    Task<ZonePlanningResponseDto> GetZonePlanningAsync(
        int year,
        int month,
        DateOnly weekStartMonday,
        CancellationToken cancellationToken = default);
}
