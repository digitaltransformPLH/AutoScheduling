namespace WorkforcePlanning.Domain.Entities;

public class OpsStoreConfig
{
    public int StoreId { get; set; }
    public decimal TcphTarget { get; set; }
    public decimal TcphCeilingMult { get; set; } = 1.05m;
    public int OpenStaff { get; set; } = 2;
    public int CloseStaff { get; set; } = 2;
    public int MinStaffPerSlot { get; set; } = 2;
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
    public string UpdatedBy { get; set; } = string.Empty;

    public Store? Store { get; set; }
}

public static class OpsStoreConfigDefaults
{
    public const decimal TcphCeilingMult = 1.05m;
    public const int OpenStaff = 2;
    public const int CloseStaff = 2;
    public const int MinStaffPerSlot = 2;
}