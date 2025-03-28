# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2024-03-21

### Added
- New image manipulation commands:
  - `?caption <text>` - Add text captions to images with outline
  - `?fry` - Deepfry images with enhanced effects
  - `?mirror` - Mirror images horizontally
- Moved image commands to a dedicated `image.py` cog for better organization

### Changed
- Updated help command to include new image commands
- Improved code organization with cog system

## [1.0.0] - 2024-03-21

### Added
- Initial release with basic functionality
- Moderation commands:
  - `?ban` - Ban users with reason and DM notification
  - `?kick` - Kick users with reason and DM notification
  - `?timeout` - Timeout users with duration and reason
  - `?untimeout` - Remove timeout from users
  - `?unban` - Unban users by ID
- Utility commands:
  - `?snipe` - Show last deleted message
  - `?prefix` - Show current command prefix
  - `?setprefix` - Change command prefix (admin only)
  - `?ping` - Check bot latency
  - `?help` - Show command list
  - `?repo` - Get repository link
- Image commands:
  - `?gif` - Convert images to GIF format

### Features
- Custom prefix support per server
- Role hierarchy checks for moderation commands
- DM notifications for moderation actions
- Error handling for all commands
- Consistent embed styling with custom color
- Support for user IDs in moderation commands 