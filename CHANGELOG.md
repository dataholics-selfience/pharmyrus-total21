# Changelog

## [6.0.0-PRODUCTION] - 2025-12-20

### Fixed - Critical Deploy Issues
- **CMD Format**: Changed from array to shell form for $PORT expansion
- **Port Binding**: Railway $PORT variable now properly interpolated
- **Health Check**: Updated to use dynamic ${PORT:-8000}
- **Startup**: Service now starts correctly on Railway

### Technical Changes
- Dockerfile CMD: `CMD uvicorn ... --port ${PORT:-8000}` (shell form)
- railway.toml: Removed conflicting startCommand (uses Dockerfile CMD)
- Health check: Dynamic port detection
- Fallback: Port 8000 if $PORT not set

### Verified
- ✅ Build: Successful (Ubuntu 22.04, Playwright installed)
- ✅ Deploy: Successful (service starts correctly)
- ✅ Health: Endpoint responding
- ✅ API: All endpoints functional

## [6.0.0-LAYERED-FIXED] - 2025-12-20

### Fixed - Build Issues
- Changed base image: Debian Trixie → Ubuntu 22.04 LTS
- Playwright deps: Manual installation (no install-deps)
- Fonts: Modern packages (fonts-liberation, fonts-noto-color-emoji)

## [6.0.0-LAYERED] - 2025-12-20

Initial production release
