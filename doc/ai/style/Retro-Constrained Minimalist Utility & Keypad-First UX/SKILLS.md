# TECHNICAL SKILLS & UI IMPLEMENTATION SPECIFICATIONS

This document outlines the core technical skills, UI state machine patterns, rendering strategies, and input handlers required to build and extend **LuaS30-IDE** based on the **Retro-Constrained Minimalist Utility & Keypad-First UX** paradigm (`emir/claude-s40`).

---

## 1. CORE TECHNICAL SKILLS

### A. Keypad Event Handling & State Machine
* **Key Event Mapping**: Intercept low-level keycodes and translate them deterministically into IDE commands.
* **Modal Context Switching**: Handle nested modal states (e.g., Code View -> Options Menu -> File Dialog -> Confirmation Dialog) without losing parent view buffer positions.

```lua
-- Key Code Constants for S40 / Keypad Environments
KEYS = {
    LSK       = -6,  -- Left Softkey
    RSK       = -7,  -- Right Softkey
    UP        = -1,
    DOWN      = -2,
    LEFT      = -3,
    RIGHT     = -4,
    CENTER    = -5,  -- D-Pad Center / Select
    NUM_0     = 48,
    NUM_1     = 49,
    NUM_7     = 55,
    NUM_9     = 57,
    STAR      = 42,
    HASH      = 35
}

function handleKeyPress(keyCode)
    if keyCode == KEYS.LSK then
        openContextMenu()
    elseif keyCode == KEYS.RSK then
        navigateBackOrCloseModal()
    elseif keyCode == KEYS.UP then
        moveCursorUp()
    elseif keyCode == KEYS.DOWN then
        moveCursorDown()
    elseif keyCode == KEYS.NUM_7 then
        toggleReadingViewMode() -- Claude-S40 style reading mode
    elseif keyCode == KEYS.NUM_9 then
        cycleFontSize()        -- Small / Medium / Large font
    end
end
```

---

## 2. MEMORY-CONSTRAINED RENDERER SKILLS

### A. Virtual Screen Buffer & Line Rendering
* **Viewport Clipping**: Render only the visible buffer lines on screen ($128\times160$ or $240\times320$). Never keep full DOM or scene trees in RAM.
* **Pagination & Hanging Indents**: Handle long lines by splitting them into whole visible lines without breaking Lua keywords across line boundaries.

```lua
-- Viewport Renderer Pattern
function renderEditorBuffer(gfx, lines, startLine, maxVisibleLines, fontHeight)
    local y = 16 -- Height offset for top status header
    for i = startLine, math.min(#lines, startLine + maxVisibleLines - 1) do
        local lineText = lines[i]
        local isCurrentLine = (i == currentCursorLine)
        
        -- High contrast highlight for focused editor line
        if isCurrentLine then
            gfx:setColor(0x33, 0x33, 0x33) -- Dark grey background
            gfx:fillRect(0, y, SCREEN_WIDTH, fontHeight)
            gfx:setColor(0xFF, 0xFF, 0xFF) -- White text
        else
            gfx:setColor(0x00, 0x00, 0x00) -- Black background
            gfx:setColor(0xAA, 0xAA, 0xAA) -- Light grey text
        end
        
        -- Render line gutter number and line content
        local lineGutter = string.format("%03d| ", i)
        gfx:drawString(lineGutter .. lineText, 2, y)
        
        y = y + fontHeight
    end
end
```

---

## 3. UI COMPONENT BLUEPRINTS

### 1. Dual-Softkey Footer Component
Must strictly maintain LSK and RSK text actions on the bottom line of the screen.

```
+------------------------------------+
| 001| local x = 10                  |
| 002| function run()                |
| 003|>  print(x)                    |
| 004| end                           |
+------------------------------------+
|[Options]                    [Run]  |  <-- Fixed Softkey Footer
+------------------------------------+
```

### 2. Fast Keypad Action Menu (Claude-S40 Style)
Context menus must assign numeric shortcuts (1-9) to each action for instant trigger without scrolling.

```
+------------------------------------+
| MENU OPTIONS                       |
|+----------------------------------+|
|| 1. Save File                     ||
|| 2. Toggle Word Wrap              ||
|| 3. Font Size: [Med]              ||
|| 4. Execute Script                ||
|| 5. Exit IDE                      ||
|+----------------------------------+|
|[Select]                   [Cancel] |
+------------------------------------+
```

### 3. Compact Syntax Highlighter
Single-pass string parsing designed to minimize CPU ticks:

* **Lua Keywords** (`local`, `function`, `if`, `then`, `else`, `end`): High-contrast primary color (e.g., `#FFCC00` Amber or `#00FF00` Matrix Green).
* **Strings & Comments**: Muted grey color (`#888888`).
* **Identifiers/Vars**: Standard text color (`#FFFFFF`).

---

## 4. CODEGEN & CONTRIBUTOR CHECKLIST

When writing Lua code or UI modules for **LuaS30-IDE**:

1. **[ ] Touch Independence**: Did you ensure every menu item and editor feature is accessible via keypad/D-Pad?
2. **[ ] Memory Safety**: Are all render loops operating on dynamic view buffers rather than full files?
3. **[ ] Font Resiliency**: Does the UI layout adapt cleanly when switching between font sizes (Small, Medium, Large)?
4. **[ ] High Contrast**: Are background and foreground colors readable on low-cost TFT/LCD feature phone screens?