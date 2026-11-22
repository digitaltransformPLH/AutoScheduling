using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using Serilog;
using WorkforcePlanning.Application;
using WorkforcePlanning.Application.Options;
using WorkforcePlanning.Infrastructure;

var contentRoot = AppContext.BaseDirectory;
var webRoot = Path.Combine(contentRoot, "wwwroot");
if (!File.Exists(Path.Combine(webRoot, "index.html")))
{
    // `dotnet run` content root is bin/... — fall back to project wwwroot when not copied yet
    var projectWww = Path.GetFullPath(Path.Combine(contentRoot, "..", "..", "..", "wwwroot"));
    if (File.Exists(Path.Combine(projectWww, "index.html")))
        webRoot = projectWww;
}

var logDir = Path.Combine(contentRoot, "logs");
try { Directory.CreateDirectory(logDir); } catch { /* App Pool may lack permission */ }

Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .WriteTo.File(
        Path.Combine(logDir, "app-.log"),
        rollingInterval: RollingInterval.Day,
        shared: true)
    .CreateBootstrapLogger();

try
{
    var builder = WebApplication.CreateBuilder(new WebApplicationOptions
    {
        Args = args,
        ContentRootPath = contentRoot,
        WebRootPath = webRoot
    });

    builder.Host.UseSerilog((ctx, services, cfg) => cfg
        .ReadFrom.Configuration(ctx.Configuration)
        .ReadFrom.Services(services)
        .Enrich.FromLogContext()
        .WriteTo.Console()
        .WriteTo.File(
            Path.Combine(logDir, "app-.log"),
            rollingInterval: RollingInterval.Day,
            shared: true));

    builder.Services.Configure<AuthOptions>(builder.Configuration.GetSection(AuthOptions.SectionName));
    builder.Services.Configure<SchedulingOptions>(builder.Configuration.GetSection(SchedulingOptions.SectionName));
    var authOptions = builder.Configuration.GetSection(AuthOptions.SectionName).Get<AuthOptions>() ?? new AuthOptions();
    var sessionHours = authOptions.SessionHours <= 0 ? 10 : authOptions.SessionHours;

    builder.Services.AddApplication();
    builder.Services.AddInfrastructure(builder.Configuration);

    builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
        .AddCookie(options =>
        {
            options.Cookie.Name = "WorkforcePlanning.Auth";
            options.Cookie.HttpOnly = true;
            options.Cookie.SameSite = SameSiteMode.Lax;
            options.Cookie.SecurePolicy = CookieSecurePolicy.SameAsRequest;
            options.SlidingExpiration = true;
            options.ExpireTimeSpan = TimeSpan.FromHours(sessionHours);
            options.Events.OnRedirectToLogin = ctx =>
            {
                ctx.Response.StatusCode = StatusCodes.Status401Unauthorized;
                return Task.CompletedTask;
            };
            options.Events.OnRedirectToAccessDenied = ctx =>
            {
                ctx.Response.StatusCode = StatusCodes.Status403Forbidden;
                return Task.CompletedTask;
            };
        });

    builder.Services.AddAuthorization(options =>
    {
        options.FallbackPolicy = new AuthorizationPolicyBuilder()
            .RequireAuthenticatedUser()
            .Build();
    });

    Log.Information("Auth mode: Cookie (email/password). Admin seed: {Email}", authOptions.AdminEmail);

    builder.Services.AddControllers(options =>
        {
            options.Filters.Add<UnauthorizedAccessExceptionFilter>();
        })
        .AddJsonOptions(o =>
        {
            o.JsonSerializerOptions.PropertyNameCaseInsensitive = true;
            o.JsonSerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
        });

    builder.Services.AddEndpointsApiExplorer();
    builder.Services.AddOpenApi();

    builder.Services.AddCors(options =>
    {
        options.AddPolicy("SameSiteOrDev", policy =>
        {
            policy.AllowAnyHeader().AllowAnyMethod().AllowCredentials()
                .SetIsOriginAllowed(_ => true);
        });
    });

    var app = builder.Build();

    _ = Task.Run(async () =>
    {
        try
        {
            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(60));
            await WorkforcePlanning.Infrastructure.DependencyInjection.EnsureRbacSeedAsync(app.Services);
            Log.Information("Database migrate/RBAC seed completed.");
        }
        catch (Exception ex)
        {
            Log.Warning(ex, "Database migrate/seed skipped — check ConnectionStrings:DefaultConnection.");
            try
            {
                await File.WriteAllTextAsync(
                    Path.Combine(logDir, "db-seed-error.txt"),
                    $"{DateTimeOffset.Now:O}\n{ex}");
            }
            catch { /* ignore */ }
        }
    });

    if (app.Environment.IsDevelopment())
        app.MapOpenApi().AllowAnonymous();

    app.UseSerilogRequestLogging();

    var pathBase = builder.Configuration["PathBase"]
        ?? Environment.GetEnvironmentVariable("ASPNETCORE_PATHBASE");
    if (!string.IsNullOrWhiteSpace(pathBase))
        app.UsePathBase(pathBase.StartsWith('/') ? pathBase : "/" + pathBase);

    app.UseDefaultFiles();
    app.UseStaticFiles();

    app.UseCors("SameSiteOrDev");
    app.UseAuthentication();
    app.UseAuthorization();

    app.MapControllers();

    var planningIndex = Path.Combine(webRoot, "planning", "index.html");
    if (File.Exists(planningIndex))
    {
        app.MapGet("/planning", () => Results.Redirect("/planning/index.html")).AllowAnonymous();
        app.MapGet("/planning/", () => Results.Redirect("/planning/index.html")).AllowAnonymous();
    }

    app.MapFallback(async ctx =>
    {
        var path = ctx.Request.Path.Value ?? string.Empty;
        if (path.StartsWith("/api", StringComparison.OrdinalIgnoreCase)
            || path.StartsWith("/planning", StringComparison.OrdinalIgnoreCase))
        {
            ctx.Response.StatusCode = StatusCodes.Status404NotFound;
            return;
        }

        var spaIndex = Path.Combine(webRoot, "index.html");
        if (!File.Exists(spaIndex))
        {
            ctx.Response.StatusCode = StatusCodes.Status404NotFound;
            return;
        }

        ctx.Response.ContentType = "text/html; charset=utf-8";
        await ctx.Response.SendFileAsync(spaIndex);
    }).AllowAnonymous();

    Log.Information("WebRoot: {WebRoot}", webRoot);
    app.Run();
}
catch (Exception ex)
{
    Log.Fatal(ex, "Application terminated unexpectedly");
    try
    {
        await File.WriteAllTextAsync(
            Path.Combine(logDir, "startup-fatal.txt"),
            $"{DateTimeOffset.Now:O}\n{ex}");
    }
    catch { /* ignore */ }
    throw;
}
finally
{
    await Log.CloseAndFlushAsync();
}

public sealed class UnauthorizedAccessExceptionFilter : IExceptionFilter
{
    public void OnException(ExceptionContext context)
    {
        if (context.Exception is not UnauthorizedAccessException) return;
        context.Result = new ObjectResult(new { success = false, message = context.Exception.Message })
        {
            StatusCode = StatusCodes.Status403Forbidden
        };
        context.ExceptionHandled = true;
    }
}
