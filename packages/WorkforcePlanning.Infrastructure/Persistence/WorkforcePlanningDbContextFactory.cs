using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.Extensions.Configuration;

namespace WorkforcePlanning.Infrastructure.Persistence;

public class WorkforcePlanningDbContextFactory : IDesignTimeDbContextFactory<WorkforcePlanningDbContext>
{
    public WorkforcePlanningDbContext CreateDbContext(string[] args)
    {
        var cwd = Directory.GetCurrentDirectory();
        var candidates = new[]
        {
            Path.GetFullPath(Path.Combine(cwd, "..", "..", "apps", "api")),
            Path.GetFullPath(Path.Combine(cwd, "..", "WorkforcePlanning.Api")),
            Path.Combine(cwd, "..", "..", "apps", "api"),
        };
        var basePath = candidates.FirstOrDefault(Directory.Exists) ?? cwd;

        var config = new ConfigurationBuilder()
            .SetBasePath(basePath)
            .AddJsonFile("appsettings.json", optional: true)
            .AddJsonFile("appsettings.Development.json", optional: true)
            .Build();

        var cs = config.GetConnectionString("DefaultConnection")
            ?? "Server=localhost;Database=WorkforcePlanning;Trusted_Connection=True;TrustServerCertificate=True;";

        var options = new DbContextOptionsBuilder<WorkforcePlanningDbContext>()
            .UseSqlServer(cs)
            .Options;

        return new WorkforcePlanningDbContext(options);
    }
}
