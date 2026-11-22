using FluentValidation;
using WorkforcePlanning.Application.DTOs;

namespace WorkforcePlanning.Application.Validators;

public class UpsertStoreRequestValidator : AbstractValidator<UpsertStoreRequest>
{
    public UpsertStoreRequestValidator()
    {
        RuleFor(x => x.Code).NotEmpty().MaximumLength(10);
        RuleFor(x => x.Name).NotEmpty().MaximumLength(200);
        RuleFor(x => x.City).MaximumLength(100);
        RuleFor(x => x.Concept).MaximumLength(50);
        RuleFor(x => x.Email).MaximumLength(256).EmailAddress().When(x => !string.IsNullOrWhiteSpace(x.Email));
    }
}

public class UpsertAmOmAssignmentRequestValidator : AbstractValidator<UpsertAmOmAssignmentRequest>
{
    public UpsertAmOmAssignmentRequestValidator()
    {
        RuleFor(x => x.OperationManagerId).GreaterThan(0);
    }
}

public class CreateAmOmAssignmentRequestValidator : AbstractValidator<CreateAmOmAssignmentRequest>
{
    public CreateAmOmAssignmentRequestValidator()
    {
        RuleFor(x => x.AreaManagerId).GreaterThan(0);
        RuleFor(x => x.OperationManagerId).GreaterThan(0);
    }
}
