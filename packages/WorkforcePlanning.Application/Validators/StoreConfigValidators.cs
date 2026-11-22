using FluentValidation;
using WorkforcePlanning.Application.DTOs;

namespace WorkforcePlanning.Application.Validators;

public class UpsertStoreConfigRequestValidator : AbstractValidator<UpsertStoreConfigRequest>
{
    public UpsertStoreConfigRequestValidator()
    {
        RuleFor(x => x.TcphTarget)
            .GreaterThan(0)
            .WithMessage("TCPH target phải lớn hơn 0.");

        RuleFor(x => x.TcphCeilingMult)
            .GreaterThan(1m)
            .LessThanOrEqualTo(2m)
            .WithMessage("Hệ số trần TCPH phải trong khoảng (1, 2].");

        RuleFor(x => x.OpenStaff).GreaterThanOrEqualTo(1);
        RuleFor(x => x.CloseStaff).GreaterThanOrEqualTo(1);
        RuleFor(x => x.MinStaffPerSlot).GreaterThanOrEqualTo(1);
    }
}