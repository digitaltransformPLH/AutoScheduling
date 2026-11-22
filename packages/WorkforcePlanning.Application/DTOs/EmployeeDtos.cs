namespace WorkforcePlanning.Application.DTOs;

public class EmployeeListItemDto
{
    public int Id { get; set; }
    public string FullName { get; set; } = string.Empty;
    public long EmployeeNumber { get; set; }
    public string PlantCode { get; set; } = string.Empty;
    public string? PlantName { get; set; }
    public string Position { get; set; } = string.Empty;
    public string EmploymentType { get; set; } = string.Empty;
    public string LaborGroup { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
}

public class EmployeeDetailDto : EmployeeListItemDto
{
}

public class UpsertEmployeeRequest
{
    public string FullName { get; set; } = string.Empty;
    public long EmployeeNumber { get; set; }
    public string PlantCode { get; set; } = string.Empty;
    public string Position { get; set; } = string.Empty;
    public string EmploymentType { get; set; } = string.Empty;
    public string LaborGroup { get; set; } = string.Empty;
    public string Status { get; set; } = "Active";
}

public class EmployeeLookupsDto
{
    public string[] Positions { get; set; } = [];
    public string[] EmploymentTypes { get; set; } = [];
    public string[] LaborGroups { get; set; } = [];
    public string[] Statuses { get; set; } = [];
}

public class EmployeeImportResultDto
{
    public int Created { get; set; }
    public int Updated { get; set; }
    public int Failed { get; set; }
    public List<EmployeeImportRowErrorDto> Errors { get; set; } = new();
}

public class EmployeeImportRowErrorDto
{
    public int Row { get; set; }
    public string Message { get; set; } = string.Empty;
}

public class EmployeeSecondmentListItemDto
{
    public int Id { get; set; }
    public int EmployeeId { get; set; }
    public long EmployeeNumber { get; set; }
    public string FullName { get; set; } = string.Empty;
    public string HomePlantCode { get; set; } = string.Empty;
    public string? HomePlantName { get; set; }
    public string ReceivingStoreCode { get; set; } = string.Empty;
    public string? ReceivingStoreName { get; set; }
    public string StartDate { get; set; } = string.Empty;
    public string EndDate { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty;
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public string UpdatedBy { get; set; } = string.Empty;
}

public class CreateEmployeeSecondmentRequest
{
    public string StartDate { get; set; } = string.Empty;
    public string EndDate { get; set; } = string.Empty;
    public string ReceivingStoreCode { get; set; } = string.Empty;
}

public class UpdateEmployeeSecondmentRequest
{
    public string StartDate { get; set; } = string.Empty;
    public string EndDate { get; set; } = string.Empty;
    public string ReceivingStoreCode { get; set; } = string.Empty;
}