namespace WorkforcePlanning.Application.DTOs;

public class StoreConfigListItemDto
{
    public int StoreId { get; set; }
    public string StoreCode { get; set; } = string.Empty;
    public string StoreName { get; set; } = string.Empty;
    public bool IsConfigured { get; set; }
    public decimal? TcphTarget { get; set; }
    public decimal? TcphCeilingMult { get; set; }
    public int? OpenStaff { get; set; }
    public int? CloseStaff { get; set; }
    public int? MinStaffPerSlot { get; set; }
    public string? UpdatedAt { get; set; }
    public string? UpdatedBy { get; set; }
}

public class StoreConfigDetailDto
{
    public int StoreId { get; set; }
    public string StoreCode { get; set; } = string.Empty;
    public string StoreName { get; set; } = string.Empty;
    public bool IsConfigured { get; set; }
    public decimal TcphTarget { get; set; }
    public decimal TcphCeilingMult { get; set; }
    public int OpenStaff { get; set; }
    public int CloseStaff { get; set; }
    public int MinStaffPerSlot { get; set; }
    public string? UpdatedAt { get; set; }
    public string? UpdatedBy { get; set; }
}

public class UpsertStoreConfigRequest
{
    public decimal TcphTarget { get; set; }
    public decimal TcphCeilingMult { get; set; } = OpsStoreConfigDefaultsDto.TcphCeilingMult;
    public int OpenStaff { get; set; } = OpsStoreConfigDefaultsDto.OpenStaff;
    public int CloseStaff { get; set; } = OpsStoreConfigDefaultsDto.CloseStaff;
    public int MinStaffPerSlot { get; set; } = OpsStoreConfigDefaultsDto.MinStaffPerSlot;
}

public static class OpsStoreConfigDefaultsDto
{
    public const decimal TcphCeilingMult = 1.05m;
    public const int OpenStaff = 2;
    public const int CloseStaff = 2;
    public const int MinStaffPerSlot = 2;
}

public class StoreConfigImportResultDto
{
    public int Created { get; set; }
    public int Updated { get; set; }
    public int Failed { get; set; }
    public List<StoreConfigImportRowErrorDto> Errors { get; set; } = new();
}

public class StoreConfigImportRowErrorDto
{
    public int Row { get; set; }
    public string? PlantCode { get; set; }
    public string Message { get; set; } = string.Empty;
}