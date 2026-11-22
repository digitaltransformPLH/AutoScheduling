namespace WorkforcePlanning.Domain.Entities;

public class UserStore
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public int StoreId { get; set; }

    public User User { get; set; } = null!;
    public Store Store { get; set; } = null!;
}
