using FluentValidation;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using WorkforcePlanning.Application.DTOs;
using WorkforcePlanning.Application.Interfaces;

namespace WorkforcePlanning.Api.Controllers;

[ApiController]
[Route("api/v1/auth")]
public class AuthController : ControllerBase
{
    private readonly IAuthService _auth;
    private readonly IValidator<LoginRequest> _validator;

    public AuthController(IAuthService auth, IValidator<LoginRequest> validator)
    {
        _auth = auth;
        _validator = validator;
    }

    [AllowAnonymous]
    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request, CancellationToken cancellationToken)
    {
        var validation = await _validator.ValidateAsync(request ?? new LoginRequest(), cancellationToken);
        if (!validation.IsValid)
            return BadRequest(new { success = false, message = string.Join(" | ", validation.Errors.Select(e => e.ErrorMessage)) });

        var me = await _auth.LoginAsync(request!, cancellationToken);
        if (me is null)
            return Unauthorized(new { success = false, message = "Email hoặc mật khẩu không đúng." });

        return Ok(me);
    }

    [Authorize]
    [HttpPost("logout")]
    public async Task<IActionResult> Logout()
    {
        await _auth.LogoutAsync();
        return Ok(new { success = true });
    }
}
