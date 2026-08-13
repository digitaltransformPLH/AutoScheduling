namespace WorkforcePlanning.Domain.Entities;

public class AmOmAssignment
{
    public int Id { get; set; }
    public int AreaManagerId { get; set; }
    public int OperationManagerId { get; set; }
    public DateOnly EffectiveFrom { get; set; }
    public DateOnly? EffectiveTo { get; set; }

    public Person AreaManager { get; set; } = null!;
    public Person OperationManager { get; set; } = null!;
}
