using FluentValidation;
using Microsoft.Extensions.DependencyInjection;
using WorkforcePlanning.Application.Validators;

namespace WorkforcePlanning.Application;

public static class DependencyInjection
{
    public static IServiceCollection AddApplication(this IServiceCollection services)
    {
        services.AddValidatorsFromAssemblyContaining<UpsertStoreConfigRequestValidator>();
        return services;
    }
}
