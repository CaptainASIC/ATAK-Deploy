# ATAK-Deploy

Version: 1.0.0

A deployable version of the ATAK software and controls, designed for Railway deployment with proper CICD integration.

## Features

- Automated ATAK server deployment
- Certificate management system
- User management interface
- Data package generation
- Database integration (PostgreSQL)
- Redis caching support
- Environment-based configuration
- Railway deployment ready

## Prerequisites

- Python 3.8+
- PostgreSQL
- Redis (optional, for caching)
- Docker (for local development)

## Project Structure

```
ATAK-Deploy/
├── src/                    # Source code
│   ├── core/              # Core functionality
│   ├── api/               # API endpoints
│   ├── db/                # Database models and migrations
│   ├── utils/             # Utility functions
│   └── config/            # Configuration management
├── tests/                 # Test suite
├── migrations/            # Database migrations
├── docker/               # Docker configuration
├── scripts/              # Utility scripts
└── docs/                 # Documentation
```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/atak_db
REDIS_URL=redis://localhost:6379/0

# Application Configuration
APP_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key

# ATAK Configuration
ATAK_SERVER_HOST=localhost
ATAK_SERVER_PORT=8089
```

## Database Migrations

This project uses Alembic for database migrations. To initialize your database:

```bash
# Initialize migrations
alembic init migrations

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Development

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables
5. Initialize the database
6. Run the development server:
   ```bash
   python src/main.py
   ```

## Deployment

This project is configured for deployment on Railway. The `railway.toml` file contains the necessary configuration for automated deployment.

To deploy:

1. Push your changes to Git
2. Railway will automatically detect changes and trigger deployment
3. Database migrations will be automatically applied

## Version Control

We use semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR version for incompatible API changes
- MINOR version for backwards-compatible functionality additions
- PATCH version for backwards-compatible bug fixes

## Contributing

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details
