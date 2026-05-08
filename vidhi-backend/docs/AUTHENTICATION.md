# Authentication Guide - VIDHI API

## Overview

VIDHI API uses JWT (JSON Web Tokens) for authentication with support for multiple user types and guest access.

## Authentication Methods

### 1. JWT Token Authentication (Registered Users)
- **Use case**: Registered users (individuals, lawyers, organizations)
- **Token type**: Bearer token
- **Expiration**: 24 hours
- **Header**: `Authorization: Bearer <token>`

### 2. API Key Authentication (Service-to-Service)
- **Use case**: Backend services, integrations
- **Header**: `X-API-Key: <api_key>`
- **No expiration**: Keys are valid until revoked

### 3. Guest Access (Anonymous Users)
- **Use case**: First-time users, demos
- **Limitations**: Rate-limited, limited features
- **Endpoints**: Only `/chat`, `/emergency`, and document education endpoints

---

## User Types

| Type | Description | Access Level |
|------|-------------|--------------|
| **individual** | Regular citizen | Full access to legal assistance |
| **lawyer** | Legal professional | Full access + professional features |
| **organization** | NGO, legal aid org | Full access + organization features |
| **guest** | Anonymous user | Limited access, rate-limited |

---

## API Endpoints

### Register New User

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "user_id": "user@example.com",
  "password": "secure_password_123",
  "email": "user@example.com",
  "phone": "+91-9876543210",
  "name": "John Doe",
  "user_type": "individual"
}
```

**Response:**
```json
{
  "user_id": "user@example.com",
  "email": "user@example.com",
  "phone": "+91-9876543210",
  "name": "John Doe",
  "user_type": "individual",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "user_id": "user@example.com",
  "password": "secure_password_123"
}
```

**Response:**
```json
{
  "user_id": "user@example.com",
  "email": "user@example.com",
  "name": "John Doe",
  "user_type": "individual",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Guest Access

```http
POST /api/v1/auth/guest
Content-Type: application/json

{
  "session_id": "browser_session_123"
}
```

**Response:**
```json
{
  "session_id": "browser_session_123",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "message": "Guest access granted. Register for full features."
}
```

### Get Current User Info

```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "user@example.com",
  "email": "user@example.com",
  "phone": "+91-9876543210",
  "name": "John Doe",
  "user_type": "individual",
  "created_at": "2026-05-06T10:30:00",
  "is_active": true
}
```

### Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Logged out successfully",
  "hint": "Please discard your access token on the client side"
}
```

---

## Using Authentication

### Protected Endpoints

Most endpoints require authentication. Include the JWT token in the Authorization header:

```bash
curl -X POST http://localhost:8000/api/v1/documents/draft \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"document_type": "rental_agreement", ...}'
```

### Guest-Allowed Endpoints

These endpoints work without authentication but with limited features:

- `/chat` - Basic chat functionality
- `/emergency` - Emergency legal rights
- `/api/v1/documents/simplify` - Document simplification
- `/api/v1/documents/explain-clause` - Clause explanation
- `/api/v1/documents/define-term` - Term definition

```bash
# Works without authentication (as guest)
curl -X POST http://localhost:8000/chat \
  -F "text=What are my rights during arrest?" \
  -F "language=hindi"
```

### Public Endpoints

These endpoints don't require authentication:

- `/` - Health check
- `/health` - Detailed health check
- `/languages` - Supported languages
- `/docs` - API documentation
- `/api/v1/auth/*` - Authentication endpoints

---

## Frontend Integration

### React/TypeScript Example

```typescript
// Store token after login
const login = async (userId: string, password: string) => {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, password })
  });
  
  const data = await response.json();
  
  // Store token in localStorage
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('user_info', JSON.stringify(data));
  
  return data;
};

// Use token in API calls
const chatWithAuth = async (message: string) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('/chat', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return response.json();
};

// Logout
const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_info');
};
```

---

## Security Best Practices

### For Developers

1. **Never commit secrets**
   - Keep `JWT_SECRET_KEY` in `.env` file
   - Use strong, random secret keys in production
   - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

2. **Use HTTPS in production**
   - JWT tokens should only be transmitted over HTTPS
   - Set `secure` flag on cookies if using cookie-based auth

3. **Implement token refresh**
   - Current tokens expire after 24 hours
   - Implement refresh token mechanism for better UX

4. **Rate limiting**
   - Guest users have stricter rate limits
   - Implement per-user rate limiting (next improvement)

5. **Password security**
   - Passwords are hashed with SHA-256 + salt
   - Consider upgrading to bcrypt or Argon2 for production

### For Users

1. **Use strong passwords**
   - Minimum 8 characters
   - Mix of letters, numbers, symbols

2. **Keep tokens secure**
   - Don't share your access token
   - Logout when done on shared devices

3. **Register for full features**
   - Guest access is limited
   - Registration unlocks all features

---

## API Key Management

### Generate API Key

```python
from services.auth_service import generate_api_key

api_key = generate_api_key()
print(f"New API key: {api_key}")
# Output: vidhi_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Add to Environment

```bash
# .env file
API_KEYS=vidhi_key1,vidhi_key2,vidhi_key3
```

### Use API Key

```bash
curl -X POST http://localhost:8000/api/v1/documents/draft \
  -H "X-API-Key: vidhi_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{"document_type": "rental_agreement", ...}'
```

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Invalid or missing authentication credentials",
  "error": "unauthorized",
  "hint": "Please provide valid authentication credentials (JWT token or API key)"
}
```

**Causes:**
- Missing Authorization header
- Invalid or expired token
- Invalid API key

**Solution:**
- Login again to get a new token
- Check that token is included in Authorization header
- Verify API key is correct

### 403 Forbidden

```json
{
  "detail": "Insufficient permissions",
  "error": "forbidden"
}
```

**Causes:**
- User type doesn't have access to this endpoint
- Guest user trying to access protected feature

**Solution:**
- Register for full access
- Contact admin for permission upgrade

---

## Testing Authentication

### Run Tests

```bash
cd vidhi-backend
pytest tests/test_auth.py -v
```

### Manual Testing

```bash
# 1. Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test@example.com",
    "password": "test123",
    "email": "test@example.com",
    "name": "Test User"
  }'

# 2. Save the access_token from response

# 3. Use token to access protected endpoint
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <paste_token_here>"

# 4. Try without token (should fail)
curl -X GET http://localhost:8000/api/v1/auth/me
```

---

## Migration from Unauthenticated

If you have existing code that doesn't use authentication:

### Before (No Auth)
```python
response = requests.post('http://localhost:8000/chat', 
    data={'text': 'Hello'})
```

### After (With Auth)
```python
# Option 1: Use guest token
guest_response = requests.post('http://localhost:8000/api/v1/auth/guest',
    json={'session_id': 'my_session'})
token = guest_response.json()['access_token']

# Option 2: Or just use without token (guest mode)
response = requests.post('http://localhost:8000/chat',
    data={'text': 'Hello'})  # Still works!
```

**Note:** Guest-allowed endpoints still work without authentication, but you'll be rate-limited.

---

## Troubleshooting

### "Invalid or missing authentication credentials"

**Check:**
1. Is Authorization header included?
2. Is token format correct? `Bearer <token>`
3. Has token expired? (24 hour expiration)
4. Is JWT_SECRET_KEY same as when token was created?

### "User already exists"

**Solution:**
- Use `/api/v1/auth/login` instead of `/register`
- Or use a different user_id

### "Invalid credentials"

**Check:**
1. Is user_id correct?
2. Is password correct?
3. Is user account active?

---

## Next Steps

After implementing authentication, consider:

1. **Rate Limiting** (Next priority #4)
   - Limit requests per user/guest
   - Prevent API abuse

2. **Database Integration**
   - Replace in-memory user store with DynamoDB
   - Persist users across restarts

3. **OAuth Integration**
   - Add Google/Facebook login
   - Aadhaar authentication

4. **Token Refresh**
   - Implement refresh tokens
   - Better UX for long sessions

5. **Password Reset**
   - Email-based password reset
   - SMS-based OTP
