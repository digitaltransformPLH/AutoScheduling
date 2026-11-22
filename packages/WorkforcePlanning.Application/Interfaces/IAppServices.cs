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

public interface IEmployeeSecondmentService
{
    Task<PagedResult<EmployeeSecondmentListItemDto>> ListPagedAsync(
        int page,
        int pageSize,
        string? search,
        string? plantCode,
        string? status,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default);
    Task<EmployeeSecondmentListItemDto?> GetAsync(int id, CancellationToken cancellationToken = default);
    Task<EmployeeSecondmentListItemDto> CreateAsync(
        int employeeId,
        CreateEmployeeSecondmentRequest request,
        string updatedBy,
        CancellationToken cancellationToken = default);
    Task<EmployeeSecondmentListItemDto?> UpdateAsync(
        int id,
        UpdateEmployeeSecondmentRequest request,
        string updatedBy,
        CancellationToken cancellationToken = default);
    Task<EmployeeSecondmentListItemDto?> CancelAsync(
        int id,
        string updatedBy,
        CancellationToken cancellationToken = default);
}

public interface IEmployeeAdminService
{
    Task<PagedResult<EmployeeListItemDto>> ListPagedAsync(
        int page,
        int pageSize,
        string? search,
        string? plantCode,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default);
    Task<EmployeeDetailDto?> GetAsync(int id, CancellationToken cancellationToken = default);
    Task<EmployeeDetailDto> CreateAsync(UpsertEmployeeRequest request, CancellationToken cancellationToken = default);
    Task<EmployeeDetailDto?> UpdateAsync(int id, UpsertEmployeeRequest request, CancellationToken cancellationToken = default);
    Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default);
    EmployeeLookupsDto GetLookups();
    Task<byte[]> ExportExcelAsync(string? plantCode, IReadOnlyCollection<string>? accessiblePlantCodes, CancellationToken cancellationToken = default);
    Task<EmployeeImportResultDto> ImportExcelAsync(
        Stream content,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default);
}

public interface IZonePlanningService
{
    Task<ZonePlanningResponseDto> GetZonePlanningAsync(
        int year,
        int month,
        DateOnly weekStartMonday,
        CancellationToken cancellationToken = default);
}

public interface IEmployeeAvailabilityService
{
    Task<EmployeeAvailabilityWeekResponse> GetWeekAsync(
        string plantCode,
        DateOnly anchorDate,
        int page,
        int pageSize,
        string? search,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default);

    Task<EmployeeAvailabilitySlotListItemDto> CreateAsync(
        DateOnly anchorDate,
        UpsertEmployeeAvailabilitySlotRequest request,
        CancellationToken cancellationToken = default);

    Task<EmployeeAvailabilitySlotListItemDto?> UpdateAsync(
        int id,
        DateOnly anchorDate,
        UpsertEmployeeAvailabilitySlotRequest request,
        CancellationToken cancellationToken = default);

    Task<bool> DeleteAsync(int id, CancellationToken cancellationToken = default);

    Task<byte[]> ExportExcelAsync(
        string plantCode,
        DateOnly anchorDate,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default);

    Task<EmployeeAvailabilityImportResultDto> ImportExcelAsync(
        Stream content,
        DateOnly anchorDate,
        IReadOnlyCollection<string>? accessiblePlantCodes,
        CancellationToken cancellationToken = default);

    Task<IReadOnlyList<EmployeeAvailabilityEmployeePickDto>> ListEmployeePicksAsync(
        string plantCode,
        DateOnly anchorDate,
        string? search,
        CancellationToken cancellationToken = default);
}

public interface IStoreConfigService
{
    Task<PagedResult<StoreConfigListItemDto>> ListPagedAsync(
        int page,
        int pageSize,
        string? search,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default);

    Task<StoreConfigDetailDto?> GetByStoreIdAsync(
        int storeId,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default);

    Task<StoreConfigDetailDto?> GetByStoreCodeAsync(
        string storeCode,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default);

    Task<StoreConfigDetailDto?> UpsertAsync(
        int storeId,
        UpsertStoreConfigRequest request,
        string updatedBy,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default);

    Task<byte[]> ExportExcelAsync(
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default);

    Task<StoreConfigImportResultDto> ImportExcelAsync(
        Stream content,
        string updatedBy,
        IReadOnlyCollection<string>? accessibleStoreCodes,
        CancellationToken cancellationToken = default);
}

public interface ISchedulingReadService
{
    Task<SchedulingMetaDto> GetMetaAsync(CancellationToken cancellationToken = default);

    Task<IReadOnlyList<SchedulingStoreItemDto>> ListStoresAsync(
        bool readyOnly,
        IReadOnlySet<string> allowedStoreCodes,
        bool allStores,
        CancellationToken cancellationToken = default);

    Task<IReadOnlyList<ForecastWeekDto>> ListForecastWeeksAsync(CancellationToken cancellationToken = default);

    Task<IReadOnlyList<ScheduleWeekDto>> ListSchedulesAsync(
        string? storeCode,
        IReadOnlySet<string> allowedStoreCodes,
        bool allStores,
        CancellationToken cancellationToken = default);

    Task<ScheduleWeekDto?> GetScheduleWeekAsync(
        string storeCode,
        DateOnly weekStart,
        CancellationToken cancellationToken = default);

    Task<OverviewDto> GetOverviewAsync(
        string storeCode,
        DateOnly weekStart,
        CancellationToken cancellationToken = default);

    Task<IReadOnlyList<RosterDayDto>> GetRosterAsync(
        string storeCode,
        DateOnly weekStart,
        CancellationToken cancellationToken = default);

    Task<IReadOnlyList<SchedulingRunDto>> ListRunsAsync(
        string? storeCode,
        int limit,
        IReadOnlySet<string> allowedStoreCodes,
        bool allStores,
        CancellationToken cancellationToken = default);

    Task<SchedulingRunDto?> GetRunAsync(int runId, CancellationToken cancellationToken = default);
}

public interface ISchedulingRunService
{
    Task<SchedulingRunDto> StartRunAsync(
        StartSchedulingRunRequest request,
        string requestedByEmail,
        CancellationToken cancellationToken = default);
}

public interface ISchedulingFile2ExportService
{
    Task<File2ExportResult> ExportAsync(string storeCode, DateOnly weekStart, CancellationToken cancellationToken = default);
}
