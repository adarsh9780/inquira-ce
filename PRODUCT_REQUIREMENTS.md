# Inquira - Product Requirements Document

## Overview

Inquira is a FastAPI-based conversational AI platform that integrates with Google Gemini LLM for data analysis. The platform provides secure code execution, persistent database caching, and an intuitive web interface for data scientists and analysts.

### Business Purpose

Inquira serves as a bridge between natural language queries and complex data analysis, enabling users to:

- Ask business questions in plain English and receive actionable insights
- Generate and execute Python code automatically for data processing
- Visualize results through interactive charts and tables
- Maintain conversation context across multiple queries
- Share analysis workflows through downloadable code

The platform is designed for data analysts, business users, and technical professionals who need fast insights from large datasets without writing complex code.

## Core Features

### 1. Conversational Data Analysis

- **Natural Language Queries**: Users can ask questions about their data in plain English
- **LLM Integration**: Powered by Google Gemini 2.5 Flash for intelligent code generation
- **Contextual Responses**: System maintains conversation context and data understanding
- **Multi-format Support**: Handles CSV, Parquet, JSON, and Excel files

### 2. Secure Code Execution

- **Sandboxed Environment**: Isolated Python execution with restricted builtins
- **Security Analysis**: Automatic detection of potentially harmful code patterns
- **Resource Limits**: Memory and execution time constraints
- **Error Handling**: Comprehensive error reporting and recovery

### 3. Persistent Database Caching

- **Automatic Optimization**: Converts CSV files to DuckDB databases on first access
- **Persistent Storage**: Databases survive application restarts
- **Smart Updates**: Detects source file changes and recreates databases automatically
- **Performance Gains**: 5-10x faster query execution for large datasets

### 4. Real-Time Processing

- **WebSocket Communication**: Real-time progress updates during data processing
- **Background Processing**: Non-blocking database creation and schema generation
- **Parallel Operations**: Simultaneous schema generation and preview caching
- **Progress Messaging**: Contextual status messages for each processing stage
- **Connection Management**: Automatic handling of WebSocket disconnections

### 5. User Management

- **Authentication System**: Secure user registration and login
- **Profile Management**: User preferences and settings
- **API Key Management**: Secure storage of LLM service credentials
- **Session Management**: Proper session handling and cleanup

## Technical Architecture

### Backend Components

#### Core Services

- **FastAPI Application**: RESTful API with automatic OpenAPI documentation
- **Database Manager**: Persistent DuckDB database caching system
- **Code Whisperer**: Secure Python code execution environment
- **LLM Service**: Google Gemini integration with fallback handling

#### Data Flow

```
User Query → LLM Analysis → Code Generation → Secure Execution → Result Formatting → Response
```

#### Database Architecture

```
CSV/Parquet/JSON → DuckDB Database → Persistent Storage → Cached Connections → Query Execution
```

#### Code Execution Environment

- **Environment Reset**: Code execution environment resets when code changes (hash-based detection)
- **Variable Persistence**: Variables maintained between queries within same code context
- **Connection Injection**: DuckDB connections automatically injected as 'conn' variable
- **Security Sandboxing**: Restricted execution environment with limited builtins
- **Error Handling**: Comprehensive error reporting with execution time tracking

#### Database Management Quirks

- **Table Naming**: Automatic table name generation from file paths with sanitization
- **Metadata Tracking**: Creation time, file size, row count, and access patterns stored
- **Smart Updates**: Automatic database recreation when source files are modified
- **User Isolation**: Each user has separate database directory and files
- **Connection Caching**: Persistent connections to avoid repeated file loading

### Frontend Components

#### Web Interface

- **React/Vue.js Application**: Modern single-page application
- **Real-time Updates**: WebSocket support for streaming responses
- **Data Visualization**: Integrated plotting with Plotly.js
- **File Upload**: Drag-and-drop file upload with progress indicators

#### API Integration

- **RESTful Endpoints**: Comprehensive API for all backend services
- **Authentication**: JWT-based authentication with refresh tokens
- **Error Handling**: Client-side error handling and user feedback
- **Caching**: Browser-side caching for improved performance

#### WebSocket Communication

- **Real-Time Updates**: Live progress messages during long-running operations
- **Connection Management**: Automatic reconnection and error recovery
- **User Identification**: Support for both actual user IDs and fallback identifiers
- **Message Types**: Structured messages for progress, completion, and errors
- **Background Processing**: Non-blocking operations with client feedback

## Performance Requirements

### Response Times

- **Query Analysis**: < 2 seconds for LLM response generation
- **Code Execution**: < 30 seconds for typical data analysis tasks
- **Database Creation**: < 60 seconds for files up to 1GB
- **Subsequent Queries**: < 5 seconds for cached database queries

### Scalability

- **Concurrent Users**: Support for 50+ simultaneous users
- **File Size Limits**: Handle files up to 10GB in size
- **Query Complexity**: Support for complex multi-step analyses
- **Memory Usage**: Efficient memory management for large datasets

### Optimization Features

- **Database Caching**: Persistent DuckDB databases with smart invalidation
- **Query Result Caching**: Cache frequently executed queries
- **Lazy Loading**: Load only required data subsets
- **Background Processing**: Asynchronous database creation for large files

## Security Requirements

### Code Execution Security

- **Sandboxing**: Complete isolation of user code execution
- **Permission Control**: Restricted file system and network access
- **Resource Limits**: CPU, memory, and execution time limits
- **Code Analysis**: Static analysis for security vulnerabilities

### Data Security

- **File Access Control**: User-specific file access permissions
- **Database Encryption**: Optional encryption for sensitive data
- **Audit Logging**: Comprehensive logging of all operations
- **Data Sanitization**: Input validation and sanitization

### API Security

- **Authentication**: JWT-based authentication with secure storage
- **Authorization**: Role-based access control
- **Rate Limiting**: Protection against abuse and DoS attacks
- **CORS Configuration**: Proper cross-origin resource sharing setup

## User Experience Requirements

### Interface Design

- **Intuitive Workflow**: Simple file upload → natural language queries → results
- **Progressive Disclosure**: Show complexity only when needed
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Accessibility**: WCAG 2.1 AA compliance

### Workflow Optimization

- **One-Click Setup**: Minimal configuration required
- **Smart Defaults**: Intelligent default settings based on data type
- **Context Preservation**: Maintain analysis context across sessions
- **Export Capabilities**: Export results in multiple formats

## Functional Requirements

### Data Analysis Capabilities

- **Statistical Analysis**: Mean, median, standard deviation, correlations
- **Data Visualization**: Charts, graphs, and interactive plots
- **Filtering & Grouping**: Complex query construction
- **Time Series Analysis**: Date-based analysis and trending
- **Geospatial Analysis**: Location-based data processing

### File Format Support

- **CSV Files**: Standard and custom delimited formats
- **Parquet Files**: Optimized columnar storage
- **JSON Files**: Structured and semi-structured data
- **Excel Files**: Multiple sheets and formatting preservation

### Schema Generation Workflow

- **LLM-Powered Analysis**: Schema descriptions generated using LLM analysis of data samples
- **Context Integration**: Business domain context incorporated into schema generation
- **User Refinement**: Users can modify and enhance generated schemas
- **Persistent Storage**: Schemas stored as JSON files with version tracking
- **Validation**: Schema validation against actual data structure

### Parallel Processing Capabilities

- **Concurrent Operations**: Schema generation and preview caching run simultaneously
- **Resource Optimization**: Efficient use of system resources during parallel processing
- **Progress Synchronization**: Coordinated progress updates across parallel tasks
- **Error Isolation**: Failures in one task don't affect others
- **Result Aggregation**: Combined results from parallel processing stages

### Integration Requirements

- **Google Gemini API**: Primary LLM service with fallback options
- **DuckDB**: High-performance analytical database
- **Plotly**: Interactive data visualization
- **Pandas**: Data manipulation and analysis

## Non-Functional Requirements

### Reliability

- **Uptime**: 99.5% service availability
- **Error Recovery**: Automatic recovery from failures
- **Data Integrity**: Ensure data consistency across operations
- **Backup & Recovery**: Regular backups with quick recovery

### Maintainability

- **Code Quality**: Comprehensive test coverage (>80%)
- **Documentation**: Complete API and user documentation
- **Modular Design**: Clean separation of concerns
- **Version Control**: Proper semantic versioning

### Monitoring & Analytics

- **Performance Monitoring**: Real-time performance metrics
- **Usage Analytics**: User behavior and feature usage tracking
- **Error Tracking**: Comprehensive error logging and alerting
- **Health Checks**: Automated system health monitoring

## Future Enhancements

### Advanced Features

- **Multi-user Collaboration**: Shared workspaces and analysis
- **Custom Model Training**: Fine-tuned models for specific domains
- **Real-time Data Streams**: Support for streaming data sources
- **Advanced Visualizations**: 3D plots and custom chart types

### Scalability Improvements

- **Distributed Processing**: Support for large-scale data processing
- **Cloud Integration**: AWS S3, Google Cloud Storage support
- **Container Orchestration**: Kubernetes deployment support
- **Load Balancing**: Horizontal scaling capabilities

### Enterprise Features

- **Audit Trails**: Complete audit logging for compliance
- **Role-based Access**: Advanced permission management
- **SSO Integration**: Single sign-on support
- **API Rate Limiting**: Advanced rate limiting and quotas

## Success Metrics

### User Adoption

- **User Retention**: >70% monthly active user retention
- **Query Success Rate**: >90% of queries executed successfully
- **Time to Insight**: <5 minutes from file upload to first insight

### Performance Metrics

- **Query Response Time**: <3 seconds average response time
- **Database Creation Time**: <30 seconds for 100MB files
- **Concurrent Users**: Support for 100+ simultaneous users
- **Uptime**: >99.9% service availability

### Business Impact

- **User Productivity**: 50% reduction in time spent on data analysis
- **Error Reduction**: 80% reduction in analysis errors
- **Cost Efficiency**: 60% reduction in infrastructure costs through optimization
