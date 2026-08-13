namespace WorkforcePlanning.Domain.Entities;

/// <summary>
/// Store org detail (Plant/store code → AreaManager, OperationManager, Region).
/// Sourced from Order Template Sorting.xlsx sheet Stores.
/// </summary>
public class DimStoreDetail
{
    /// <summary>Plant / store code (dim_store2).</summary>
    public string StoreCode { get; set; } = string.Empty;

    public string StoreName { get; set; } = string.Empty;
    public string? Concept { get; set; }
    public string? City { get; set; }

    public string AreaManager { get; set; } = string.Empty;
    public string OperationManager { get; set; } = string.Empty;

    /// <summary>Region / Vùng: H, T, or W.</summary>
    public string Region { get; set; } = string.Empty;
}
