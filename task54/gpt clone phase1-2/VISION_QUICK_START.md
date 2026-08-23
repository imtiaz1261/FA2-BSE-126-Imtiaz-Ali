# Image Understanding (Vision) Module - Quick Start

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd backend
pip install boto3 pillow openai anthropic
```

### 2. Configure Environment

Add to `.env`:
```bash
# S3 (AWS, MinIO, DigitalOcean Spaces, etc.)
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=chatline-images
S3_REGION=us-east-1

# Vision LLM (choose one)
VISION_API_KEY=sk-...  # For OpenAI
# OR
VISION_API_KEY=claude-api-key  # For Anthropic

# Model selection
VISION_MODEL=gpt-4-vision-preview  # OpenAI
# OR
VISION_MODEL=claude-3-vision-sonnet  # Anthropic

# Optional
MAX_IMAGE_SIZE_MB=10
IMAGE_UPLOAD_EXPIRY_HOURS=24
```

### 3. Run Migration

```bash
cd backend
alembic upgrade head
```

This creates:
- `vision_images` table
- `vision_requests` table

### 4. Start Backend

```bash
uvicorn app.main:app --reload
```

Vision endpoints now available:
- `POST /chat/vision/upload`
- `POST /chat/vision/qa`
- `POST /chat/vision/extract`

### 5. Use in Frontend

```tsx
import { ImageComposer } from "@/components/ImageComposer";
import { visionQA, visionExtract } from "@/lib/visionApi";

export function ChatInput() {
  const [images, setImages] = useState([]);
  const [mode, setMode] = useState("qa");

  return (
    <div>
      <ImageComposer
        conversationId={conversationId}
        mode={mode}
        onModeChange={setMode}
        onImagesReady={setImages}
      />

      {mode === "qa" && (
        <input
          placeholder="Ask about the image..."
          onSubmit={(q) => visionQA(
            images.map(i => i.image_id),
            q,
            conversationId
          )}
        />
      )}

      {mode === "extract" && (
        <button onClick={() => visionExtract(
          images.map(i => i.image_id),
          "receipt",
          null,
          conversationId
        )}>
          Extract Data
        </button>
      )}
    </div>
  );
}
```

---

## File Upload Flow

1. **ImageComposer** - Three input methods
   - Drag-and-drop onto drop zone
   - Click to open file picker
   - Paste from clipboard (Cmd/Ctrl+V)

2. **Validation** (Frontend + Backend)
   - Format: JPEG, PNG, WebP, GIF only
   - Size: Max 10MB per image
   - Per-image error display

3. **Upload Process**
   - POST /chat/vision/upload
   - Returns signed URLs (24-hour validity)
   - Thumbnails displayed with progress

4. **Storage**
   - Files stored in S3 with user scoping: `/users/{user_id}/{uuid}_{filename}`
   - Database tracks image metadata
   - Signed URLs prevent public access

---

## Vision Q&A

**Ask questions about images:**

```bash
curl -X POST http://localhost:8000/chat/vision/qa \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_ids": ["uuid1", "uuid2"],
    "question": "What are in these images?",
    "conversation_id": "conv-uuid"
  }'
```

**Response:**
```json
{
  "request_id": "uuid",
  "answer": "The images show...",
  "images_processed": ["uuid1", "uuid2"],
  "created_at": "2024-08-14T10:00:00Z"
}
```

---

## Structured Extraction

**Extract data from images:**

```bash
curl -X POST http://localhost:8000/chat/vision/extract \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_ids": ["receipt-uuid"],
    "extraction_type": "receipt"
  }'
```

**Supported Types:**
- `receipt` - Items, subtotal, tax, total, date, merchant
- `form` - Form fields and values
- `table` - Table headers and rows
- `custom` - Define your own schema

**Response:**
```json
{
  "request_id": "uuid",
  "extraction_type": "receipt",
  "data": {
    "items": [
      {"name": "Item 1", "quantity": 1, "unit_price": 10.00, "total": 10.00}
    ],
    "subtotal": 10.00,
    "tax": 0.80,
    "total": 10.80,
    "date": "2024-08-14",
    "merchant": "Store Name"
  },
  "images_processed": ["uuid"],
  "created_at": "2024-08-14T10:00:00Z"
}
```

---

## Component Usage

### ImageComposer
```tsx
<ImageComposer
  conversationId="conv-id"           // Optional
  mode="qa"                          // or "extract"
  onModeChange={(mode) => {...}}     // Mode toggle
  onImagesReady={(images) => {...}}  // Called when upload complete
/>
```

### visionApi Functions
```typescript
// Upload images
uploadImages(files, conversationId, onProgress);

// Q&A
visionQA(imageIds, question, conversationId);

// Extraction
visionExtract(imageIds, type, customSchema, conversationId);

// Status
getVisionStatus(requestId);

// Delete
deleteImage(imageId);

// Utilities
validateImageFile(file);
formatFileSize(bytes);
imageToBase64(file);
getImageDimensions(file);
```

---

## Configuration Options

### Image Size
```python
# config.py
max_image_size_mb: int = 10  # Change to 20, 50, etc.
```

### URL Expiry
```python
# config.py
image_upload_expiry_hours: int = 24  # Change to 48, 72, etc.
```

### LLM Model
```python
# config.py (use OpenAI)
vision_model: str = "gpt-4-vision-preview"

# OR (use Anthropic)
vision_model: str = "claude-3-vision-sonnet"
```

---

## Common Issues

### "Unsupported format"
- Only JPEG, PNG, WebP, GIF supported
- Check file extension
- Try different format

### "File too large"
- Max 10MB per image (configurable)
- Compress image before upload
- Change MAX_IMAGE_SIZE_MB in config

### "S3 upload failed"
- Verify S3 credentials in .env
- Ensure bucket exists
- Check region is correct
- Test with AWS CLI first

### "Vision API error"
- Check API key is valid
- Verify API has credits/quota
- Check model name is correct
- Look at backend logs for details

---

## Testing

### Test Upload
```bash
curl -X POST http://localhost:8000/chat/vision/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "files=@image.jpg" \
  -F "conversation_id=conv-uuid"
```

### Test Q&A
```bash
# After getting image_id from upload
curl -X POST http://localhost:8000/chat/vision/qa \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_ids": ["image-uuid"],
    "question": "What do you see?"
  }'
```

### Test Extraction
```bash
curl -X POST http://localhost:8000/chat/vision/extract \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "image_ids": ["image-uuid"],
    "extraction_type": "receipt"
  }'
```

---

## Next Steps

1. **Configure S3**
   - AWS S3, MinIO, DigitalOcean Spaces, etc.
   - Create bucket and get credentials

2. **Get Vision API Key**
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com

3. **Integrate with Chat**
   - Add ImageComposer to your chat input
   - Connect Q&A and extract buttons
   - Display results in conversation

4. **Test End-to-End**
   - Upload image via UI
   - Ask question
   - See LLM response
   - Try extraction mode

5. **Deploy to Production**
   - Use managed S3 (AWS, DigitalOcean, etc.)
   - Configure production S3 credentials
   - Set appropriate file size limits
   - Monitor API costs

---

## Architecture

```
Browser → ImageComposer (drag-drop, paste, picker)
  ↓
visionApi.ts (HTTP client)
  ↓
FastAPI backend (/chat/vision/upload, /qa, /extract)
  ↓
S3 Storage (AWS/MinIO) ← images stored with user scoping
  ↓
Vision LLM (OpenAI GPT-4V or Anthropic Claude 3 Vision)
  ↓
Database (vision_images, vision_requests tables)
  ↓
Response → Browser (answer or extracted JSON)
```

---

## Performance Expectations

| Operation | Time |
|-----------|------|
| Image upload | 2-5 seconds |
| Vision Q&A | 5-15 seconds |
| Extraction | 8-20 seconds |
| Signed URL gen | <100ms |

Actual times depend on:
- File size (larger = slower upload)
- LLM response time (varies by model)
- Network latency
- Image complexity

---

## Design System Compliance

All components use Module 1 design tokens:
- Colors: accent, ink, canvas, danger, success
- Spacing: consistent padding/gaps
- Typography: body, meta, font weights
- Dark mode: fully supported
- Accessibility: keyboard nav, ARIA labels

---

## Support & Reference

- **Full Docs:** VISION_MODULE_COMPLETE.md
- **API Reference:** backend/app/routers/vision.py
- **Client Reference:** frontend/src/lib/visionApi.ts
- **Component Docs:** frontend/src/components/ImageComposer.tsx

---

Ready to understand images! 🚀

*Start by uploading an image and asking a question!*
