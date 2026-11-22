using FluentValidation;
using WorkforcePlanning.Application.Common;
using WorkforcePlanning.Application.DTOs;

namespace WorkforcePlanning.Application.Validators;

public class UpsertEmployeeAvailabilitySlotRequestValidator : AbstractValidator<UpsertEmployeeAvailabilitySlotRequest>
{
    public UpsertEmployeeAvailabilitySlotRequestValidator()
    {
        RuleFor(x => x.PlantCode).NotEmpty().MaximumLength(10);
        RuleFor(x => x.EmployeeNumber).GreaterThan(0);
        RuleFor(x => x.WorkDate).NotEmpty().Must(BeValidDate).WithMessage("WorkDate không hợp lệ (yyyy-MM-dd).");

        When(x => x.IsPaidLeave, () =>
        {
            RuleFor(x => x.BusyFrom).Empty();
            RuleFor(x => x.BusyTo).Empty();
        }).Otherwise(() =>
        {
            RuleFor(x => x.BusyFrom).NotEmpty().Must(BeValidTime).WithMessage("Bận từ không hợp lệ (HH:mm).");
            RuleFor(x => x.BusyTo).NotEmpty().Must(BeValidTime).WithMessage("Bận đến không hợp lệ (HH:mm).");
            RuleFor(x => x).Must(x => BusyEndAfterStart(x)).WithMessage("Bận đến phải sau Bận từ.");
        });
    }

    private static bool BeValidDate(string? s) =>
        !string.IsNullOrWhiteSpace(s) && DateOnly.TryParse(s.Trim(), out _);

    private static bool BeValidTime(string? s) =>
        !string.IsNullOrWhiteSpace(s) && BusyTimeParser.TryParse(s, out var t) && t is not null;

    private static bool BusyEndAfterStart(UpsertEmployeeAvailabilitySlotRequest x)
    {
        if (!BusyTimeParser.TryParse(x.BusyFrom, out var from) || from is null) return false;
        if (!BusyTimeParser.TryParse(x.BusyTo, out var to) || to is null) return false;
        return to > from;
    }
}