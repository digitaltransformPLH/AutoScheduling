namespace WorkforcePlanning.Domain.Entities;

public class Store
{
    public int Id { get; set; }
    public string Code { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string? City { get; set; }
    public string? Concept { get; set; }
    public DateOnly? OpenDate { get; set; }
    public DateOnly? CloseDate { get; set; }
    public string? Email { get; set; }
    public int? AreaManagerId { get; set; }
    public bool IsActive { get; set; } = true;

    public Person? AreaManager { get; set; }
    public ICollection<UserStore> UserStores { get; set; } = new List<UserStore>();
    public OpsStoreConfig? OpsStoreConfig { get; set; }
}
