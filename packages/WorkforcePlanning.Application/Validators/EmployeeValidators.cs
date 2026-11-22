using FluentValidation;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Domain.Constants;

namespace WorkforcePlanning.Application.Validators;

public class UpsertEmployeeRequestValidator : AbstractValidator<UpsertEmployeeRequest>
{
    public UpsertEmployeeRequestValidator()
    {
        RuleFor(x => x.FullName).NotEmpty().MaximumLength(200);
        RuleFor(x => x.EmployeeNumber).GreaterThan(0);
        RuleFor(x => x.PlantCode).NotEmpty().MaximumLength(10);
        RuleFor(x => x.Position).NotEmpty().MaximumLength(100)
            .Must(v => EmployeeCatalog.Positions.Contains(v))
            .WithMessage("Position không hợp lệ.");
        RuleFor(x => x.EmploymentType).NotEmpty().MaximumLength(20)
            .Must(v => EmployeeCatalog.EmploymentTypes.Contains(v))
            .WithMessage("Employment Type không hợp lệ.");
        RuleFor(x => x.LaborGroup).NotEmpty().MaximumLength(50)
            .Must(v => EmployeeCatalog.LaborGroups.Contains(v))
            .WithMessage("Labor group không hợp lệ.");
        RuleFor(x => x.Status).NotEmpty().MaximumLength(20)
            .Must(v => EmployeeCatalog.Statuses.Contains(v))
            .WithMessage("Status không hợp lệ.");
    }
}

public class CreateEmployeeSecondmentRequestValidator : AbstractValidator<CreateEmployeeSecondmentRequest>
{
    public CreateEmployeeSecondmentRequestValidator()
    {
        RuleFor(x => x.ReceivingStoreCode).NotEmpty().MaximumLength(10);
        RuleFor(x => x.StartDate).NotEmpty().Must(BeValidDate).WithMessage("Ngày bắt đầu không hợp lệ.");
        RuleFor(x => x.EndDate).NotEmpty().Must(BeValidDate).WithMessage("Ngày kết thúc không hợp lệ.");
        RuleFor(x => x).Must(x => ParseDate(x.StartDate) <= ParseDate(x.EndDate))
            .WithMessage("Ngày kết thúc phải >= ngày bắt đầu.");
    }

    private static bool BeValidDate(string value) => DateOnly.TryParse(value, out _);

    private static DateOnly ParseDate(string value) =>
        DateOnly.TryParse(value, out var d) ? d : DateOnly.MinValue;
}

public class UpdateEmployeeSecondmentRequestValidator : AbstractValidator<UpdateEmployeeSecondmentRequest>
{
    public UpdateEmployeeSecondmentRequestValidator()
    {
        RuleFor(x => x.ReceivingStoreCode).NotEmpty().MaximumLength(10);
        RuleFor(x => x.StartDate).NotEmpty().Must(BeValidDate).WithMessage("Ngày bắt đầu không hợp lệ.");
        RuleFor(x => x.EndDate).NotEmpty().Must(BeValidDate).WithMessage("Ngày kết thúc không hợp lệ.");
        RuleFor(x => x).Must(x => ParseDate(x.StartDate) <= ParseDate(x.EndDate))
            .WithMessage("Ngày kết thúc phải >= ngày bắt đầu.");
    }

    private static bool BeValidDate(string value) => DateOnly.TryParse(value, out _);

    private static DateOnly ParseDate(string value) =>
        DateOnly.TryParse(value, out var d) ? d : DateOnly.MinValue;
}