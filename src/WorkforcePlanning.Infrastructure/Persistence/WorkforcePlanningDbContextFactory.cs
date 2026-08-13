using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.Extensions.Configuration;

namespace WorkforcePlanning.Infrastructure.Persistence;

public class WorkforcePlanningDbContextFactory : IDesignTimeDbContextFactory<WorkforcePlanningDbContext>
{
    public WorkforcePlanningDbContext CreateDbContext(string[] args)
    {
        var basePath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "..", "WorkforcePlanning.Api"));
        if (!Directory.Exists(basePath))
            basePath = Directory.GetCurrentDirectory();

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
