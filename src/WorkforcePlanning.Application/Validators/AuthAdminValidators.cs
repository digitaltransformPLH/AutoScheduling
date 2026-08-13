using FluentValidation;
using WorkforcePlanning.Application.DTOs;

namespace WorkforcePlanning.Application.Validators;

public class LoginRequestValidator : AbstractValidator<LoginRequest>
{
    public LoginRequestValidator()
    {
        RuleFor(x => x.Email).NotEmpty().EmailAddress().MaximumLength(256);
        RuleFor(x => x.Password).NotEmpty().MaximumLength(200);
    }
}

public class UpsertUserRequestValidator : AbstractValidator<UpsertUserRequest>
{
    public UpsertUserRequestValidator()
    {
        RuleFor(x => x.Email).NotEmpty().EmailAddress().MaximumLength(256);
        RuleFor(x => x.DisplayName).NotEmpty().MaximumLength(200);
        RuleFor(x => x.RoleId).GreaterThan(0);
        RuleFor(x => x.Password)
            .MinimumLength(6)
            .When(x => !string.IsNullOrWhiteSpace(x.Password));
        RuleFor(x => x)
            .Must(x => x.AllStores || (x.StoreIds?.Count > 0))
            .WithMessage("Chọn ít nhất một cửa hàng hoặc bật Tất cả cửa hàng.");
    }
}

public class UpsertRoleRequestValidator : AbstractValidator<UpsertRoleRequest>
{
    public UpsertRoleRequestValidator()
    {
        RuleFor(x => x.Name).NotEmpty().MaximumLength(100);
        RuleFor(x => x.Description).MaximumLength(500);
    }
}

public class SetRolePermissionsRequestValidator : AbstractValidator<SetRolePermissionsRequest>
{
    public SetRolePermissionsRequestValidator()
    {
        RuleFor(x => x.PermissionIds).NotNull();
    }
}
