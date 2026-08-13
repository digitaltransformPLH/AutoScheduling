namespace WorkforcePlanning.Domain.Entities;

public class Person
{
    public int Id { get; set; }
    public string FullName { get; set; } = string.Empty;
    public string? Email { get; set; }
    public string? Phone { get; set; }
    /// <summary>ROM, AM, SM, or GSC.</summary>
    public string Role { get; set; } = string.Empty;
    public bool IsActive { get; set; } = true;

    public ICollection<Store> ManagedStores { get; set; } = new List<Store>();
    public ICollection<AmOmAssignment> AreaManagerAssignments { get; set; } = new List<AmOmAssignment>();
    public ICollection<AmOmAssignment> OperationManagerAssignments { get; set; } = new List<AmOmAssignment>();
}
