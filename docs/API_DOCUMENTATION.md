# A4AI Backend API Documentation

## Table of Contents
- [Authentication](#authentication)
- [Assessment APIs](#assessment-apis)
- [Activities APIs](#activities-apis)  
- [Visual Aids APIs](#visual-aids-apis)
- [Planning APIs](#planning-apis)
- [Personalization APIs](#personalization-apis)
- [Voice Assistant APIs](#voice-assistant-apis)
- [Teacher Dashboard APIs](#teacher-dashboard-apis)
- [Orchestrator APIs](#orchestrator-apis)
- [Education APIs](#education-apis)
- [Error Handling](#error-handling)
- [Authentication Guide](#authentication-guide)

---

## Authentication

All API endpoints (except authentication endpoints) require a Firebase JWT token in the Authorization header:

```
Authorization: Bearer YOUR_FIREBASE_JWT_TOKEN
```

### Base URL
```
http://localhost:8000/api/v1
```

---

## Authentication APIs

### POST /auth/login
**Description:** Authenticate user with email and password

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Login successful",
  "user_data": {
    "uid": "user_id",
    "email": "user@example.com",
    "display_name": "User Name",
    "email_verified": true,
    "custom_claims": {},
    "last_login": "2025-07-22T00:00:00"
  },
  "tokens": {
    "id_token": "jwt_token_here",
    "refresh_token": "refresh_token_here",
    "expires_in": "3600"
  }
}
```

### POST /auth/signup
**Description:** Create a new user account

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123",
  "display_name": "New User",
  "role": "student"
}
```

**Response:** Same as login response

### POST /auth/refresh-token
**Description:** Refresh expired authentication token

**Request Body:**
```json
{
  "refresh_token": "your_refresh_token"
}
```

### POST /auth/reset-password
**Description:** Send password reset email

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

### GET /auth/verify-token
**Description:** Verify the validity of an authentication token
**Headers:** `Authorization: Bearer YOUR_TOKEN`

### GET /auth/health
**Description:** Authentication service health check

---

## Assessment APIs

### POST /assessment/quiz
**Description:** Generate AI-powered quiz questions
**Authentication:** Required

**Request Body:**
```json
{
  "grade": 10,
  "topic": "Mathematics",
  "language": "English",
  "difficulty": "medium",
  "num_questions": 10,
  "question_types": ["multiple_choice", "short_answer"]
}
```

**Response:**
```json
{
  "status": "success",
  "quiz_data": {
    "quiz_id": "unique_quiz_id",
    "questions": [
      {
        "id": 1,
        "question": "What is 2 + 2?",
        "type": "multiple_choice",
        "options": ["3", "4", "5", "6"],
        "correct_answer": "4"
      }
    ],
    "topic": "Mathematics",
    "grade": 10,
    "difficulty": "medium",
    "estimated_time": 20
  }
}
```

### POST /assessment/score
**Description:** Score open-ended answers using AI
**Authentication:** Not required

**Request Body:**
```json
{
  "question": "Explain photosynthesis",
  "answer": "Student's answer here",
  "grade_level": 8
}
```

### POST /assessment/performance
**Description:** Update user performance statistics
**Authentication:** Required

**Request Body:**
```json
{
  "correct_count": 8,
  "total_questions": 10,
  "topic": "Mathematics",
  "quiz_id": "quiz_123"
}
```

### GET /assessment/recommendations
**Description:** Get personalized learning recommendations
**Authentication:** Required

---

## Activities APIs

### POST /activities/interactive-story
**Description:** Generate interactive educational stories
**Authentication:** Required

**Request Body:**
```json
{
  "topic": "Space Exploration",
  "grade_level": 5,
  "learning_objective": "Understanding planets",
  "story_length": "short",
  "interactive_elements": ["quiz", "decision_points"]
}
```

**Response:**
```json
{
  "story_data": {
    "title": "Journey to Mars",
    "content": "Story content here...",
    "interactive_elements": [
      {
        "type": "decision_point",
        "question": "Which path should you take?",
        "options": ["Left path", "Right path"]
      }
    ],
    "quiz_questions": [...]
  }
}
```

### POST /activities/ar-scene
**Description:** Generate AR/VR scene descriptions
**Authentication:** Required

**Request Body:**
```json
{
  "topic": "Ancient Egypt",
  "grade_level": 6,
  "scene_type": "historical_recreation",
  "complexity": "detailed"
}
```

### POST /activities/assign-badge
**Description:** Assign achievement badges to users
**Authentication:** Required

**Request Body:**
```json
{
  "user_id": "target_user_id",
  "badge_type": "math_master",
  "achievement_description": "Completed 10 math quizzes",
  "points_awarded": 100
}
```

### GET /activities/badges/{user_id}
**Description:** Get badges for a specific user
**Authentication:** Required

### GET /activities/my-badges
**Description:** Get badges for current authenticated user
**Authentication:** Required

### GET /activities/user/{user_id}
**Description:** Get activity summary for a user
**Authentication:** Required

---

## Visual Aids APIs

### POST /visual-aids/generate
**Description:** Generate educational visual content
**Authentication:** Required

**Request Body:**
```json
{
  "topic": "Solar System",
  "grade_level": 7,
  "visual_type": "infographic",
  "style": "colorful",
  "complexity": "intermediate"
}
```

**Response:**
```json
{
  "visual_aid": {
    "id": "visual_123",
    "topic": "Solar System",
    "url": "https://storage.googleapis.com/visual_123.png",
    "description": "Visual description",
    "grade_level": 7,
    "created_at": "2025-07-22T00:00:00"
  }
}
```

### POST /visual-aids/infographic
**Description:** Generate educational infographics
**Authentication:** Required

**Request Body:**
```json
{
  "topic": "Water Cycle",
  "grade_level": 4,
  "sections": ["Evaporation", "Condensation", "Precipitation"],
  "style": "cartoon"
}
```

### GET /visual-aids/search
**Description:** Search visual aids by topic
**Authentication:** Required
**Query Parameters:**
- `topic` (required): Topic to search for
- `asset_type` (optional): Filter by asset type
- `grade_level` (optional): Filter by grade level (1-12)
- `limit` (optional): Maximum results (default: 20, max: 100)

### GET /visual-aids/my-visual-aids
**Description:** Get visual aids for current user
**Authentication:** Required
**Query Parameters:**
- `limit` (optional): Maximum results (default: 10, max: 100)
- `asset_type` (optional): Filter by asset type

### DELETE /visual-aids/{visual_aid_id}
**Description:** Delete a visual aid
**Authentication:** Required

### GET /visual-aids/categories
**Description:** Get available visual aid categories
**Authentication:** Required

### GET /visual-aids/stats/{user_id}
**Description:** Get visual aid statistics for a user
**Authentication:** Required

---

## Planning APIs

### POST /planning/lesson-plan
**Description:** Generate comprehensive lesson plans
**Authentication:** Required

**Request Body:**
```json
{
  "class_id": "class_123",
  "topic": "Fractions",
  "grade_level": 4,
  "plan_type": "daily",
  "duration": 45,
  "learning_objectives": ["Understand fraction basics", "Compare fractions"],
  "curriculum_standards": ["4.NF.A.1", "4.NF.A.2"],
  "include_assessment": true
}
```

**Response:**
```json
{
  "lesson_plan": {
    "id": "plan_123",
    "title": "Introduction to Fractions",
    "class_id": "class_123",
    "topic": "Fractions",
    "grade_level": 4,
    "duration": 45,
    "learning_objectives": [...],
    "materials": ["Fraction manipulatives", "Whiteboard"],
    "activities": [
      {
        "name": "Warm-up",
        "duration": 10,
        "description": "Review previous concepts"
      }
    ],
    "assessment": {...},
    "homework": {...}
  }
}
```

### GET /planning/class/{class_id}/plans
**Description:** Get lesson plan history for a class
**Authentication:** Required
**Query Parameters:**
- `limit` (optional): Maximum results (default: 10, max: 100)
- `plan_type` (optional): Filter by plan type

### GET /planning/my-plans
**Description:** Get lesson plans for current user
**Authentication:** Required

### PUT /planning/lesson-plan/{plan_id}
**Description:** Update a lesson plan
**Authentication:** Required

### DELETE /planning/lesson-plan/{plan_id}
**Description:** Delete a lesson plan
**Authentication:** Required

### GET /planning/templates
**Description:** Get lesson plan templates
**Authentication:** Required

### GET /planning/subjects
**Description:** Get available subjects
**Authentication:** Required

### GET /planning/plan-types
**Description:** Get available plan types
**Authentication:** Required

---

## Personalization APIs

### GET /personalization/dashboard
**Description:** Get personalized student dashboard
**Authentication:** Required

**Response:**
```json
{
  "status": "success",
  "message": "Dashboard generated successfully",
  "data": {
    "recommendations": [
      {
        "type": "practice",
        "topic": "Algebra",
        "difficulty": "medium",
        "reason": "Based on recent performance"
      }
    ],
    "progress": {
      "completed_lessons": 15,
      "total_points": 1250,
      "current_streak": 7
    },
    "next_activities": [...]
  },
  "metadata": {
    "user_id": "user_123",
    "generated_at": "2025-07-22T00:00:00"
  }
}
```

### GET /personalization/recommendations
**Description:** Get existing personalized recommendations
**Authentication:** Required

### POST /personalization/teacher-summary
**Description:** Get AI-powered class performance summary
**Authentication:** Required

**Request Body:**
```json
{
  "class_id": "class_123"
}
```

### GET /personalization/health
**Description:** Personalization service health check

---

## Voice Assistant APIs

### POST /voice/text-chat
**Description:** Send text message to voice assistant
**Authentication:** Required

**Request Body:**
```json
{
  "user_id": "user_123",
  "message": "Help me with algebra equations",
  "session_id": "session_456",
  "generate_audio": false,
  "context": {
    "current_subject": "mathematics",
    "grade_level": 9
  }
}
```

**Response:**
```json
{
  "response": {
    "text": "I'd be happy to help you with algebra equations! What specific type of equation are you working on?",
    "audio_url": null,
    "session_id": "session_456",
    "follow_up_questions": [
      "Are you working on linear equations?",
      "Do you need help with quadratic equations?"
    ]
  }
}
```

### POST /voice/audio
**Description:** Send audio file for processing
**Authentication:** Required
**Content-Type:** `multipart/form-data`

**Form Data:**
- `audio_file`: Audio file (WAV, MP3, etc.)
- `user_id`: User identifier
- `session_id` (optional): Session ID
- `language` (optional): Language code (default: "en")

### GET /voice/sessions/{user_id}
**Description:** Get conversation history for a user
**Authentication:** Required

### POST /voice/analyze-file
**Description:** Analyze uploaded educational content
**Authentication:** Required

### GET /voice/download-audio/{audio_id}
**Description:** Download generated audio file
**Authentication:** Required

---

## Teacher Dashboard APIs

### GET /teacher-dashboard/dashboard
**Description:** Get complete teacher dashboard
**Authentication:** Required (Teacher role)
**Query Parameters:**
- `class_id` (optional): Filter by specific class
- `days` (optional): Analysis period in days (default: 30, max: 365)

**Response:**
```json
{
  "status": "success",
  "data": {
    "class_summary": {
      "total_students": 25,
      "active_students": 23,
      "average_performance": 82.5
    },
    "performance_trends": [...],
    "recent_activities": [...],
    "alerts": [
      {
        "type": "low_performance",
        "student": "John Doe",
        "subject": "Mathematics"
      }
    ]
  }
}
```

### GET /teacher-dashboard/class-analytics
**Description:** Get class analytics summary
**Authentication:** Required (Teacher role)

### POST /teacher-dashboard/student-history
**Description:** Get detailed student history
**Authentication:** Required (Teacher role)

**Request Body:**
```json
{
  "student_id": "student_123",
  "time_range": "30_days"
}
```

### GET /teacher-dashboard/classes
**Description:** Get teacher's class list
**Authentication:** Required (Teacher role)

---

## Orchestrator APIs

### GET /agentic/pipeline/status
**Description:** Get orchestration pipeline status
**Authentication:** Required

**Response:**
```json
{
  "status": "operational",
  "agents": {
    "planner": "available",
    "content": "available",
    "assessment": "available",
    "visual_aid": "available"
  },
  "pipeline_version": "3.0.0",
  "adk_integration": true,
  "orchestration_ready": true,
  "endpoints": [
    "/agentic/orchestrate",
    "/agentic/lesson/complete",
    "/agentic/lesson/plan-only"
  ],
  "last_check": "2025-07-22T00:00:00"
}
```

### POST /agentic/orchestrate
**Description:** Legacy orchestration endpoint
**Authentication:** Required

**Request Body:**
```json
{
  "topic": "Mathematics",
  "grade_level": "elementary",
  "duration": 60
}
```

### POST /agentic/lesson/complete
**Description:** Create a complete lesson with all components
**Authentication:** Required

**Request Body:**
```json
{
  "teacher_id": "teacher_123",
  "class_id": "class_456",
  "topic": "Fractions",
  "grade_level": "elementary",
  "duration": 60,
  "lesson_type": "complete",
  "include_visual_aids": true,
  "assessment_required": true
}
```

---

## Education APIs

### POST /education/activities
**Description:** Generate educational activities
**Authentication:** Required

**Request Body:**
```json
{
  "topic": "Photosynthesis",
  "grade_level": 6,
  "activity_type": "hands_on",
  "duration": 30,
  "learning_objectives": ["Understand plant processes"]
}
```

### POST /education/visual-aids
**Description:** Generate visual learning materials
**Authentication:** Required

### POST /education/lesson-plans
**Description:** Generate comprehensive lesson plans
**Authentication:** Required

### GET /education/templates
**Description:** Get educational templates
**Authentication:** Required

### GET /education/health
**Description:** Education service health check

---

## Error Handling

### Standard Error Response Format
```json
{
  "status": "error",
  "message": "Descriptive error message",
  "status_code": 400,
  "path": "/api/v1/endpoint",
  "method": "POST",
  "timestamp": "2025-07-22T00:00:00"
}
```

### Common HTTP Status Codes
- **200 OK**: Request successful
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required or invalid token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Endpoint or resource not found
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server error

### Authentication Errors
```json
{
  "status": "error",
  "message": "User not authenticated",
  "status_code": 401
}
```

---

## Authentication Guide

### Step 1: Login/Register
```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password'
  })
});

const { tokens } = await loginResponse.json();
const authToken = tokens.id_token;
```

### Step 2: Use Token in API Calls
```javascript
// Example API call with authentication
const response = await fetch('http://localhost:8000/api/v1/assessment/quiz', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    grade: 10,
    topic: 'Mathematics',
    language: 'English'
  })
});
```

### Step 3: Handle Token Expiration
```javascript
// Refresh token when needed
const refreshResponse = await fetch('http://localhost:8000/api/v1/auth/refresh-token', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    refresh_token: refreshToken
  })
});
```

---

## Testing Endpoints

You can test these endpoints using:
1. **Postman**: Import the provided collection
2. **PowerShell**: Use the `test_apis_extended.ps1` script
3. **cURL**: Command-line testing
4. **Frontend**: Direct API integration

### Example PowerShell Test
```powershell
# Get auth token
$loginResp = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Headers @{"Content-Type" = "application/json"} -Body '{"email": "test@example.com", "password": "password"}'
$token = ($loginResp.Content | ConvertFrom-Json).tokens.id_token

# Test API endpoint
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/assessment/quiz" -Method POST -Headers @{"Authorization" = "Bearer $token"; "Content-Type" = "application/json"} -Body '{"grade": 10, "topic": "Mathematics", "language": "English"}'
```

---

## Notes for Frontend Integration

1. **Token Management**: Store JWT tokens securely and implement automatic refresh
2. **Error Handling**: Implement proper error handling for all API responses
3. **Loading States**: Show loading indicators during API calls
4. **Validation**: Validate form data before sending to API
5. **Rate Limiting**: Implement client-side rate limiting if needed
6. **CORS**: API is configured to accept requests from all origins in development
7. **File Uploads**: Use FormData for file upload endpoints
8. **Real-time**: Consider WebSocket connections for real-time features

---

*Last Updated: July 22, 2025*
*API Version: 1.0.0*
