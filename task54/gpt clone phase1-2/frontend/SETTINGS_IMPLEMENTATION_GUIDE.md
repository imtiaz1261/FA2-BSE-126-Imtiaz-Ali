# Settings Panel & Model Selector Implementation Guide

## Overview

This guide explains the complete implementation of the Settings Panel, Model Selector, and Usage Meter components for the AI chat web app.

## Components

### 1. ModelSelector
**File:** `src/components/ModelSelector.tsx`

A dropdown component for selecting LLM models per conversation.

**Features:**
- Shows available models with descriptions
- Keyboard navigable (arrow keys, Enter, Escape)
- Selection persists per-conversation on the backend
- Displays active model in collapsed state

**Usage:**
```tsx
import { ModelSelector } from "@/components/ModelSelector";

<ModelSelector
  conversationId={conversationId}
  currentModelId={selectedModelId}
  onModelSelect={(modelId) => console.log(modelId)}
/>
```

**Props:**
- `conversationId` (string, required): Current conversation ID
- `currentModelId` (string, optional): Currently selected model ID
- `onModelSelect` (function, optional): Callback when model is selected

### 2. SettingsPanel
**File:** `src/components/SettingsPanel.tsx`

A modal with tabbed interface for user settings.

**Tabs:**
1. **General** - Theme, font size, language
2. **Personalization** - Custom instructions for the assistant
3. **Data Controls** - Export, clear conversations, delete account

**Usage:**
```tsx
import { SettingsPanel } from "@/components/SettingsPanel";
import { useState } from "react";

const [settingsOpen, setSettingsOpen] = useState(false);

<SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
```

### 3. Tab Components

#### GeneralTab
**File:** `src/components/settings/GeneralTab.tsx`

Settings for theme, font size, and language.

- **Theme:** Light, Dark, System
- **Font Size:** Small, Medium, Large
- **Language:** English, Español, Français, Deutsch, 日本語, 中文

#### PersonalizationTab
**File:** `src/components/settings/PersonalizationTab.tsx`

Free-text fields for customizing assistant behavior:
- "What should the assistant know about you?" - Shared as system context
- "How should it respond?" - Style, tone, verbosity preferences

#### DataControlsTab
**File:** `src/components/settings/DataControlsTab.tsx`

Data management operations:
- **Export Data** - Async job, email with download link
- **Clear Conversations** - Requires typed confirmation ("I understand")
- **Delete Account** - Requires email confirmation and password

### 4. UsageMeter
**File:** `src/components/UsageMeter.tsx`

Shows daily message usage for free-tier users.

**Features:**
- Color-coded progress bar (green → yellow → red)
- Shows remaining messages
- Optional warning messages
- Compact or full display mode

**Usage:**
```tsx
import { UsageMeter } from "@/components/UsageMeter";

// Compact (inline)
<UsageMeter compact={true} />

// Full display
<UsageMeter compact={false} showLabel={true} />
```

## State Management

### Zustand Store: `useSettingsStore`

Manages all settings state and API calls.

**File:** `src/store/settingsStore.ts`

**State:**
```typescript
interface SettingsState {
  // Preferences
  preferences: SettingsPreferences | null;
  isLoadingPreferences: boolean;
  preferencesError: string | null;

  // Models
  availableModels: AvailableModel[] | null;
  selectedModelId: string | null;
  isLoadingModels: boolean;
  modelsError: string | null;

  // Usage
  usage: UsageResponse | null;
  isLoadingUsage: boolean;
  usageError: string | null;
}
```

**Actions:**
```typescript
// Fetch and update
fetchPreferences()
updatePreferences(prefs)
setTheme(theme)
setFontSize(size)
setLanguage(lang)
setAssistantContext(context)
setResponsePreferences(prefs)

// Models
fetchModels()
selectModel(conversationId, modelId)
setSelectedModelId(modelId)

// Usage
fetchUsage()

// Data operations
initiateDataExport()
```

**Usage:**
```tsx
import { useSettingsStore } from "@/store/settingsStore";

const { 
  preferences, 
  updatePreferences, 
  availableModels,
  selectedModelId 
} = useSettingsStore();
```

## API Client

### `src/lib/settingsApi.ts`

Handles all API communication with backend settings endpoints.

**Endpoints:**
- `GET /settings` - Get user settings
- `PATCH /settings` - Update settings
- `GET /models` - List available models
- `GET /conversations/{id}/model` - Get conversation's selected model
- `PATCH /conversations/{id}/model` - Set conversation's model
- `GET /usage` - Get daily message usage
- `POST /settings/export` - Initiate data export
- `DELETE /conversations` - Clear all conversations
- `DELETE /settings/account` - Delete user account

## Backend Integration

### Database Models

**Tables:**
- `user_settings` - JSON column for flexible preferences
- `available_models` - LLM model metadata
- `conversation_models` - Per-conversation model selection
- `message_usage` - Daily message count tracking
- `data_export_jobs` - Async export job tracking

### API Routes

**File:** `backend/app/routers/settings.py`

**Key Features:**
- Settings stored as JSON (no schema migration needed)
- Keyset pagination for models
- Async data export with email link
- Confirmation-required destructive operations
- Rate limiting via message usage tracking

## Integration Examples

See `src/components/examples/SettingsIntegration.tsx` for complete examples:

### Chat Header with Model Selector
```tsx
<ChatHeaderWithModelSelector />
```

### Settings Button
```tsx
<SettingsButton />
```

### Usage Panel
```tsx
<UsagePanel />
```

### Full App Layout
```tsx
<AppLayout />
```

## Design Tokens

All components use design tokens from Module 1:

**Colors:**
- Primary: `text-accent-600 dark:text-accent-400`
- Text: `text-ink dark:text-ink-dark`
- Secondary: `text-ink/60 dark:text-ink-dark/60`
- Backgrounds: `bg-canvas dark:bg-canvas-dark`
- Borders: `border-border dark:border-border-dark`
- Danger: `text-danger` (red)

**Spacing:**
- Padding: `p-2.5`, `px-3`, `py-2`
- Gaps: `gap-2`, `gap-3`, `gap-4`

**Typography:**
- `text-body` - Regular text
- `text-meta` - Small text
- `font-medium` - Emphasized text
- `font-semibold` - Headers

**Borders & Shadows:**
- `rounded-control` - Consistent border radius
- `border-border` - Hairline border
- `shadow-modal` - Modal elevation

## Usage Meter Details

### Free Tier Limit
- Default: 20 messages per day
- Configurable in `backend/app/routers/settings.py` (FREE_TIER_MESSAGE_LIMIT)

### Color Coding
- <70%: Green (all good)
- 70-89%: Yellow (warning)
- 90%+: Red (critical)

### Auto-Refresh
- Fetches usage on component mount
- Refreshes every 5 minutes
- Manual refresh via `fetchUsage()`

## Flow Diagrams

### Model Selection Flow
```
User opens conversation
    ↓
LoadConversation called
    ↓
Fetch conversation model from backend
    ↓
ModelSelector shows current model
    ↓
User clicks dropdown
    ↓
List of available models displayed
    ↓
User selects model
    ↓
API: PATCH /conversations/{id}/model
    ↓
Backend: Update ConversationModel record
    ↓
Store updated (selectedModelId)
    ↓
Component re-renders with new model
```

### Settings Update Flow
```
User opens SettingsPanel
    ↓
fetchPreferences() called
    ↓
API: GET /settings
    ↓
Preferences populate form fields
    ↓
User modifies preference
    ↓
onChange handler updates local state
    ↓
User clicks Save
    ↓
API: PATCH /settings with updated preferences
    ↓
Backend: Update UserSettings.preferences JSON
    ↓
Store updated with new preferences
    ↓
All components subscribe to settings reactively update
```

### Data Export Flow
```
User clicks "Export Data"
    ↓
API: POST /settings/export
    ↓
Backend: Create DataExportJob with status "pending"
    ↓
Return job_id immediately
    ↓
Backend (async): Generate JSON export
    ↓
Create signed download URL
    ↓
Send email with link to user
    ↓
Update job status to "completed"
    ↓
User clicks link in email
    ↓
Download JSON file (expires in 7 days)
```

## Testing Checklist

- [ ] ModelSelector displays available models
- [ ] ModelSelector keyboard navigation works (arrows, Enter, Escape)
- [ ] Model selection persists after page reload
- [ ] SettingsPanel tabs switch correctly
- [ ] General tab: theme selector updates appearance
- [ ] General tab: font size selector works
- [ ] General tab: language selector works
- [ ] Personalization tab: can edit assistant context
- [ ] Personalization tab: can edit response preferences
- [ ] Data Controls: export initiates job
- [ ] Data Controls: clear requires correct confirmation
- [ ] Data Controls: delete requires email + password
- [ ] UsageMeter shows correct usage count
- [ ] UsageMeter changes color appropriately
- [ ] UsageMeter updates automatically
- [ ] Settings persist across sessions
- [ ] All components work in dark mode
- [ ] All components are accessible (keyboard, screen reader)

## Troubleshooting

### ModelSelector not showing models
- Check: `fetchModels()` called on mount?
- Check: Backend `/models` endpoint responding?
- Check: Console for API errors?

### Settings not persisting
- Check: `updatePreferences()` called after changes?
- Check: Network request completing?
- Check: Backend `/settings` PATCH endpoint working?

### UsageMeter always shows 0
- Check: `fetchUsage()` called?
- Check: Backend tracking message usage?
- Check: DateUT timezone correct?

### SettingsPanel modals not appearing
- Check: Modal component imported correctly?
- Check: `open` prop set to true?
- Check: CSS not hiding with `display: none`?

## Future Enhancements

1. **Theme Sync** - Apply theme changes in real-time across app
2. **Settings Sync** - Multi-device settings synchronization
3. **Model Comparison** - Side-by-side comparison of model outputs
4. **Usage Analytics** - Detailed breakdown of model usage
5. **Custom System Prompts** - Advanced prompt engineering interface
6. **Settings Presets** - Save/load setting combinations
7. **Accessibility** - Screen reader optimization for all components
8. **Mobile** - Responsive design improvements for small screens

## Performance Considerations

- Settings fetched once on app boot, cached in Zustand
- Models fetched once on app boot, cached in Zustand
- Usage refreshed every 5 minutes (configurable)
- All API calls use proper error handling
- Optimistic updates for better UX
- Debounced text input in personalization tab

## Security Considerations

- Deletion requires password confirmation
- Export URL is signed and expires in 7 days
- Settings stored server-side (not localStorage)
- No sensitive data in browser storage
- All API calls authenticated via JWT

---

**Last Updated:** August 2024
**Version:** 1.0.0
