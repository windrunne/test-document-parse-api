# DME Orders Management System

A comprehensive, production-ready REST API and frontend application for managing DME (Durable Medical Equipment) orders with AI-powered document processing.

## Features

### Backend (FastAPI)
- **CRUD Operations**: Full CRUD operations for Order entities
- **Document Processing**: AI-powered document upload and data extraction using OpenAI
- **User Management**: JWT-based authentication and user management
- **Activity Logging**: Comprehensive logging of all user activities
- **Database**: PostgreSQL with SQLAlchemy ORM
- **File Storage**: AWS S3 integration for document storage
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

### Frontend (Next.js + Tailwind)
- **Modern UI**: Responsive, component-based interface
- **Authentication**: Secure login/registration system
- **Order Management**: Intuitive order creation and management
- **Document Upload**: Drag & drop file upload with progress tracking
- **Real-time Updates**: Live data updates and notifications

### AI Document Processing
- **Multi-format Support**: PDF, JPEG, PNG, TIFF, BMP
- **Patient Data Extraction**: Automatically extracts:
  - Patient First Name
  - Patient Last Name
  - Date of Birth
- **High Accuracy**: Powered by OpenAI's GPT-4 Vision API
- **Fallback Processing**: Robust error handling and fallback methods

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   AWS S3        │
                       │   (File Storage)│
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │   (AI Processing)│
                       └─────────────────┘
```

## Tech Stack

### Backend
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT with Passlib
- **File Storage**: AWS S3 (Boto3)
- **AI Processing**: OpenAI GPT-4 Vision API
- **Migrations**: Alembic
- **Testing**: Pytest

### Frontend
- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **State Management**: Zustand + React Query
- **Forms**: React Hook Form
- **Icons**: Lucide React
- **Notifications**: React Hot Toast

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL (or use Docker)
- AWS S3 bucket
- OpenAI API key

### 1. Clone the Repository
```bash
git clone <repository-url>
cd dme-orders-system
```

### 2. Environment Setup
```bash
# Copy environment template
cp env.example .env

# Edit .env with your configuration
nano .env
```

Required environment variables:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dme_orders_db

# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket-name

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Security
SECRET_KEY=your_secret_key_here
```

### 3. Using Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Manual Setup

#### Backend
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Access the Application
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Get current user

### Orders
- `GET /api/v1/orders` - List orders (with pagination)
- `POST /api/v1/orders` - Create new order
- `GET /api/v1/orders/{id}` - Get order details
- `PUT /api/v1/orders/{id}` - Update order
- `DELETE /api/v1/orders/{id}` - Delete order

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document details
- `POST /api/v1/documents/{id}/extract` - Extract data manually
- `DELETE /api/v1/documents/{id}` - Delete document

## Database Schema

### Users
- Authentication and user management
- Role-based access control

### Orders
- Patient information (name, DOB)
- Order details and status
- Pricing and quantities

### Documents
- File metadata and storage info
- Extracted patient data
- Processing status and errors

### User Activities
- Comprehensive audit trail
- API access logging
- User action tracking

## AI Document Processing

The system uses OpenAI's GPT-4 Vision API to automatically extract patient information from medical documents:

1. **Document Upload**: Files are uploaded to AWS S3
2. **AI Processing**: OpenAI analyzes the document content
3. **Data Extraction**: Patient name and DOB are extracted
4. **Validation**: Data is validated and stored
5. **Order Creation**: Orders can be created from extracted data

### Supported Document Types
- **PDF**: Medical forms, prescriptions, reports
- **Images**: JPEG, PNG, TIFF, BMP formats
- **Size Limit**: Maximum 10MB per file

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt password encryption
- **Input Validation**: Pydantic schema validation
- **SQL Injection Protection**: SQLAlchemy ORM
- **CORS Configuration**: Configurable cross-origin settings
- **Rate Limiting**: Built-in request throttling
- **Activity Logging**: Complete audit trail

## Testing

### Backend Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_orders.py
```

### Frontend Tests
```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

## Deployment

### Production Deployment
1. **Environment Variables**: Configure production settings
2. **Database**: Use managed PostgreSQL service
3. **File Storage**: Configure production S3 bucket
4. **SSL/TLS**: Enable HTTPS with proper certificates
5. **Monitoring**: Set up logging and monitoring
6. **Scaling**: Configure load balancers and auto-scaling

### Deployment Options
- **Docker**: Containerized deployment
- **Cloud Platforms**: AWS, GCP, Azure
- **PaaS**: Heroku, Railway, Render
- **Self-hosted**: VPS or dedicated server

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation at `/docs`

## Roadmap

- [ ] Advanced document processing (OCR)
- [ ] Multi-language support
- [ ] Mobile application
- [ ] Advanced analytics and reporting
- [ ] Integration with medical systems
- [ ] Real-time notifications
- [ ] Advanced search and filtering
- [ ] Bulk operations
- [ ] API rate limiting
- [ ] Advanced caching strategies
