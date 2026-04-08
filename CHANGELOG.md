# Changelog

All notable changes to the StockPilot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

### Added

- **Authentication System**
  - JWT-based authentication with access token support
  - Secure password hashing using bcrypt
  - Login and registration endpoints
  - Token refresh functionality
  - Protected route middleware for authenticated endpoints

- **Role-Based Access Control (RBAC)**
  - Three-tier role system: Admin, Manager, and Viewer
  - Permission-based endpoint protection via dependency injection
  - Role assignment and management by administrators
  - Granular access control for inventory operations

- **Inventory CRUD Operations**
  - Full create, read, update, and delete functionality for inventory items
  - Pagination and filtering support for inventory listings
  - Search functionality across item names and descriptions
  - Stock level tracking with low-stock threshold alerts
  - Bulk operations support for inventory management

- **Category Management**
  - Hierarchical category system for organizing inventory items
  - Create, read, update, and delete categories
  - Category-based filtering for inventory queries
  - Validation to prevent deletion of categories with associated items

- **User Management**
  - Admin-level user administration panel
  - User profile viewing and editing
  - Role assignment and modification
  - Account activation and deactivation
  - User listing with search and filter capabilities

- **Admin Dashboard**
  - Overview statistics for total inventory, categories, and users
  - Low-stock item alerts and notifications
  - Recent activity feed
  - Summary metrics and key performance indicators

- **Responsive UI**
  - Mobile-first responsive design using Tailwind CSS
  - Adaptive navigation with collapsible sidebar
  - Touch-friendly interface elements
  - Consistent design system across all screen sizes

- **Avatar System**
  - User avatar upload and management
  - Default avatar generation based on user initials
  - Avatar display across the application UI
  - Support for common image formats (JPEG, PNG, WebP)

- **Database Seeding**
  - Seed script for populating the database with sample data
  - Default admin account creation on first run
  - Sample categories and inventory items for demonstration
  - Idempotent seeding to prevent duplicate data

- **Vercel Deployment Support**
  - Vercel-compatible project configuration
  - Environment variable management for production
  - Optimized build settings for serverless deployment
  - CORS configuration for cross-origin frontend access