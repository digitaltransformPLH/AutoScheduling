namespace WorkforcePlanning.Application.DTOs;

public class PersonDto
{
    public int Id { get; set; }
    public string FullName { get; set; } = string.Empty;
    public string? Email { get; set; }
    public string? Phone { get; set; }
    public string Role { get; set; } = string.Empty;
    public bool IsActive { get; set; }
}

public class AmOmAssignmentDto
{
    public int Id { get; set; }
    public int AreaManagerId { get; set; }
    public string AreaManagerName { get; set; } = string.Empty;
    public int OperationManagerId { get; set; }
    public string OperationManagerName { get; set; } = string.Empty;
    public string EffectiveFrom { get; set; } = string.Empty;
    public string? EffectiveTo { get; set; }
}

public class UpsertAmOmAssignmentRequest
{
    public int OperationManagerId { get; set; }
    public string? EffectiveFrom { get; set; }
}

public class CreateAmOmAssignmentRequest
{
    public int AreaManagerId { get; set; }
    public int OperationManagerId { get; set; }
    public string? EffectiveFrom { get; set; }
}

public class StoreDetailDto
{
    public int Id { get; set; }
    public string Code { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string? City { get; set; }
    public string? Concept { get; set; }
    public string? OpenDate { get; set; }
    public string? CloseDate { get; set; }
    public string? Email { get; set; }
    public int? AreaManagerId { get; set; }
    public string? AreaManagerName { get; set; }
    public string? OperationManagerName { get; set; }
    public bool IsActive { get; set; }
}

public class PagedResult<T>
{
    public List<T> Items { get; set; } = new();
    public int Total { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
    public int TotalPages => PageSize > 0 ? (int)Math.Ceiling(Total / (double)PageSize) : 0;
}

public class UpsertStoreRequest
{
    public string Code { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string? City { get; set; }
    public string? Concept { get; set; }
    public string? OpenDate { get; set; }
    public string? CloseDate { get; set; }
    public string? Email { get; set; }
    public int? AreaManagerId { get; set; }
    public bool IsActive { get; set; } = true;
}

public class StoreOrgResponse
{
    public string StoreCode { get; set; } = string.Empty;
    public string StoreName { get; set; } = string.Empty;
    public string? AreaManager { get; set; }
    public string? OperationManager { get; set; }
}

public class OperationManagerLookupResponse
{
    public int OperationManagerId { get; set; }
    public string OperationManagerName { get; set; } = string.Empty;
}
