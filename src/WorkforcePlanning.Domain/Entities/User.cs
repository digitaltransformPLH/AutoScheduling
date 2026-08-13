namespace WorkforcePlanning.Domain.Entities;

public class User
{
    public int Id { get; set; }
    public string Email { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public bool IsActive { get; set; } = true;
    public int RoleId { get; set; }
    public bool AllStores { get; set; }

    public Role Role { get; set; } = null!;
    public ICollection<UserStore> UserStores { get; set; } = new List<UserStore>();
}
