# Image Understanding (Vision) Module

Welcome to the production-ready Image Understanding module for your AI chat application. This enables multimodal LLM capabilities for image Q&A and structured data extraction.

## 📚 Documentation

- **[VISION_QUICK_START.md](./VISION_QUICK_START.md)** - 5-minute setup guide
- **[VISION_MODULE_COMPLETE.md](./VISION_MODULE_COMPLETE.md)** - Comprehensive reference

## 🎯 What You Get

### Backend
✅ S3 storage with signed URLs (user-scoped)  
✅ Multimodal LLM integration (GPT-4V or Claude 3 Vision)  
✅ Image upload with validation (format, size)  
✅ Vision Q&A endpoint  
✅ Structured data extraction  
✅ Full authentication and error handling  

### Frontend
✅ Three input methods: drag-drop, file picker, paste  
✅ Image preview thumbnails with remove buttons  
✅ Upload progress bars  
✅ Per-image error display  
✅ Mode toggle (Q&A ↔ Extract)  
✅ Module 1 design token compliance  

---

## 🚀 Quick Start (5 minutes)

### 1. Install
```bash
pip install boto3 pillow openai anthropic
```

### 2. Configure `.env`
```bash
# S3
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=chatline-images

# Vision LLM
VISION_API_KEY=sk-... or claude-api-key
VISION_MODEL=gpt-4-vision-preview or claude-3-vision-sonnet
```

### 3. Migrate DB
```bash
alembic upgrade head
```

### 4. Use in Chat
```tsx
<ImageComposer conversationId={id} onImagesReady={setImages} />
```

---

## 📖 Key Features

### Image Upload
- Drag-and-drop, file picker, or paste from clipboard
- Format validation (JPEG, PNG, WebP, GIF)
- Size validation (max 10MB)
- Per-image error display
- Upload progress tracking

### Vision Q&A
- Ask questions about one or more images
- Free-form natural language responses
- Multi-image support with per-image association
- Request tracking in database

### Structured Extraction
- Extract receipt data (items, total, date, merchant)
- Extract form fields and values
- Extract table data (headers and rows)
- Custom schema support
- Automatic JSON parsing with retry

### Frontend Components
- **ImageComposer** - Input with preview thumbnails
- **visionApi** - TypeScript client for all operations
- Full accessibility and dark mode support

---

## 📊 Architecture

```
User uploads image(s)
    ↓
ImageComposer (drag-drop, picker, paste)
    ↓
uploadImages() → POST /chat/vision/upload
    ↓
S3 storage (user-scoped) + signed URL
    ↓
visionQA() or visionExtract() → multimodal LLM
    ↓
Answer or structured JSON returned
```

---

## 🔧 API Endpoints

### Upload Images
```
POST /chat/vision/upload
- Input: Multipart files, optional conversation_id
- Output: Image metadata with signed URLs
- Validates: Format, size, image validity
```

### Vision Q&A
```
POST /chat/vision/qa
- Input: image_ids, question, conversation_id
- Output: LLM-generated answer
- Process: Retrieves images, calls multimodal LLM
```

### Structured Extraction
```
POST /chat/vision/extract
- Input: image_ids, extraction_type, custom_schema
- Output: Parsed JSON matching schema
- Types: receipt, form, table, custom
```

### Status & Management
```
GET /chat/vision/{request_id}      - Get request status
DELETE /chat/vision/images/{id}    - Delete image
```

---

## 💻 Frontend Usage

### Component
```tsx
import { ImageComposer } from "@/components/ImageComposer";

<ImageComposer
  conversationId={id}
  mode="qa"  // or "extract"
  onModeChange={(m) => setMode(m)}
  onImagesReady={(images) => setImages(images)}
/>
```

### API Client
```typescript
import {
  uploadImages,
  visionQA,
  visionExtract,
  validateImageFile,
} from "@/lib/visionApi";

// Validate before upload
const { valid, error } = validateImageFile(file);

// Upload
const images = await uploadImages([file], conversationId);

// Q&A
const answer = await visionQA(imageIds, question);

// Extract
const data = await visionExtract(imageIds, "receipt");
```

---

## 🎨 Design System

All components follow Module 1 design tokens:
- **Colors:** Accent, ink, canvas, danger, success
- **Spacing:** Consistent padding and gaps
- **Typography:** Body, meta, font weights
- **Dark Mode:** Full support
- **Accessibility:** ARIA, keyboard navigation

---

## 🔐 Security

✅ User-scoped S3 storage (`users/{user_id}/...`)  
✅ Signed URLs with 24-hour expiry  
✅ Per-request authentication  
✅ Image ownership verification  
✅ File type and size validation (frontend + backend)  
✅ No public URLs  

---

## 📈 Performance

| Operation | Time |
|-----------|------|
| Image upload | 2-5s |
| Vision Q&A | 5-15s |
| Extraction | 8-20s |

Depends on file size, LLM model, and network latency.

---

## 🐛 Troubleshooting

**Images won't upload?**
- Check S3 credentials
- Verify file format (JPEG, PNG, WebP, GIF)
- Ensure file size < 10MB

**Vision LLM error?**
- Verify API key is valid
- Check API quota/credits
- Confirm model name is correct

**Extraction returns invalid JSON?**
- Automatically retries once
- Try simpler extraction type
- Check image has extractable content

---

## 📁 Files Created

**Backend:**
- `models.py` - VisionImage, VisionRequest models
- `config.py` - Vision settings
- `schemas_vision.py` - API schemas
- `routers/vision.py` - 5 endpoints
- `services/s3_storage.py` - S3 management
- `services/vision_llm.py` - Multimodal LLM service

**Frontend:**
- `lib/visionApi.ts` - API client (8 functions)
- `components/ImageComposer.tsx` - Input component

---

## ✅ Checklist

Before deploying:
- [ ] S3 bucket created and credentials configured
- [ ] Vision API key obtained and set
- [ ] Database migration run
- [ ] Backend started and endpoints accessible
- [ ] Frontend components integrated
- [ ] Test image upload flow
- [ ] Test Q&A with image
- [ ] Test extraction
- [ ] Error handling verified
- [ ] Dark mode tested
- [ ] Mobile responsiveness checked

---

## 🚀 Next Steps

1. **Setup S3** - AWS, MinIO, DigitalOcean Spaces
2. **Get Vision API Key** - OpenAI or Anthropic
3. **Configure .env** - S3 and API settings
4. **Run Migration** - Creates vision tables
5. **Integrate ImageComposer** - Add to chat UI
6. **Test Flows** - Upload, Q&A, extraction
7. **Deploy** - To production

---

## 📞 Support

- **Quick Start:** VISION_QUICK_START.md
- **Full Docs:** VISION_MODULE_COMPLETE.md
- **Code:** See inline comments in services and routers
- **Issues:** Check troubleshooting section

---

## 🎉 Ready to See!

You have everything you need to:
✅ Upload images (drag-drop, picker, paste)  
✅ Ask questions about images  
✅ Extract structured data from documents  
✅ Store and manage images securely  
✅ Display results in your chat UI  

**Let's build amazing vision experiences!** 🚀

---

*Implementation: August 14, 2024*  
*Version: 1.0.0*  
*Status: Production Ready*
