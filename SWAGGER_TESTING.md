# Phase 1 Auth Service - Swagger UI Testing Guide

## Access Swagger Documentation

### Direct Service Port (Recommended)
- **Swagger UI (Interactive)**: http://localhost:8001/docs
- **ReDoc (Read-only)**: http://localhost:8001/redoc
- **OpenAPI Schema**: http://localhost:8001/openapi.json

### Through Traefik Load Balancer
- **Swagger UI**: http://localhost/api/v1/auth/docs
- **ReDoc**: http://localhost/api/v1/auth/redoc

---

## Step-by-Step Swagger Testing

### Step 1: Open Swagger UI
Navigate to **http://localhost:8001/docs** in your browser.

You should see all endpoints organized by tag:
- **auth** - Public authentication endpoints
- **admin** - Admin-only endpoints for user management

---

### Step 2: Test Login Endpoint

1. **Find** the **POST /auth/login** endpoint (under "auth" tag)
2. **Click** "Try it out" button
3. **Enter** the request body:
   ```json
   {
     "email": "admin@educorp.dev",
     "password": "AdminPass123!"
   }
   ```
4. **Click** "Execute"
5. **Expected Response** (200):
   ```json
   {
     "data": {
       "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
       "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
       "token_type": "bearer",
       "expires_in": 900,
       "user": {
         "id": "550e8400-e29b-41d4-a716-446655440000",
         "email": "admin@educorp.dev",
         "roles": ["admin", "instructor", "student"]
       }
     },
     "meta": {
       "correlation_id": "uuid",
       "timestamp": "2026-04-13T10:30:00Z"
     }
   }
   ```

6. **Copy** the entire `access_token` value (it's a long JWT string)

---

### Step 3: Authorize Swagger UI with Token

1. **Click** the green **"Authorize"** button at the top-right
2. **Paste** your token in the dialog:
   - **Value field**: `Bearer <paste_your_access_token_here>`
   - Example: `Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...`
3. **Click** "Authorize"
4. **Click** "Close" to dismiss the dialog

✅ Now all protected endpoints will automatically include your token!

---

### Step 4: Test Protected Endpoints

#### GET /auth/me - Get Current User Profile
1. Find **GET /auth/me** endpoint
2. Click "Try it out"
3. Click "Execute" (no body needed, token is auto-included)
4. Response shows your user profile

#### PATCH /auth/me - Update Profile
1. Find **PATCH /auth/me** endpoint
2. Click "Try it out"
3. Enter request body:
   ```json
   {
     "first_name": "Johnny",
     "last_name": "Admin",
     "avatar_url": "https://example.com/avatar.jpg"
   }
   ```
4. Click "Execute"
5. Verify the response shows updated fields

#### POST /auth/refresh - Rotate Token
1. Find **POST /auth/refresh** endpoint
2. Click "Try it out"
3. Enter the `refresh_token` from your login response:
   ```json
   {
     "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
   }
   ```
4. Click "Execute"
5. You'll get new `access_token` and `refresh_token`
6. Copy the new `access_token` and re-authorize in Swagger

#### GET /admin/users - List All Users
1. Find **GET /admin/users** endpoint
2. Click "Try it out"
3. Set query parameters:
   - `page` = 1
   - `page_size` = 10
   - Leave `role`, `is_active`, `search` empty (optional filters)
4. Click "Execute"
5. See paginated list of all users with their roles

#### PATCH /admin/users/{user_id}/roles - Grant/Revoke Roles
1. Find **PATCH /admin/users/{user_id}/roles** endpoint
2. Click "Try it out"
3. **Replace** `{user_id}` with an actual user UUID from the list users response
4. Enter request body:
   ```json
   {
     "add_roles": ["instructor"],
     "remove_roles": []
   }
   ```
5. Click "Execute"
6. Check response to confirm roles were updated

---

### Step 5: Test Public Endpoints (No Auth)

#### POST /auth/register - Create New User
1. First, **logout** by clicking "Authorize" > "Logout" (optional, but clean)
2. Find **POST /auth/register** endpoint
3. Click "Try it out"
4. Enter request body:
   ```json
   {
     "email": "newuser@example.com",
     "password": "NewPass123!",
     "first_name": "New",
     "last_name": "User"
   }
   ```
5. Click "Execute"
6. Expected response (201):
   ```json
   {
     "data": {
       "id": "new-uuid",
       "email": "newuser@example.com",
       "first_name": "New",
       "last_name": "User",
       "is_active": false,
       "is_verified": false,
       "roles": ["student"],
       "created_at": "2026-04-13T10:30:00Z"
     }
   }
   ```
   Note: `is_active=false` and `is_verified=false` until email is verified

#### POST /auth/forgot-password - Request Password Reset
1. Find **POST /auth/forgot-password** endpoint
2. Click "Try it out"
3. Enter:
   ```json
   {
     "email": "newuser@example.com"
   }
   ```
4. Click "Execute"
5. Response (200):
   ```json
   {
     "data": {
       "message": "If the email exists, a password reset link has been sent"
     }
   }
   ```
   (Generic response for security - doesn't reveal if email exists)

---

## Testing Checklist

Complete the following tests in order:

- [ ] **Login with admin** (get access + refresh tokens)
- [ ] **Authorize Swagger** with access token
- [ ] **Get Profile** (GET /auth/me)
- [ ] **Update Profile** (PATCH /auth/me)
- [ ] **List Users** (GET /admin/users)
- [ ] **Grant Instructor Role** (PATCH /admin/users/{id}/roles)
- [ ] **Register New User** (POST /auth/register without auth)
- [ ] **Request Password Reset** (POST /auth/forgot-password)
- [ ] **Refresh Token** (POST /auth/refresh)

---

## Common Issues & Solutions

### "Token not provided" or 401 Unauthorized
- Check that you've clicked "Authorize" and pasted the token correctly
- Make sure token starts with `Bearer ` in the authorize dialog
- Token expires in 15 minutes - get a new one with refresh endpoint

### "FORBIDDEN" or 403 Error
- This endpoint requires admin role
- Make sure you're logged in as admin user
- Check your user's roles in GET /auth/me response

### "Validation Error" (422)
- Check request body JSON syntax
- Verify email format is valid
- Password must have uppercase, lowercase, digit, and be 8+ chars

### "Email Verification Pending" (401)
- New users can't login until email is verified
- Extract verification token from database:
  ```sql
  SELECT token_hash FROM auth.email_verifications 
  WHERE user_id = (SELECT id FROM auth.users WHERE email = 'newuser@example.com')
  LIMIT 1;
  ```
- Use that token in POST /auth/verify-email

---

## Response Format Reference

All successful responses follow this format:
```json
{
  "data": { ... },
  "meta": {
    "correlation_id": "uuid-string",
    "timestamp": "2026-04-13T10:30:00Z"
  }
}
```

All error responses:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { ... },
    "correlation_id": "uuid-string",
    "timestamp": "2026-04-13T10:30:00Z"
  }
}
```

Common error codes:
- `UNAUTHORIZED` (401) - Invalid/expired token
- `FORBIDDEN` (403) - Insufficient permissions
- `VALIDATION_ERROR` (422) - Bad request body
- `CONFLICT` (409) - Duplicate email
- `RESOURCE_NOT_FOUND` (404) - User not found

---

## Pro Tips

1. **Keep multiple tabs open** - One for Swagger docs reference, one for testing
2. **Read response examples** - Each endpoint shows example requestbody and response in the schema
3. **Use query params** - For GET endpoints, scroll down to see optional filters
4. **Check status codes** - 201 = created, 200 = ok, 4xx = client error, 5xx = server error
5. **Review correlation_id** - Useful for debugging logs across services

Happy testing! 🚀
