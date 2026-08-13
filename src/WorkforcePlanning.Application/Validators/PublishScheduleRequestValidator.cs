using FluentValidation;
using WorkforcePlanning.Application.DTOs;

namespace WorkforcePlanning.Application.Validators;

public class PublishScheduleRequestValidator : AbstractValidator<PublishScheduleRequest>
{
    private static readonly string[] ExpectedDays =
    [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ];

    public PublishScheduleRequestValidator()
    {
        RuleFor(x => x.StoreCode).NotEmpty().MaximumLength(10);
        RuleFor(x => x.WeekStart).NotEmpty().Must(BeIsoDate).WithMessage("weekStart must be YYYY-MM-DD.");
        RuleFor(x => x.WeekEnd).NotEmpty().Must(BeIsoDate).WithMessage("weekEnd must be YYYY-MM-DD.");
        RuleFor(x => x.PublishId).NotEmpty().MaximumLength(64);
        RuleFor(x => x.PublishVersion).GreaterThan(0);
        RuleFor(x => x.PublishedAt).NotEmpty();
        RuleFor(x => x.Records).NotNull().Must(r => r.Count == 7)
            .WithMessage("records must contain exactly 7 daily rows.");

        RuleFor(x => x).Custom((req, ctx) =>
        {
            if (!DateOnly.TryParse(req.WeekStart, out var weekStart))
                return;

            if (weekStart.DayOfWeek != DayOfWeek.Monday)
            {
                ctx.AddFailure("weekStart", "weekStart must be a Monday.");
                return;
            }

            if (!DateOnly.TryParse(req.WeekEnd, out var weekEnd) || weekEnd != weekStart.AddDays(6))
            {
                ctx.AddFailure("weekEnd", "weekEnd must be weekStart + 6 days.");
            }

            for (var i = 0; i < req.Records.Count; i++)
            {
                var r = req.Records[i];
                var expectedDate = weekStart.AddDays(i);

                if (!string.Equals(r.StoreCode, req.StoreCode, StringComparison.OrdinalIgnoreCase))
                    ctx.AddFailure($"records[{i}].Store Code", "Store Code must match request storeCode.");

                if (!string.Equals(r.PublishId, req.PublishId, StringComparison.Ordinal))
                    ctx.AddFailure($"records[{i}].Publish ID", "Publish ID must match request publishId.");

                if (r.PublishVersion != req.PublishVersion)
                    ctx.AddFailure($"records[{i}].Publish Version", "Publish Version must match request publishVersion.");

                if (!DateOnly.TryParse(r.Date, out var date) || date != expectedDate)
                    ctx.AddFailure($"records[{i}].Date", $"Date must be {expectedDate:yyyy-MM-dd}.");

                if (!string.Equals(r.Day, ExpectedDays[i], StringComparison.OrdinalIgnoreCase))
                    ctx.AddFailure($"records[{i}].Day", $"Day must be {ExpectedDays[i]}.");

                if (r.ADTC is null)
                    ctx.AddFailure($"records[{i}].ADTC", "ADTC is required.");

                if (r.Month != expectedDate.Month || r.Year != expectedDate.Year)
                    ctx.AddFailure($"records[{i}]", "Month/Year must match Date.");
            }
        });
    }

    private static bool BeIsoDate(string value) =>
        DateOnly.TryParseExact(value, "yyyy-MM-dd", out _);
}
